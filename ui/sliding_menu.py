from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QRect
from PyQt6.QtGui import QFont, QColor

class SlidingMenuWidget(QFrame):
    """上から下にスライドするメニューウィジェット（Live2D対応版）"""
    
    # シグナル定義
    # 音声モデル関連
    load_model_clicked = pyqtSignal()
    load_from_history_clicked = pyqtSignal()
    
    # 画像関連
    load_image_clicked = pyqtSignal()
    load_image_from_history_clicked = pyqtSignal()
    
    # Live2D関連（新規追加）
    load_live2d_clicked = pyqtSignal()
    load_live2d_from_history_clicked = pyqtSignal()
    
    menu_closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.is_visible = False
        self.target_height = 320  # Live2D項目追加で高さを拡張
        
        self.init_ui()
        self.setup_animation()
        self.setup_shadow()
        
        # 初期状態は非表示
        self.hide()
        
    def init_ui(self):
        """UIを初期化（Live2D項目追加版）"""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-top: none;
                border-radius: 0px 0px 8px 8px;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 12px 20px;
                text-align: left;
                font-size: 13px;
                color: #333;
            }
            QPushButton:hover {
                background-color: #f0f7ff;
                color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #e3f2fd;
            }
            QPushButton:disabled {
                color: #999;
                background-color: #f5f5f5;
            }
        """)
        
        # レイアウト
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # === 音声モデル関連 ===
        model_section_label = self.create_section_label("🎤 音声モデル")
        layout.addWidget(model_section_label)
        
        self.load_model_btn = QPushButton("📂 音声モデルを読み込み")
        self.load_model_btn.setToolTip("Style-Bert-VITS2モデルを読み込む")
        self.load_model_btn.clicked.connect(self.on_load_model_clicked)
        
        self.load_history_btn = QPushButton("📋 音声モデルを履歴から読み込み")
        self.load_history_btn.setToolTip("過去に読み込んだモデルから選択")
        self.load_history_btn.clicked.connect(self.on_load_from_history_clicked)
        
        layout.addWidget(self.load_model_btn)
        layout.addWidget(self.load_history_btn)
        
        # セパレーター
        separator1 = self.create_separator()
        layout.addWidget(separator1)
        
        # === 画像・キャラクター関連 ===
        image_section_label = self.create_section_label("🎨 キャラクター")
        layout.addWidget(image_section_label)
        
        self.load_image_btn = QPushButton("🖼️ 立ち絵画像を読み込み")
        self.load_image_btn.setToolTip("PNG/JPEG画像を立ち絵として読み込む")
        self.load_image_btn.clicked.connect(self.on_load_image_clicked)
        
        self.load_image_history_btn = QPushButton("📸 立ち絵を履歴から読み込み")
        self.load_image_history_btn.setToolTip("過去に読み込んだ立ち絵から選択")
        self.load_image_history_btn.clicked.connect(self.on_load_image_from_history_clicked)
        self.load_image_history_btn.setEnabled(True)
        
        layout.addWidget(self.load_image_btn)
        layout.addWidget(self.load_image_history_btn)
        
        # === Live2D関連（新規追加） ===
        separator2 = self.create_separator()
        layout.addWidget(separator2)
        
        live2d_section_label = self.create_section_label("🎭 Live2D")
        layout.addWidget(live2d_section_label)
        
        self.load_live2d_btn = QPushButton("🎪 Live2Dモデルを読み込み")
        self.load_live2d_btn.setToolTip("Live2Dモデルフォルダを読み込む")
        self.load_live2d_btn.clicked.connect(self.on_load_live2d_clicked)
        
        self.load_live2d_history_btn = QPushButton("🎭 Live2Dを履歴から読み込み")
        self.load_live2d_history_btn.setToolTip("過去に読み込んだLive2Dモデルから選択")
        self.load_live2d_history_btn.clicked.connect(self.on_load_live2d_from_history_clicked)
        
        layout.addWidget(self.load_live2d_btn)
        layout.addWidget(self.load_live2d_history_btn)
        
        layout.addStretch()
    
    def create_section_label(self, text):
        """セクションラベルを作成"""
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                color: #495057;
                border: none;
                padding: 6px 20px;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        return label
    
    def create_separator(self):
        """セパレーターを作成"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("color: #eee; margin: 4px 10px;")
        return separator
        
    def setup_shadow(self):
        """ドロップシャドウエフェクトを設定"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
    def setup_animation(self):
        """アニメーションを設定"""
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuint) 
        self.animation.finished.connect(self.on_animation_finished)
        
    def show_menu(self):
        """メニューを表示（スライドイン）"""
        if self.is_visible:
            return
            
        if self.parent_widget:
            menubar = self.parent_widget.menuBar()
            menubar_height = menubar.height()
            parent_width = self.parent_widget.width()
            
            start_rect = QRect(0, menubar_height, parent_width, 0)
            end_rect = QRect(0, menubar_height, parent_width, self.target_height)
            
            self.setGeometry(start_rect)
            self.show()
            self.raise_()
            
            self.animation.setStartValue(start_rect)
            self.animation.setEndValue(end_rect)
            self.animation.start()
            
            self.is_visible = True
    
    def hide_menu(self):
        """メニューを非表示（スライドアウト）"""
        if not self.is_visible:
            return
            
        current_rect = self.geometry()
        end_rect = QRect(current_rect.x(), current_rect.y(), current_rect.width(), 0)
        
        self.animation.setStartValue(current_rect)
        self.animation.setEndValue(end_rect)
        self.animation.start()
        
        self.is_visible = False
    
    def on_animation_finished(self):
        """アニメーション完了時の処理"""
        if not self.is_visible:
            self.hide()
    
    def toggle_menu(self):
        """メニューの表示/非表示を切り替え"""
        if self.is_visible:
            self.hide_menu()
        else:
            self.show_menu()
    
    # === 音声モデル関連のイベントハンドラー ===
    def on_load_model_clicked(self):
        """音声モデル読み込みボタンクリック"""
        self.hide_menu()
        self.load_model_clicked.emit()
    
    def on_load_from_history_clicked(self):
        """音声モデル履歴から読み込みボタンクリック"""
        self.hide_menu()
        self.load_from_history_clicked.emit()
    
    # === 画像関連のイベントハンドラー ===
    def on_load_image_clicked(self):
        """立ち絵画像読み込みボタンクリック"""
        self.hide_menu()
        self.load_image_clicked.emit()
    
    def on_load_image_from_history_clicked(self):
        """立ち絵履歴から読み込みボタンクリック"""
        self.hide_menu()
        self.load_image_from_history_clicked.emit()
    
    # === Live2D関連のイベントハンドラー（新規追加） ===
    def on_load_live2d_clicked(self):
        """Live2D読み込みボタンクリック"""
        self.hide_menu()
        self.load_live2d_clicked.emit()
    
    def on_load_live2d_from_history_clicked(self):
        """Live2D履歴から読み込みボタンクリック"""
        self.hide_menu()
        self.load_live2d_from_history_clicked.emit()
    
    def mousePressEvent(self, event):
        """マウスクリックイベント（メニュー内クリックは伝播させない）"""
        event.accept()
        super().mousePressEvent(event)