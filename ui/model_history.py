from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

class ModelHistoryItem(QWidget):
    """名前＋メモ、✎改名・×削除・読み込み。黒縁は常時。"""
    load_requested = pyqtSignal(str)       # model_id
    edit_requested = pyqtSignal(str)       # model_id
    delete_requested = pyqtSignal(str)     # model_id
    note_changed   = pyqtSignal(str, str)  # (model_id, note)

    def __init__(self, model_data, parent=None):
        super().__init__(parent)
        self.model_data = model_data
        self._note_timer = QTimer(self)
        self._note_timer.setSingleShot(True)
        self._note_timer.setInterval(400)  # デバウンス 0.4s
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # 上段：名前＋アクション
        top = QHBoxLayout()
        top.setSpacing(8)

        self.name_label = QLabel(self.model_data['name'])
        self.name_label.setFont(QFont("", 10, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color:#333;")
        top.addWidget(self.name_label, 1)

        edit_btn = QPushButton("✎")
        edit_btn.setFixedSize(28, 28)
        edit_btn.setToolTip("名前を編集")
        edit_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #757575;
                border: 1px solid #e0e0e0; border-radius: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #f2f2f2; }
        """)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.model_data['id']))
        top.addWidget(edit_btn)

        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(28, 28)
        delete_btn.setToolTip("履歴から削除")
        delete_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #f44336;
                border: 1px solid #ffcdd2; border-radius: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #ffebee; }
        """)
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.model_data['id']))
        top.addWidget(delete_btn)

        load_btn = QPushButton("読み込み")
        load_btn.setFixedSize(82, 30)
        load_btn.setStyleSheet("""
            QPushButton {
                background-color:#2196f3; color:white; border:none; border-radius:6px;
                font-size:10pt; font-weight:bold; padding:0 10px;
            }
            QPushButton:hover { background-color:#1976d2; }
        """)
        load_btn.clicked.connect(lambda: self.load_requested.emit(self.model_data['id']))
        top.addWidget(load_btn)

        # 下段：メモ
        self.note_edit = QLineEdit(self.model_data.get('note', ""))
        self.note_edit.setPlaceholderText("このモデルのメモ（任意）")
        self.note_edit.setStyleSheet("""
            QLineEdit {
                padding:6px 8px; background:#fff;
                border:1px solid #cccccc; border-radius:4px; color:#444;
            }
            QLineEdit:focus { border:1px solid #888888; }
        """)
        self.note_edit.textEdited.connect(self._on_note_edited)
        self._note_timer.timeout.connect(
            lambda: self.note_changed.emit(self.model_data['id'], self.note_edit.text())
        )

        root.addLayout(top)
        root.addWidget(self.note_edit)

        # アイテム自体の黒縁（常時）
        self.setStyleSheet("background:white; border:1px solid #cccccc; border-radius:6px;")

    def _on_note_edited(self, _):
        self._note_timer.start()

class ModelHistoryWidget(QWidget):
    """モデル履歴表示（シンプル）"""
    model_selected = pyqtSignal(dict)  # 選択されたモデルデータ

    def __init__(self, model_manager, parent=None):
        super().__init__(parent)
        self.model_manager = model_manager
        self._build()
        self.refresh_list()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        title = QLabel("モデル履歴")
        title.setFont(QFont("", 10, QFont.Weight.Bold))
        title.setStyleSheet("color:#333; padding:4px 0;")

        self.list = QListWidget()
        self.list.setStyleSheet("""
            QListWidget { border: 1px solid #ddd; border-radius: 6px; background: #fafafa; }
            QListWidget::item { margin: 8px; }
            QListWidget::item:selected { background: #e3f2fd; }  /* 枠いじらない */
            QListWidget::item:focus { outline: none; }            /* 点線殺す */
        """)

        clear = QPushButton("履歴をクリア")
        clear.setStyleSheet("""
            QPushButton { color:#666; border:1px solid #ddd; border-radius:6px; padding:4px 10px; font-size:9pt; }
            QPushButton:hover { background:#f5f5f5; }
        """)
        clear.clicked.connect(self.clear_history)

        footer = QHBoxLayout()
        footer.addStretch()
        footer.addWidget(clear)

        root.addWidget(title)
        root.addWidget(self.list, 1)
        root.addLayout(footer)

    def refresh_list(self):
        self.list.clear()
        models = self.model_manager.get_all_models()
        if not models:
            it = QListWidgetItem()
            empty = QLabel("履歴がありません")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color:#999; padding:24px;")
            self.list.addItem(it)
            self.list.setItemWidget(it, empty)
            return

        for m in models:
            it = QListWidgetItem()
            w = ModelHistoryItem(m)
            w.load_requested.connect(self.load_model)
            w.edit_requested.connect(self.edit_model_name)
            w.delete_requested.connect(self.delete_model)
            w.note_changed.connect(self.update_model_note)
            it.setSizeHint(w.sizeHint())
            self.list.addItem(it)
            self.list.setItemWidget(it, w)

    def load_model(self, model_id):
        m = self.model_manager.get_model_by_id(model_id)
        if m:
            # update_last_used は削除済みなので呼ばない
            self.model_selected.emit(m)
            self.refresh_list()

    def edit_model_name(self, model_id):
        m = self.model_manager.get_model_by_id(model_id)
        if not m:
            return
        from PyQt6.QtWidgets import QInputDialog
        new, ok = QInputDialog.getText(self, "モデル名を編集", "新しいモデル名:", text=m['name'])
        if ok and new.strip():
            self.model_manager.update_model_name(model_id, new.strip())
            self.refresh_list()

    def update_model_note(self, model_id, note):
        self.model_manager.update_note(model_id, note)

    def delete_model(self, model_id):
        if not self.model_manager.get_model_by_id(model_id):
            return
        self.model_manager.remove_model(model_id)
        self.refresh_list()

    def clear_history(self):
        reply = QMessageBox.question(
            self, "確認", "すべての履歴を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.model_manager.models = []
            self.model_manager.save_history(quiet=True)
            self.refresh_list()
