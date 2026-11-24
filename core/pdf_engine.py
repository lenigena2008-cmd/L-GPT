"""Moteur RAG local de L-GPT, adapté du prototype pdfreader.py."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Callable
from threading import Event

import numpy as np
import ollama
import pymupdf

EMBEDDING_MODEL = "nomic-embed-text"
CHUNK_SIZE = 1000
OVERLAP = 150
TOP_K = 5
MAX_CONTEXT = 10000
MAX_TOKENS = -1  # Ollama : génération sans limite artificielle de tokens
CONTEXT_WINDOW = 8192  # fenêtre standard du chat ; indépendante de la limite de génération
SUMMARY_CONTEXT_WINDOW = 16384  # synthèses longues : fenêtre augmentée, avec repli si la mémoire manque
SYSTEM_PROMPT = """Tu es L-GPT, un assistant spécialisé dans l'analyse de documents PDF.
Réponds en français, clairement et de manière pédagogique. Utilise en priorité les extraits fournis.
N'invente pas de contenu et ne prétends pas avoir consulté des pages qui ne sont pas fournies.
Si les extraits ne suffisent pas, dis-le explicitement. Tu peux apporter une explication générale, en la distinguant du contenu du PDF.
Cite les numéros de page lorsque c'est possible.
N'utilise JAMAIS de LaTeX ni de commandes LaTeX (pas de délimiteurs mathématiques ni de commandes de mise en forme).
Écris toutes les formules en texte simple lisible : fractions sous la forme (a)/(b), puissances avec ^ (x^2), multiplications avec ×, racines avec √(...), indices en texte simple (H2O)."""


def _notify(callback: Callable[[str], None] | None, message: str) -> None:
    if callback:
        callback(message)


def _fingerprint(pdf_path: Path) -> str:
    stat = pdf_path.stat()
    raw = f"{pdf_path.resolve()}{stat.st_size}{stat.st_mtime_ns}{EMBEDDING_MODEL}{CHUNK_SIZE}{OVERLAP}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _index_path(pdf_path: Path) -> Path:
    return pdf_path.with_name(pdf_path.name + ".rag.json")


def _split_text(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    parts, start = [], 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        part = text[start:end].strip()
        if part:
            parts.append(part)
        if end >= len(text):
            break
        start = end - OVERLAP
    return parts


def _embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    response = ollama.embed(model=EMBEDDING_MODEL, input=texts)
    return response["embeddings"]


def build_index(pdf_file: str | Path, progress: Callable[[str], None] | None = None):
    path = Path(pdf_file)
    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise ValueError("Le fichier sélectionné n'est pas un PDF valide.")

    index_file = _index_path(path)
    fingerprint = _fingerprint(path)
    if index_file.is_file():
        try:
            saved = json.loads(index_file.read_text(encoding="utf-8"))
            if (saved.get("fingerprint") == fingerprint
                    and saved.get("embedding_model") == EMBEDDING_MODEL
                    and saved.get("chunk_size") == CHUNK_SIZE
                    and saved.get("overlap") == OVERLAP
                    and len(saved.get("chunks", [])) == len(saved.get("embeddings", []))):
                _notify(progress, f"Index existant chargé · {len(saved['chunks'])} passages")
                return saved["chunks"], saved["embeddings"]
        except (OSError, ValueError, KeyError, TypeError):
            pass

    _notify(progress, "Lecture du PDF…")
    pages = []
    with pymupdf.open(path) as document:
        for number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append({"page": number, "text": text})
    if not pages:
        raise ValueError("Aucun texte n'a été trouvé dans ce PDF. S'il s'agit d'un scan, un OCR sera nécessaire.")

    chunks = []
    for page in pages:
        for number, part in enumerate(_split_text(page["text"]), start=1):
            chunks.append({"page": page["page"], "chunk": number, "text": part})
    if not chunks:
        raise ValueError("Aucun passage exploitable n'a été extrait du PDF.")

    _notify(progress, f"Calcul des embeddings · {len(chunks)} passages…")
    embeddings = _embed([chunk["text"] for chunk in chunks])
    data = {
        "fingerprint": fingerprint,
        "embedding_model": EMBEDDING_MODEL,
        "chunk_size": CHUNK_SIZE,
        "overlap": OVERLAP,
        "chunks": chunks,
        "embeddings": embeddings,
    }
    index_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    _notify(progress, f"Document indexé · {len(chunks)} passages")
    return chunks, embeddings


def retrieve(question: str, chunks: list[dict], embeddings: list[list[float]]) -> list[dict]:
    result = ollama.embed(model=EMBEDDING_MODEL, input=question)
    query_vector = np.asarray(result["embeddings"][0], dtype=np.float32)
    matrix = np.asarray(embeddings, dtype=np.float32)
    query_norm = np.linalg.norm(query_vector)
    norms = np.linalg.norm(matrix, axis=1)
    if query_norm == 0:
        return []
    scores = np.dot(matrix, query_vector) / (norms * query_norm + 1e-10)
    best = np.argsort(scores)[::-1][:TOP_K]
    return [
        {"page": chunks[int(i)]["page"], "chunk": chunks[int(i)]["chunk"],
         "source": chunks[int(i)].get("source", "PDF"), "text": chunks[int(i)]["text"], "score": float(scores[i])}
        for i in best
    ]


def answer(question: str, chunks: list[dict], embeddings: list[list[float]],
           history: list[dict], model: str, on_token: Callable[[str], None] | None = None,
           stop_event: Event | None = None, system_prompt: str | None = None,
           runtime_options: dict | None = None, memory_context: str = ""):
    passages = retrieve(question, chunks, embeddings)
    if stop_event and stop_event.is_set():
        raise InterruptedError("Génération arrêtée par l'utilisateur.")
    if not passages:
        raise RuntimeError("Aucun passage pertinent n'a été retrouvé.")

    context_parts, total = [], 0
    for passage in passages:
        part = f"\n--- DOCUMENT {passage.get('source', 'PDF')} / PAGE {passage['page']} / PASSAGE {passage['chunk']} ---\n{passage['text']}\n"
        remaining = MAX_CONTEXT - total
        if remaining <= 0:
            break
        context_parts.append(part[:remaining])
        total += min(len(part), remaining)

    base_prompt = system_prompt or SYSTEM_PROMPT
    if memory_context and system_prompt != DOCUMENT_ONLY_PROMPT:
        base_prompt += "\n\nCONTEXTE MÉMORISÉ PERTINENT (à utiliser seulement si utile, sans le présenter comme une source documentaire) :\n" + memory_context
    messages = [{"role": "system", "content": base_prompt}]
    messages.extend(history[-4:])
    messages.append({"role": "user", "content": "Voici les passages retrouvés dans le PDF :\n"
                     + "\n".join(context_parts) + "\nQuestion :\n" + question})

    stream = ollama.chat(
        model=model,
        messages=messages,
        stream=True,
        think=False,
        options={"num_predict": int((runtime_options or {}).get("num_predict", MAX_TOKENS)), "num_ctx": int((runtime_options or {}).get("num_ctx", CONTEXT_WINDOW))},
    )
    response_parts = []
    iterator = iter(stream)
    try:
        for item in iterator:
            if stop_event and stop_event.is_set():
                close = getattr(iterator, "close", None)
                if close:
                    close()
                raise InterruptedError("Génération arrêtée par l'utilisateur.")
            token = item.message.content or ""
            if token:
                response_parts.append(token)
                if on_token:
                    on_token(token)
    finally:
        if stop_event and stop_event.is_set():
            close = getattr(iterator, "close", None)
            if close:
                close()
    response = "".join(response_parts).strip()
    new_history = history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": response},
    ]
    return response, passages, new_history[-4:]




GENERAL_SYSTEM_PROMPT = """Tu es L-GPT, un assistant IA local polyvalent dont la mission prioritaire est d'aider à comprendre et synthétiser les cours PDF, tout en sachant répondre aux questions générales.
Réponds en français sauf demande contraire. Sois précis, pédagogique, structuré et honnête sur tes limites. N'invente ni sources ni vérifications.
N'utilise JAMAIS de LaTeX. Écris les formules en texte simple : (a)/(b), x^2, ×, √(...), H2O.
Distingue clairement les faits établis, les hypothèses et les incertitudes."""

DOCUMENT_ONLY_PROMPT = """Tu es L-GPT en mode DOCUMENT. Réponds exclusivement à partir des extraits PDF fournis.
N'utilise aucune connaissance extérieure pour compléter la réponse. Si les extraits ne contiennent pas la réponse, dis clairement que l'information n'est pas présente dans les documents disponibles.
Cite les fichiers et numéros de page quand ils sont fournis. Réponds en français.
N'utilise jamais de LaTeX ; écris les formules en texte simple."""

