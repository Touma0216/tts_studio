from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap
from pathlib import Path

class ImageHistoryItem(QWidget):
    """画像履歴項目：名前＋メモ、✎改名・×削除・読み込み。黒縁は常時。"""
    load_requested = pyqtSignal(str)       # image_id
    edit_requested = pyqtSignal(str)       # image_id
    delete_requested = pyqtSignal(str)     # image_id
    note_changed   = pyqtSignal(str, str)  # (image_id, note)

    def __init__(self, image_data, parent=None):
        super().__init__(parent)
        self.image_data = image_data
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

        self.name_label = QLabel(self.image_data['name'])
        self.name_label.setFont(QFont("", 10, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color:#333;")
        top.addWidget(self.name_label, 1)

        # 画像パス表示（小さく）
        image_path = self.image_data.get('image_path', '')
        if image_path:
            path_label = QLabel(f"📁 {Path(image_path).name}")
            path_label.setStyleSheet("color:#666; font-size:9px;")
            path_label.setWordWrap(True)
        
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
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.image_data['id']))
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
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.image_data['id']))
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
        load_btn.clicked.connect(lambda: self.load_requested.emit(self.image_data['id']))
        top.addWidget(load_btn)

        # 中段：画像パス表示
        if image_path:
            middle = QHBoxLayout()
            middle.addWidget(path_label)
            middle.addStretch()

        # 下段：メモ
        self.note_edit = QLineEdit(self.image_data.get('note', ""))
        self.note_edit.setPlaceholderText("この画像のメモ（任意）")
        self.note_edit.setStyleSheet("""
            QLineEdit {
                padding:6px 8px; background:#fff;
                border:1px solid #cccccc; border-radius:4px; color:#444;
            }
            QLineEdit:focus { border:1px solid #888888; }
        """)
        self.note_edit.textEdited.connect(self._on_note_edited)
        self._note_timer.timeout.connect(
            lambda: self.note_changed.emit(self.image_data['id'], self.note_edit.text())
        )

        root.addLayout(top)
        if image_path:
            root.addLayout(middle)
        root.addWidget(self.note_edit)

        # アイテム自体の黒縁（常時）
        self.setStyleSheet("background:white; border:1px solid #cccccc; border-radius:6px;")

    def _on_note_edited(self, _):
        self._note_timer.start()

class ImageHistoryWidget(QWidget):
    """画像履歴表示（音声モデル履歴と同じ仕組み）"""
    image_selected = pyqtSignal(dict)  # 選択された画像データ

    def __init__(self, image_manager, parent=None):
        super().__init__(parent)
        self.image_manager = image_manager
        self._build()
        self.refresh_list()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        title = QLabel("画像履歴")
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
        images = self.image_manager.get_all_images()
        if not images:
            it = QListWidgetItem()
            empty = QLabel("履歴がありません")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color:#999; padding:24px;")
            self.list.addItem(it)
            self.list.setItemWidget(it, empty)
            return

        for img in images:
            it = QListWidgetItem()
            w = ImageHistoryItem(img)
            w.load_requested.connect(self.load_image)
            w.edit_requested.connect(self.edit_image_name)
            w.delete_requested.connect(self.delete_image)
            w.note_changed.connect(self.update_image_note)
            it.setSizeHint(w.sizeHint())
            self.list.addItem(it)
            self.list.setItemWidget(it, w)

    def load_image(self, image_id):
        img = self.image_manager.get_image_by_id(image_id)
        if img:
            # 画像ファイルの存在確認
            if not Path(img['image_path']).exists():
                QMessageBox.warning(self, "エラー", 
                    f"画像ファイルが見つかりません:\n{img['image_path']}")
                return
            
            # 履歴の先頭に移動（image_manager.add_imageが自動的に行う）
            self.image_manager.add_image(img['image_path'], img['name'])
            self.image_selected.emit(img)
            self.refresh_list()

    def edit_image_name(self, image_id):
        img = self.image_manager.get_image_by_id(image_id)
        if not img:
            return
        from PyQt6.QtWidgets import QInputDialog
        new, ok = QInputDialog.getText(self, "画像名を編集", "新しい画像名:", text=img['name'])
        if ok and new.strip():
            self.image_manager.update_image_name(image_id, new.strip())
            self.refresh_list()

    def update_image_note(self, image_id, note):
        """画像のメモを更新"""
        self.image_manager.update_note(image_id, note)

    def delete_image(self, image_id):
        if not self.image_manager.get_image_by_id(image_id):
            return
        
        reply = QMessageBox.question(
            self, "確認", "この画像を履歴から削除しますか？\n（画像ファイル自体は削除されません）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.image_manager.remove_image(image_id)
            self.refresh_list()

    def clear_history(self):
        reply = QMessageBox.question(
            self, "確認", "すべての画像履歴を削除しますか？\n（画像ファイル自体は削除されません）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.image_manager.images = []
            self.image_manager.save_history(quiet=True)
            self.refresh_list()