from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

import ollama
from PySide6.QtCore import Qt, QObject, QThread, Signal, QTimer, QEvent
from PySide6.QtGui import QFont, QIcon, QColor, QTextDocument
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QTextBrowser, QTextEdit, QVBoxLayout, QWidget, QProgressBar,
    QListWidget, QListWidgetItem, QToolButton, QGraphicsDropShadowEffect
)

from core.pdf_engine import answer, build_indexes, create_summary_pdf

APP_NAME = "L-GPT"
MODELS = ["qwen3.8:27b", "qwen3.5:9b", "qwen3.5:4b"]

STYLE = r"""
* { font-family: 'Segoe UI'; }
QMainWindow, QWidget#root { background: #080b16; color: #edf0ff; }
QWidget#sidebar { background: #0b1020; border-right: 1px solid #202744; }
QWidget#mainArea { background: #0a0e1b; }
QLabel { color: #e9edff; }
QLabel#brand { font-size: 23px; font-weight: 800; letter-spacing: 1px; color: #ffffff; }
QLabel#brandSub { color: #8792b4; font-size: 9px; font-weight: 700; letter-spacing: 2px; }
QLabel#section { color: #7885a8; font-size: 9px; font-weight: 800; letter-spacing: 1.8px; }
QLabel#muted { color: #929cba; font-size: 11px; }
QLabel#pageTitle { font-size: 17px; font-weight: 700; color: #f5f6ff; }
QLabel#heroTitle { font-size: 35px; font-weight: 800; color: #ffffff; }
QLabel#heroSubtitle { font-size: 14px; color: #a5afcf; }
QLabel#status { background: #102b2b; color: #75e2c0; border: 1px solid #20554d; border-radius: 12px; padding: 7px 11px; font-size: 10px; font-weight: 700; }
QLabel#statusBusy { background: #282044; color: #c7b9ff; border: 1px solid #55448d; border-radius: 12px; padding: 7px 11px; font-size: 10px; font-weight: 700; }
QPushButton { background: #151d35; color: #dce3ff; border: 1px solid #293455; border-radius: 11px; padding: 10px 12px; font-size: 11px; font-weight: 600; text-align: left; }
QPushButton:hover { background: #202b4b; border-color: #695be0; }
QPushButton:disabled { color: #59627d; background: #11182b; border-color: #202943; }
QPushButton#newChat { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7659f5,stop:1 #4f76e8); border: 1px solid #8b79ff; color: white; padding: 13px; font-size: 12px; }
QPushButton#newChat:hover { background: #8b73ff; }
QPushButton#send { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #a17bff,stop:1 #627bff); color: white; border: none; border-radius: 15px; min-width: 48px; max-width: 48px; min-height: 46px; max-height: 46px; font-size: 21px; font-weight: 800; padding: 0; text-align: center; }
QPushButton#send:hover { background: #ad91ff; }
QPushButton#send:disabled { background: #35304f; color: #827aab; }
QPushButton#suggestion { background: #111a30; border: 1px solid #293757; border-radius: 13px; padding: 13px; color: #cbd4f5; }
QPushButton#suggestion:hover { background: #1b2645; border-color: #7665ef; }
QPushButton#smallAction { background: transparent; border: 1px solid #303a5c; padding: 7px 10px; border-radius: 9px; }
QComboBox { background: #111a30; color: #e8ecff; border: 1px solid #2b3658; border-radius: 10px; padding: 10px 11px; min-width: 150px; font-size: 11px; }
QComboBox:hover { border-color: #7465e8; }
QComboBox QAbstractItemView { background: #141e37; color: #e8ecff; selection-background-color: #594caa; border: 1px solid #3b4770; }
QFrame#docCard { background: #111a2e; border: 1px solid #293858; border-radius: 14px; }
QFrame#heroPanel { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #151b38,stop:.55 #11162b,stop:1 #21153b); border: 1px solid #3a376d; border-radius: 25px; }
QFrame#composer { background: #111a30; border: 1px solid #3a4770; border-radius: 19px; }
QFrame#composer:focus-within { border: 1px solid #8b75ff; }
QFrame#tipCard { background: #121b31; border: 1px solid #2b3859; border-radius: 14px; }
QFrame#bubbleUser { background: #1c2540; border: 1px solid #34436d; border-radius: 17px; }
QFrame#bubbleAssistant { background: transparent; border: none; }
QLabel#avatarAI { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #a27aff,stop:1 #536df2); color: white; border-radius: 12px; font-weight: 900; font-size: 11px; }
QLabel#avatarUser { background: #253451; color: #dbe5ff; border: 1px solid #435477; border-radius: 12px; font-weight: 700; font-size: 9px; }
QLabel#messageName { color: #aab5d5; font-size: 10px; font-weight: 800; letter-spacing: .5px; }
QTextBrowser { background: transparent; color: #e9edff; border: none; font-size: 13px; selection-background-color: #6554bd; }
QTextEdit#input { background: transparent; color: #f3f5ff; border: none; padding: 9px 7px; font-size: 13px; selection-background-color: #6554bd; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 3px; }
QScrollBar::handle:vertical { background: #354064; border-radius: 4px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #7668c8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QListWidget { background: transparent; border: none; color: #aeb9d9; outline: none; font-size: 11px; }
QListWidget::item { padding: 10px 9px; border-radius: 9px; }
QListWidget::item:hover { background: #151f38; }
QListWidget::item:selected { background: #202747; color: white; }
QProgressBar { background: #202a45; border: none; border-radius: 4px; height: 5px; text-align: center; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #9b71ff,stop:1 #5c8cff); border-radius: 4px; }
"""