COMBINED_PROMPT = """Tu es L-GPT en mode DOCUMENTS + CONNAISSANCES.
Utilise les extraits PDF lorsqu'ils sont pertinents, puis complète avec tes connaissances générales uniquement lorsque cela apporte une vraie valeur.
Distingue explicitement les deux provenances avec les sous-titres « D'après les documents » et « Complément de connaissances » lorsque les deux sont utilisées.
Ne présente jamais une connaissance générale comme si elle figurait dans le PDF. Si les documents contredisent une connaissance générale fiable, signale la différence sans effacer le contenu du cours.
Cite les noms de fichiers et pages disponibles. Si les extraits ne répondent pas à la question, indique-le avant le complément général.
Réponds en français sauf demande contraire. N'utilise jamais de LaTeX ; écris les formules en texte simple : (a)/(b), x^2, ×, √(...), H2O."""


def _classify_question_intent(question: str) -> tuple[bool, bool]:
    """Retourne (demande explicite de document, demande d'explication/complément)."""
    q = question.lower()
    doc_patterns = (
        r"\b(selon|d'apr[eè]s|dans|à partir de|sur base de) (?:le |la |les |mon |mes )?(?:pdf|document|cours|fichier|chapitre)\b",
        r"\b(mon cours|mes notes|le document|les documents|ce pdf|cette synth[eè]se|la page \d+)\b",
        r"\b(r[eé]sume|r[eé]sumer|synth[eè]se|extrais|retrouve dans)\b",
    )
    explicit = any(re.search(pattern, q) for pattern in doc_patterns)
    enrich = bool(re.search(r"\b(explique|approfondis|compl[eè]te|donne des exemples|compare|pourquoi|comment fonctionne|mise en contexte)\b", q))
    return explicit, enrich


