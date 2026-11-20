from __future__ import annotations

import sys
import os
import sqlite3
import uuid
import json
import re
from threading import Event
from pathlib import Path
from datetime import datetime
from time import perf_counter

import ollama
from PySide6.QtCore import Qt, QObject, QThread, Signal, QTimer, QEvent
from PySide6.QtGui import QFont, QIcon, QColor, QTextDocument
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QTextBrowser, QTextEdit, QVBoxLayout, QWidget, QProgressBar,
    QListWidget, QListWidgetItem, QToolButton, QGraphicsDropShadowEffect,
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QPlainTextEdit,
    QTabWidget, QTableWidget, QTableWidgetItem, QSpinBox, QCheckBox
)

from core.pdf_engine import answer_chat, build_indexes, create_summary_pdf

APP_NAME = "L-GPT"
APP_VERSION = "3.0"
FALLBACK_MODELS = ["qwen3.8:27b", "qwen3.5:9b", "qwen3.5:4b"]
EMBEDDING_MODEL_NAMES = {"nomic-embed-text", "nomic-embed-text:latest"}

def data_directory() -> Path:
    """Dossier de données utilisateur adapté à Windows, macOS et Linux.

    Le chemin Windows historique est conservé pour retrouver automatiquement
    les conversations et mémoires des versions précédentes.
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    folder = base / "L-GPT"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def resource_path(relative_path: str) -> Path:
    """Résout les ressources en mode Python et dans un bundle PyInstaller."""
    bundle_root = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return Path(bundle_root) / relative_path

class ConversationStore:
    """Stockage SQLite local des conversations L-GPT."""
    def __init__(self):
        self.path = data_directory() / "conversations.db"
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, messages TEXT NOT NULL, pdf_paths TEXT NOT NULL DEFAULT '[]'
            )""")
            db.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL, updated_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.commit()

    def get_setting(self, key, default=None):
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
        if not row: return default
        try: return json.loads(row[0])
        except Exception: return default

    def set_setting(self, key, value):
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO app_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value, ensure_ascii=False)))
            db.commit()

    def memories(self):
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT id,category,title,content,updated_at FROM memories ORDER BY category,title").fetchall()
        return rows

    def save_memory(self, category, title, content, memory_id=None):
        now = datetime.now().isoformat(timespec="seconds")
        with sqlite3.connect(self.path) as db:
            if memory_id:
                db.execute("UPDATE memories SET category=?,title=?,content=?,updated_at=? WHERE id=?", (category,title,content,now,memory_id))
            else:
                db.execute("INSERT INTO memories(category,title,content,updated_at) VALUES(?,?,?,?)", (category,title,content,now))
            db.commit()

    def delete_memory(self, memory_id):
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM memories WHERE id=?", (memory_id,)); db.commit()

    def save(self, conversation_id, title, messages, pdf_paths):
        now = datetime.now().isoformat(timespec="seconds")
        with sqlite3.connect(self.path) as db:
            existing = db.execute("SELECT created_at FROM conversations WHERE id=?", (conversation_id,)).fetchone()
            created = existing[0] if existing else now
            db.execute("""INSERT INTO conversations(id,title,created_at,updated_at,messages,pdf_paths)
                VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                title=excluded.title, updated_at=excluded.updated_at,
                messages=excluded.messages, pdf_paths=excluded.pdf_paths""",
                (conversation_id, title, created, now, json.dumps(messages, ensure_ascii=False), json.dumps(pdf_paths, ensure_ascii=False)))
            db.commit()

    def list(self):
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT id,title,updated_at FROM conversations ORDER BY updated_at DESC").fetchall()
        return [{"id": r[0], "title": r[1], "updated_at": r[2]} for r in rows]

    def load(self, conversation_id):
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT title,messages,pdf_paths FROM conversations WHERE id=?", (conversation_id,)).fetchone()
        if not row: return None
        return {"title": row[0], "messages": json.loads(row[1]), "pdf_paths": json.loads(row[2])}

    def delete(self, conversation_id):
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
            db.commit()