class IndexWorker(QObject):
    progress = Signal(str)
    finished = Signal(object, object)
    failed = Signal(str)
    def __init__(self, paths):
        super().__init__(); self.paths = paths
    def run(self):
        try:
            chunks, embeddings = build_indexes(self.paths, self.progress.emit)
            self.finished.emit(chunks, embeddings)
        except Exception as exc:
            self.failed.emit(str(exc))

class SummaryWorker(QObject):
    progress = Signal(str)
    finished = Signal(str)
    failed = Signal(str)
    def __init__(self, paths, output, model):
        super().__init__(); self.paths, self.output, self.model = paths, output, model
    def run(self):
        try: self.finished.emit(create_summary_pdf(self.paths, self.output, self.model, self.progress.emit))
        except Exception as exc: self.failed.emit(str(exc))

class ChatWorker(QObject):
    token = Signal(str)
    finished = Signal(str, object, object)
    failed = Signal(str)
    def __init__(self, question, chunks, embeddings, history, model):
        super().__init__()
        self.question, self.chunks = question, chunks
        self.embeddings, self.history, self.model = embeddings, history, model
    def run(self):
        try:
            response, sources, history = answer(
                self.question, self.chunks, self.embeddings,
                self.history, self.model, self.token.emit
            )
            self.finished.emit(response, sources, history)
        except Exception as exc:
            message = str(exc)
            lowered = message.lower()
            if any(term in lowered for term in ("out of memory", "failed to allocate", "kv cache", "cuda out of memory", "llama-server")):
                message += ("\n\nPiste de résolution : L-GPT utilise maintenant une fenêtre de contexte réduite à 2048 tokens "
                            "pour limiter la mémoire nécessaire au cache KV. Ferme les applications lourdes et, si le problème persiste, "
                            "sélectionne un modèle plus léger comme qwen3.5:9b ou qwen3.5:4b.")
            self.failed.emit(message)