def select_answer_source(question: str, chunks: list[dict], embeddings: list[list[float]]) -> dict:
    """Sélectionne une source en combinant intention linguistique et pertinence RAG.

    Les seuils sont volontairement conservateurs : un PDF simplement proche du sujet
    ne doit pas détourner une question générale vers le mode documentaire.
    """
    has_docs = bool(chunks) and bool(embeddings)
    explicit_doc, wants_enrichment = _classify_question_intent(question)
    if not has_docs:
        return {"mode": "Connaissances", "reason": "Aucun PDF indexé : réponse à partir des connaissances du modèle.", "score": None}

    passages = retrieve(question, chunks, embeddings)
    scores = sorted((float(x.get("score", 0.0)) for x in passages), reverse=True)
    best = scores[0] if scores else 0.0
    second = scores[1] if len(scores) > 1 else 0.0
    # Un écart net entre les deux meilleurs scores renforce la confiance, sans
    # constituer à lui seul une preuve de pertinence.
    strong_match = best >= 0.56
    plausible_match = best >= 0.43

    if explicit_doc:
        if wants_enrichment and plausible_match:
            mode = "Documents + connaissances"
            reason = "La question vise le cours et demande aussi une explication ou un complément."
        else:
            mode = "Document"
            reason = "La formulation demande explicitement une réponse fondée sur les documents."
    elif strong_match and wants_enrichment:
        mode = "Documents + connaissances"
        reason = "Les passages retrouvés sont pertinents et la question appelle un approfondissement."
    elif strong_match and best - second >= 0.025:
        mode = "Documents + connaissances"
        reason = "Les documents contiennent des passages fortement liés à la question ; ils seront croisés avec les connaissances générales."
    elif plausible_match and re.search(r"\b(cours|chapitre|notion|mati[eè]re|exercice|professeur|examen)\b", question, re.I):
        mode = "Documents + connaissances"
        reason = "Le sujet semble lié au cours et des passages pertinents ont été retrouvés."
    else:
        mode = "Connaissances"
        reason = "Les documents ne présentent pas de correspondance suffisamment fiable avec cette question générale."
    return {"mode": mode, "reason": reason, "score": best, "passages": passages}


