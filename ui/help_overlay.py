import os
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextBrowser, 
                            QGraphicsDropShadowEffect, QPushButton)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QRect
from PyQt6.QtGui import QColor

class HelpOverlayWidget(QWidget):
    """操作説明オーバーレイウィンドウ"""
    
    # シグナル定義
    close_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.is_visible = False
        
        self.init_ui()
        self.load_help_content()
        self.setup_animation()
        
        # 初期状態は非表示
        self.hide()
    
    def init_ui(self):
        """UIを初期化"""
        # ウィンドウ属性設定
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 背景を半透明の黒に
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 150);
            }
        """)
        
        # レイアウト
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # HTML表示用ブラウザ
        self.help_browser = QTextBrowser()
        self.help_browser.setOpenExternalLinks(False)
        self.help_browser.setStyleSheet("""
            QTextBrowser {
                border: none;
                background: transparent;
            }
        """)
        
        # ドロップシャドウ効果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 5)
        self.help_browser.setGraphicsEffect(shadow)
        
        layout.addWidget(self.help_browser)
        
        # マウスクリックイベント
        self.mousePressEvent = self.on_background_click
    
    def load_help_content(self):
        """ヘルプHTMLを読み込む"""
        try:
            # HTMLファイルパスを取得
            current_dir = Path(__file__).parent
            html_file = current_dir / "operation_instructions.html"
            
            if html_file.exists():
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                self.help_browser.setHtml(html_content)
            else:
                # ファイルが見つからない場合のフォールバック
                self.help_browser.setHtml(self.get_fallback_content())
                
        except Exception as e:
            # エラー時のフォールバック
            self.help_browser.setHtml(f"<p>操作説明の読み込みに失敗しました: {str(e)}</p>")
    
    def get_fallback_content(self):
        """ファイルが見つからない場合の簡易ヘルプ"""
        return """
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h1>TTSスタジオ 操作説明</h1>
        <h2>基本ショートカット</h2>
        <ul>
        <li><strong>Ctrl+H</strong> - この説明を表示/非表示</li>
        <li><strong>Ctrl+Tab</strong> - マスタータブに移動</li>
        <li><strong>Ctrl+1-9</strong> - 各テキスト行に移動</li>
        <li><strong>Ctrl+P</strong> - 現在行を再生</li>
        <li><strong>Ctrl+R</strong> - 連続再生</li>
        <li><strong>Ctrl+S</strong> - 個別保存</li>
        </ul>
        <p>詳細な操作説明は operation_instructions.html ファイルをご確認ください。</p>
        </body>
        </html>
        """
    
    def setup_animation(self):
        """アニメーションを設定"""
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.fade_animation.finished.connect(self.on_animation_finished)
    
    def show_overlay(self):
        """オーバーレイを表示"""
        if self.is_visible:
            return
            
        if self.parent_widget:
            # 親ウィンドウのサイズに合わせる
            parent_rect = self.parent_widget.geometry()
            self.setGeometry(parent_rect)
            
        self.show()
        self.raise_()
        
        # フェードイン
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
        
        self.is_visible = True
    
    def hide_overlay(self):
        """オーバーレイを非表示"""
        if not self.is_visible:
            return
            
        # フェードアウト
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()
        
        self.is_visible = False
    
    def on_animation_finished(self):
        """アニメーション完了時の処理"""
        if not self.is_visible:
            self.hide()
    
    def toggle_overlay(self):
        """オーバーレイの表示/非表示を切り替え"""
        if self.is_visible:
            self.hide_overlay()
        else:
            self.show_overlay()
    
    def on_background_click(self, event):
        """背景クリック時の処理"""
        # ヘルプブラウザ以外の場所をクリックした場合は閉じる
        if not self.help_browser.geometry().contains(event.pos()):
            self.hide_overlay()
        super().mousePressEvent(event)
    
    def keyPressEvent(self, event):
        """キー押下イベント"""
        # Escapeキーまたは Ctrl+H で閉じる
        if (event.key() == Qt.Key.Key_Escape or 
            (event.key() == Qt.Key.Key_H and event.modifiers() == Qt.KeyboardModifier.ControlModifier)):
            self.hide_overlay()
        super().keyPressEvent(event)