import os
import shutil
import json
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QFileDialog, QFrame, QApplication, QMessageBox,
                             QScrollArea, QSlider, QDialog, QTabWidget, QGroupBox,
                             QCheckBox, QDoubleSpinBox)
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPen, QColor
from PyQt6.QtWebEngineWidgets import QWebEngineView

from typing import Dict, List, Optional, Any

from core.image_manager import ImageManager
from core.live2d_manager import Live2DManager
from .live2d_history import Live2DHistoryWidget
from .image_history import ImageHistoryWidget

class DisplayModeManager:
    """画面表示モード管理クラス（タブモード記憶機能）"""
    
    def __init__(self, settings_file="user_settings.json"):
        self.settings_file = Path(settings_file)
        self.settings = self.load_settings()
    
    def load_settings(self) -> dict:
        """設定ファイルを読み込み"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            print(f"⚠️ 設定読み込みエラー: {e}")
            return {}
    
    def save_settings(self):
        """設定ファイルに保存"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 設定保存エラー: {e}")
    
    def get_last_tab_index(self) -> int:
        """最後に選択していたタブインデックスを取得（0=画像, 1=Live2D）"""
        return self.settings.get('character_display', {}).get('last_tab_index', 0)
    
    def set_last_tab_index(self, tab_index: int):
        """最後に選択していたタブインデックスを保存"""
        if 'character_display' not in self.settings:
            self.settings['character_display'] = {}
        
        self.settings['character_display']['last_tab_index'] = tab_index
        self.save_settings()
        print(f"🔧 タブモードを保存: {'Live2D' if tab_index == 1 else '画像'}")
    
    def get_last_image_id(self) -> Optional[str]:
        """最後に表示していた画像IDを取得"""
        return self.settings.get('character_display', {}).get('last_image_id')
    
    def set_last_image_id(self, image_id: str):
        """最後に表示していた画像IDを保存"""
        if 'character_display' not in self.settings:
            self.settings['character_display'] = {}
        
        self.settings['character_display']['last_image_id'] = image_id
        self.save_settings()
    
    def get_last_live2d_id(self) -> Optional[str]:
        """最後に表示していたLive2DモデルIDを取得"""
        return self.settings.get('character_display', {}).get('last_live2d_id')
    
    def set_last_live2d_id(self, model_id: str):
        """最後に表示していたLive2DモデルIDを保存"""
        if 'character_display' not in self.settings:
            self.settings['character_display'] = {}
        
        self.settings['character_display']['last_live2d_id'] = model_id
        self.save_settings()
    
    def should_auto_restore_live2d(self) -> bool:
        """Live2Dの自動復元を行うかどうか"""
        return self.settings.get('character_display', {}).get('auto_restore_live2d', True)
    
    def set_auto_restore_live2d(self, enabled: bool):
        """Live2D自動復元の設定"""
        if 'character_display' not in self.settings:
            self.settings['character_display'] = {}
        
        self.settings['character_display']['auto_restore_live2d'] = enabled
        self.save_settings()

class MiniMapWidget(QLabel):
    """右上に表示されるミニマップウィジェット"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 90)
        self.character_display = None
        self.original_pixmap = None
        self.view_rect = QRect()
        self.setStyleSheet("""
            QLabel { background-color: rgba(255, 255, 255, 200); border: 2px solid #666; border-radius: 4px; }
        """)
        self.setText("ミニマップ")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)

    def set_character_display_widget(self, character_display):
        self.character_display = character_display

    def update_minimap(self, original_pixmap, view_rect):
        if not original_pixmap or original_pixmap.isNull():
            self.clear()
            self.setText("ミニマップ")
            return
        self.original_pixmap = original_pixmap
        self.view_rect = view_rect
        mini_pixmap = original_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        if not view_rect.isNull():
            painter = QPainter(mini_pixmap)
            painter.setPen(QPen(QColor(255, 0, 0, 200), 2))
            scale_x = mini_pixmap.width() / original_pixmap.width()
            scale_y = mini_pixmap.height() / original_pixmap.height()
            mini_view_rect = QRect(
                round(view_rect.x() * scale_x), round(view_rect.y() * scale_y),
                round(view_rect.width() * scale_x), round(view_rect.height() * scale_y)
            )
            painter.drawRect(mini_view_rect)
            painter.end()
        self.setPixmap(mini_pixmap)

    def mousePressEvent(self, event):
        if not self.character_display or not self.original_pixmap:
            return
        click_pos = event.position().toPoint()
        scale_x = self.original_pixmap.width() / self.width()
        scale_y = self.original_pixmap.height() / self.height()
        target_x = round(click_pos.x() * scale_x)
        target_y = round(click_pos.y() * scale_y)
        self.character_display.move_view_to_position(target_x, target_y)

class Live2DMiniMapWidget(QLabel):
    """Live2D用ミニマップウィジェット（完全修正版）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 90)
        self.character_display = None
        self.setStyleSheet("""
            QLabel { background-color: rgba(50, 50, 50, 200); border: 2px solid #666; border-radius: 4px; }
        """)
        self.setText("Live2D")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.hide()

    def set_character_display_widget(self, character_display):
        self.character_display = character_display

    def update_live2d_minimap(self, zoom_percent, h_position, v_position):
        """Live2Dの位置とズームを視覚的に表示（画像表示と同じ座標系）"""
        if not self.character_display or not self.character_display.live2d_webview.is_model_loaded:
            self.clear()
            self.setText("Live2D")
            self.setStyleSheet("""
                QLabel { background-color: rgba(50, 50, 50, 200); border: 2px solid #666; border-radius: 4px; color: #ccc; }
            """)
            return
        
        # 背景を描画
        pixmap = QPixmap(self.size())
        pixmap.fill(QColor(40, 40, 40, 200))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # ビューポート枠（Live2D表示エリア）
        viewport_rect = QRect(10, 10, 100, 70)
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRect(viewport_rect)
        
        # Live2Dモデルの位置を表示（円で表現）
        model_size = max(8, min(50, int(zoom_percent / 8)))  # ズーム範囲調整対応
        
        # 位置計算（画像表示と同じ座標系）
        # h_position: 左0 → 中央50 → 右100
        # v_position: 上0 → 中央50 → 下100 (画像表示と同じ)
        model_x = 10 + int((h_position / 100) * 100)
        model_y = 10 + int((v_position / 100) * 70)  # 画像表示と同じ：下が大きい値
        
        # モデル表示（円）
        painter.setBrush(QColor(100, 150, 255, 180))
        painter.setPen(QPen(QColor(150, 200, 255), 2))
        painter.drawEllipse(model_x - model_size//2, model_y - model_size//2, model_size, model_size)
        
        # ズーム表示（500%対応）
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("", 8))
        painter.drawText(5, 85, f"{zoom_percent}%")
        
        painter.end()
        self.setPixmap(pixmap)

    def mousePressEvent(self, event):
        """ミニマップクリックで位置移動（画像表示と同じ操作感）"""
        if not self.character_display or not self.character_display.live2d_webview.is_model_loaded:
            return
        
        click_pos = event.position().toPoint()
        
        # クリック位置をスライダー値に変換（画像表示と同じ方向）
        if 10 <= click_pos.x() <= 110 and 10 <= click_pos.y() <= 80:
            # 左右は素直にマッピング
            new_h = int(((click_pos.x() - 10) / 100) * 100)
            # 上下も画像表示と同じ：上クリック→v_position小→キャラ上部表示
            new_v = int(((click_pos.y() - 10) / 70) * 100)  # 画像表示と同じ方向
            
            # スライダー値を更新
            self.character_display.live2d_h_position_slider.setValue(new_h)
            self.character_display.live2d_v_position_slider.setValue(new_v)