def _stream_general(question, history, model, on_token=None, stop_event=None, system_prompt=GENERAL_SYSTEM_PROMPT, runtime_options=None, memory_context=""):
    if memory_context:
        system_prompt += "\n\nCONTEXTE MÉMORISÉ PERTINENT (à utiliser seulement si utile) :\n" + memory_context
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-4:])
    messages.append({"role": "user", "content": question})
    stream = ollama.chat(model=model, messages=messages, stream=True, think=False,
                         options={"num_predict": int((runtime_options or {}).get("num_predict", MAX_TOKENS)), "num_ctx": int((runtime_options or {}).get("num_ctx", CONTEXT_WINDOW))})
    parts=[]; iterator=iter(stream)
    try:
        for item in iterator:
            if stop_event and stop_event.is_set():
                close=getattr(iterator,"close",None)
                if close: close()
                raise InterruptedError("Génération arrêtée par l'utilisateur.")
            token=item.message.content or ""
            if token:
                parts.append(token)
                if on_token: on_token(token)
    finally:
        if stop_event and stop_event.is_set():
            close=getattr(iterator,"close",None)
            if close: close()
    response=_latex_to_plain("".join(parts)).strip()
    new_history=history+[{"role":"user","content":question},{"role":"assistant","content":response}]
    return response, [], new_history[-4:]


def answer_chat(question, chunks, embeddings, history, model, mode="Intelligent", on_token=None, stop_event=None, runtime_options=None, memory_context=""):
    """Modes : Document, Connaissances et Intelligent avec sélection raisonnée des sources."""
    has_docs = bool(chunks) and bool(embeddings)
    selected = mode
    decision_reason = ""
    passages = []

    if mode == "Intelligent":
        decision = select_answer_source(question, chunks, embeddings)
        selected = decision["mode"]
        decision_reason = decision["reason"]
        passages = decision.get("passages", [])

    if selected == "Connaissances":
        response, sources, new_history = _stream_general(question, history, model, on_token, stop_event, runtime_options=runtime_options, memory_context=memory_context)
        label = "Connaissances"
        if mode == "Intelligent" and decision_reason:
            label += f" · {decision_reason}"
        return response, sources, new_history, label

    if not has_docs:
        raise RuntimeError("Le mode Document nécessite au moins un PDF importé et indexé. Importe un document ou choisis Connaissances / Intelligent.")

    if selected == "Document":
        response, sources, new_history = answer(
            question, chunks, embeddings, history, model, on_token, stop_event,
            system_prompt=DOCUMENT_ONLY_PROMPT, runtime_options=runtime_options)
        label = "Documents"
        if mode == "Intelligent" and decision_reason:
            label += f" · {decision_reason}"
        return response, sources, new_history, label

    response, sources, new_history = answer(
        question, chunks, embeddings, history, model, on_token, stop_event,
        system_prompt=COMBINED_PROMPT, runtime_options=runtime_options, memory_context=memory_context)
    label = "Documents + connaissances"
    if mode == "Intelligent" and decision_reason:
        label += f" · {decision_reason}"
    return response, sources, new_history, label

