from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QRect
from PyQt6.QtGui import QFont, QColor

class SlidingMenuWidget(QFrame):
    """上から下にスライドするメニューウィジェット"""
    
    # シグナル定義
    load_model_clicked = pyqtSignal()
    load_from_history_clicked = pyqtSignal()
    menu_closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.is_visible = False
        self.target_height = 120  # 展開時の高さ
        
        self.init_ui()
        self.setup_animation()
        self.setup_shadow()
        
        # 初期状態は非表示
        self.hide()
        
    def init_ui(self):
        """UIを初期化"""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        
        # --- スタイルシートを修正（box-shadowを削除） ---
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-top: none;
                border-radius: 0px 0px 8px 8px; /* 角の丸みを少し大きく */
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
        """)
        
        # レイアウト
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # メニュー項目
        self.load_model_btn = QPushButton("📂 モデルを読み込み")
        self.load_model_btn.setToolTip("Style-Bert-VITS2モデルを読み込む")
        self.load_model_btn.clicked.connect(self.on_load_model_clicked)
        
        self.load_history_btn = QPushButton("📋 モデル履歴から読み込み")
        self.load_history_btn.setToolTip("過去に読み込んだモデルから選択")
        self.load_history_btn.clicked.connect(self.on_load_from_history_clicked)
        
        # セパレーター
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("color: #eee; margin: 0px 10px;")
        
        layout.addWidget(self.load_model_btn)
        layout.addWidget(separator)
        layout.addWidget(self.load_history_btn)
        layout.addStretch()
        
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
        
        # --- アニメーションカーブをより滑らかなものに変更 ---
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
    
    def on_load_model_clicked(self):
        """モデル読み込みボタンクリック"""
        self.hide_menu()
        self.load_model_clicked.emit()
    
    def on_load_from_history_clicked(self):
        """履歴から読み込みボタンクリック"""
        self.hide_menu()
        self.load_from_history_clicked.emit()
    
    def mousePressEvent(self, event):
        """マウスクリックイベント（メニュー内クリックは伝播させない）"""
        event.accept()
        super().mousePressEvent(event)