STYLE = r"""
* { font-family: 'Arial'; }
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
    def __init__(self, paths, output, model, stop_event):
        super().__init__(); self.paths, self.output, self.model, self.stop_event = paths, output, model, stop_event
    def run(self):
        try: self.finished.emit(create_summary_pdf(self.paths, self.output, self.model, self.progress.emit, self.stop_event))
        except Exception as exc: self.failed.emit(str(exc))

class ChatWorker(QObject):
    token = Signal(str)
    finished = Signal(str, object, object, str)
    failed = Signal(str)
    def __init__(self, question, chunks, embeddings, history, model, mode, stop_event, runtime_options=None, memory_context=""):
        super().__init__()
        self.question, self.chunks = question, chunks
        self.embeddings, self.history, self.model = embeddings, history, model
        self.mode, self.stop_event = mode, stop_event
        self.runtime_options, self.memory_context = runtime_options or {}, memory_context
    def run(self):
        try:
            response, sources, history, source_mode = answer_chat(
                self.question, self.chunks, self.embeddings,
                self.history, self.model, self.mode, self.token.emit, self.stop_event,
                self.runtime_options, self.memory_context
            )
            self.finished.emit(response, sources, history, source_mode)
        except Exception as exc:
            message = str(exc)
            lowered = message.lower()
            if any(term in lowered for term in ("out of memory", "failed to allocate", "kv cache", "cuda out of memory", "llama-server")):
                message += ("\n\nPiste de résolution : L-GPT utilise une fenêtre de contexte de 4096 tokens "
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
            body { color: #e9edff; font-family: 'Arial'; font-size: 14px; line-height: 1.55; }
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
        self.setWindowTitle(f"L-GPT {APP_VERSION} | Assistant IA local")
        self.resize(1440, 920)
        self.setMinimumSize(1050, 700)
        icon_file = "assets/lgpt.png" if sys.platform == "darwin" else "assets/lgpt.ico"
        self.setWindowIcon(QIcon(str(resource_path(icon_file))))
        self.pdf_path = None
        self.pdf_paths = []
        self.chunks = None
        self.embeddings = None
        self.history = []
        self.busy = False
        self.index_thread = self.index_worker = None
        self.summary_thread = self.summary_worker = None
        self.chat_thread = self.chat_worker = None
        self.chat_stop_event = None
        self.summary_stop_event = None
        self.assistant_browser = None
        self.stream_text = ""
        self.store = ConversationStore()
        self.conversation_id = str(uuid.uuid4())
        self.transcript = []
        self.current_title = "Nouvelle conversation"
        self._history_items = {}
        self.setStyleSheet(STYLE)
        self.settings = self.store.get_setting("runtime", {"profile":"Équilibré", "auto_model":True, "context":16384, "kv_cache":"f16", "num_predict":2048})
        self._build_ui()
        self._check_ollama()
        self.reload_conversations()

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
        self.stop_summary_button = QPushButton("■   Arrêter la synthèse")
        self.stop_summary_button.setObjectName("smallAction")
        self.stop_summary_button.clicked.connect(self.stop_summary)
        self.stop_summary_button.hide(); side.addWidget(self.stop_summary_button)
        self.doc_name = QLabel("Aucun document importé"); self.doc_name.setObjectName("muted"); self.doc_name.setWordWrap(True); side.addWidget(self.doc_name)
        self.index_progress = QProgressBar(); self.index_progress.setRange(0,0); self.index_progress.hide(); side.addWidget(self.index_progress)
        self.index_label = QLabel("En attente d'un document"); self.index_label.setObjectName("muted"); side.addWidget(self.index_label)

        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet("background:#202a45;"); side.addWidget(sep)
        label = QLabel("MODÈLE IA"); label.setObjectName("section"); side.addWidget(label)
        model_row = QHBoxLayout()
        self.model_combo = QComboBox(); self.model_combo.setMinimumWidth(0); model_row.addWidget(self.model_combo, 1)
        self.refresh_models_button = QPushButton("↻"); self.refresh_models_button.setFixedWidth(34)
        self.refresh_models_button.setToolTip("Actualiser les modèles installés dans Ollama")
        self.refresh_models_button.clicked.connect(self.refresh_models); model_row.addWidget(self.refresh_models_button)
        side.addLayout(model_row)
        self.model_hint = QLabel("Détection automatique des modèles Ollama"); self.model_hint.setObjectName("muted"); side.addWidget(self.model_hint)
        self.settings_button = QPushButton("⚙   Paramètres IA et mémoire")
        self.settings_button.clicked.connect(self.open_settings); side.addWidget(self.settings_button)

        sep2 = QFrame(); sep2.setFixedHeight(1); sep2.setStyleSheet("background:#202a45;"); side.addWidget(sep2)
        hist_label = QLabel("RÉCENT"); hist_label.setObjectName("section"); side.addWidget(hist_label)
        self.history_list = QListWidget(); self.history_list.itemClicked.connect(self.restore_conversation); side.addWidget(self.history_list,1)
        history_actions = QHBoxLayout()
        self.rename_chat_button = QPushButton("Renommer"); self.rename_chat_button.setObjectName("smallAction")
        self.rename_chat_button.clicked.connect(self.rename_conversation)
        self.delete_chat_button = QPushButton("Supprimer"); self.delete_chat_button.setObjectName("smallAction")
        self.delete_chat_button.clicked.connect(self.delete_conversation)
        history_actions.addWidget(self.rename_chat_button); history_actions.addWidget(self.delete_chat_button)
        side.addLayout(history_actions)
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
        self.mode_combo = QComboBox(); self.mode_combo.addItems(["Intelligent", "Document", "Connaissances"]); self.mode_combo.setCurrentText("Intelligent"); self.mode_combo.setToolTip("Choisis la source des réponses. Intelligent sélectionne automatiquement la meilleure approche."); self.mode_combo.setMinimumWidth(175); top.addWidget(self.mode_combo)
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
        self.input = QTextEdit(objectName="input"); self.input.setPlaceholderText("Pose une question à L-GPT, avec ou sans PDF...")
        self.input.setFixedHeight(60); self.input.setMaximumHeight(130); self.input.setAcceptRichText(False)
        self.input.installEventFilter(self)
        compose.addWidget(self.input,1)
        self.send_btn = QPushButton("↑"); self.send_btn.setObjectName("send"); self.send_btn.clicked.connect(self.send_message); compose.addWidget(self.send_btn)
        self.stop_chat_btn = QPushButton("■")
        self.stop_chat_btn.setObjectName("send")
        self.stop_chat_btn.setToolTip("Arrêter la génération en cours")
        self.stop_chat_btn.clicked.connect(self.stop_chat)
        self.stop_chat_btn.hide(); compose.addWidget(self.stop_chat_btn)
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
        subtitle = QLabel("Un assistant local pour tes cours, tes documents et toutes tes questions."); subtitle.setObjectName("heroSubtitle"); subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(eyebrow); lay.addWidget(title); lay.addWidget(subtitle); lay.addSpacing(15)
        cards = QHBoxLayout(); cards.setSpacing(12)
        suggestions = [
            ("✦  Comprendre", "Explique-moi simplement la différence entre une IA et un modèle de langage."),
            ("⌕  Explorer un cours", "Explique-moi les notions essentielles de mon document."),
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

    def _quantization_from_details(self, details):
        candidates = []
        if isinstance(details, dict):
            candidates += [str(details.get(k, "")) for k in ("quantization_level", "quantization", "format")]
            detail_block = details.get("details", {}) or {}
            candidates += [str(detail_block.get(k, "")) for k in ("quantization_level", "format")]
            modelinfo = details.get("model_info", {}) or {}
            candidates += [str(v) for k, v in modelinfo.items() if "quantization" in k.lower()]
        raw = " ".join(candidates).upper()
        known = ("Q2_K", "Q3_K_S", "Q3_K_M", "Q3_K_L", "Q4_0", "Q4_1", "Q4_K_S", "Q4_K_M", "Q5_0", "Q5_1", "Q5_K_S", "Q5_K_M", "Q6_K", "Q8_0", "IQ1_S", "IQ1_M", "IQ2_XXS", "IQ2_XS", "IQ2_S", "IQ2_M", "IQ3_XXS", "IQ3_XS", "IQ3_S", "IQ3_M", "IQ4_NL", "IQ4_XS", "F16", "BF16", "F32", "TQ1_0", "TQ2_0", "MXFP4", "NVFP4", "FP8", "INT8", "INT4")
        for item in sorted(known, key=len, reverse=True):
            if item in raw: return item
        return "Non communiquée par Ollama"

    def _choose_model(self, question):
        models = list(getattr(self, "installed_models", []))
        selected = self.model_combo.currentText()
        if not self.settings.get("auto_model", True) or not models:
            return selected, "Sélection manuelle" if not self.settings.get("auto_model", True) else "Modèle choisi dans la liste"
        profile = self.settings.get("profile", "Équilibré")
        lower = question.lower()
        deep = len(question) > 500 or any(x in lower for x in ("analyse en détail", "démontre", "compare", "étape par étape", "approfondis", "raisonne"))
        simple = len(question) < 140 and not deep and not self.pdf_paths
        if profile == "Qualité": target = "27b" if deep else "9b"
        elif profile == "Performance": target = "4b" if simple else "9b"
        else: target = "27b" if deep else ("4b" if simple else "9b")
        chosen = next((m for m in models if target in m.lower()), None)
        if not chosen: chosen = selected if selected in models else models[0]
        reason = f"Profil {profile} · tâche {'approfondie' if deep else 'simple' if simple else 'standard'}"
        return chosen, reason

    def open_settings(self):
        dialog = QDialog(self); dialog.setWindowTitle(f"Paramètres L-GPT {APP_VERSION}"); dialog.resize(820, 610)
        tabs = QTabWidget(dialog); layout = QVBoxLayout(dialog); layout.addWidget(tabs)
        # Configuration IA
        ai = QWidget(); form = QFormLayout()
        profile = QComboBox(); profile.addItems(["Performance", "Équilibré", "Qualité"]); profile.setCurrentText(self.settings.get("profile", "Équilibré"))
        auto = QCheckBox("Choisir automatiquement le modèle selon la tâche"); auto.setChecked(self.settings.get("auto_model", True))
        context = QComboBox(); context.addItems(["8192", "16384", "32768", "65536"]); context.setCurrentText(str(self.settings.get("context", 16384)))
        kv = QComboBox(); kv.addItems(["f16", "q8_0", "q4_0"]); kv.setCurrentText(self.settings.get("kv_cache", "f16"))
        tokens = QComboBox(); tokens.addItems(["512", "1024", "2048", "4096", "8192"]); tokens.setCurrentText(str(self.settings.get("num_predict", 2048)))
        form.addRow("Profil de performance", profile); form.addRow("Routage", auto); form.addRow("Contexte (num_ctx)", context); form.addRow("Tokens de sortie maximum", tokens); form.addRow("Préférence cache KV", kv)
        note = QLabel("Le contexte et la limite de sortie sont appliqués à chaque requête Ollama. Le type de cache KV reste une préférence informative : Ollama le configure au niveau du serveur (OLLAMA_KV_CACHE_TYPE), pas par requête. Flash Attention et les options non prises en charge ne sont pas forcées."); note.setWordWrap(True); note.setObjectName("muted"); form.addRow(note)
        model_table = QTableWidget(0, 4); model_table.setHorizontalHeaderLabels(["Modèle", "Taille", "Quantification", "Détails"]); model_table.horizontalHeader().setStretchLastSection(True)
        try:
            result = ollama.list(); entries = result.get("models", []) if isinstance(result, dict) else getattr(result, "models", [])
            for entry in entries:
                get = (lambda k, d=None: entry.get(k,d)) if isinstance(entry,dict) else (lambda k,d=None: getattr(entry,k,d))
                name = get("model") or get("name") or "?"; size = get("size",0); size_text = f"{size/1e9:.1f} Go" if size else "—"
                try:
                    details_raw = ollama.show(name)
                    details = details_raw if isinstance(details_raw,dict) else {"details":getattr(details_raw,"details",{}) or {}, "model_info":getattr(details_raw,"modelinfo",{}) or {}}
                    quant = self._quantization_from_details(details)
                    family = (details.get("details",{}) or {}).get("family", "")
                    detail_text = family or "Métadonnées Ollama"
                except Exception: quant, detail_text = "Indisponible", "Détails indisponibles"
                row = model_table.rowCount(); model_table.insertRow(row)
                for col,val in enumerate((name,size_text,quant,detail_text)): model_table.setItem(row,col,QTableWidgetItem(str(val)))
        except Exception:
            model_table.setRowCount(1); model_table.setItem(0,0,QTableWidgetItem("Ollama indisponible"))
        resource_label = QLabel("État des modèles chargés : actualisation…")
        resource_label.setWordWrap(True); resource_label.setObjectName("muted")
        try:
            running = ollama.ps()
            running_entries = running.get("models", []) if isinstance(running, dict) else getattr(running, "models", [])
            if running_entries:
                lines = []
                for entry in running_entries:
                    getr = (lambda k, d=None: entry.get(k,d)) if isinstance(entry,dict) else (lambda k,d=None: getattr(entry,k,d))
                    name = getr("name") or getr("model") or "Modèle"
                    size = getr("size", 0) or 0
                    processor = getr("size_vram", 0) or 0
                    lines.append(f"{name} · {size/1e9:.1f} Go chargés · mémoire GPU rapportée {processor/1e9:.1f} Go")
                resource_label.setText("Modèles actuellement chargés :\n" + "\n".join(lines))
            else:
                resource_label.setText("Aucun modèle actuellement chargé (ollama ps). Les informations RAM/CPU/GPU détaillées ne sont pas exposées de façon uniforme par Ollama.")
        except Exception as exc:
            resource_label.setText(f"État des modèles indisponible : {exc}")
        ai_layout = QVBoxLayout(); ai_layout.addLayout(form); ai_layout.addWidget(QLabel("Modèles détectés localement")); ai_layout.addWidget(model_table); ai_layout.addWidget(resource_label); ai.setLayout(ai_layout)
        tabs.addTab(ai, "IA et modèles")
        # Mémoire
        mem = QWidget(); mem_layout = QVBoxLayout(mem)
        memory_table = QTableWidget(0,3); memory_table.setHorizontalHeaderLabels(["Catégorie", "Titre", "Contenu"]); memory_table.horizontalHeader().setStretchLastSection(True)
        def reload_memories():
            memory_table.setRowCount(0)
            for mid,cat,title,content,updated in self.store.memories():
                r=memory_table.rowCount(); memory_table.insertRow(r)
                for c,v in enumerate((cat,title,content)):
                    cell=QTableWidgetItem(str(v)); cell.setData(Qt.ItemDataRole.UserRole,mid); memory_table.setItem(r,c,cell)
        reload_memories(); mem_layout.addWidget(memory_table)
        mem_actions=QHBoxLayout(); add_mem=QPushButton("Ajouter une mémoire"); edit_mem=QPushButton("Modifier"); del_mem=QPushButton("Supprimer")
        def edit_memory(existing=None):
            d=QDialog(dialog); d.setWindowTitle("Mémoire L-GPT"); f=QFormLayout(d)
            cat=QComboBox(); cat.addItems(["Générale", "Projet"])
            title=QLineEdit(); content=QPlainTextEdit(); content.setMinimumHeight(120)
            if existing: cat.setCurrentText(existing[1]); title.setText(existing[2]); content.setPlainText(existing[3])
            f.addRow("Type",cat); f.addRow("Titre",title); f.addRow("Information",content)
            buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); buttons.accepted.connect(d.accept); buttons.rejected.connect(d.reject); f.addRow(buttons)
            if d.exec() and title.text().strip() and content.toPlainText().strip():
                self.store.save_memory(cat.currentText(),title.text().strip(),content.toPlainText().strip(),existing[0] if existing else None); reload_memories()
        add_mem.clicked.connect(lambda: edit_memory())
        def selected_memory():
            row=memory_table.currentRow()
            if row<0: return None
            item=memory_table.item(row,0); mid=item.data(Qt.ItemDataRole.UserRole)
            return next((x for x in self.store.memories() if x[0]==mid),None)
        edit_mem.clicked.connect(lambda: edit_memory(selected_memory()) if selected_memory() else None)
        def delete_selected_memory():
            item=selected_memory()
            if item and QMessageBox.question(dialog,"Supprimer la mémoire",f"Supprimer « {item[2]} » ?")==QMessageBox.StandardButton.Yes:
                self.store.delete_memory(item[0]); reload_memories()
        del_mem.clicked.connect(delete_selected_memory)
        for b in (add_mem,edit_mem,del_mem): mem_actions.addWidget(b)
        mem_layout.addLayout(mem_actions)
        mem_hint=QLabel("Les mémoires sont stockées localement et les plus pertinentes sont maintenant retrouvées automatiquement à chaque question. Elles sont ajoutées comme contexte auxiliaire (jamais comme preuve PDF). Vérifie et corrige les souvenirs depuis cet onglet."); mem_hint.setWordWrap(True); mem_hint.setObjectName("muted"); mem_layout.addWidget(mem_hint)
        tabs.addTab(mem,"Mémoire")
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); layout.addWidget(buttons)
        def save_settings():
            self.settings={"profile":profile.currentText(),"auto_model":auto.isChecked(),"context":int(context.currentText()),"kv_cache":kv.currentText(),"num_predict":int(tokens.currentText())}
            self.store.set_setting("runtime",self.settings); d=dialog; d.accept()
        buttons.accepted.connect(save_settings); buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def refresh_models(self):
        """Recharge la liste des modèles réellement installés dans le serveur Ollama."""
        try:
            result = ollama.list()
            entries = result.get("models", []) if isinstance(result, dict) else getattr(result, "models", [])
            names = []
            for entry in entries:
                name = entry.get("model") or entry.get("name") if isinstance(entry, dict) else (getattr(entry, "model", None) or getattr(entry, "name", None))
                if name and name not in names and name not in EMBEDDING_MODEL_NAMES and not name.startswith("nomic-embed-"):
                    names.append(name)
            names.sort(key=str.casefold)
            previous = self.model_combo.currentText()
            self.model_combo.clear()
            self.model_combo.addItems(names or FALLBACK_MODELS)
            self.installed_models = names
            if previous and self.model_combo.findText(previous) >= 0:
                self.model_combo.setCurrentText(previous)
            if names:
                self.model_hint.setText(f"{len(names)} modèle(s) détecté(s) · actualise avec ↻ après un ollama pull")
            else:
                self.model_hint.setText("Aucun modèle de conversation détecté dans Ollama")
            return True
        except Exception:
            self.model_combo.clear()
            self.model_combo.addItems(FALLBACK_MODELS)
            self.installed_models = []
            self.model_hint.setText("Ollama indisponible · modèles par défaut affichés")
            return False

    def _check_ollama(self):
        try:
            ollama.list()
            self.refresh_models()
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
        self.pdf_paths = paths; self.pdf_path = paths[0]
        name = f"{len(paths)} document(s) : " + ", ".join(Path(x).name for x in paths)
        self.doc_name.setText(name); self.doc_card_name.setText(name)
        self._start_indexing(paths)

    def _start_indexing(self, paths):
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
        self.summary_stop_event = Event()
        self.stop_summary_button.show()
        self.status.setText("◌  CRÉATION DE LA SYNTHÈSE"); self.status.setObjectName("statusBusy")
        self.index_label.setText("Préparation de la synthèse…")
        self.summary_thread = QThread(); self.summary_worker = SummaryWorker(list(self.pdf_paths), output, self.model_combo.currentText(), self.summary_stop_event)
        self.summary_worker.moveToThread(self.summary_thread)
        self.summary_thread.started.connect(self.summary_worker.run)
        self.summary_worker.progress.connect(self.index_label.setText)
        self.summary_worker.finished.connect(self.summary_done); self.summary_worker.failed.connect(self.summary_error)
        self.summary_worker.finished.connect(self.summary_thread.quit); self.summary_worker.failed.connect(self.summary_thread.quit)
        self.summary_thread.finished.connect(self.summary_worker.deleteLater); self.summary_thread.finished.connect(self.summary_thread.deleteLater)
        self.summary_thread.finished.connect(self.summary_thread_done); self.summary_thread.start()

    def stop_summary(self):
        if self.summary_stop_event is not None:
            self.summary_stop_event.set()
            self.stop_summary_button.setEnabled(False)
            self.index_label.setText("Arrêt demandé…")

    def summary_done(self, path):
        self.index_label.setText("Synthèse PDF créée avec succès")
        QMessageBox.information(self, "Synthèse terminée", f"Le PDF a été créé :\n{path}")

    def summary_error(self, error):
        if self.summary_stop_event is not None and self.summary_stop_event.is_set():
            self.index_label.setText("Synthèse interrompue par l'utilisateur")
            self.status.setText("●  SYNTHÈSE ARRÊTÉE")
            return
        self.index_label.setText("Échec de la création du PDF")
        QMessageBox.critical(self, "Impossible de créer la synthèse", error)

    def summary_thread_done(self):
        self.summary_button.setEnabled(bool(self.pdf_paths)); self.import_button.setEnabled(True)
        self.stop_summary_button.hide(); self.stop_summary_button.setEnabled(True)
        self.summary_stop_event = None
        self.summary_thread = self.summary_worker = None
        if self.status.text().find("ARRÊTÉE") < 0:
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

    def _conversation_title(self, messages):
        first = next((m.get("content", "") for m in messages if m.get("role") == "user"), "Conversation")
        title = first.strip().replace("\n", " ")[:42] or "Conversation"
        return title + ("…" if len(first.strip()) > 42 else "")

    def persist_current_conversation(self):
        if not self.transcript:
            return
        if self.current_title == "Nouvelle conversation":
            self.current_title = self._conversation_title(self.transcript)
            self.page_title.setText(self.current_title)
        self.store.save(self.conversation_id, self.current_title, self.transcript, self.pdf_paths)
        self.reload_conversations(select_id=self.conversation_id)

    def reload_conversations(self, select_id=None):
        self.history_list.clear(); self._history_items = {}
        for conv in self.store.list():
            stamp = conv["updated_at"].replace("T", " ")[:16]
            item = QListWidgetItem(f"◦  {conv['title']}\n    {stamp}")
            item.setData(Qt.ItemDataRole.UserRole, conv["id"])
            self.history_list.addItem(item); self._history_items[conv["id"]] = item
            if conv["id"] == select_id: self.history_list.setCurrentItem(item)

    def new_chat(self):
        if self.busy:
            QMessageBox.information(self, "Réponse en cours", "Attends la fin de la réponse avant de commencer une nouvelle conversation.")
            return
        self.persist_current_conversation()
        self.conversation_id = str(uuid.uuid4())
        self.transcript = []; self.history = []
        self.current_title = "Nouvelle conversation"
        self.page_title.setText("Votre espace intelligent")
        self._clear_chat(); self.show_welcome(); self.input.clear(); self.input.setFocus()
        self.history_list.clearSelection(); self.scroll_bottom()

    def restore_conversation(self, item):
        if self.busy: return
        conversation_id = item.data(Qt.ItemDataRole.UserRole)
        data = self.store.load(conversation_id)
        if not data: return
        self.conversation_id = conversation_id
        self.current_title = data["title"]
        self.transcript = data["messages"]
        # L'historique de contexte envoyé au modèle est limité aux deux derniers échanges.
        self.history = [{"role": m["role"], "content": m["content"]} for m in self.transcript[-4:]]
        self.pdf_paths = [path for path in data.get("pdf_paths", []) if Path(path).is_file()]
        self.pdf_path = self.pdf_paths[0] if self.pdf_paths else None
        self.chunks = self.embeddings = None
        self.summary_button.setEnabled(False)
        if self.pdf_paths:
            names = ", ".join(Path(x).name for x in self.pdf_paths)
            label = f"{len(self.pdf_paths)} document(s) : {names}"
            self.doc_name.setText(label); self.doc_card_name.setText(label)
            self.index_label.setText("Réindexation des PDF de cette conversation…")
            self._start_indexing(self.pdf_paths)
        else:
            self.doc_name.setText("Aucun document importé"); self.doc_card_name.setText("Aucun document sélectionné")
            self.index_label.setText("Aucun PDF associé · les questions générales restent disponibles")
        self.page_title.setText(self.current_title); self._clear_chat()
        for msg in self.transcript:
            self.add_message(msg.get("content", ""), "user" if msg.get("role") == "user" else "assistant")
        self.scroll_bottom()

    def rename_conversation(self):
        item = self.history_list.currentItem()
        if not item: return
        from PySide6.QtWidgets import QInputDialog
        conversation_id = item.data(Qt.ItemDataRole.UserRole)
        data = self.store.load(conversation_id)
        if not data: return
        title, ok = QInputDialog.getText(self, "Renommer la conversation", "Nouveau titre :", text=data["title"])
        if ok and title.strip():
            data["title"] = title.strip()
            self.store.save(conversation_id, title.strip(), data["messages"], data["pdf_paths"])
            if conversation_id == self.conversation_id:
                self.current_title = title.strip(); self.page_title.setText(self.current_title)
            self.reload_conversations(select_id=conversation_id)

    def delete_conversation(self):
        item = self.history_list.currentItem()
        if not item: return
        conversation_id = item.data(Qt.ItemDataRole.UserRole)
        answer = QMessageBox.question(self, "Supprimer", "Supprimer définitivement cette conversation ?")
        if answer != QMessageBox.StandardButton.Yes: return
        self.store.delete(conversation_id)
        if conversation_id == self.conversation_id:
            self.conversation_id = str(uuid.uuid4()); self.transcript = []; self.history = []
            self.current_title = "Nouvelle conversation"; self.page_title.setText("Votre espace intelligent")
            self._clear_chat(); self.show_welcome()
        self.reload_conversations()

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

    def _relevant_memory_context(self, question):
        """Retrouve les souvenirs par recouvrement lexical simple, sans envoyer toute la mémoire."""
        stopwords = {"avec", "dans", "pour", "mais", "donc", "une", "des", "les", "sur", "que", "qui", "quoi", "comment", "pourquoi", "est", "sont", "aux", "mon", "mes", "ton", "tes", "cette", "cela", "plus", "moins", "faire", "fait", "peux", "peut", "veux", "voudrais"}
        words = {w for w in re.findall(r"[a-zA-ZÀ-ÿ0-9_-]{3,}", question.lower()) if w not in stopwords}
        ranked = []
        for mid, category, title, content, updated in self.store.memories():
            text = f"{title} {content} {category}"
            terms = {w for w in re.findall(r"[a-zA-ZÀ-ÿ0-9_-]{3,}", text.lower()) if w not in stopwords}
            overlap = len(words & terms)
            # Les projets sont légèrement favorisés lorsqu'un terme du titre correspond.
            title_terms = {w for w in re.findall(r"[a-zA-ZÀ-ÿ0-9_-]{3,}", title.lower()) if w not in stopwords}
            score = overlap + (2 if words & title_terms else 0)
            if score > 0:
                ranked.append((score, category, title, content))
        ranked.sort(key=lambda x: x[0], reverse=True)
        selected = ranked[:5]
        if not selected:
            return ""
        return "\n\n".join(f"[{cat} — {title}]\n{content[:1800]}" for _, cat, title, content in selected)[:6500]

    def send_message(self):
        if self.busy: return
        question = self.input.toPlainText().strip()
        if not question: return
        if self.index_thread is not None:
            QMessageBox.information(self,"Indexation en cours","Attends la fin de l’indexation avant de poser ta question."); return
        self.input.clear(); self.page_title.setText(question[:48] + ("…" if len(question)>48 else ""))
        self.add_message(question,"user"); self.assistant_browser = self.add_message("", "assistant"); self.stream_text = ""
        self.transcript.append({"role": "user", "content": question})
        self.persist_current_conversation()
        self.busy = True; self.send_btn.hide(); self.stop_chat_btn.show(); self.stop_chat_btn.setEnabled(True)
        self.chat_stop_event = Event()
        self.input.setEnabled(False); self.import_button.setEnabled(False)
        self.status.setText("◌  L-GPT RÉFLÉCHIT"); self.status.setObjectName("statusBusy"); self.status.style().unpolish(self.status); self.status.style().polish(self.status)
        chosen_model, route_reason = self._choose_model(question)
        self.generation_started = perf_counter()
        self.model_hint.setText(f"{chosen_model} · {route_reason}")
        self.chat_thread = QThread(); runtime_options = {"num_ctx": int(self.settings.get("context", 16384)), "num_predict": int(self.settings.get("num_predict", 2048))}
        memory_context = self._relevant_memory_context(question)
        if memory_context:
            self.model_hint.setText(f"{chosen_model} · {route_reason} · mémoire pertinente injectée")
        self.chat_worker = ChatWorker(question,self.chunks or [],self.embeddings or [],list(self.history),chosen_model,self.mode_combo.currentText(),self.chat_stop_event,runtime_options,memory_context)
        self.chat_worker.moveToThread(self.chat_thread); self.chat_thread.started.connect(self.chat_worker.run)
        self.chat_worker.token.connect(self.on_token); self.chat_worker.finished.connect(self.on_answer_finished); self.chat_worker.failed.connect(self.on_answer_error)
        self.chat_worker.finished.connect(self.chat_thread.quit); self.chat_worker.failed.connect(self.chat_thread.quit)
        self.chat_thread.finished.connect(self.chat_worker.deleteLater); self.chat_thread.finished.connect(self.chat_thread.deleteLater); self.chat_thread.finished.connect(self.chat_thread_done)
        self.chat_thread.start()

    def stop_chat(self):
        if self.chat_stop_event is not None:
            self.chat_stop_event.set()
            self.stop_chat_btn.setEnabled(False)
            self.status.setText("◌  ARRÊT DE LA GÉNÉRATION…")

    def on_token(self, token):
        self.stream_text += token; self.assistant_browser.set_chat_markdown(self.stream_text); self.scroll_bottom()

    def on_answer_finished(self, response, sources, history, source_mode):
        self.history = history
        elapsed = max(0.001, perf_counter() - getattr(self, "generation_started", perf_counter()))
        estimated_tokens = max(1, round(len(response) / 4))
        speed = estimated_tokens / elapsed
        text = response + f"\n\n---\n*Source utilisée : **{source_mode}***\n*Temps total : {elapsed:.1f} s · environ {estimated_tokens} tokens · {speed:.1f} tokens/s (estimation à partir du texte)*"
        if sources:
            text += "\n\n---\n\n### Sources du document\n"
            for source in sources:
                page = source.get("page", "?") if isinstance(source,dict) else "?"
                chunk = source.get("chunk", "") if isinstance(source,dict) else ""
                filename = source.get("source", "PDF") if isinstance(source,dict) else "PDF"
                text += f"\n- **{filename}** · page **{page}**" + (f" · passage {chunk}" if chunk else "")
        self.assistant_browser.set_chat_markdown(text); self.scroll_bottom()
        self.transcript.append({"role": "assistant", "content": text})
        self.persist_current_conversation()
        self.status.setText("●  RÉPONSE TERMINÉE"); self.status.setObjectName("status"); self.status.style().unpolish(self.status); self.status.style().polish(self.status)

    def on_answer_error(self, error):
        if self.chat_stop_event is not None and self.chat_stop_event.is_set():
            partial = self.stream_text.strip()
            stopped_text = (partial + "\n\n*— Génération arrêtée.*") if partial else "*Génération arrêtée.*"
            self.assistant_browser.set_chat_markdown(stopped_text)
            self.transcript.append({"role": "assistant", "content": stopped_text})
            self.persist_current_conversation()
            self.status.setText("●  GÉNÉRATION ARRÊTÉE")
            return
        error_text = "**Une erreur est survenue :**\n\n" + error
        self.assistant_browser.set_chat_markdown(error_text)
        self.transcript.append({"role": "assistant", "content": error_text})
        self.persist_current_conversation()
        self.status.setText("●  ERREUR")

    def chat_thread_done(self):
        self.busy = False; self.stop_chat_btn.hide(); self.stop_chat_btn.setEnabled(True)
        self.send_btn.show(); self.send_btn.setEnabled(True); self.input.setEnabled(True); self.import_button.setEnabled(True)
        self.input.setFocus(); self.chat_thread = self.chat_worker = None
        self.chat_stop_event = None
        if self.status.text().find("ERREUR") < 0 and self.status.text().find("ARRÊTÉE") < 0:
            self.status.setText("●  OLLAMA CONNECTÉ"); self.status.setObjectName("status"); self.status.style().unpolish(self.status); self.status.style().polish(self.status)

    def closeEvent(self, event):
        if self.busy or self.index_thread is not None or self.summary_thread is not None:
            QMessageBox.information(self,"Opération en cours","Attends la fin de la génération ou de l'indexation avant de fermer L-GPT."); event.ignore(); return
        self.persist_current_conversation()
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
    app.setFont(QFont())
    window = MainWindow(); window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
