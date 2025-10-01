from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QListWidget, QListWidgetItem, QLabel, QMessageBox,
                             QFrame, QSizePolicy, QSpacerItem)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QIcon

class Live2DHistoryWidget(QWidget):
    """Live2D履歴表示・選択ウィジェット"""
    
    model_selected = pyqtSignal(dict)  # モデルデータを送信
    
    def __init__(self, live2d_manager, parent=None):
        super().__init__(parent)
        self.live2d_manager = live2d_manager
        self.current_models = []
        
        self.init_ui()
        self.load_model_history()

    def init_ui(self):
        self.setStyleSheet("QWidget { background-color: #f8f9fa; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # タイトル
        title_label = QLabel("Live2Dモデル履歴")
        title_label.setFont(QFont("", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #333; padding: 5px 0;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 説明文
        description_label = QLabel("過去に読み込んだLive2Dモデルから選択してください。")
        description_label.setStyleSheet("color: #666; font-size: 11px; padding: 0 5px;")
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description_label)
        
        # 区切り線
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setStyleSheet("color: #dee2e6;")
        layout.addWidget(divider)
        
        # モデルリスト
        self.model_list = QListWidget()
        self.model_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 5px;
                font-size: 12px;
            }
            QListWidget::item {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                margin: 2px;
                padding: 8px;
                min-height: 60px;
            }
            QListWidget::item:selected {
                background-color: #e7f3ff;
                border-color: #007bff;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
                border-color: #adb5bd;
            }
        """)
        self.model_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.model_list.itemDoubleClicked.connect(self.on_model_double_clicked)
        layout.addWidget(self.model_list, 1)
        
        # ボタンエリア
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 更新")
        self.refresh_btn.setStyleSheet(self._get_button_style("#6c757d"))
        self.refresh_btn.setMinimumHeight(35)
        self.refresh_btn.clicked.connect(self.refresh_history)
        
        self.delete_btn = QPushButton("🗑️ 削除")
        self.delete_btn.setStyleSheet(self._get_button_style("#dc3545"))
        self.delete_btn.setMinimumHeight(35)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected_model)
        
        self.select_btn = QPushButton("✅ 選択")
        self.select_btn.setStyleSheet(self._get_button_style("#28a745"))
        self.select_btn.setMinimumHeight(35)
        self.select_btn.setEnabled(False)
        self.select_btn.clicked.connect(self.select_current_model)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.select_btn)
        
        layout.addLayout(button_layout)
        
        # 選択変更時の処理
        self.model_list.itemSelectionChanged.connect(self.on_selection_changed)

    def _get_button_style(self, color: str) -> str:
        """ボタンのスタイルシートを生成"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 16px;
            }}
            QPushButton:hover:enabled {{
                background-color: {self._darken_color(color)};
            }}
            QPushButton:pressed:enabled {{
                background-color: {self._darken_color(color, 0.3)};
            }}
            QPushButton:disabled {{
                background-color: #f0f0f0;
                color: #aaaaaa;
            }}
        """

    def _darken_color(self, hex_color: str, factor: float = 0.15) -> str:
        """色を暗くする"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(max(0, int(c * (1 - factor))) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"

    def load_model_history(self):
        """Live2Dモデル履歴を読み込み"""
        self.model_list.clear()
        self.current_models = []
        
        models = self.live2d_manager.get_all_models()
        if not models:
            # 履歴が空の場合
            item = QListWidgetItem("📭 Live2Dモデル履歴がありません")
            item.setFlags(Qt.ItemFlag.NoItemFlags)  # 選択不可
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.model_list.addItem(item)
            return
        
        self.current_models = models
        
        for model_data in models:
            self.add_model_item(model_data)

    def add_model_item(self, model_data):
        """Live2Dモデルアイテムをリストに追加"""
        model_path = model_data['model_folder_path']
        model_name = model_data['name']
        
        # フォルダの存在確認
        folder_exists = Path(model_path).exists()
        
        # アイテム作成
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, model_data)
        
        # アイテムウィジェット作成
        item_widget = self.create_model_item_widget(model_data, folder_exists)
        item.setSizeHint(item_widget.sizeHint())
        
        self.model_list.addItem(item)
        self.model_list.setItemWidget(item, item_widget)

    def create_model_item_widget(self, model_data, folder_exists):
        """Live2Dモデルアイテムウィジェット作成"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)
        
        # アイコン部分
        icon_label = QLabel()
        if folder_exists:
            icon_label.setText("🎭")
            icon_label.setStyleSheet("font-size: 24px; color: #8e44ad;")
        else:
            icon_label.setText("❌")
            icon_label.setStyleSheet("font-size: 24px; color: #dc3545;")
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # 情報部分
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        # モデル名
        name_label = QLabel(model_data['name'])
        name_label.setFont(QFont("", 11, QFont.Weight.Bold))
        if folder_exists:
            name_label.setStyleSheet("color: #333;")
        else:
            name_label.setStyleSheet("color: #dc3545;")
        info_layout.addWidget(name_label)
        
        # フォルダパス
        path_label = QLabel(model_data['model_folder_path'])
        path_label.setStyleSheet("color: #666; font-size: 10px;")
        path_label.setWordWrap(False)
        # パスが長い場合は省略
        if len(model_data['model_folder_path']) > 60:
            short_path = "..." + model_data['model_folder_path'][-57:]
            path_label.setText(short_path)
        path_label.setToolTip(model_data['model_folder_path'])
        info_layout.addWidget(path_label)
        
        # 日時情報
        last_used = datetime.fromisoformat(model_data['last_used'])
        time_str = last_used.strftime("%Y年%m月%d日 %H:%M")
        
        # フォルダ情報
        if folder_exists:
            model_info = self.live2d_manager.get_model_info(model_data['model_folder_path'])
            folder_size = model_info['folder_size'] / 1024 / 1024  # MB
            detail_text = f"📅 最終使用: {time_str} | 📐 ファイル数: {model_info['file_count']} | 💾 {folder_size:.1f} MB"
            detail_color = "#666"
        else:
            detail_text = f"⚠️ フォルダが見つかりません | 📅 最終使用: {time_str}"
            detail_color = "#dc3545"
        
        detail_label = QLabel(detail_text)
        detail_label.setStyleSheet(f"color: {detail_color}; font-size: 9px;")
        info_layout.addWidget(detail_label)
        
        layout.addLayout(info_layout, 1)
        
        # 状態インジケータ
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        if folder_exists:
            # 検証結果
            validation = self.live2d_manager.validate_model_folder(model_data['model_folder_path'])
            if validation['is_valid']:
                status_label = QLabel("✅")
                status_label.setToolTip("有効なLive2Dモデル")
                status_label.setStyleSheet("font-size: 16px; color: #28a745;")
            else:
                status_label = QLabel("⚠️")
                status_label.setToolTip("不完全なモデルファイル")
                status_label.setStyleSheet("font-size: 16px; color: #ffc107;")
        else:
            status_label = QLabel("❌")
            status_label.setToolTip("フォルダが見つかりません")
            status_label.setStyleSheet("font-size: 16px; color: #dc3545;")
        
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(status_label)
        status_layout.addStretch()
        
        layout.addLayout(status_layout)
        
        return widget

    def on_selection_changed(self):
        """選択変更時の処理"""
        selected_items = self.model_list.selectedItems()
        has_selection = len(selected_items) > 0
        
        self.delete_btn.setEnabled(has_selection)
        
        if has_selection:
            item = selected_items[0]
            model_data = item.data(Qt.ItemDataRole.UserRole)
            if model_data:
                folder_exists = Path(model_data['model_folder_path']).exists()
                validation = self.live2d_manager.validate_model_folder(model_data['model_folder_path'])
                self.select_btn.setEnabled(folder_exists and validation['is_valid'])
            else:
                self.select_btn.setEnabled(False)
        else:
            self.select_btn.setEnabled(False)

    def on_model_double_clicked(self, item):
        """Live2Dモデルダブルクリック時"""
        model_data = item.data(Qt.ItemDataRole.UserRole)
        if model_data:
            folder_exists = Path(model_data['model_folder_path']).exists()
            validation = self.live2d_manager.validate_model_folder(model_data['model_folder_path'])
            if folder_exists and validation['is_valid']:
                self.model_selected.emit(model_data)
            else:
                if not folder_exists:
                    QMessageBox.warning(self, "エラー", "Live2Dモデルフォルダが見つかりません。")
                else:
                    QMessageBox.warning(self, "エラー", "Live2Dモデルファイルが不完全です。")

    def select_current_model(self):
        """現在選択されているLive2Dモデルを選択"""
        selected_items = self.model_list.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        model_data = item.data(Qt.ItemDataRole.UserRole)
        if model_data:
            self.model_selected.emit(model_data)

    def delete_selected_model(self):
        """選択されたLive2Dモデルを履歴から削除"""
        selected_items = self.model_list.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        model_data = item.data(Qt.ItemDataRole.UserRole)
        if not model_data:
            return
        
        # 確認ダイアログ
        reply = QMessageBox.question(
            self, "削除確認",
            f"以下のLive2Dモデルを履歴から削除しますか？\n\n"
            f"モデル名: {model_data['name']}\n"
            f"フォルダ: {model_data['model_folder_path']}\n\n"
            f"※実際のファイルは削除されません",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 履歴から削除
            if self.live2d_manager.remove_model(model_data['id']):
                QMessageBox.information(self, "削除完了", "Live2Dモデルを履歴から削除しました。")
                self.refresh_history()
            else:
                QMessageBox.warning(self, "エラー", "Live2Dモデルの削除に失敗しました。")

    def refresh_history(self):
        """履歴を更新"""
        self.load_model_history()
        QMessageBox.information(self, "更新完了", "Live2D履歴を更新しました。")