class ChatMessageBrowser(QTextBrowser):
    """Affiche le Markdown comme dans un chat, sans petite zone défilante interne."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(30)
        self.setMaximumHeight(16777215)
        self.document().setDocumentMargin(1)
        self.document().setDefaultStyleSheet("""
            body { color: #e9edff; font-family: 'Segoe UI'; font-size: 14px; line-height: 1.55; }
            p { margin: 5px 0 10px 0; }
            h1, h2, h3 { color: #ffffff; margin-top: 17px; margin-bottom: 8px; }
            h1 { font-size: 23px; } h2 { font-size: 19px; } h3 { font-size: 16px; }
            a { color: #a995ff; }
            code { color: #d8caff; background-color: #202744; }
            pre { background-color: #111a30; border: 1px solid #303b60; padding: 12px; }
            blockquote { color: #b8c2e4; border-left: 3px solid #8874f5; margin-left: 4px; padding-left: 10px; }
            table { border-collapse: collapse; }
            th, td { border: 1px solid #394568; padding: 6px 9px; }
            th { background-color: #202744; }
            li { margin: 3px 0; }
            hr { color: #394568; }
        """)

    def set_chat_markdown(self, markdown):
        self.setMarkdown(markdown)
        QTimer.singleShot(0, self.fit_document)

    def fit_document(self):
        width = max(100, self.viewport().width())
        self.document().setTextWidth(width)
        height = int(self.document().size().height()) + 14
        self.setMinimumHeight(max(34, height))
        self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_document()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("L-GPT | Assistant IA local")
        self.resize(1440, 920)
        self.setMinimumSize(1050, 700)
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "assets" / "lgpt.ico")))
        self.pdf_path = None
        self.pdf_paths = []
        self.chunks = None
        self.embeddings = None
        self.history = []
        self.busy = False
        self.index_thread = self.index_worker = None
        self.summary_thread = self.summary_worker = None
        self.chat_thread = self.chat_worker = None
        self.assistant_browser = None
        self.stream_text = ""
        self.saved_conversations = []
        self.current_title = "Nouvelle conversation"
        self.setStyleSheet(STYLE)
        self._build_ui()
        self._check_ollama()

    def _build_ui(self):
        root = QWidget(objectName="root")
        outer = QHBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        self.setCentralWidget(root)

        # Sidebar
        self.sidebar = QWidget(objectName="sidebar"); self.sidebar.setFixedWidth(270)
        side = QVBoxLayout(self.sidebar); side.setContentsMargins(19,22,17,18); side.setSpacing(13)
        brand_row = QHBoxLayout()
        mark = QLabel("L"); mark.setFixedSize(42,42); mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #a27aff,stop:1 #536df2); color:white; border-radius:14px; font-size:22px; font-weight:900;")
        brand_col = QVBoxLayout(); brand = QLabel("L-GPT"); brand.setObjectName("brand")
        sub = QLabel("LOCAL INTELLIGENCE"); sub.setObjectName("brandSub")
        brand_col.addWidget(brand); brand_col.addWidget(sub)
        brand_row.addWidget(mark); brand_row.addSpacing(9); brand_row.addLayout(brand_col); brand_row.addStretch()
        side.addLayout(brand_row); side.addSpacing(10)

        self.new_button = QPushButton("＋   Nouvelle conversation"); self.new_button.setObjectName("newChat")
        self.new_button.clicked.connect(self.new_chat); side.addWidget(self.new_button)

        label = QLabel("DOCUMENTS"); label.setObjectName("section"); side.addWidget(label)
        self.import_button = QPushButton("▧   Importer des PDF")
        self.import_button.clicked.connect(self.import_pdf); side.addWidget(self.import_button)
        self.summary_button = QPushButton("✧   Créer un résumé PDF")
        self.summary_button.clicked.connect(self.create_summary); self.summary_button.setEnabled(False); side.addWidget(self.summary_button)
        self.doc_name = QLabel("Aucun document importé"); self.doc_name.setObjectName("muted"); self.doc_name.setWordWrap(True); side.addWidget(self.doc_name)
        self.index_progress = QProgressBar(); self.index_progress.setRange(0,0); self.index_progress.hide(); side.addWidget(self.index_progress)
        self.index_label = QLabel("En attente d'un document"); self.index_label.setObjectName("muted"); side.addWidget(self.index_label)

        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet("background:#202a45;"); side.addWidget(sep)
        label = QLabel("MODÈLE IA"); label.setObjectName("section"); side.addWidget(label)
        self.model_combo = QComboBox(); self.model_combo.addItems(MODELS); side.addWidget(self.model_combo)
        self.model_hint = QLabel("Exécution locale via Ollama"); self.model_hint.setObjectName("muted"); side.addWidget(self.model_hint)

        sep2 = QFrame(); sep2.setFixedHeight(1); sep2.setStyleSheet("background:#202a45;"); side.addWidget(sep2)
        hist_label = QLabel("RÉCENT"); hist_label.setObjectName("section"); side.addWidget(hist_label)
        self.history_list = QListWidget(); self.history_list.itemClicked.connect(self.restore_conversation); side.addWidget(self.history_list,1)
        footer = QHBoxLayout()
        footer_mark = QLabel("●"); footer_mark.setStyleSheet("color:#6fe0bb; font-size:11px;")
        footer_text = QLabel("Vos documents restent sur cet appareil"); footer_text.setObjectName("muted")
        footer.addWidget(footer_mark); footer.addWidget(footer_text); footer.addStretch(); side.addLayout(footer)
        outer.addWidget(self.sidebar)

        # Main content
        self.main_area = QWidget(objectName="mainArea")
        main = QVBoxLayout(self.main_area); main.setContentsMargins(34,23,34,20); main.setSpacing(15)
        top = QHBoxLayout()
        self.page_title = QLabel("Votre espace intelligent"); self.page_title.setObjectName("pageTitle")
        top.addWidget(self.page_title); top.addStretch()
        self.status = QLabel("●  PRÊT"); self.status.setObjectName("status"); top.addWidget(self.status)
        main.addLayout(top)

        self.doc_card = QFrame(objectName="docCard")
        doc = QHBoxLayout(self.doc_card); doc.setContentsMargins(15,10,14,10); doc.setSpacing(12)
        pdf_badge = QLabel("PDF"); pdf_badge.setAlignment(Qt.AlignmentFlag.AlignCenter); pdf_badge.setFixedSize(38,38)
        pdf_badge.setStyleSheet("background:#33265f;color:#c7b6ff;border:1px solid #57458c;border-radius:10px;font-weight:900;font-size:10px;")
        self.doc_card_name = QLabel("Aucun document sélectionné"); self.doc_card_name.setStyleSheet("font-size:11px;font-weight:700;color:#dfe5ff;")
        self.remove_doc = QPushButton("Retirer"); self.remove_doc.setObjectName("smallAction"); self.remove_doc.clicked.connect(self.remove_pdf)
        doc.addWidget(pdf_badge); doc.addWidget(self.doc_card_name); doc.addStretch(); doc.addWidget(self.remove_doc)
        main.addWidget(self.doc_card)

        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.chat_host = QWidget(); self.chat_layout = QVBoxLayout(self.chat_host)
        self.chat_layout.setContentsMargins(8,15,8,18); self.chat_layout.setSpacing(20); self.chat_layout.addStretch()
        self.scroll.setWidget(self.chat_host); main.addWidget(self.scroll,1)
        self.show_welcome()

        composer = QFrame(objectName="composer")
        shadow = QGraphicsDropShadowEffect(composer); shadow.setBlurRadius(28); shadow.setOffset(0,5); shadow.setColor(QColor(0, 0, 0, 150))
        composer.setGraphicsEffect(shadow)
        compose = QHBoxLayout(composer); compose.setContentsMargins(15,8,10,8); compose.setSpacing(10)
        self.input = QTextEdit(objectName="input"); self.input.setPlaceholderText("Pose une question sur ton document...")
        self.input.setFixedHeight(60); self.input.setMaximumHeight(130); self.input.setAcceptRichText(False)
        self.input.installEventFilter(self)
        compose.addWidget(self.input,1)
        self.send_btn = QPushButton("↑"); self.send_btn.setObjectName("send"); self.send_btn.clicked.connect(self.send_message); compose.addWidget(self.send_btn)
        main.addWidget(composer)
        note = QLabel("L-GPT peut se tromper. Vérifie les informations importantes."); note.setObjectName("muted"); note.setAlignment(Qt.AlignmentFlag.AlignCenter); main.addWidget(note)
        outer.addWidget(self.main_area,1)

    def show_welcome(self):
        panel = QFrame(objectName="heroPanel")
        shadow = QGraphicsDropShadowEffect(panel); shadow.setBlurRadius(45); shadow.setOffset(0,8); shadow.setColor(QColor(0, 0, 0, 150)); panel.setGraphicsEffect(shadow)
        lay = QVBoxLayout(panel); lay.setContentsMargins(42,38,42,35); lay.setSpacing(13)
        lay.addStretch()
        orb = QLabel("L"); orb.setFixedSize(76,76); orb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        orb.setStyleSheet("background: qradialgradient(cx:.35,cy:.3,r:1,stop:0 #c5aaff,stop:.35 #8567ff,stop:1 #3e4eb4); border:1px solid #b49cff; border-radius:25px; color:white; font-size:38px; font-weight:900;")
        lay.addWidget(orb,0,Qt.AlignmentFlag.AlignHCenter)
        eyebrow = QLabel("VOTRE ASSISTANT IA PERSONNEL"); eyebrow.setObjectName("section"); eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Bienvenue sur L-GPT"); title.setObjectName("heroTitle"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Une intelligence locale pour comprendre, explorer et apprendre."); subtitle.setObjectName("heroSubtitle"); subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(eyebrow); lay.addWidget(title); lay.addWidget(subtitle); lay.addSpacing(15)
        cards = QHBoxLayout(); cards.setSpacing(12)
        suggestions = [
            ("✦  Comprendre", "Explique-moi les notions essentielles de ce document."),
            ("⌕  Rechercher", "Retrouve les informations les plus importantes du document."),
            ("▤  Synthétiser", "Fais une synthèse structurée de ce document."),
        ]
        for heading, prompt in suggestions:
            b = QPushButton(heading + "\n" + prompt); b.setObjectName("suggestion"); b.setMinimumHeight(76); b.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
            b.clicked.connect(lambda checked=False, p=prompt: self.use_suggestion(p)); cards.addWidget(b)
        lay.addLayout(cards); lay.addStretch()
        self.chat_layout.insertWidget(self.chat_layout.count()-1,panel)

    def use_suggestion(self, prompt):
        self.input.setPlainText(prompt); self.send_message()

    def eventFilter(self, obj, event):
        if obj is self.input and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self.send_message(); return True
        return super().eventFilter(obj,event)

    def _check_ollama(self):
        try:
            ollama.list()
            self.status.setText("●  OLLAMA CONNECTÉ")
            self.status.setObjectName("status")
            self.status.style().unpolish(self.status); self.status.style().polish(self.status)
        except Exception:
            self.status.setText("●  OLLAMA HORS LIGNE")
            self.status.setObjectName("statusBusy")
            self.status.style().unpolish(self.status); self.status.style().polish(self.status)
            self.index_label.setText("Démarre Ollama pour utiliser L-GPT")

    def import_pdf(self):
        if self.busy or self.index_thread is not None: return
        paths, _ = QFileDialog.getOpenFileNames(self,"Importer des PDF",str(Path.home()),"Fichiers PDF (*.pdf)")
        if not paths: return
        self.pdf_paths = paths; self.pdf_path = paths[0]; name = f"{len(paths)} document(s) : " + ", ".join(Path(x).name for x in paths)
        self.doc_name.setText(name); self.doc_card_name.setText(name)
        self.index_label.setText("Préparation de l'index..."); self.index_progress.show(); self.import_button.setEnabled(False)
        self.status.setText("◌  INDEXATION")
        self.index_thread = QThread(); self.index_worker = IndexWorker(paths); self.index_worker.moveToThread(self.index_thread)
        self.index_thread.started.connect(self.index_worker.run)
        self.index_worker.progress.connect(self.on_index_progress)
        self.index_worker.finished.connect(self.on_index_ready)
        self.index_worker.failed.connect(self.on_index_error)
        self.index_worker.finished.connect(self.index_thread.quit); self.index_worker.failed.connect(self.index_thread.quit)
        self.index_thread.finished.connect(self.index_worker.deleteLater); self.index_thread.finished.connect(self.index_thread.deleteLater)
        self.index_thread.finished.connect(self.index_thread_done); self.index_thread.start()

    def on_index_progress(self, message): self.index_label.setText(message)
    def on_index_ready(self, chunks, embeddings):
        self.chunks, self.embeddings = chunks, embeddings
        self.index_label.setText(f"{len(self.pdf_paths)} PDF · {len(chunks)} passages indexés")
        self.summary_button.setEnabled(True)
        self.status.setText("●  DOCUMENTS PRÊTS")
    def on_index_error(self, error):
        self.chunks = self.embeddings = None
        self.index_label.setText("Échec de l'indexation")
        QMessageBox.critical(self,"Impossible d'indexer le PDF",error)
    def index_thread_done(self):
        self.index_progress.hide(); self.import_button.setEnabled(True)
        self.index_thread = self.index_worker = None

    def remove_pdf(self):
        if self.busy or self.index_thread is not None: return
        self.pdf_path = self.chunks = self.embeddings = None
        self.pdf_paths = []
        self.summary_button.setEnabled(False)
        self.doc_name.setText("Aucun document importé"); self.doc_card_name.setText("Aucun document sélectionné")
        self.index_label.setText("En attente d'un document")
        self.status.setText("●  OLLAMA CONNECTÉ")

    def create_summary(self):
        if self.busy or self.index_thread is not None or not self.pdf_paths: return
        default = str(Path(self.pdf_paths[0]).with_name("Synthese_L-GPT.pdf"))
        output, _ = QFileDialog.getSaveFileName(self, "Enregistrer la synthèse PDF", default, "Fichier PDF (*.pdf)")
        if not output: return
        if not output.lower().endswith(".pdf"): output += ".pdf"
        self.summary_button.setEnabled(False); self.import_button.setEnabled(False)
        self.status.setText("◌  CRÉATION DE LA SYNTHÈSE"); self.status.setObjectName("statusBusy")
        self.index_label.setText("Préparation de la synthèse…")
        self.summary_thread = QThread(); self.summary_worker = SummaryWorker(list(self.pdf_paths), output, self.model_combo.currentText())
        self.summary_worker.moveToThread(self.summary_thread)
        self.summary_thread.started.connect(self.summary_worker.run)
        self.summary_worker.progress.connect(self.index_label.setText)
        self.summary_worker.finished.connect(self.summary_done); self.summary_worker.failed.connect(self.summary_error)
        self.summary_worker.finished.connect(self.summary_thread.quit); self.summary_worker.failed.connect(self.summary_thread.quit)
        self.summary_thread.finished.connect(self.summary_worker.deleteLater); self.summary_thread.finished.connect(self.summary_thread.deleteLater)
        self.summary_thread.finished.connect(self.summary_thread_done); self.summary_thread.start()

    def summary_done(self, path):
        self.index_label.setText("Synthèse PDF créée avec succès")
        QMessageBox.information(self, "Synthèse terminée", f"Le PDF a été créé :\n{path}")

    def summary_error(self, error):
        self.index_label.setText("Échec de la création du PDF")
        QMessageBox.critical(self, "Impossible de créer la synthèse", error)

    def summary_thread_done(self):
        self.summary_button.setEnabled(bool(self.pdf_paths)); self.import_button.setEnabled(True)
        self.summary_thread = self.summary_worker = None
        self.status.setText("●  DOCUMENTS PRÊTS")

    def _clear_chat(self):
        # Supprime les widgets ET les layouts de lignes (les messages sont dans des QHBoxLayout).
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                while child_layout.count():
                    child_item = child_layout.takeAt(0)
                    child_widget = child_item.widget()
                    if child_widget is not None:
                        child_widget.deleteLater()
                child_layout.deleteLater()
        self.chat_layout.addStretch(1)

    def new_chat(self):
        if self.busy:
            QMessageBox.information(self, "Réponse en cours",
                                    "Attends la fin de la réponse avant de commencer une nouvelle conversation.")
            return
        # Archive la conversation actuelle uniquement si elle contient un échange.
        if self.history:
            first_question = next((m.get("content", "") for m in self.history if m.get("role") == "user"), "Conversation")
            title = first_question.strip().replace("\n", " ")[:42] or "Conversation"
            if len(first_question.strip()) > 42:
                title += "…"
            self.saved_conversations.insert(0, (title, list(self.history)))
            self.history_list.insertItem(0, QListWidgetItem("◦  " + title))
        self.history = []
        self.current_title = "Nouvelle conversation"
        self.page_title.setText("Votre espace intelligent")
        self._clear_chat()
        self.show_welcome()
        self.input.clear()
        self.input.setFocus()
        self.scroll_bottom()

    def restore_conversation(self, item):
        if self.busy: return
        index = self.history_list.row(item)
        if index < 0 or index >= len(self.saved_conversations): return
        title, history = self.saved_conversations[index]
        self.history = list(history); self.page_title.setText(title); self._clear_chat()
        for msg in self.history:
            self.add_message(msg["content"], "user" if msg["role"] == "user" else "assistant")

    def add_message(self, content, role):
        is_user = role == "user"
        bubble = QFrame(objectName="bubbleUser" if is_user else "bubbleAssistant")
        bubble.setMaximumWidth(850 if is_user else 16777215)
        bubble.setSizePolicy(QSizePolicy.Policy.Maximum if is_user else QSizePolicy.Policy.Expanding,
                             QSizePolicy.Policy.Preferred)
        lay = QVBoxLayout(bubble)
        lay.setContentsMargins(17, 13, 17, 13) if is_user else lay.setContentsMargins(2, 7, 8, 7)
        lay.setSpacing(9)
        head = QHBoxLayout()
        avatar = QLabel("TOI" if is_user else "L")
        avatar.setObjectName("avatarUser" if is_user else "avatarAI")
        avatar.setFixedSize(27, 27)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name = QLabel("VOUS" if is_user else "L-GPT")
        name.setObjectName("messageName")
        head.addWidget(avatar)
        head.addWidget(name)
        head.addStretch()
        if not is_user:
            copy_btn = QPushButton("Copier")
            copy_btn.setObjectName("smallAction")
            head.addWidget(copy_btn)
        lay.addLayout(head)
        browser = ChatMessageBrowser()
        browser.set_chat_markdown(content)
        lay.addWidget(browser)
        if not is_user:
            copy_btn.clicked.connect(lambda checked=False, b=browser: QApplication.clipboard().setText(b.toPlainText()))
        row = QHBoxLayout()
        if is_user:
            row.addStretch(1)
            row.addWidget(bubble, 0)
        else:
            row.addWidget(bubble, 1)
        self.chat_layout.insertLayout(self.chat_layout.count()-1, row)
        QTimer.singleShot(50, self.scroll_bottom)
        return browser

    def scroll_bottom(self):
        bar = self.scroll.verticalScrollBar(); bar.setValue(bar.maximum())

    def send_message(self):
        if self.busy: return
        question = self.input.toPlainText().strip()
        if not question: return
        if self.chunks is None or self.embeddings is None:
            QMessageBox.information(self,"Ajoute un document","Importe un PDF et attends la fin de son indexation avant de poser une question."); return
        self.input.clear(); self.page_title.setText(question[:48] + ("…" if len(question)>48 else ""))
        self.add_message(question,"user"); self.assistant_browser = self.add_message("", "assistant"); self.stream_text = ""
        self.busy = True; self.send_btn.setEnabled(False); self.input.setEnabled(False); self.import_button.setEnabled(False)
        self.status.setText("◌  L-GPT RÉFLÉCHIT"); self.status.setObjectName("statusBusy"); self.status.style().unpolish(self.status); self.status.style().polish(self.status)
        self.chat_thread = QThread(); self.chat_worker = ChatWorker(question,self.chunks,self.embeddings,list(self.history),self.model_combo.currentText())
        self.chat_worker.moveToThread(self.chat_thread); self.chat_thread.started.connect(self.chat_worker.run)
        self.chat_worker.token.connect(self.on_token); self.chat_worker.finished.connect(self.on_answer_finished); self.chat_worker.failed.connect(self.on_answer_error)
        self.chat_worker.finished.connect(self.chat_thread.quit); self.chat_worker.failed.connect(self.chat_thread.quit)
        self.chat_thread.finished.connect(self.chat_worker.deleteLater); self.chat_thread.finished.connect(self.chat_thread.deleteLater); self.chat_thread.finished.connect(self.chat_thread_done)
        self.chat_thread.start()

    def on_token(self, token):
        self.stream_text += token; self.assistant_browser.set_chat_markdown(self.stream_text); self.scroll_bottom()

    def on_answer_finished(self, response, sources, history):
        self.history = history
        text = response
        if sources:
            text += "\n\n---\n\n### Sources du document\n"
            for source in sources:
                page = source.get("page", "?") if isinstance(source,dict) else "?"
                chunk = source.get("chunk", "") if isinstance(source,dict) else ""
                filename = source.get("source", "PDF") if isinstance(source,dict) else "PDF"
                text += f"\n- **{filename}** · page **{page}**" + (f" · passage {chunk}" if chunk else "")
        self.assistant_browser.set_chat_markdown(text); self.scroll_bottom()
        self.status.setText("●  RÉPONSE TERMINÉE"); self.status.setObjectName("status"); self.status.style().unpolish(self.status); self.status.style().polish(self.status)

    def on_answer_error(self, error):
        self.assistant_browser.set_chat_markdown("**Une erreur est survenue :**\n\n" + error)
        self.status.setText("●  ERREUR")

    def chat_thread_done(self):
        self.busy = False; self.send_btn.setEnabled(True); self.input.setEnabled(True); self.import_button.setEnabled(True)
        self.input.setFocus(); self.chat_thread = self.chat_worker = None
        if self.status.text().find("ERREUR") < 0:
            self.status.setText("●  OLLAMA CONNECTÉ"); self.status.setObjectName("status"); self.status.style().unpolish(self.status); self.status.style().polish(self.status)

    def closeEvent(self, event):
        if self.busy or self.index_thread is not None or self.summary_thread is not None:
            QMessageBox.information(self,"Opération en cours","Attends la fin de la génération ou de l'indexation avant de fermer L-GPT."); event.ignore(); return
        event.accept()

def main():
    # Les erreurs de démarrage sont conservées dans un fichier plutôt que de disparaître avec pythonw.exe.
    import traceback
    def log_exception(exc_type, exc_value, exc_tb):
        log = Path(__file__).with_name("L-GPT_erreurs.log")
        with log.open("a", encoding="utf-8") as stream:
            stream.write("\n\n--- Erreur L-GPT ---\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=stream)
    sys.excepthook = log_exception
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("Segoe UI",10))
    window = MainWindow(); window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