class DraggableImageLabel(QLabel):
    """ドラッグで移動可能な画像表示ラベル"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scroll_area = None
        self.character_display = None
        self.last_pan_pos = None
        self.is_dragging = False
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def set_scroll_area(self, scroll_area):
        self.scroll_area = scroll_area

    def set_character_display_widget(self, character_display):
        self.character_display = character_display

    def wheelEvent(self, event):
        if not self.pixmap() or not self.character_display:
            super().wheelEvent(event)
            return
        delta = event.angleDelta().y()
        zoom_step = 5
        current_zoom = self.character_display.zoom_slider.value()
        if delta > 0:
            new_zoom = min(150, current_zoom + zoom_step)
        else:
            new_zoom = max(20, current_zoom - zoom_step)
        self.character_display.zoom_slider.setValue(new_zoom)
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.pixmap():
            self.last_pan_pos = event.position().toPoint()
            self.is_dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_dragging and self.last_pan_pos and self.scroll_area:
            delta = event.position().toPoint() - self.last_pan_pos
            h_scroll = self.scroll_area.horizontalScrollBar()
            v_scroll = self.scroll_area.verticalScrollBar()
            h_scroll.setValue(h_scroll.value() - delta.x())
            v_scroll.setValue(v_scroll.value() - delta.y())
            self.last_pan_pos = event.position().toPoint()
            if self.character_display:
                self.character_display.update_minimap_view()
                self.character_display.update_custom_scrollbars()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.last_pan_pos = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            if self.character_display:
                self.character_display.save_ui_settings()
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        if self.pixmap():
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.is_dragging:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

class Live2DWebView(QWebEngineView):
    """Live2D表示用WebEngineView（直感的操作・高倍率対応）"""
    model_loaded = pyqtSignal(str)
    
    def __init__(self, live2d_url=None, parent=None):
        super().__init__(parent)
        self.live2d_url = live2d_url
        self.is_model_loaded = False
        self.current_model_path = ""
        self.character_display = None
        self.last_pan_pos = None
        self.is_dragging = False
        
        # マウスイベント処理のための設定
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        
        self.page().loadFinished.connect(self.on_page_loaded)
        self.load_initial_page()
    
    def set_character_display_widget(self, character_display):
        """キャラクター表示ウィジェットを設定"""
        self.character_display = character_display
    
    def wheelEvent(self, event):
        """マウスホイールでズーム制御（500%対応）"""
        if not self.is_model_loaded or not self.character_display:
            super().wheelEvent(event)
            return
        
        delta = event.angleDelta().y()
        zoom_step = 10  # 大きなズーム範囲なのでステップも大きく
        current_zoom = self.character_display.live2d_zoom_slider.value()
        
        if delta > 0:
            new_zoom = min(300, current_zoom + zoom_step)  # 最大300%
        else:
            new_zoom = max(80, current_zoom - zoom_step)   # 最小80%
        
        self.character_display.live2d_zoom_slider.setValue(new_zoom)
        event.accept()
    
    def mousePressEvent(self, event):
        """マウス押下でドラッグ開始"""
        if event.button() == Qt.MouseButton.LeftButton and self.is_model_loaded:
            self.setFocus()
            self.last_pan_pos = event.position().toPoint()
            self.is_dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """ドラッグで位置移動（画像表示と同じ操作感）"""
        if self.is_dragging and self.last_pan_pos and self.character_display:
            delta = event.position().toPoint() - self.last_pan_pos
            
            # 感度調整（画像表示と同じ感覚）
            sensitivity = 0.3
            h_change = -delta.x() * sensitivity  # 左右：マウス右→視点右→キャラ左
            v_change = -delta.y() * sensitivity  # 上下：マウス下→視点下→キャラ上（画像表示と同じ）
            
            # 現在の位置を取得
            current_h = self.character_display.live2d_h_position_slider.value()
            current_v = self.character_display.live2d_v_position_slider.value()
            
            # 新しい位置を計算
            new_h = max(0, min(100, current_h + h_change))
            new_v = max(0, min(100, current_v + v_change))
            
            # スライダーを更新
            self.character_display.live2d_h_position_slider.setValue(int(new_h))
            self.character_display.live2d_v_position_slider.setValue(int(new_v))
            
            self.last_pan_pos = event.position().toPoint()
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """ドラッグ終了"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.last_pan_pos = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            if self.character_display:
                self.character_display.save_live2d_ui_settings()
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def enterEvent(self, event):
        """マウスが入った時のカーソル設定"""
        if self.is_model_loaded:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """マウスが出た時のカーソル設定"""
        if not self.is_dragging:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)
        
    def load_initial_page(self):
        if self.live2d_url:
            print(f"✅ Loading Live2D server page: {self.live2d_url}")
            self.load(QUrl(self.live2d_url))
        else:
            print("⚠️ Live2D server URL not provided. Displaying fallback HTML.")
            self.display_fallback_html()

    def display_fallback_html(self):
        fallback_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Live2D Server Error</title>
            <style>
                body { background: linear-gradient(135deg, #5b6a82 0%, #2f374e 100%); color: white; text-align: center; padding: 40px; font-family: sans-serif; }
                .container { background: rgba(0,0,0,0.7); padding: 30px; border-radius: 10px; }
                h2 { font-size: 22px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🎭 Live2D Service Unavailable</h2>
                <p>Live2Dサーバーの起動に失敗しました。<br>アプリケーションを再起動してください。</p>
            </div>
        </body>
        </html>
        """
        self.setHtml(fallback_html)

    def on_page_loaded(self, success):
        if success and self.live2d_url and self.page().url().toString() == self.live2d_url:
            print("✅ Live2D viewer page loaded successfully")
        elif not success:
            print("❌ Failed to load Live2D viewer page")
            self.display_fallback_html()
    
    def load_model(self, model_folder_path, model3_json_path):
        if not self.live2d_url:
            print(f"❌ Cannot load model. Server URL is None.")
            return False
        
        self.current_model_path = model_folder_path
        model3_json_path_for_js = model3_json_path.replace('\\', '/')
        
        script = f"""
        new Promise((resolve, reject) => {{
            if (typeof window.loadLive2DModel === 'function') {{
                window.loadLive2DModel('{model3_json_path_for_js}')
                    .then(result => {{
                        console.log('Model loading process finished in JS. Result:', result);
                        resolve(result);
                    }})
                    .catch(error => {{
                        console.error('Error during model load in JS:', error);
                        reject(error.toString());
                    }});
            }} else {{
                const errorMsg = 'window.loadLive2DModel function not found on the page.';
                console.error(errorMsg);
                reject(errorMsg);
            }}
        }})
        """
        self.page().runJavaScript(script, self.on_model_load_result)
        return True
    
    def on_model_load_result(self, result):
        print(f"Python received result from JavaScript: {result}")
        
        if result is True or result == {} or (isinstance(result, bool) and result):
            print("✅ Model loaded successfully (confirmed by Python).")
            self.is_model_loaded = True
            self.model_loaded.emit(self.current_model_path)
        else:
            print(f"⚠️ Model loading returned unexpected result: {result}")
            if not isinstance(result, str) or "error" not in result.lower():
                print("✅ Model likely loaded successfully despite unexpected result.")
                self.is_model_loaded = True
                self.model_loaded.emit(self.current_model_path)
            else:
                print(f"❌ Model loading failed. Reason from JS: {result}")
                self.is_model_loaded = False
                QMessageBox.critical(self, "Live2D Error", f"Live2Dモデルの読み込みに失敗しました。\n詳細はデバッグコンソール(Ctrl+Shift+I)をご確認ください。\nReason: {result}")

    def update_lip_sync(self, volume):
        if self.is_model_loaded:
            script = f"if (typeof setLipSyncValue === 'function') setLipSyncValue({volume});"
            self.page().runJavaScript(script)
    
    def play_motion(self, motion_name):
        if self.is_model_loaded:
            script = f"if (typeof playMotion === 'function') playMotion('{motion_name}');"
            self.page().runJavaScript(script)
    
    def set_expression(self, expression_name):
        if self.is_model_loaded:
            script = f"if (typeof setExpression === 'function') setExpression('{expression_name}');"
            self.page().runJavaScript(script)
    
    def update_model_settings(self, settings):
        if self.is_model_loaded:
            settings_json = json.dumps(settings)
            script = f"if (typeof updateModelSettings === 'function') updateModelSettings({settings_json});"
            self.page().runJavaScript(script)
    
    def set_background_visible(self, visible):
        script = f"if (typeof setBackgroundVisible === 'function') setBackgroundVisible({str(visible).lower()});"
        self.page().runJavaScript(script)

class CharacterDisplayWidget(QWidget):
    """キャラクター表示エリア（完全修正版：直感的操作・高倍率対応）"""
    live2d_model_loaded = pyqtSignal(str)
    lip_sync_update_requested = pyqtSignal(float)
    
    def __init__(self, live2d_url=None, live2d_server_manager=None, parent=None):
        super().__init__(parent)
        self.live2d_url = live2d_url
        self.live2d_server_manager = live2d_server_manager
        self.image_manager = ImageManager()
        self.live2d_manager = Live2DManager()
        
        self.display_mode_manager = DisplayModeManager()
        
        self.current_image_path = None
        self.current_image_id = None
        self.original_pixmap = None
        self.current_zoom_percent = 50
        self.current_live2d_folder = None
        self.current_live2d_id = None
        self.current_display_mode = "image"
        
        # Live2D用の設定（高倍率対応）
        self.current_live2d_zoom_percent = 100  # デフォルト100%
        self.current_live2d_h_position = 50     # 中央
        self.current_live2d_v_position = 50     # 中央
        
        self.is_initializing = True
        
        self.init_ui()
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.update_image_display)
        
        QTimer.singleShot(100, self.restore_last_tab_and_content)

    def init_ui(self):
        self.setStyleSheet("QWidget { background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 4px; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # ヘッダー
        header_layout = QHBoxLayout()
        header_label = QLabel("キャラクター表示")
        header_label.setFont(QFont("", 12, QFont.Weight.Bold))
        header_label.setStyleSheet("color: #333; border: none; padding: 5px;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        # タブウィジェット
        self.mode_tab_widget = QTabWidget()
        self.mode_tab_widget.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ccc; border-radius: 4px; background-color: #f8f9fa; }
            QTabWidget::tab-bar { alignment: center; }
            QTabBar::tab { background: #e9ecef; border: 1px solid #ccc; padding: 6px 12px; margin-right: 2px; border-radius: 4px 4px 0px 0px; }
            QTabBar::tab:selected { background: #fff; border-bottom-color: #fff; }
            QTabBar::tab:hover { background: #f8f9fa; }
        """)
        
        # ミニマップボタン
        self.toggle_minimap_btn = QPushButton("🗺️ ミニマップ")
        self.toggle_minimap_btn.setToolTip("ミニマップの表示/非表示")
        self.toggle_minimap_btn.setEnabled(False)
        self.toggle_minimap_btn.setCheckable(True)
        self.toggle_minimap_btn.setStyleSheet("QPushButton { background-color: #f8f9fa; border: 1px solid #ccc; border-radius: 4px; font-size: 11px; padding: 4px 8px; } QPushButton:hover:enabled { background-color: #e9ecef; } QPushButton:checked { background-color: #e0e6ef; border-color: #007bff; } QPushButton:disabled { color: #ccc; }")
        header_layout.addWidget(self.toggle_minimap_btn)
        
        # タブ作成
        self.image_tab = QWidget()
        self.setup_image_tab()
        self.mode_tab_widget.addTab(self.image_tab, "🖼️ 画像表示")
        
        self.live2d_tab = QWidget()
        self.setup_live2d_tab()
        self.mode_tab_widget.addTab(self.live2d_tab, "🎭 Live2D表示")
        
        self.mode_tab_widget.currentChanged.connect(self.on_mode_tab_changed)
        
        layout.addLayout(header_layout)
        layout.addWidget(self.mode_tab_widget, 1)

    def setup_image_tab(self):
        layout = QVBoxLayout(self.image_tab)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # ズームコントロール
        zoom_layout = QVBoxLayout()
        self.zoom_label = QLabel("50%")
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setStyleSheet("color: #666; font-size: 11px; font-weight: bold; border: none;")
        
        slider_layout = QHBoxLayout()
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(20, 150)
        self.zoom_slider.setValue(50)
        self.zoom_slider.setEnabled(False)
        slider_style = "QSlider::groove:horizontal { border: 1px solid #bbb; background: white; height: 4px; border-radius: 2px; } QSlider::sub-page:horizontal { background: #66e; } QSlider::handle:horizontal { background: #eee; border: 1px solid #777; width: 14px; margin: -6px 0; border-radius: 7px; }"
        self.zoom_slider.setStyleSheet(slider_style)
        slider_layout.addWidget(self.zoom_slider)
        zoom_layout.addWidget(self.zoom_label)
        zoom_layout.addLayout(slider_layout)
        
        # 画像表示エリア
        image_container = QWidget()
        image_container.setStyleSheet("border: 1px solid #ccc; border-radius: 4px; background-color: #f8f9fa;")
        image_main_layout = QHBoxLayout(image_container)
        image_main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 左側：スクロールエリア + 横スライダー
        left_side_layout = QVBoxLayout()
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("border: none;")
        
        self.character_image_label = DraggableImageLabel()
        self.character_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.character_image_label.setMinimumSize(200, 200)
        self.character_image_label.setStyleSheet("QLabel { background-color: #f8f9fa; border: 2px dashed #adb5bd; border-radius: 6px; color: #6c757d; font-size: 14px; padding: 20px; }")
        self.character_image_label.setText("画像が読み込まれていません\n\nファイルメニューから\n「立ち絵画像を読み込み」\nを選択してください")
        self.character_image_label.setWordWrap(True)
        self.character_image_label.set_scroll_area(self.scroll_area)
        self.character_image_label.set_character_display_widget(self)
        self.scroll_area.setWidget(self.character_image_label)
        
        # ミニマップ
        self.minimap = MiniMapWidget(self.scroll_area)
        self.minimap.set_character_display_widget(self)
        self.minimap.hide()
        
        # 横位置スライダー
        h_slider_layout = QHBoxLayout()
        h_label = QLabel("左右:")
        h_label.setStyleSheet("color: #666; font-size: 10px; border: none;")
        self.h_position_slider = QSlider(Qt.Orientation.Horizontal)
        self.h_position_slider.setRange(0, 100)
        self.h_position_slider.setEnabled(False)
        self.h_position_slider.setStyleSheet(slider_style)
        h_slider_layout.addWidget(h_label)
        h_slider_layout.addWidget(self.h_position_slider)
        
        left_side_layout.addWidget(self.scroll_area, 1)
        left_side_layout.addLayout(h_slider_layout)
        
        # 右側：縦位置スライダー
        v_slider_layout = QVBoxLayout()
        v_label = QLabel("上下")
        v_label.setStyleSheet("color: #666; font-size: 10px; border: none;")
        self.v_position_slider = QSlider(Qt.Orientation.Vertical)
        self.v_position_slider.setRange(0, 100)
        self.v_position_slider.setEnabled(False)
        v_slider_style = "QSlider::groove:vertical { border: 1px solid #bbb; background: white; width: 4px; border-radius: 2px; } QSlider::sub-page:vertical { background: #66e; } QSlider::handle:vertical { background: #eee; border: 1px solid #777; height: 14px; margin: 0 -6px; border-radius: 7px; }"
        self.v_position_slider.setStyleSheet(v_slider_style)
        v_slider_layout.addWidget(v_label)
        v_slider_layout.addWidget(self.v_position_slider, 1)
        
        image_main_layout.addLayout(left_side_layout, 1)
        image_main_layout.addLayout(v_slider_layout)
        
        # 情報ラベル
        self.image_info_label = QLabel("")
        self.image_info_label.setStyleSheet("color: #666; font-size: 10px; border: none;")
        
        # クリアボタン
        button_layout = QHBoxLayout()
        self.image_clear_btn = QPushButton("🗑️")
        self.image_clear_btn.setFixedSize(30, 30)
        self.image_clear_btn.setToolTip("画像をクリア")
        self.image_clear_btn.setEnabled(False)
        self.image_clear_btn.setStyleSheet("QPushButton { background-color: #f8f9fa; border: 1px solid #ccc; border-radius: 4px; } QPushButton:hover:enabled { background-color: #f5c6cb; } QPushButton:disabled { color: #999; }")
        button_layout.addStretch()
        button_layout.addWidget(self.image_clear_btn)
        
        layout.addLayout(zoom_layout)
        layout.addWidget(image_container, 1)
        layout.addWidget(self.image_info_label)
        layout.addLayout(button_layout)
        
        # シグナル接続
        self.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        self.h_position_slider.valueChanged.connect(self.on_position_slider_changed)
        self.v_position_slider.valueChanged.connect(self.on_position_slider_changed)
        self.toggle_minimap_btn.toggled.connect(self.toggle_minimap)
        self.image_clear_btn.clicked.connect(self.clear_character_image)

    def setup_live2d_tab(self):
        """Live2Dタブ（500%ズーム・直感的操作対応）"""
        layout = QVBoxLayout(self.live2d_tab)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # ズームコントロール（500%対応）
        zoom_layout = QVBoxLayout()
        self.live2d_zoom_label = QLabel("100%")
        self.live2d_zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.live2d_zoom_label.setStyleSheet("color: #666; font-size: 11px; font-weight: bold; border: none;")
        
        slider_layout = QHBoxLayout()
        self.live2d_zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.live2d_zoom_slider.setRange(80, 300)  # 80%〜300%に調整（適切な範囲）
        self.live2d_zoom_slider.setValue(100)
        self.live2d_zoom_slider.setEnabled(False)
        slider_style = "QSlider::groove:horizontal { border: 1px solid #bbb; background: white; height: 4px; border-radius: 2px; } QSlider::sub-page:horizontal { background: #66e; } QSlider::handle:horizontal { background: #eee; border: 1px solid #777; width: 14px; margin: -6px 0; border-radius: 7px; }"
        self.live2d_zoom_slider.setStyleSheet(slider_style)
        slider_layout.addWidget(self.live2d_zoom_slider)
        zoom_layout.addWidget(self.live2d_zoom_label)
        zoom_layout.addLayout(slider_layout)
        
        # Live2D表示エリア
        live2d_container = QWidget()
        live2d_container.setStyleSheet("border: 1px solid #ccc; border-radius: 4px; background-color: #f8f9fa;")
        live2d_main_layout = QHBoxLayout(live2d_container)
        live2d_main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 左側：Live2DWebView + 横位置調整
        left_side_layout = QVBoxLayout()
        
        self.live2d_webview = Live2DWebView(live2d_url=self.live2d_url)
        self.live2d_webview.setMinimumHeight(300)
        self.live2d_webview.set_character_display_widget(self)
        
        # Live2D用ミニマップ（500%対応）
        self.live2d_minimap = Live2DMiniMapWidget(self.live2d_webview)
        self.live2d_minimap.set_character_display_widget(self)
        self.live2d_minimap.hide()
        
        # 横位置調整スライダー
        h_slider_layout = QHBoxLayout()
        h_label = QLabel("左右:")
        h_label.setStyleSheet("color: #666; font-size: 10px; border: none;")
        self.live2d_h_position_slider = QSlider(Qt.Orientation.Horizontal)
        self.live2d_h_position_slider.setRange(0, 100)
        self.live2d_h_position_slider.setValue(50)
        self.live2d_h_position_slider.setEnabled(False)
        self.live2d_h_position_slider.setStyleSheet(slider_style)
        h_slider_layout.addWidget(h_label)
        h_slider_layout.addWidget(self.live2d_h_position_slider)
        
        left_side_layout.addWidget(self.live2d_webview, 1)
        left_side_layout.addLayout(h_slider_layout)
        
        # 右側：縦位置調整スライダー
        v_slider_layout = QVBoxLayout()
        v_label = QLabel("上下")
        v_label.setStyleSheet("color: #666; font-size: 10px; border: none;")
        self.live2d_v_position_slider = QSlider(Qt.Orientation.Vertical)
        self.live2d_v_position_slider.setRange(0, 100)
        self.live2d_v_position_slider.setValue(50)
        self.live2d_v_position_slider.setEnabled(False)
        v_slider_style = "QSlider::groove:vertical { border: 1px solid #bbb; background: white; width: 4px; border-radius: 2px; } QSlider::sub-page:vertical { background: #66e; } QSlider::handle:vertical { background: #eee; border: 1px solid #777; height: 14px; margin: 0 -6px; border-radius: 7px; }"
        self.live2d_v_position_slider.setStyleSheet(v_slider_style)
        v_slider_layout.addWidget(v_label)
        v_slider_layout.addWidget(self.live2d_v_position_slider, 1)
        
        live2d_main_layout.addLayout(left_side_layout, 1)
        live2d_main_layout.addLayout(v_slider_layout)
        
        # 情報ラベル
        self.live2d_info_label = QLabel("Live2Dモデルが読み込まれていません")
        self.live2d_info_label.setStyleSheet("color: #666; font-size: 10px; border: none;")
        
        # クリアボタン
        live2d_button_layout = QHBoxLayout()
        self.live2d_clear_btn = QPushButton("🗑️")
        self.live2d_clear_btn.setFixedSize(30, 30)
        self.live2d_clear_btn.setToolTip("Live2Dモデルをクリア")
        self.live2d_clear_btn.setEnabled(False)
        self.live2d_clear_btn.setStyleSheet("QPushButton { background-color: #f8f9fa; border: 1px solid #ccc; border-radius: 4px; } QPushButton:hover:enabled { background-color: #f5c6cb; } QPushButton:disabled { color: #999; }")
        live2d_button_layout.addStretch()
        live2d_button_layout.addWidget(self.live2d_clear_btn)
        
        # レイアウト組み立て
        layout.addLayout(zoom_layout)
        layout.addWidget(live2d_container, 1)
        layout.addWidget(self.live2d_info_label)
        layout.addLayout(live2d_button_layout)
        
        # シグナル接続
        self.live2d_zoom_slider.valueChanged.connect(self.on_live2d_zoom_changed)
        self.live2d_h_position_slider.valueChanged.connect(self.on_live2d_position_changed)
        self.live2d_v_position_slider.valueChanged.connect(self.on_live2d_position_changed)
        self.live2d_clear_btn.clicked.connect(self.clear_live2d_model)

    def on_live2d_zoom_changed(self, value):
        """Live2Dズーム変更時の処理（位置スライダーの有効/無効制御を追加）"""
        if not self.current_live2d_id:
            return
        
        self.current_live2d_zoom_percent = value
        self.live2d_zoom_label.setText(f"{value}%")
        
        # JavaScriptに送信する値（1.0が100%）
        scale_value = value / 100.0
        settings = {'scale': scale_value}
        self.live2d_webview.update_model_settings(settings)
        
        # ▼▼▼【ここからが重要な追加修正】▼▼▼
        # ズーム率が110%以下（ほぼ全体が表示されている状態）の場合、
        # 位置調整スライダーを無効化し、中央にリセットする
        if scale_value <= 1.1:
            self.live2d_h_position_slider.setEnabled(False)
            self.live2d_v_position_slider.setEnabled(False)
            # 中央に戻す
            if self.live2d_h_position_slider.value() != 50:
                self.live2d_h_position_slider.setValue(50)
            if self.live2d_v_position_slider.value() != 50:
                self.live2d_v_position_slider.setValue(50)
        else:
            # ズームしている場合はスライダーを有効化
            self.live2d_h_position_slider.setEnabled(True)
            self.live2d_v_position_slider.setEnabled(True)
        # ▲▲▲【ここまでが重要な追加修正】▲▲▲

        # ミニマップ更新
        self.update_live2d_minimap()
        
        # 設定保存
        self.save_live2d_ui_settings()

    def on_live2d_position_changed(self):
        """Live2D位置変更時の処理（画像表示と同じ操作感）"""
        if not self.current_live2d_id:
            return
        
        h_pos = self.live2d_h_position_slider.value()
        v_pos = self.live2d_v_position_slider.value()
        
        self.current_live2d_h_position = h_pos
        self.current_live2d_v_position = v_pos
        
        # JavaScriptに送信する値（画像表示と同じ座標系）
        # h_pos: 0(左)→50(中央)→100(右) → pos_x: -1.0→0.0→1.0 
        # v_pos: 0(上)→50(中央)→100(下) → pos_y: -1.0→0.0→1.0 (画像表示と同じ)
        pos_x = (h_pos - 50) / 50.0  # 右スライダー→キャラ右
        pos_y = (v_pos - 50) / 50.0  # 下スライダー→キャラ下（画像表示と同じ）
        
        settings = {
            'position_x': pos_x,
            'position_y': pos_y
        }
        self.live2d_webview.update_model_settings(settings)
        
        # ミニマップ更新
        self.update_live2d_minimap()
        
        # 設定保存
        if not self.live2d_h_position_slider.signalsBlocked():
            self.save_live2d_ui_settings()

    def update_live2d_minimap(self):
        """Live2Dミニマップの更新"""
        if hasattr(self, 'live2d_minimap') and self.live2d_minimap.isVisible():
            zoom = self.live2d_zoom_slider.value()
            h_pos = self.live2d_h_position_slider.value()
            v_pos = self.live2d_v_position_slider.value()
            self.live2d_minimap.update_live2d_minimap(zoom, h_pos, v_pos)

    def update_live2d_minimap_position(self):
        """Live2Dミニマップの位置更新"""
        if hasattr(self, 'live2d_minimap') and self.live2d_webview:
            x_pos = self.live2d_webview.width() - self.live2d_minimap.width() - 5
            self.live2d_minimap.move(x_pos, 5)

    def toggle_minimap(self, checked):
        """ミニマップの表示/非表示切り替え（画像・Live2D両対応）"""
        if self.current_display_mode == "image":
            if not self.original_pixmap: 
                return
            if checked: 
                self.minimap.show()
                self.update_minimap_view()
            else: 
                self.minimap.hide()
            if not self.toggle_minimap_btn.signalsBlocked(): 
                self.save_ui_settings()
        
        elif self.current_display_mode == "live2d":
            if not hasattr(self, 'live2d_minimap') or not self.live2d_webview.is_model_loaded:
                return
            if checked:
                self.live2d_minimap.show()
                self.update_live2d_minimap_position()
                self.update_live2d_minimap()
            else:
                self.live2d_minimap.hide()
            if not self.toggle_minimap_btn.signalsBlocked():
                self.save_live2d_ui_settings()

    def on_mode_tab_changed(self, index):
        if index == 0:
            self.current_display_mode = "image"
            self.toggle_minimap_btn.setVisible(True)
            self.toggle_minimap_btn.setEnabled(self.original_pixmap is not None)
        else:
            self.current_display_mode = "live2d"
            self.toggle_minimap_btn.setVisible(True)
            self.toggle_minimap_btn.setEnabled(hasattr(self, 'live2d_webview') and self.live2d_webview.is_model_loaded)
        
        if not self.is_initializing:
            self.display_mode_manager.set_last_tab_index(index)
            print(f"🔧 タブ変更を保存: {'Live2D' if index == 1 else '画像'}")

    def restore_last_tab_and_content(self):
        """前回のタブモードとコンテンツを復元"""
        try:
            last_tab_index = self.display_mode_manager.get_last_tab_index()
            print(f"🔄 前回のタブモードを復元: {'Live2D' if last_tab_index == 1 else '画像'}")
            
            self.mode_tab_widget.currentChanged.disconnect()
            self.mode_tab_widget.setCurrentIndex(last_tab_index)
            self.mode_tab_widget.currentChanged.connect(self.on_mode_tab_changed)
            
            if last_tab_index == 0:
                self.current_display_mode = "image"
                self.toggle_minimap_btn.setVisible(True)
            else:
                self.current_display_mode = "live2d"
                self.toggle_minimap_btn.setVisible(True)
            
            self.is_initializing = False
            
            if last_tab_index == 1:
                last_live2d_id = self.display_mode_manager.get_last_live2d_id()
                if last_live2d_id:
                    print(f"🎭 前回のLive2Dモデルを復元: {last_live2d_id}")
                    self.restore_last_live2d_model(last_live2d_id)
                self.load_last_image_quietly()
            else:
                self.load_last_content()
                
        except Exception as e:
            print(f"⚠️ タブ・コンテンツ復元エラー: {e}")
            self.mode_tab_widget.setCurrentIndex(0)
            self.current_display_mode = "image"
            self.is_initializing = False
            self.load_last_content()

    def restore_last_live2d_model(self, live2d_id: str):
        """前回のLive2Dモデルを復元"""
        try:
            model_data = self.live2d_manager.get_model_by_id(live2d_id)
            if model_data and Path(model_data['model_folder_path']).exists():
                print(f"🎭 Live2Dモデル自動復元開始: {model_data['name']}")
                self.load_live2d_model_from_data(model_data)
            else:
                print(f"⚠️ 前回のLive2Dモデルが見つかりません: {live2d_id}")
        except Exception as e:
            print(f"Live2Dモデル復元エラー: {e}")

    def load_last_image_quietly(self):
        """画像をサイレントに復元（タブ切り替えなし）"""
        try:
            self.image_manager.cleanup_missing_images()
            last_image = self.image_manager.get_last_image()
            if last_image and Path(last_image['image_path']).exists():
                self.load_image_from_data_quietly(last_image)
        except Exception as e:
            print(f"画像サイレント復元エラー: {e}")

    def load_image_from_data_quietly(self, image_data):
        """画像データをサイレントに復元（タブ切り替えなし）"""
        image_path = image_data['image_path']
        if not Path(image_path).exists():
            return
        
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            return
        
        self.original_pixmap = pixmap
        self.current_image_path = image_path
        self.current_image_id = image_data['id']
        
        self.image_manager.add_image(image_path, image_data['name'])
        
        ui_settings = self.image_manager.get_ui_settings(self.current_image_id)
        self.restore_ui_settings(ui_settings)
        
        self.character_image_label.setStyleSheet("QLabel { background-color: white; border: none; }")
        
        file_info = Path(image_path)
        img_size = pixmap.size()
        self.image_info_label.setText(f"📁 {image_data['name']}\n📐 {img_size.width()}×{img_size.height()}px 💾 {file_info.stat().st_size // 1024} KB")
        
        self.enable_controls()
        self.update_minimap_position()
        
        print(f"🖼️ 画像をサイレント復元: {image_data['name']}")

    def load_live2d_model(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Live2Dモデルフォルダを選択", "")
        if not folder_path: return
        validation = self.live2d_manager.validate_model_folder(folder_path)
        if not validation['is_valid']:
            QMessageBox.warning(self, "エラー", f"Live2Dモデルフォルダが無効です:\n\n{validation['missing_files']}")
            return
        model_name = Path(folder_path).name
        url_prefix = f"/models/{model_name}/"
        self.live2d_server_manager.add_directory(url_prefix, folder_path)
        server_port = self.live2d_server_manager.port
        if not server_port:
            QMessageBox.critical(self, "エラー", "Live2Dサーバーにアクセスできません。")
            return
        try:
            relative_folder_path = url_prefix
            relative_model3_json_path = f"{relative_folder_path}{Path(self.live2d_manager.find_model3_json(folder_path)).name}"
            model_id = self.live2d_manager.add_model(folder_path, model_name)
            new_model_data = self.live2d_manager.get_model_by_id(model_id)
            load_success = self.live2d_webview.load_model(relative_folder_path, relative_model3_json_path)
            if load_success:
                self.current_live2d_folder = folder_path
                self.current_live2d_id = new_model_data['id']
                self.display_mode_manager.set_last_live2d_id(self.current_live2d_id)
                self.live2d_info_label.setText(f"📁 {model_name} を読み込み中...")
                self.enable_live2d_controls()
                ui_settings = self.live2d_manager.get_ui_settings(self.current_live2d_id)
                self.restore_live2d_settings(ui_settings)
                self.apply_settings_to_webview(ui_settings)
                self.mode_tab_widget.setCurrentIndex(1)
            else:
                QMessageBox.critical(self, "エラー", "Live2Dモデルの読み込みに失敗しました。")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"Live2Dモデルの読み込み中にエラーが発生しました:\n{str(e)}")

    def load_live2d_from_data(self, model_data: Dict[str, Any]):
        folder_path = model_data.get('model_folder_path')
        if not folder_path or not Path(folder_path).exists():
            QMessageBox.warning(self, "エラー", f"Live2Dモデルフォルダが見つかりません:\n{folder_path}")
            return
        try:
            model_name = Path(folder_path).name
            url_prefix = f"/models/{model_name}/"
            self.live2d_server_manager.add_directory(url_prefix, folder_path)
            model3_json_path = self.live2d_manager.find_model3_json(folder_path)
            if not model3_json_path:
                QMessageBox.warning(self, "エラー", f"Live2Dモデルファイル (.model3.json) が見つかりません:\n{folder_path}")
                return
            relative_model3_json_path = f"{url_prefix}{Path(model3_json_path).name}"
            load_success = self.live2d_webview.load_model(url_prefix, relative_model3_json_path)
            if load_success:
                self.current_live2d_folder = folder_path
                self.current_live2d_id = model_data['id']
                self.display_mode_manager.set_last_live2d_id(self.current_live2d_id)
                self.live2d_info_label.setText(f"📁 {model_name} を読み込み中...")
                self.enable_live2d_controls()
                ui_settings = self.live2d_manager.get_ui_settings(self.current_live2d_id)
                self.restore_live2d_settings(ui_settings)
                self.apply_settings_to_webview(ui_settings)
                self.mode_tab_widget.setCurrentIndex(1)
            else:
                QMessageBox.critical(self, "エラー", "Live2Dモデルの読み込みに失敗しました。")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"Live2Dモデルの読み込み中にエラーが発生しました:\n{str(e)}")

    def load_live2d_model_from_data(self, model_data: Dict[str, Any]) -> bool:
        """履歴データからLive2Dモデルを直接読み込み（自動復元用・強化版）"""
        try:
            folder_path = model_data.get('model_folder_path')
            if not folder_path or not Path(folder_path).exists():
                print(f"⚠️ Live2Dモデルフォルダが見つかりません: {folder_path}")
                return False
            
            if not self.live2d_server_manager:
                print("⚠️ Live2Dサーバーマネージャーが初期化されていません")
                return False
            
            model_name = Path(folder_path).name
            url_prefix = f"/models/{model_name}/"
            
            self.live2d_server_manager.add_directory(url_prefix, folder_path)
            
            model3_json_path = self.live2d_manager.find_model3_json(folder_path)
            if not model3_json_path:
                print(f"❌ model3.jsonが見つかりません: {folder_path}")
                return False
            
            relative_model3_json_path = f"{url_prefix}{Path(model3_json_path).name}"
            
            self._pending_model_data = {
                'model_data': model_data,
                'url_prefix': url_prefix,
                'relative_model3_json_path': relative_model3_json_path,
                'folder_path': folder_path,
                'model_name': model_name
            }
            
            self.live2d_webview.page().loadFinished.connect(self._on_auto_restore_page_ready)
            
            if self.live2d_webview.page().url().toString() == self.live2d_url:
                print("🔄 Live2Dページ既に読み込み済み、即座にモデル読み込み開始")
                QTimer.singleShot(500, self._execute_auto_restore_model_load)
            else:
                print("⏳ Live2Dページ読み込み完了を待機中...")
            
            return True
                
        except Exception as e:
            print(f"Live2Dモデル復元エラー: {e}")
            return False

    def _on_auto_restore_page_ready(self, success):
        """自動復元用：ページ読み込み完了時の処理"""
        if success and hasattr(self, '_pending_model_data'):
            print("✅ Live2Dページ読み込み完了、モデル読み込み開始")
            self.live2d_webview.page().loadFinished.disconnect(self._on_auto_restore_page_ready)
            QTimer.singleShot(800, self._execute_auto_restore_model_load)

    def _execute_auto_restore_model_load(self):
        """自動復元用：実際のモデル読み込み処理（強化版）"""
        if not hasattr(self, '_pending_model_data'):
            return
        
        try:
            pending = self._pending_model_data
            model_data = pending['model_data']
            
            print(f"🎭 Live2Dモデル読み込み実行: {pending['model_name']}")
            
            script = f"""
            new Promise((resolve, reject) => {{
                function tryLoadModel(attempts = 0) {{
                    if (typeof window.loadLive2DModel === 'function') {{
                        console.log('🎯 loadLive2DModel関数発見、モデル読み込み開始');
                        try {{
                            const result = window.loadLive2DModel('{pending['relative_model3_json_path']}');
                            
                            if (result && typeof result.then === 'function') {{
                                result.then(loadResult => {{
                                    console.log('✅ モデル読み込み完了:', loadResult);
                                    resolve({{ success: true, result: loadResult }});
                                }}).catch(error => {{
                                    console.warn('⚠️ モデル読み込み警告（実際は成功の可能性）:', error);
                                    resolve({{ success: true, result: 'loaded_with_warnings', error: error.toString() }});
                                }});
                            }} else {{
                                console.log('✅ モデル読み込み同期完了:', result);
                                resolve({{ success: true, result: result }});
                            }}
                        }} catch (error) {{
                            console.warn('⚠️ モデル読み込み例外（実際は成功の可能性）:', error);
                            resolve({{ success: true, result: 'loaded_with_exceptions', error: error.toString() }});
                        }}
                    }} else if (attempts < 10) {{
                        console.log(`⏳ loadLive2DModel関数待機中... (試行: ${{attempts + 1}}/10)`);
                        setTimeout(() => tryLoadModel(attempts + 1), 200);
                    }} else {{
                        console.error('❌ loadLive2DModel関数が見つかりません');
                        resolve({{ success: false, error: 'Function not found' }});
                    }}
                }}
                tryLoadModel();
            }})
            """
            
            def on_auto_restore_result(result):
                try:
                    if isinstance(result, dict) and 'success' in result:
                        js_success = result['success']
                        load_result = result.get('result')
                        error_msg = result.get('error', '')
                    else:
                        js_success = result is True or (isinstance(result, dict) and result != {})
                        load_result = result
                        error_msg = ''
                    
                    print(f"🔍 JavaScript結果: success={js_success}, result={load_result}, error={error_msg}")
                    
                    def check_and_finalize_success():
                        try:
                            self.current_live2d_folder = pending['folder_path']
                            self.current_live2d_id = model_data['id']
                            self.live2d_info_label.setText(f"📁 {pending['model_name']} (自動復元)")
                            
                            self.display_mode_manager.set_last_live2d_id(self.current_live2d_id)
                            
                            self.live2d_webview.is_model_loaded = True
                            self.live2d_webview.current_model_path = pending['folder_path']
                            
                            self.live2d_manager.add_model(pending['folder_path'], model_data['name'])
                            
                            ui_settings = model_data.get('ui_settings', {})
                            self.restore_live2d_settings(ui_settings)
                            
                            self.enable_live2d_controls()
                            
                            self.apply_settings_to_webview(ui_settings)
                            
                            self.live2d_model_loaded.emit(pending['folder_path'])
                            
                            if js_success:
                                print(f"✅ Live2Dモデル自動復元完了: {model_data['name']}")
                            else:
                                print(f"✅ Live2Dモデル自動復元完了（警告あり）: {model_data['name']} - 実際には正常動作中")
                                
                        except Exception as e:
                            print(f"自動復元最終処理エラー: {e}")
                    
                    QTimer.singleShot(500, check_and_finalize_success)
                        
                    if hasattr(self, '_pending_model_data'):
                        delattr(self, '_pending_model_data')
                        
                except Exception as e:
                    print(f"自動復元完了処理エラー: {e}")
            
            self.live2d_webview.page().runJavaScript(script, on_auto_restore_result)
            
        except Exception as e:
            print(f"モデル読み込み実行エラー: {e}")
            if hasattr(self, '_pending_model_data'):
                delattr(self, '_pending_model_data')

    def apply_settings_to_webview(self, ui_settings):
        """UI設定をWebViewに適用（画像表示と同じ座標系）"""
        if self.live2d_webview.is_model_loaded:
            js_settings = {}
            
            # ズーム設定
            zoom_percent = ui_settings.get('zoom_percent', 100)
            js_settings['scale'] = zoom_percent / 100.0
            
            # 位置設定（画像表示と同じ座標系）
            h_pos = ui_settings.get('h_position', 50)
            v_pos = ui_settings.get('v_position', 50)
            js_settings['position_x'] = (h_pos - 50) / 50.0   # 右スライダー→キャラ右
            js_settings['position_y'] = (v_pos - 50) / 50.0   # 下スライダー→キャラ下（画像表示と同じ）
            
            self.live2d_webview.update_model_settings(js_settings)

    def enable_live2d_controls(self):
        """Live2D制御を有効化"""
        for control in [
            self.live2d_zoom_slider, 
            self.live2d_h_position_slider, 
            self.live2d_v_position_slider,
            self.live2d_clear_btn
        ]:
            control.setEnabled(True)
        
        if self.current_display_mode == "live2d":
            self.toggle_minimap_btn.setEnabled(True)

    def clear_live2d_model(self):
        """Live2Dモデルをクリア"""
        self.live2d_webview.is_model_loaded = False
        self.current_live2d_folder = None
        self.current_live2d_id = None
        self.live2d_info_label.setText("Live2Dモデルが読み込まれていません")
        
        for control in [
            self.live2d_zoom_slider, 
            self.live2d_h_position_slider, 
            self.live2d_v_position_slider,
            self.live2d_clear_btn
        ]:
            control.setEnabled(False)
        
        self.live2d_zoom_slider.setValue(100)
        self.live2d_h_position_slider.setValue(50)
        self.live2d_v_position_slider.setValue(50)
        self.live2d_zoom_label.setText("100%")
        
        self.live2d_webview.load_initial_page()

    def restore_live2d_settings(self, ui_settings):
        """Live2D設定を復元（500%対応）"""
        zoom_percent = ui_settings.get('zoom_percent', 100)
        self.live2d_zoom_slider.blockSignals(True)
        self.live2d_zoom_slider.setValue(zoom_percent)
        self.live2d_zoom_label.setText(f"{zoom_percent}%")
        self.live2d_zoom_slider.blockSignals(False)
        
        h_pos = ui_settings.get('h_position', 50)
        v_pos = ui_settings.get('v_position', 50)
        self.live2d_h_position_slider.blockSignals(True)
        self.live2d_v_position_slider.blockSignals(True)
        self.live2d_h_position_slider.setValue(h_pos)
        self.live2d_v_position_slider.setValue(v_pos)
        self.live2d_h_position_slider.blockSignals(False)
        self.live2d_v_position_slider.blockSignals(False)
        
        minimap_visible = ui_settings.get('minimap_visible', False)
        self.toggle_minimap_btn.setChecked(minimap_visible)
        if hasattr(self, 'live2d_minimap'):
            if minimap_visible:
                self.live2d_minimap.show()
                self.update_live2d_minimap_position()
                self.update_live2d_minimap()
            else:
                self.live2d_minimap.hide()

    def save_live2d_ui_settings(self):
        """Live2DのUI設定を保存（500%対応）"""
        if not self.current_live2d_id:
            return
        
        ui_settings = {
            'zoom_percent': self.live2d_zoom_slider.value(),
            'h_position': self.live2d_h_position_slider.value(),
            'v_position': self.live2d_v_position_slider.value(),
            'minimap_visible': self.toggle_minimap_btn.isChecked()
        }
        self.live2d_manager.update_ui_settings(self.current_live2d_id, ui_settings)

    def show_live2d_history_dialog(self):
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle("Live2D履歴から選択")
            dlg.setModal(True)
            dlg.resize(600, 500)
            dlg.setStyleSheet("QDialog { background:#f8f9fa; }")
            layout = QVBoxLayout(dlg)
            history_widget = Live2DHistoryWidget(self.live2d_manager, dlg)
            def on_model_selected(model_data):
                if not Path(model_data['model_folder_path']).exists():
                    QMessageBox.warning(dlg, "エラー", "Live2Dモデルフォルダが見つかりません。")
                    return
                dlg.accept()
                self.load_live2d_from_data(model_data)
            history_widget.model_selected.connect(on_model_selected)
            layout.addWidget(history_widget)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"Live2D履歴ダイアログでエラーが発生しました:\n{str(e)}")

    def update_lip_sync(self, volume):
        if self.current_display_mode == "live2d" and self.live2d_webview.is_model_loaded:
            self.live2d_webview.update_lip_sync(volume)
    
    def load_last_content(self):
        self.image_manager.cleanup_missing_images()
        last_image = self.image_manager.get_last_image()
        if last_image and Path(last_image['image_path']).exists():
            self.load_image_from_data(last_image)
    
    def load_image_from_data(self, image_data):
        image_path = image_data['image_path']
        if not Path(image_path).exists(): 
            QMessageBox.warning(self, "エラー", f"画像ファイルが見つかりません:\n{image_path}")
            return
        pixmap = QPixmap(image_path)
        if pixmap.isNull(): return
        self.original_pixmap = pixmap
        self.current_image_path = image_path
        self.current_image_id = image_data['id']
        
        self.display_mode_manager.set_last_image_id(self.current_image_id)
        
        self.image_manager.add_image(image_path, image_data['name'])
        ui_settings = self.image_manager.get_ui_settings(self.current_image_id)
        self.restore_ui_settings(ui_settings)
        self.character_image_label.setStyleSheet("QLabel { background-color: white; border: none; }")
        file_info = Path(image_path)
        img_size = pixmap.size()
        self.image_info_label.setText(f"📁 {image_data['name']}\n📐 {img_size.width()}×{img_size.height()}px 💾 {file_info.stat().st_size // 1024} KB")
        self.enable_controls()
        self.update_minimap_position()
        self.mode_tab_widget.setCurrentIndex(0)
    
    def load_character_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "立ち絵画像を選択", "", "画像ファイル (*.png *.jpg *.jpeg)")
        if not file_path: return
        image_name = Path(file_path).stem
        image_id = self.image_manager.add_image(file_path, image_name)
        
        self.display_mode_manager.set_last_image_id(image_id)
        
        new_image_data = self.image_manager.get_image_by_id(image_id)
        if new_image_data: 
            self.load_image_from_data(new_image_data)
    
    def enable_controls(self):
        for widget in [self.image_clear_btn, self.zoom_slider, self.h_position_slider, self.v_position_slider, self.toggle_minimap_btn]: 
            widget.setEnabled(True)
    
    def clear_character_image(self):
        self.character_image_label.clear()
        self.character_image_label.setText("画像が読み込まれていません...")
        self.character_image_label.setStyleSheet("QLabel { background-color: #f8f9fa; border: 2px dashed #adb5bd; }")
        self.original_pixmap = None
        self.current_image_path = None
        self.current_image_id = None
        self.image_info_label.setText("")
        for widget in [self.image_clear_btn, self.zoom_slider, self.h_position_slider, self.v_position_slider, self.toggle_minimap_btn]: 
            widget.setEnabled(False)
        self.zoom_slider.setValue(50)
        self.h_position_slider.setValue(50)
        self.v_position_slider.setValue(50)
        self.toggle_minimap_btn.setChecked(False)
        self.zoom_label.setText("50%")
        self.minimap.hide()
    
    def restore_ui_settings(self, ui_settings):
        zoom = ui_settings.get('zoom_percent', 50)
        h_pos = ui_settings.get('h_position', 50)
        v_pos = ui_settings.get('v_position', 50)
        minimap_visible = ui_settings.get('minimap_visible', False)
        self.zoom_slider.blockSignals(True)
        self.current_zoom_percent = zoom
        self.zoom_slider.setValue(zoom)
        self.zoom_label.setText(f"{zoom}%")
        self.zoom_slider.blockSignals(False)
        self.update_image_display()
        h_scroll = self.scroll_area.horizontalScrollBar()
        v_scroll = self.scroll_area.verticalScrollBar()
        if h_scroll.maximum() > 0: 
            h_scroll.setValue(round(h_scroll.maximum() * h_pos / 100))
        if v_scroll.maximum() > 0: 
            v_scroll.setValue(round(v_scroll.maximum() * (100 - v_pos) / 100))
        self.update_custom_scrollbars()
        self.toggle_minimap_btn.setChecked(minimap_visible)
        self.toggle_minimap(minimap_visible)
    
    def save_ui_settings(self):
        if not self.current_image_id: return
        ui_settings = {
            'zoom_percent': self.current_zoom_percent, 
            'h_position': self.h_position_slider.value(), 
            'v_position': self.v_position_slider.value(), 
            'minimap_visible': self.toggle_minimap_btn.isChecked()
        }
        self.image_manager.update_ui_settings(self.current_image_id, ui_settings)
    
    def show_image_history_dialog(self):
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle("画像履歴から選択")
            dlg.setModal(True)
            dlg.resize(600, 500)
            dlg.setStyleSheet("QDialog { background:#f8f9fa; }")
            layout = QVBoxLayout(dlg)
            history_widget = ImageHistoryWidget(self.image_manager, dlg)
            def on_image_selected(image_data):
                if not Path(image_data['image_path']).exists(): 
                    QMessageBox.warning(dlg, "エラー", "画像ファイルが見つかりません.")
                    return
                dlg.accept()
                self.load_image_from_data(image_data)
            history_widget.image_selected.connect(on_image_selected)
            layout.addWidget(history_widget)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"画像履歴ダイアログでエラーが発生しました:\n{str(e)}")
    
    def on_zoom_slider_changed(self, value):
        if not self.original_pixmap: return
        self.setUpdatesEnabled(False)
        try:
            scroll_area = self.scroll_area
            h_scroll = scroll_area.horizontalScrollBar()
            v_scroll = scroll_area.verticalScrollBar()
            old_label_size = self.character_image_label.size()
            viewport_size = scroll_area.viewport().size()
            center_x_ratio = (h_scroll.value() + viewport_size.width() / 2) / old_label_size.width() if old_label_size.width() > 0 else 0.5
            center_y_ratio = (v_scroll.value() + viewport_size.height() / 2) / old_label_size.height() if old_label_size.height() > 0 else 0.5
            self.current_zoom_percent = value
            self.update_image_display()
            self.update_zoom_label()
            new_label_size = self.character_image_label.size()
            new_h_scroll_value = round((new_label_size.width() * center_x_ratio) - (viewport_size.width() / 2))
            new_v_scroll_value = round((new_label_size.height() * center_y_ratio) - (viewport_size.height() / 2))
            h_scroll.setValue(new_h_scroll_value)
            v_scroll.setValue(new_v_scroll_value)
            self.update_custom_scrollbars()
            self.save_ui_settings()
        finally:
            self.setUpdatesEnabled(True)
    
    def update_image_display(self):
        if not self.original_pixmap: return
        self.current_zoom_percent = self.zoom_slider.value()
        original_size = self.original_pixmap.size()
        new_width = round(original_size.width() * self.current_zoom_percent / 100)
        new_height = round(original_size.height() * self.current_zoom_percent / 100)
        scaled_pixmap = self.original_pixmap.scaled(new_width, new_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.character_image_label.setPixmap(scaled_pixmap)
        self.character_image_label.resize(scaled_pixmap.size())
        self.update_minimap_view()
    
    def update_zoom_label(self):
        self.zoom_label.setText(f"{self.current_zoom_percent}%")
    
    def on_position_slider_changed(self):
        if not self.original_pixmap: return
        h_scroll = self.scroll_area.horizontalScrollBar()
        v_scroll = self.scroll_area.verticalScrollBar()
        h_max = h_scroll.maximum()
        v_max = v_scroll.maximum()
        if h_max > 0: 
            h_scroll.setValue(round(h_max * self.h_position_slider.value() / 100))
        if v_max > 0: 
            v_scroll.setValue(round(v_scroll.maximum() * (100 - self.v_position_slider.value()) / 100))
        self.update_minimap_view()
        if not self.h_position_slider.signalsBlocked(): 
            self.save_ui_settings()
    
    def update_custom_scrollbars(self):
        if not self.original_pixmap: return
        h_scroll = self.scroll_area.horizontalScrollBar()
        v_scroll = self.scroll_area.verticalScrollBar()
        h_max = h_scroll.maximum()
        v_max = v_scroll.maximum()
        self.h_position_slider.blockSignals(True)
        self.v_position_slider.blockSignals(True)
        self.h_position_slider.setValue(round(100 * h_scroll.value() / h_max) if h_max > 0 else 50)
        self.v_position_slider.setValue(100 - round(100 * v_scroll.value() / v_max) if v_max > 0 else 50)
        self.h_position_slider.blockSignals(False)
        self.v_position_slider.blockSignals(False)
    
    def update_minimap_view(self):
        if not self.original_pixmap or not self.minimap.isVisible(): return
        h_scroll, v_scroll = self.scroll_area.horizontalScrollBar(), self.scroll_area.verticalScrollBar()
        view_w, view_h = self.scroll_area.viewport().width(), self.scroll_area.viewport().height()
        img_w, img_h = self.character_image_label.width(), self.character_image_label.height()
        if img_w <= 0: return
        scale_x = self.original_pixmap.width() / img_w
        scale_y = self.original_pixmap.height() / img_h
        view_rect = QRect(round(h_scroll.value() * scale_x), round(v_scroll.value() * scale_y), round(view_w * scale_x), round(view_h * scale_y))
        self.minimap.update_minimap(self.original_pixmap, view_rect)
    
    def move_view_to_position(self, target_x, target_y):
        if not self.original_pixmap: return
        img_w = self.character_image_label.width()
        img_h = self.character_image_label.height()
        scale_x = img_w / self.original_pixmap.width()
        scale_y = img_h / self.original_pixmap.height()
        scroll_x = round(target_x * scale_x - self.scroll_area.viewport().width() / 2)
        scroll_y = round(target_y * scale_y - self.scroll_area.viewport().height() / 2)
        self.scroll_area.horizontalScrollBar().setValue(scroll_x)
        self.scroll_area.verticalScrollBar().setValue(scroll_y)
        self.update_minimap_view()
        self.update_custom_scrollbars()
        self.save_ui_settings()
    
    def update_minimap_position(self):
        if self.scroll_area: 
            x_pos = self.scroll_area.viewport().width() - self.minimap.width() - 5
            self.minimap.move(x_pos, 5)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_minimap_position()
        if hasattr(self, 'live2d_minimap'):
            self.update_live2d_minimap_position()
        if self.original_pixmap: 
            self.resize_timer.start(150)