def build_indexes(pdf_files: list[str | Path], progress: Callable[[str], None] | None = None):
    """Indexe plusieurs PDF et fusionne leurs passages dans une base commune."""
    all_chunks, all_embeddings = [], []
    for position, file in enumerate(pdf_files, start=1):
        path = Path(file)
        _notify(progress, f"Document {position}/{len(pdf_files)} · {path.name}")
        chunks, embeddings = build_index(path, progress)
        for chunk in chunks:
            all_chunks.append({**chunk, "source": path.name})
        all_embeddings.extend(embeddings)
    if not all_chunks:
        raise ValueError("Aucun texte exploitable n'a été trouvé dans les PDF sélectionnés.")
    return all_chunks, all_embeddings



def _latex_to_plain(text: str) -> str:
    """Nettoie le LaTeX résiduel et convertit les expressions courantes en texte lisible."""
    if not text:
        return ""

    # Délimiteurs mathématiques et commandes de structure.
    text = text.replace(r"\[", "").replace(r"\]", "")
    text = text.replace(r"\(", "").replace(r"\)", "")
    text = text.replace("$$", "").replace("$", "")
    text = re.sub(r"\\(?:begin|end)\s*\{[^{}]*\}", " ", text)
    text = text.replace(r"\\", " ")  # sauts de ligne LaTeX (\)
    text = re.sub(r"\\(?:displaystyle|textstyle|scriptstyle|limits|nonumber|notag)\b", "", text)
    text = re.sub(r"\\(?:left|right)\b", "", text)
    text = re.sub(r"\\(?:,|;|:|!|quad|qquad|enspace|thinspace)", " ", text)

    # Convertit les groupes { ... } en tenant compte des accolades imbriquées.
    def take_group(value: str, pos: int):
        while pos < len(value) and value[pos].isspace():
            pos += 1
        if pos >= len(value) or value[pos] != "{":
            return None, pos
        depth, i = 1, pos + 1
        while i < len(value) and depth:
            if value[i] == "{": depth += 1
            elif value[i] == "}": depth -= 1
            i += 1
        if depth:
            return None, pos
        return value[pos + 1:i - 1], i

    # Racines d’ordre n : \sqrt[n]{x} devient √[n](x).
    text = re.sub(r"\\sqrt\s*\[([^]]+)\]\s*\{([^{}]*)\}", r"√[\1](\2)", text)

    # Plusieurs passes permettent de traiter les fractions et racines imbriquées.
    for _ in range(12):
        old = text
        for command in (r"\\frac", r"\\dfrac", r"\\tfrac"):
            pattern = re.compile(command + r"\s*\{")
            while True:
                match = pattern.search(text)
                if not match:
                    break
                numerator, after_num = take_group(text, match.end() - 1)
                if numerator is None:
                    break
                denominator, after_den = take_group(text, after_num)
                if denominator is None:
                    break
                text = text[:match.start()] + f"({numerator})/({denominator})" + text[after_den:]
        for command, wrapper in ((r"\\sqrt", "√"), (r"\\text", ""), (r"\\textbf", ""),
                                 (r"\\textit", ""), (r"\\mathrm", ""), (r"\\mathbf", ""),
                                 (r"\\mathit", ""), (r"\\mathsf", ""), (r"\\mathtt", ""),
                                 (r"\\mathbb", ""), (r"\\mathcal", ""), (r"\\operatorname", ""),
                                 (r"\\ce", ""), (r"\\pu", ""), (r"\\overline", ""),
                                 (r"\\underline", ""), (r"\\hat", ""), (r"\\bar", ""),
                                 (r"\\vec", "")):
            pattern = re.compile(command + r"\s*\{")
            while True:
                match = pattern.search(text)
                if not match:
                    break
                content, after = take_group(text, match.end() - 1)
                if content is None:
                    break
                replacement = f"√({content})" if wrapper == "√" else content
                text = text[:match.start()] + replacement + text[after:]
        if text == old:
            break

    # Symboles mathématiques, grecques et opérateurs fréquents.
    replacements = {
        r"\times": "×", r"\cdot": "·", r"\div": "÷", r"\pm": "±",
        r"\leq": "≤", r"\le": "≤", r"\geq": "≥", r"\ge": "≥",
        r"\neq": "≠", r"\approx": "≈", r"\equiv": "≡", r"\infty": "∞",
        r"\pi": "π", r"\theta": "θ", r"\alpha": "α", r"\beta": "β",
        r"\gamma": "γ", r"\delta": "δ", r"\Delta": "Δ", r"\lambda": "λ",
        r"\mu": "μ", r"\sigma": "σ", r"\omega": "ω", r"\Omega": "Ω",
        r"\sum": "Σ", r"\prod": "Π", r"\int": "∫", r"\partial": "∂",
        r"\nabla": "∇", r"\rightarrow": "→", r"\to": "→",
        r"\Rightarrow": "⇒", r"\Leftrightarrow": "⇔", r"\degree": "°",
        r"\%": "%", r"\approx": "≈", r"\emptyset": "∅",
        r"\in": "∈", r"\notin": "∉", r"\subset": "⊂", r"\cup": "∪", r"\cap": "∩",
        r"\cdots": "…", r"\ldots": "…", r"\therefore": "∴",
        r"\_": "_", r"\{": "{", r"\}": "}", r"\&": "&",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)

    # Indices et exposants : x_{n+1} -> x_n+1 ; x^{2} -> x^2.
    text = re.sub(r"_\s*\{([^{}]*)\}", r"_\1", text)
    text = re.sub(r"\^\s*\{([^{}]*)\}", r"^\1", text)
    text = re.sub(r"\\(?:sin|cos|tan|ln|log|lim|max|min|exp)\b", lambda m: m.group(0)[1:], text)

    # Supprime les commandes restantes inconnues sans laisser leur syntaxe LaTeX.
    text = re.sub(r"\\[A-Za-z]+\*?", "", text)
    text = text.replace("{", "").replace("}", "")
    text = text.replace("&", " ")  # séparateurs d’alignement des environnements mathématiques
    text = re.sub(r"\\([_^])", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _summary_chat(model: str, messages: list[dict], stop_event: Event | None = None) -> str:
    """Génère une partie de synthèse avec la plus grande fenêtre raisonnable.

    num_predict=-1 désactive la limite artificielle de sortie. Si la mémoire
    disponible ne permet pas 16k de contexte, on réessaie avec 8k puis 4k.
    """
    last_error = None
    for context_size in (SUMMARY_CONTEXT_WINDOW, 8192, 4096):
        try:
            stream = ollama.chat(
                model=model,
                messages=messages,
                stream=True,
                think=False,
                options={"num_predict": -1, "num_ctx": context_size},
            )
            pieces = []
            iterator = iter(stream)
            try:
                for item in iterator:
                    if stop_event and stop_event.is_set():
                        close = getattr(iterator, "close", None)
                        if close:
                            close()
                        raise InterruptedError("Génération arrêtée par l'utilisateur.")
                    token = item.message.content or ""
                    if token:
                        pieces.append(token)
            finally:
                if stop_event and stop_event.is_set():
                    close = getattr(iterator, "close", None)
                    if close:
                        close()
            content = "".join(pieces).strip()
            if not content:
                raise RuntimeError("Le modèle a renvoyé une synthèse vide.")
            return content
        except Exception as exc:
            last_error = exc
            message = str(exc).lower()
            memory_error = any(term in message for term in (
                "out of memory", "memory", "cuda", "allocat", "buffer", "resource exhausted"
            ))
            if not memory_error or context_size == 4096:
                raise
    raise RuntimeError(f"Impossible de générer la synthèse : {last_error}")


def create_summary_pdf(pdf_files: list[str | Path], output_file: str | Path, model: str,
                       progress: Callable[[str], None] | None = None, stop_event: Event | None = None):
    """Produit une synthèse pédagogique PDF, en plusieurs étapes pour éviter les coupures."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from xml.sax.saxutils import escape

    system_prompt = (
        "Tu es un professeur qui crée des synthèses de cours fiables, complètes et pédagogiques en français. "
        "N'invente rien. Conserve les définitions, notions, formules, méthodes, exemples, démonstrations et distinctions importantes. "
        "Structure avec des titres et des listes. Ne termine jamais au milieu d'une phrase : achève toutes les phrases et sections. "
        "Si le contenu est long, sois dense mais ne supprime pas les notions essentielles. "
        "INTERDICTION ABSOLUE d'écrire en LaTeX ou d'utiliser des commandes LaTeX. "
        "Toutes les formules doivent être en texte simple lisible : fractions comme (a)/(b), puissances comme x^2, "
        "multiplication avec ×, racines comme √(...), indices en texte simple comme H2O. "
        "Ne mets jamais de formule entre $...$, \\(...\\) ou \\[...\\]."
    )
    merge_prompt = (
        "Tu es chargé de réunir plusieurs parties d'une synthèse de cours en un document unique. "
        "Conserve toutes les définitions, notions, formules, méthodes, exemples et distinctions importantes. "
        "Supprime uniquement les répétitions, organise avec des titres cohérents et n'invente rien. "
        "Rédige une synthèse complète et termine toutes les phrases et sections. "
        "INTERDICTION ABSOLUE d'utiliser du LaTeX ou des commandes comme \\frac, \\sqrt, \\text, \\begin et \\end : écris les formules en texte simple, par exemple (a)/(b), x^2, ×, √(...), H2O."
    )

    source_sections = []
    for index, file in enumerate(pdf_files, start=1):
        if stop_event and stop_event.is_set():
            raise InterruptedError("Génération arrêtée par l'utilisateur.")
        path = Path(file)
        _notify(progress, f"Lecture du document {index}/{len(pdf_files)} · {path.name}")
        with pymupdf.open(path) as doc:
            pages = [(n, page.get_text("text").strip()) for n, page in enumerate(doc, 1)]
        text = "\n".join(f"[Page {n}] {t}" for n, t in pages if t)
        if not text.strip():
            raise ValueError(f"Aucun texte détecté dans {path.name}. Les PDF scannés nécessitent un OCR.")
        source_sections.append((path.name, text))

    summaries = []
    for doc_index, (name, content) in enumerate(source_sections, start=1):
        # Des morceaux plus petits laissent davantage de place à la réponse dans la fenêtre de contexte.
        pieces = [content[i:i + 6500] for i in range(0, len(content), 6000)]
        partials = []
        for part_index, piece in enumerate(pieces, start=1):
            if stop_event and stop_event.is_set():
                raise InterruptedError("Génération arrêtée par l'utilisateur.")
            _notify(progress, f"Analyse IA · {name} · partie {part_index}/{len(pieces)}")
            partial = _summary_chat(model, [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (
                    f"Crée une partie de synthèse complète et organisée du cours provenant de {name}. "
                    f"Partie {part_index}/{len(pieces)}. Mentionne les pages lorsqu'elles sont indiquées. "
                    "N'utilise aucun LaTeX. Termine correctement la dernière phrase.\n\n" + piece
                )},
            ], stop_event)
            partials.append(partial)

        # Fusion hiérarchique : évite d'envoyer toutes les parties en une seule requête trop volumineuse.
        level = 1
        while len(partials) > 1:
            merged = []
            for group_start in range(0, len(partials), 3):
                if stop_event and stop_event.is_set():
                    raise InterruptedError("Génération arrêtée par l'utilisateur.")
                group = partials[group_start:group_start + 3]
                _notify(progress, f"Consolidation · {name} · niveau {level} · groupe {group_start // 3 + 1}")
                merged.append(_summary_chat(model, [
                    {"role": "system", "content": merge_prompt},
                    {"role": "user", "content": (
                        f"Réunis ces {len(group)} parties en une synthèse cohérente. "
                        "Garde toutes les informations utiles et n'interromps aucune phrase.\n\n"
                        + "\n\n--- PARTIE SUIVANTE ---\n\n".join(group)
                    )},
                ], stop_event))
            partials = merged
            level += 1
        summaries.append((name, partials[0]))

    if stop_event and stop_event.is_set():
        raise InterruptedError("Génération arrêtée par l'utilisateur.")
    _notify(progress, "Création du fichier PDF…")
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25, leading=31, textColor=colors.HexColor("#30245f"), alignment=TA_CENTER, spaceAfter=16))
    styles.add(ParagraphStyle(name="SectionTitle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=17, leading=22, textColor=colors.HexColor("#5142a5"), spaceBefore=15, spaceAfter=9, keepWithNext=True))
    styles.add(ParagraphStyle(name="BodyCustom", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=15, spaceAfter=7))
    styles.add(ParagraphStyle(name="SubTitle", parent=styles["Heading2"], fontSize=12, leading=16, textColor=colors.HexColor("#343b58"), spaceBefore=9, spaceAfter=5))
    story = [Spacer(1, 35*mm), Paragraph("SYNTHÈSE DE COURS", styles["CoverTitle"]), Paragraph("Générée par L-GPT · Intelligence artificielle locale", styles["BodyText"]), Spacer(1, 18*mm), Paragraph("Documents analysés", styles["SectionTitle"])]
    for name, _ in summaries:
        story.append(Paragraph("• " + escape(name), styles["BodyCustom"]))
    story.append(PageBreak())
    for idx, (name, summary) in enumerate(summaries):
        story.append(Paragraph(escape(name), styles["SectionTitle"]))
        # Markdown léger vers les styles ReportLab.
        for raw in summary.splitlines():
            line = _latex_to_plain(raw.strip())
            if not line:
                story.append(Spacer(1, 3)); continue
            if line.startswith("### "):
                story.append(Paragraph(escape(line[4:]), styles["SubTitle"]))
            elif line.startswith("## "):
                story.append(Paragraph(escape(line[3:]), styles["SectionTitle"]))
            elif line.startswith("# "):
                story.append(Paragraph(escape(line[2:]), styles["SectionTitle"]))
            elif line.startswith(("- ", "* ", "• ")):
                story.append(Paragraph("• " + escape(line[2:]), styles["BodyCustom"]))
            else:
                story.append(Paragraph(escape(line).replace("**", ""), styles["BodyCustom"]))
        if idx < len(summaries)-1: story.append(PageBreak())
    def footer(canvas, doc):
        canvas.saveState(); canvas.setFont("Helvetica",8); canvas.setFillColor(colors.HexColor("#7b8195"))
        canvas.drawString(18*mm, 12*mm, "L-GPT · Synthèse générée localement")
        canvas.drawRightString(A4[0]-18*mm, 12*mm, f"Page {doc.page}"); canvas.restoreState()
    SimpleDocTemplate(str(output_file), pagesize=A4, rightMargin=19*mm, leftMargin=19*mm, topMargin=19*mm, bottomMargin=21*mm, title="Synthèse de cours - L-GPT", author="L-GPT").build(story, onFirstPage=footer, onLaterPages=footer)
    _notify(progress, f"PDF créé · {output_file.name}")
    return str(output_file)
