# ui/main_window.py (修正版: ミニマップ表示位置修正)
import os
import numpy as np
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QFileDialog, QStyle, QFrame, QApplication, QMessageBox, QScrollArea, QSlider, QSplitter)
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from PyQt6.QtGui import QFont, QAction, QPixmap, QPainter, QPen, QColor

# 自作モジュール
from .model_history import ModelHistoryWidget
from .model_loader import ModelLoaderDialog
from .tabbed_audio_control import TabbedAudioControl
from .multi_text import MultiTextWidget
from .keyboard_shortcuts import KeyboardShortcutManager
from .sliding_menu import SlidingMenuWidget
from core.tts_engine import TTSEngine
from core.model_manager import ModelManager
from .help_dialog import HelpDialog

# 音声処理関連
from core.audio_processor import AudioProcessor
from core.audio_analyzer import AudioAnalyzer
from core.audio_effects_processor import AudioEffectsProcessor


class MiniMapWidget(QLabel):
    """右上に表示されるミニマップウィジェット（手動表示版）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 90)
        self.main_window = None
        self.original_pixmap = None
        self.view_rect = QRect()
        
        # 枠線とスタイル設定
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 200);
                border: 2px solid #666;
                border-radius: 4px;
            }
        """)
        
        # 初期状態
        self.setText("ミニマップ")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        
    def set_main_window(self, main_window):
        """メインウィンドウの参照を設定"""
        self.main_window = main_window
        
    def update_minimap(self, original_pixmap, view_rect):
        """ミニマップを更新"""
        if not original_pixmap or original_pixmap.isNull():
            self.clear()
            self.setText("ミニマップ")
            return
            
        self.original_pixmap = original_pixmap
        self.view_rect = view_rect
        
        # ミニマップ用にリサイズ
        mini_pixmap = original_pixmap.scaled(
            self.size(), 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # ビューエリアの矩形を描画
        if not view_rect.isNull():
            painter = QPainter(mini_pixmap)
            painter.setPen(QPen(QColor(255, 0, 0, 200), 2))
            
            # 元画像サイズに対する比率を計算
            scale_x = mini_pixmap.width() / original_pixmap.width()
            scale_y = mini_pixmap.height() / original_pixmap.height()
            
            # ビューエリアをミニマップサイズに変換
            mini_view_rect = QRect(
                int(view_rect.x() * scale_x),
                int(view_rect.y() * scale_y),
                int(view_rect.width() * scale_x),
                int(view_rect.height() * scale_y)
            )
            
            painter.drawRect(mini_view_rect)
            painter.end()
        
        self.setPixmap(mini_pixmap)
    
    def mousePressEvent(self, event):
        """ミニマップクリックでビューを移動"""
        if not self.main_window or not self.original_pixmap:
            return
            
        # クリック位置をオリジナル画像座標に変換
        click_pos = event.position().toPoint()
        
        scale_x = self.original_pixmap.width() / self.width()
        scale_y = self.original_pixmap.height() / self.height()
        
        target_x = int(click_pos.x() * scale_x)
        target_y = int(click_pos.y() * scale_y)
        
        # メインビューを指定位置に移動
        self.main_window.move_view_to_position(target_x, target_y)


class DraggableImageLabel(QLabel):
    """ドラッグで移動可能な画像表示ラベル（ホイールズーム対応版）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scroll_area = None
        self.main_window = None
        self.last_pan_pos = None
        self.is_dragging = False
        self.setMouseTracking(True)
        # ドラッグ用のカーソル設定
        self.setCursor(Qt.CursorShape.OpenHandCursor)
    
    def set_scroll_area(self, scroll_area):
        """スクロールエリアを設定"""
        self.scroll_area = scroll_area
    
    def set_main_window(self, main_window):
        """メインウィンドウの参照を設定"""
        self.main_window = main_window
    
    def wheelEvent(self, event):
        """マウスホイールでズーム（シンプル版）"""
        if not self.pixmap() or not self.main_window:
            super().wheelEvent(event)
            return
        
        # ホイールの回転方向を取得
        delta = event.angleDelta().y()
        zoom_step = 5  # 1回のスクロールで5%ずつ変更
        
        current_zoom = self.main_window.zoom_slider.value()
        
        if delta > 0:  # 上方向スクロール（ズームイン）
            new_zoom = min(150, current_zoom + zoom_step)
        else:  # 下方向スクロール（ズームアウト）
            new_zoom = max(20, current_zoom - zoom_step)
        
        self.main_window.zoom_slider.setValue(new_zoom)
        event.accept()  # イベントを確実に処理済みにする
    
    def mousePressEvent(self, event):
        """マウス押下時"""
        if event.button() == Qt.MouseButton.LeftButton and self.pixmap():
            self.last_pan_pos = event.position().toPoint()
            self.is_dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)  # ドラッグ中のカーソル
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """マウス移動時（ドラッグ処理）"""
        if self.is_dragging and self.last_pan_pos and self.scroll_area:
            # 移動量を計算
            delta = event.position().toPoint() - self.last_pan_pos
            
            # スクロールバーの値を更新（移動方向と逆）
            h_scroll = self.scroll_area.horizontalScrollBar()
            v_scroll = self.scroll_area.verticalScrollBar()
            
            h_scroll.setValue(h_scroll.value() - delta.x())
            v_scroll.setValue(v_scroll.value() - delta.y())
            
            self.last_pan_pos = event.position().toPoint()
            
            # ミニマップとカスタムスクロールバーを更新
            if self.main_window:
                self.main_window.update_minimap_view()
                self.main_window.update_custom_scrollbars()
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """マウス離した時"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.last_pan_pos = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)  # 通常カーソルに戻す
        super().mouseReleaseEvent(event)
    
    def enterEvent(self, event):
        """マウスが入った時"""
        if self.pixmap():  # 画像がある場合のみ
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """マウスが出た時"""
        if not self.is_dragging:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)


class TTSStudioMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tts_engine = TTSEngine()
        self.model_manager = ModelManager()
        
        # 音声処理関連を追加
        self.audio_processor = AudioProcessor()
        self.audio_analyzer = AudioAnalyzer()
        self.audio_effects_processor = AudioEffectsProcessor()
        self.last_generated_audio = None  # 解析用に最新の音声を保存
        self.last_sample_rate = None
        
        # 画像管理関連（新規追加）
        self.current_image_path = None  # 現在読み込まれている画像パス
        self.image_history = []  # 画像履歴（将来の実装用）
        
        # ズーム関連の変数（シンプル版）
        self.original_pixmap = None  # 元画像
        self.current_zoom_percent = 50  # 現在のズーム率（%）
        self.max_zoom_percent = 150  # 最大ズーム率
        
        self.init_ui()
        self.help_dialog = HelpDialog(self)
        
        # 音声処理統合設定（クリーナー + エフェクト）
        self.setup_audio_processing_integration()
        
        # スライド式メニューを作成（画像シグナル追加）
        self.sliding_menu = SlidingMenuWidget(self)
        # 音声モデル関連
        self.sliding_menu.load_model_clicked.connect(self.open_model_loader)
        self.sliding_menu.load_from_history_clicked.connect(self.show_model_history_dialog)
        # 画像関連（新規追加）
        self.sliding_menu.load_image_clicked.connect(self.load_character_image)
        self.sliding_menu.load_image_from_history_clicked.connect(self.show_image_history_dialog)
        
        # キーボードショートカット設定
        self.keyboard_shortcuts = KeyboardShortcutManager(self)
        
        self.load_last_model()

    def init_ui(self):
        self.setWindowTitle("TTSスタジオ")
        self.setGeometry(100, 100, 1200, 800)
        self.create_menu_bar()

        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setSpacing(10)
        main.setContentsMargins(15, 15, 15, 15)

        # メインスプリッターを作成（左右リサイズ可能）
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #dee2e6;
                width: 3px;
            }
            QSplitter::handle:hover {
                background-color: #adb5bd;
            }
        """)

        # 左ペインウィジェット
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.multi_text = MultiTextWidget()
        self.multi_text.play_single_requested.connect(self.play_single_text)
        self.multi_text.row_added.connect(self.on_text_row_added)
        self.multi_text.row_removed.connect(self.on_text_row_removed)
        self.multi_text.row_numbers_updated.connect(self.on_row_numbers_updated)

        # 音声パラメータラベル削除（タブで表示されるため）
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setStyleSheet("color: #dee2e6;")

        # TabbedAudioControl（音声パラメータ + クリーナー + エフェクト統合版）
        self.tabbed_audio_control = TabbedAudioControl()
        self.tabbed_audio_control.parameters_changed.connect(self.on_parameters_changed)
        self.tabbed_audio_control.cleaner_settings_changed.connect(self.on_cleaner_settings_changed)
        self.tabbed_audio_control.effects_settings_changed.connect(self.on_effects_settings_changed)
        self.tabbed_audio_control.add_text_row("initial", 1)

        controls = QHBoxLayout()
        controls.addStretch()

        # --- ボタン群 ---
        self.sequential_play_btn = QPushButton("連続して再生(Ctrl + R)")
        self.sequential_play_btn.setMinimumHeight(35)
        self.sequential_play_btn.setEnabled(False)
        self.sequential_play_btn.setStyleSheet(self._blue_btn_css())
        self.sequential_play_btn.clicked.connect(self.play_sequential)

        self.save_individual_btn = QPushButton("個別保存(Ctrl + S)")
        self.save_individual_btn.setMinimumHeight(35)
        self.save_individual_btn.setEnabled(False)
        self.save_individual_btn.setStyleSheet(self._green_btn_css())
        self.save_individual_btn.clicked.connect(self.save_individual)

        self.save_continuous_btn = QPushButton("連続保存(Ctrl + Shift + S)")
        self.save_continuous_btn.setMinimumHeight(35)
        self.save_continuous_btn.setEnabled(False)
        self.save_continuous_btn.setStyleSheet(self._orange_btn_css())
        self.save_continuous_btn.clicked.connect(self.save_continuous)

        controls.addWidget(self.sequential_play_btn)
        controls.addWidget(self.save_individual_btn)
        controls.addWidget(self.save_continuous_btn)

        left_layout.addWidget(self.multi_text, 2)
        left_layout.addWidget(divider)
        left_layout.addWidget(self.tabbed_audio_control, 1)
        left_layout.addLayout(controls)

        # 右ペイン（キャラクター表示エリア）
        self.character_display_widget = self.create_character_display_widget()

        # スプリッターに追加
        self.main_splitter.addWidget(left_widget)
        self.main_splitter.addWidget(self.character_display_widget)
        
        # 初期サイズ比率設定（左7:右3の比率で開始）
        self.main_splitter.setSizes([700, 300])
        
        # 最小サイズ設定
        left_widget.setMinimumWidth(500)  # 左ペイン最小幅
        self.character_display_widget.setMinimumWidth(200)  # 右ペイン最小幅
        
        # 最大サイズ制約（7:3比率を維持）
        self.main_splitter.splitterMoved.connect(self.on_splitter_moved)
        
        main.addWidget(self.main_splitter)

    def create_character_display_widget(self):
        """キャラクター表示ウィジェット作成（リサイズ対応版）"""
        widget = QWidget()
        # 固定幅制限を削除（リサイズ可能にするため）
        widget.setStyleSheet("""
            QWidget { 
                background-color: #ffffff; 
                border: 1px solid #dee2e6; 
                border-radius: 4px; 
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # ヘッダーレイアウト（ラベル + ボタン）
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        header_label = QLabel("キャラクター表示")
        header_label.setFont(QFont("", 12, QFont.Weight.Bold))
        header_label.setStyleSheet("color: #333; border: none; padding: 5px;")

        header_layout.addWidget(header_label)
        header_layout.addStretch()

        # ミニマップ表示/非表示ボタン
        self.toggle_minimap_btn = QPushButton("🗺️ ミニマップ")
        self.toggle_minimap_btn.setToolTip("ミニマップの表示/非表示")
        self.toggle_minimap_btn.setEnabled(False)
        self.toggle_minimap_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 11px;
                padding: 4px 8px;
            }
            QPushButton:hover:enabled {
                background-color: #e9ecef;
                border-color: #bbb;
            }
            QPushButton:checked {
                background-color: #e0e6ef;
                border-color: #007bff;
            }
            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #ccc;
            }
        """)
        self.toggle_minimap_btn.setCheckable(True)
        self.toggle_minimap_btn.toggled.connect(self.toggle_minimap)

        header_layout.addWidget(self.toggle_minimap_btn)
        
        # ズームコントロール
        zoom_layout = QVBoxLayout()
        zoom_layout.setSpacing(4)
        
        # ズーム率表示
        self.zoom_label = QLabel("50%")
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setStyleSheet("color: #666; font-size: 11px; font-weight: bold; border: none;")
        
        # ズームスライダー（シンプル版）
        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(6)
        
        # ズームスライダー（20%-150%の直接制御）
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(20, 150)  # 直接パーセンテージで管理
        self.zoom_slider.setValue(50)  # 初期値50%（全身表示用）
        self.zoom_slider.setEnabled(False)
        self.zoom_slider.setToolTip("ズーム調整（マウスホイールでも操作可能）")
        
        # スライダースタイル
        slider_style = """
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #66e, stop: 1 #bbf);
                border: 1px solid #777;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #eee, stop: 1 #ccc);
                border: 1px solid #777;
                width: 14px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 7px;
            }
        """
        
        self.zoom_slider.setStyleSheet(slider_style)
        
        # メイン画像表示エリア（正しいスライダー配置版）
        image_container = QWidget()
        image_container.setStyleSheet("border: 1px solid #ccc; border-radius: 4px; background-color: #f8f9fa;")
        
        # 画像エリア全体のレイアウト（縦スライダー、横スライダー配置用）
        image_main_layout = QHBoxLayout(image_container)
        image_main_layout.setContentsMargins(5, 5, 5, 5)
        image_main_layout.setSpacing(5)
        
        # 左側：スクロールエリア + 下部横スライダー
        left_side_layout = QVBoxLayout()
        left_side_layout.setSpacing(5)
        
        # スクロールエリア（ドラッグ移動対応）
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)  # 手動サイズ管理
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("border: none; background-color: #f8f9fa;")
        
        # カスタム画像表示ラベル（ドラッグ移動対応）
        self.character_image_label = DraggableImageLabel()
        self.character_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.character_image_label.setMinimumSize(200, 200)
        self.character_image_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 2px dashed #adb5bd;
                border-radius: 6px;
                color: #6c757d;
                font-size: 14px;
                padding: 20px;
            }
        """)
        self.character_image_label.setText("画像が読み込まれていません\n\nファイルメニューから\n「立ち絵画像を読み込み」\nを選択してください")
        self.character_image_label.setWordWrap(True)
        self.character_image_label.set_scroll_area(self.scroll_area)
        self.character_image_label.set_main_window(self)
        
        self.scroll_area.setWidget(self.character_image_label)
        
        # --- ここから変更点 ---
        # ミニマップ（右上に配置、親をscroll_areaに変更）
        self.minimap = MiniMapWidget(self.scroll_area)
        # --- ここまで変更点 ---
        self.minimap.set_main_window(self)
        self.minimap.hide()  # 初期状態では非表示
        
        # 横スライダー（左右位置調整）
        h_slider_layout = QHBoxLayout()
        h_slider_layout.setSpacing(4)
        
        h_label = QLabel("左右:")
        h_label.setStyleSheet("color: #666; font-size: 10px; border: none;")
        h_label.setFixedWidth(25)
        
        self.h_position_slider = QSlider(Qt.Orientation.Horizontal)
        self.h_position_slider.setRange(0, 100)
        self.h_position_slider.setValue(50)  # 中央
        self.h_position_slider.setEnabled(False)
        self.h_position_slider.setToolTip("左右位置調整")
        self.h_position_slider.setStyleSheet(slider_style)
        
        h_slider_layout.addWidget(h_label)
        h_slider_layout.addWidget(self.h_position_slider)
        
        left_side_layout.addWidget(self.scroll_area, 1)
        left_side_layout.addLayout(h_slider_layout)
        
        # 右側：縦スライダー（上下位置調整）
        v_slider_layout = QVBoxLayout()
        v_slider_layout.setSpacing(4)
        
        v_label = QLabel("上下")
        v_label.setStyleSheet("color: #666; font-size: 10px; border: none; text-align: center;")
        v_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.v_position_slider = QSlider(Qt.Orientation.Vertical)
        self.v_position_slider.setRange(0, 100)
        self.v_position_slider.setValue(50)  # 中央
        self.v_position_slider.setEnabled(False)
        self.v_position_slider.setToolTip("上下位置調整")
        self.v_position_slider.setStyleSheet("""
            QSlider::groove:vertical {
                border: 1px solid #bbb;
                background: white;
                width: 4px;
                border-radius: 2px;
            }
            QSlider::sub-page:vertical {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #66e, stop: 1 #bbf);
                border: 1px solid #777;
                width: 4px;
                border-radius: 2px;
            }
            QSlider::handle:vertical {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #eee, stop: 1 #ccc);
                border: 1px solid #777;
                height: 14px;
                margin-left: -6px;
                margin-right: -6px;
                border-radius: 7px;
            }
        """)
        
        v_slider_layout.addWidget(v_label)
        v_slider_layout.addWidget(self.v_position_slider, 1)
        
        # メインレイアウトに追加
        image_main_layout.addLayout(left_side_layout, 1)
        image_main_layout.addLayout(v_slider_layout)
        
        # シグナル接続（シンプル版）
        self.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        self.h_position_slider.valueChanged.connect(self.on_position_slider_changed)
        self.v_position_slider.valueChanged.connect(self.on_position_slider_changed)
        
        slider_layout.addWidget(self.zoom_slider, 1)
        
        zoom_layout.addWidget(self.zoom_label)
        zoom_layout.addLayout(slider_layout)
        
        # 画像情報ラベル
        self.image_info_label = QLabel("")
        self.image_info_label.setStyleSheet("color: #666; font-size: 10px; border: none;")
        self.image_info_label.setWordWrap(True)
        
        # ボタン行
        button_layout = QHBoxLayout()
        
        self.image_clear_btn = QPushButton("🗑️")
        self.image_clear_btn.setFixedSize(30, 30)
        self.image_clear_btn.setToolTip("画像をクリア")
        self.image_clear_btn.setEnabled(False)
        self.image_clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover:enabled {
                background-color: #f5c6cb;
                border-color: #f1556c;
            }
            QPushButton:disabled {
                color: #999;
            }
        """)
        self.image_clear_btn.clicked.connect(self.clear_character_image)
        
        button_layout.addStretch()
        button_layout.addWidget(self.image_clear_btn)
        
        # レイアウト組み立て
        layout.addLayout(header_layout) # ヘッダーラベルからヘッダーレイアウトに変更
        layout.addLayout(zoom_layout)
        layout.addWidget(image_container, 1)  # 伸縮
        layout.addWidget(self.image_info_label)
        layout.addLayout(button_layout)
        
        return widget

    # --- ボタン用CSS ---
    def _blue_btn_css(self) -> str:
        return """
            QPushButton {
                background-color: #1976d2; color: white;
                border: none; border-radius: 4px;
                font-size: 13px; font-weight: bold; padding: 6px 16px;
            }
            QPushButton:hover:enabled { background-color: #1565c0; }
            QPushButton:pressed:enabled { background-color: #0d47a1; }
            QPushButton:disabled { background-color: #f0f0f0; color: #aaaaaa; }
        """

    def _green_btn_css(self) -> str:
        return """
            QPushButton {
                background-color: #4caf50; color: white;
                border: none; border-radius: 4px;
                font-size: 13px; font-weight: bold; padding: 6px 16px;
            }
            QPushButton:hover:enabled { background-color: #388e3c; }
            QPushButton:pressed:enabled { background-color: #2e7d32; }
            QPushButton:disabled { background-color: #f0f0f0; color: #aaaaaa; }
        """

    def _orange_btn_css(self) -> str:
        return """
            QPushButton {
                background-color: #ff9800; color: white;
                border: none; border-radius: 4px;
                font-size: 13px; font-weight: bold; padding: 6px 16px;
            }
            QPushButton:hover:enabled { background-color: #f57c00; }
            QPushButton:pressed:enabled { background-color: #e65100; }
            QPushButton:disabled { background-color: #f0f0f0; color: #aaaaaa; }
        """

    def create_menu_bar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar { background-color: #f8f9fa; color: #333; border-bottom: 1px solid #dee2e6; padding: 4px; }
            QMenuBar::item { background-color: transparent; padding: 6px 12px; margin: 0px 2px; border-radius: 4px; }
            QMenuBar::item:selected { background-color: #e9ecef; }
            QMenuBar::item:pressed { background-color: #dee2e6; }
        """)

        # ファイルメニューをアクションとして追加（サブメニューなし）
        file_action = menubar.addAction("ファイル(F)")
        file_action.triggered.connect(self.toggle_file_menu)

        help_action = menubar.addAction("説明(H)")
        help_action.triggered.connect(self.show_help_dialog)

    def show_help_dialog(self):
        self.help_dialog.show()
        self.help_dialog.raise_()
        self.help_dialog.activateWindow()

    def toggle_file_menu(self):
        """ファイルメニューの表示/非表示を切り替え"""
        self.sliding_menu.toggle_menu()
    
    def mousePressEvent(self, event):
        """マウスクリック時の処理（メニュー外クリックでメニューを閉じる）"""
        # スライドメニューの外側をクリックした場合、メニューを閉じる
        if self.sliding_menu.is_visible and not self.sliding_menu.geometry().contains(event.pos()):
            self.sliding_menu.hide_menu()
        super().mousePressEvent(event)

    def on_splitter_moved(self, pos, index):
        """スプリッター移動時の7:3比率制約"""
        if hasattr(self, 'main_splitter'):  # 初期化完了後のみ
            sizes = self.main_splitter.sizes()
            total_width = sum(sizes)
            
            # 7:3の最大比率をチェック（右ペインが30%を超えないように）
            max_right_width = total_width * 0.3
            min_left_width = total_width * 0.7
            
            if len(sizes) >= 2:
                left_width, right_width = sizes[0], sizes[1]
                
                # 右ペインが30%を超えた場合、制限する
                if right_width > max_right_width:
                    new_right_width = int(max_right_width)
                    new_left_width = total_width - new_right_width
                    self.main_splitter.setSizes([new_left_width, new_right_width])
                
                # 左ペインが70%を下回った場合、制限する  
                elif left_width < min_left_width:
                    new_left_width = int(min_left_width)
                    new_right_width = total_width - new_left_width
                    self.main_splitter.setSizes([new_left_width, new_right_width])

    def update_minimap_position(self):
        """ミニマップの位置を更新（リサイズ対応）"""
        if hasattr(self, 'minimap') and self.scroll_area:
            # スクロールエリアのビューポート右上に配置し、他のUIとの重なりを防ぐ
            viewport_width = self.scroll_area.viewport().width()
            # 右端と上端から5pxの余白を設ける
            x_pos = viewport_width - self.minimap.width() - 5
            y_pos = 5
            self.minimap.move(x_pos, y_pos)

    def load_character_image(self):
        """立ち絵画像を読み込む（TTS用途向けシンプル版）"""
        try:
            # ファイル選択ダイアログ
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "立ち絵画像を選択",
                "",
                "画像ファイル (*.png *.jpg *.jpeg *.bmp *.gif);;PNG files (*.png);;JPEG files (*.jpg *.jpeg);;All files (*.*)"
            )
            
            if file_path:
                # 画像読み込み
                pixmap = QPixmap(file_path)
                
                if pixmap.isNull():
                    QMessageBox.warning(self, "エラー", "画像ファイルの読み込みに失敗しました。")
                    return
                
                # 元画像を保存
                self.original_pixmap = pixmap
                
                # TTS用途向けのシンプルなズーム設定
                self.max_zoom_percent = 150
                
                # 初期ズーム50%（全身表示に適したサイズ）
                self.current_zoom_percent = 50
                self.zoom_slider.setValue(50)
                self.update_image_display()
                
                # スタイル更新（枠線を実線に）
                self.character_image_label.setStyleSheet("""
                    QLabel {
                        background-color: white;
                        border: none;
                    }
                """)
                
                # 画像情報を表示
                file_info = Path(file_path)
                image_size = pixmap.size()
                self.image_info_label.setText(
                    f"📁 {file_info.name}\n"
                    f"📐 {image_size.width()} × {image_size.height()}px\n"
                    f"💾 {file_info.stat().st_size // 1024} KB"
                )
                
                # 現在の画像パスを保存
                self.current_image_path = file_path
                
                # コントロールを有効化
                self.image_clear_btn.setEnabled(True)
                self.zoom_slider.setEnabled(True)
                self.h_position_slider.setEnabled(True)
                self.v_position_slider.setEnabled(True)
                self.toggle_minimap_btn.setEnabled(True)
                self.toggle_minimap_btn.setChecked(False) # 初期状態は非表示
                
                # ズーム表示更新
                self.update_zoom_label()
                
                # ミニマップの位置を更新
                self.update_minimap_position()
                
                # 将来の履歴機能用
                self.add_image_to_history(file_path)
                
                print(f"✅ 立ち絵画像読み込み完了: {file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"画像読み込み中にエラーが発生しました:\n{str(e)}")
            print(f"❌ 画像読み込みエラー: {e}")

    def clear_character_image(self):
        """キャラクター画像をクリア（改良版）"""
        # 画像をクリア
        self.character_image_label.clear()
        self.character_image_label.setText("画像が読み込まれていません\n\nファイルメニューから\n「立ち絵画像を読み込み」\nを選択してください")
        
        # スタイルを元に戻す
        self.character_image_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 2px dashed #adb5bd;
                border-radius: 6px;
                color: #6c757d;
                font-size: 14px;
                padding: 20px;
            }
        """)
        
        # ズーム関連をリセット
        self.original_pixmap = None
        self.max_zoom_percent = 150
        
        # 情報をクリア
        self.image_info_label.setText("")
        self.current_image_path = None
        
        # コントロールを無効化
        self.image_clear_btn.setEnabled(False)
        self.zoom_slider.setEnabled(False)
        self.zoom_slider.setValue(50)  # 初期値に戻す
        self.h_position_slider.setEnabled(False)
        self.h_position_slider.setValue(50)  # 中央にリセット
        self.v_position_slider.setEnabled(False)
        self.v_position_slider.setValue(50)  # 中央にリセット
        self.toggle_minimap_btn.setEnabled(False)
        self.toggle_minimap_btn.setChecked(False) # ボタンの状態もリセット
        
        # ズーム表示をリセット
        self.zoom_label.setText("50%")
        
        # ミニマップを隠す
        self.minimap.hide()
        
        print("🗑️ 立ち絵画像クリア完了")

    def add_image_to_history(self, image_path):
        """画像を履歴に追加（将来の実装用）"""
        if image_path not in self.image_history:
            self.image_history.insert(0, image_path)
            # 履歴は最大10件まで
            if len(self.image_history) > 10:
                self.image_history = self.image_history[:10]

    def show_image_history_dialog(self):
        """画像履歴ダイアログを表示（将来の実装用）"""
        QMessageBox.information(self, "未実装", "画像履歴機能は今後実装予定です。")

    def on_zoom_slider_changed(self, value):
        """ズームスライダーの値が変更された時（シンプル版）"""
        if not self.original_pixmap:
            return
        
        # 直接ズーム率として使用（20%-150%）
        self.current_zoom_percent = value
        
        self.update_image_display()
        self.update_zoom_label()
        
        # ミニマップ更新（ちかちか防止のため少し遅延）
        QApplication.processEvents()
        self.update_minimap_view()
        
        # 位置調整スライダーも更新
        self.update_custom_scrollbars()

    def update_image_display(self):
        """現在のズームレベルに基づいて画像を更新（シンプル版）"""
        if not self.original_pixmap:
            return
        
        # 直接ズーム率を使用
        original_size = self.original_pixmap.size()
        new_width = int(original_size.width() * self.current_zoom_percent / 100)
        new_height = int(original_size.height() * self.current_zoom_percent / 100)
        
        scaled_pixmap = self.original_pixmap.scaled(
            new_width, new_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # 画像を表示
        self.character_image_label.setPixmap(scaled_pixmap)
        self.character_image_label.setText("")
        
        # ラベルサイズを画像に合わせる（スクロール用）
        self.character_image_label.resize(scaled_pixmap.size())

    def update_zoom_label(self):
        """ズーム表示ラベルを更新（シンプル版）"""
        self.zoom_label.setText(f"{self.current_zoom_percent}%")
    
    def on_position_slider_changed(self):
        """位置調整スライダーの値が変更された時"""
        if not self.original_pixmap:
            return
        
        # スクロールエリアとスクロールバーの情報を取得
        h_scroll = self.scroll_area.horizontalScrollBar()
        v_scroll = self.scroll_area.verticalScrollBar()
        
        # スライダーの値（0-100）を実際のスクロール位置に変換
        h_value = self.h_position_slider.value()  # 0-100
        v_value = self.v_position_slider.value()  # 0-100
        
        # 左右スクロール範囲に変換（通常通り）
        if h_scroll.maximum() > 0:
            new_h_pos = int(h_scroll.maximum() * h_value / 100)
            h_scroll.setValue(new_h_pos)
        
        # 上下スクロール範囲に変換（方向を逆転）
        if v_scroll.maximum() > 0:
            # 上に動かしたら上に行くよう、方向を反転
            inverted_v_value = 100 - v_value
            new_v_pos = int(v_scroll.maximum() * inverted_v_value / 100)
            v_scroll.setValue(new_v_pos)
        
        # ミニマップを更新
        self.update_minimap_view()

    def update_custom_scrollbars(self):
        """カスタムスクロールバー（位置調整スライダー）を現在の位置に同期（シンプル版）"""
        if not self.original_pixmap:
            # 画像がない場合は中央に設定
            self.h_position_slider.blockSignals(True)
            self.v_position_slider.blockSignals(True)
            self.h_position_slider.setValue(50)
            self.v_position_slider.setValue(50)
            self.h_position_slider.blockSignals(False)
            self.v_position_slider.blockSignals(False)
            return
        
        h_scroll = self.scroll_area.horizontalScrollBar()
        v_scroll = self.scroll_area.verticalScrollBar()
        
        # スクロール位置を反映
        if h_scroll.maximum() > 0:
            h_percent = int(100 * h_scroll.value() / h_scroll.maximum())
            self.h_position_slider.blockSignals(True)  # 無限ループを防ぐ
            self.h_position_slider.setValue(h_percent)
            self.h_position_slider.blockSignals(False)
        else:
            # スクロールできない場合は中央
            self.h_position_slider.blockSignals(True)
            self.h_position_slider.setValue(50)
            self.h_position_slider.blockSignals(False)
        
        if v_scroll.maximum() > 0:
            v_percent = int(100 * v_scroll.value() / v_scroll.maximum())
            # 上下方向を反転してスライダーに反映
            inverted_v_percent = 100 - v_percent
            self.v_position_slider.blockSignals(True)  # 無限ループを防ぐ
            self.v_position_slider.setValue(inverted_v_percent)
            self.v_position_slider.blockSignals(False)
        else:
            # スクロールできない場合は中央
            self.v_position_slider.blockSignals(True)
            self.v_position_slider.setValue(50)
            self.v_position_slider.blockSignals(False)

    # ================================
    # ミニマップ機能
    # ================================
    def toggle_minimap(self, checked):
        """ミニマップの表示/非表示を切り替え"""
        if not self.original_pixmap:
            return
        
        if checked:
            self.minimap.show()
            self.update_minimap_view()  # 表示時に更新
        else:
            self.minimap.hide()

    def update_minimap_view(self):
        """ミニマップのビューエリアを更新"""
        if not self.original_pixmap or not self.minimap.isVisible():
            return
        
        # 現在の表示エリアを計算
        h_scroll = self.scroll_area.horizontalScrollBar()
        v_scroll = self.scroll_area.verticalScrollBar()
        
        # スクロールエリアのサイズ
        scroll_width = self.scroll_area.viewport().width()
        scroll_height = self.scroll_area.viewport().height()
        
        # 現在の画像サイズ
        current_image_width = self.character_image_label.width()
        current_image_height = self.character_image_label.height()
        
        if current_image_width <= 0 or current_image_height <= 0:
            return
        
        # 表示エリアの原画像に対する座標を計算
        scale_to_original_x = self.original_pixmap.width() / current_image_width
        scale_to_original_y = self.original_pixmap.height() / current_image_height
        
        view_rect = QRect(
            int(h_scroll.value() * scale_to_original_x),
            int(v_scroll.value() * scale_to_original_y),
            int(min(scroll_width, current_image_width) * scale_to_original_x),
            int(min(scroll_height, current_image_height) * scale_to_original_y)
        )
        
        # ミニマップを更新
        self.minimap.update_minimap(self.original_pixmap, view_rect)
    
    def move_view_to_position(self, target_x, target_y):
        """ビューを指定位置に移動（ミニマップクリック用）"""
        if not self.original_pixmap:
            return
        
        # 現在の画像サイズ
        current_image_width = self.character_image_label.width()
        current_image_height = self.character_image_label.height()
        
        if current_image_width <= 0 or current_image_height <= 0:
            return
        
        # 原画像座標から現在の表示座標に変換
        scale_to_current_x = current_image_width / self.original_pixmap.width()
        scale_to_current_y = current_image_height / self.original_pixmap.height()
        
        # スクロール位置を計算（クリック位置を中央にする）
        scroll_x = int(target_x * scale_to_current_x - self.scroll_area.viewport().width() / 2)
        scroll_y = int(target_y * scale_to_current_y - self.scroll_area.viewport().height() / 2)
        
        # スクロールバーを更新
        h_scroll = self.scroll_area.horizontalScrollBar()
        v_scroll = self.scroll_area.verticalScrollBar()
        
        h_scroll.setValue(scroll_x)
        v_scroll.setValue(scroll_y)
        
        # ミニマップを更新
        self.update_minimap_view()
    
    def resizeEvent(self, event):
        """ウィンドウリサイズ時の処理"""
        super().resizeEvent(event)
        
        # 少し遅延させてから位置を更新すると、より正確なサイズを取得できる場合がある
        QTimer.singleShot(0, self.update_minimap_position)
        
        # ズーム表示の再計算
        if hasattr(self, 'original_pixmap') and self.original_pixmap:
            QApplication.processEvents()  # UI更新を待つ
            self.update_image_display()
            self.update_minimap_view()
    
    # ================================
    # 音声処理統合設定（クリーナー + エフェクト）
    # ================================
    def setup_audio_processing_integration(self):
        """音声処理（クリーナー + エフェクト）との統合設定"""
        # クリーナーの解析要求シグナルを接続
        self.tabbed_audio_control.cleaner_control.analyze_requested.connect(
            self.handle_cleaner_analysis_request
        )
    
    def handle_cleaner_analysis_request(self):
        """クリーナーからの解析要求を処理"""
        if not self.tts_engine.is_loaded:
            QMessageBox.warning(self, "エラー", "モデルが読み込まれていません。\n先にモデルを読み込んでから解析してください。")
            return
        
        # テスト用音声を生成して解析
        self.generate_test_audio_for_analysis()
    
    def generate_test_audio_for_analysis(self):
        """解析用のテスト音声を生成（1行目のテキストを使用）修正版"""
        # 1行目のテキストを取得
        texts_data = self.multi_text.get_all_texts_and_parameters()
        
        if texts_data:
            # 1行目のテキストを使用
            first_data = texts_data[0]
            test_text = first_data['text']
            row_id = first_data['row_id']
            test_params = self.tabbed_audio_control.get_parameters(row_id) or first_data['parameters']
            
            # テキストが空の場合のチェック
            if not test_text.strip():
                test_text = "これは音声解析用のサンプルテキストです。ほのかちゃんの声で品質をチェックします。"
                print("⚠️ 1行目のテキストが空のため、サンプルテキストを使用")
        else:
            # テキストが全くない場合はサンプルテキストを使用
            test_text = "これは音声解析用のサンプルテキストです。ほのかちゃんの声で品質をチェックします。"
            test_params = {
                'style': 'Neutral', 'style_weight': 1.0,
                'length_scale': 0.85, 'pitch_scale': 1.0,
                'intonation_scale': 1.0, 'sdp_ratio': 0.25, 'noise': 0.35
            }
            print("⚠️ テキストが未入力のため、サンプルテキストを使用")
        
        progress = None  # プログレスダイアログの参照を初期化
        
        try:
            print(f"🎤 解析用音声を生成中: '{test_text[:30]}...'")
            
            # 解析用進捗表示（改良版）
            progress = QMessageBox(self)
            progress.setWindowTitle("音声生成中")
            progress.setText(f"解析用の音声を生成しています...\n\nテキスト: {test_text[:50]}...")
            progress.setStandardButtons(QMessageBox.StandardButton.NoButton)  # ボタン無し
            progress.setWindowModality(Qt.WindowModality.ApplicationModal)  # モーダル設定
            progress.show()
            
            # UI更新を強制
            QApplication.processEvents()
            
            # 音声合成（クリーナーは適用しない - 生音声を解析）
            sr, audio = self.tts_engine.synthesize(test_text, **test_params)
            print(f"✅ 音声生成完了: shape={audio.shape}, sr={sr}, 長さ={len(audio)/sr:.2f}秒")
            
            # 保存（解析用）
            self.last_generated_audio = audio
            self.last_sample_rate = sr
            
            # プログレスダイアログを確実に閉じる
            if progress:
                progress.close()
                progress.deleteLater()  # メモリからも削除
                progress = None
            
            # UI更新を強制
            QApplication.processEvents()
            
            print("🔍 音声解析を開始...")
            
            # クリーナーに解析依頼（直接音声データを渡す）
            self.tabbed_audio_control.cleaner_control.set_audio_data_for_analysis(audio, sr)
            
        except Exception as e:
            # エラー時も確実にプログレスダイアログを閉じる
            if progress:
                try:
                    progress.close()
                    progress.deleteLater()
                    progress = None
                except:
                    pass  # ダイアログが既に破棄されている場合は無視
            
            # UI更新を強制
            QApplication.processEvents()
            
            print(f"❌ 解析用音声生成エラー: {e}")
            QMessageBox.critical(self, "エラー", f"解析用音声の生成に失敗しました:\n{str(e)}")
        
        finally:
            # 最終的な確認でプログレスダイアログを閉じる
            if progress:
                try:
                    progress.close()
                    progress.deleteLater()
                    progress = None
                except:
                    pass
            
            # UI更新を強制
            QApplication.processEvents()

    # ---------- 履歴ダイアログ ----------
    def open_model_loader(self):
        dialog = ModelLoaderDialog(self)
        dialog.model_loaded.connect(self.load_model)
        dialog.exec()

    def show_model_history_dialog(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QMessageBox

        if not self.model_manager.get_all_models():
            QMessageBox.information(self, "履歴なし", "モデル履歴がありません。")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("モデル履歴から選択")
        dlg.setModal(True)
        dlg.resize(560, 420)
        dlg.setStyleSheet("QDialog { background:#f8f9fa; }")

        lay = QVBoxLayout(dlg)
        widget = ModelHistoryWidget(self.model_manager, dlg)

        def _on_selected(model_data):
            if not self.model_manager.validate_model_files(model_data):
                QMessageBox.warning(dlg, "エラー", "モデルファイルが見つかりません。")
                return
            paths = {
                'model_path': model_data['model_path'],
                'config_path': model_data['config_path'],
                'style_path': model_data['style_path'],
            }
            dlg.accept()
            self.load_model(paths)

        widget.model_selected.connect(_on_selected)
        lay.addWidget(widget)
        dlg.exec()

    # ---------- モデル読み込み ----------
    def load_model(self, paths):
        """モデルを読み込む（感情デバッグ対応版）"""
        try:
            success = self.tts_engine.load_model(
                paths["model_path"], 
                paths["config_path"], 
                paths["style_path"]
            )
            
            if success:
                # 履歴に追加
                self.model_manager.add_model(
                    paths["model_path"], 
                    paths["config_path"], 
                    paths["style_path"]
                )
                
                # ボタンを有効化
                self.sequential_play_btn.setEnabled(True)
                self.save_individual_btn.setEnabled(True)
                self.save_continuous_btn.setEnabled(True)
                
                # ウィンドウタイトル更新
                model_name = Path(paths["model_path"]).parent.name
                self.setWindowTitle(f"TTSスタジオ - {model_name}")
                
                # 感情情報をコンソールに表示
                print("\n" + "="*50)
                print("🎭 モデル読み込み完了 - 感情情報:")
                print("="*50)
                available_styles = self.tts_engine.get_available_styles()
                print(f"📋 利用可能感情: {available_styles}")
                
                # fear関連の感情をチェック
                fear_emotions = [e for e in available_styles if 'fear' in e.lower()]
                if fear_emotions:
                    print(f"😰 Fear関連感情: {fear_emotions}")
                else:
                    print("⚠️ Fear関連感情が見つかりません")
                
                print("="*50 + "\n")
                
                QMessageBox.information(self, "成功", f"モデルを読み込みました。\n\n🎭 利用可能感情: {len(available_styles)}個")
                
                # 感情UIを更新
                self.update_emotion_ui_after_model_load()
                
            else:
                QMessageBox.critical(self, "エラー", "モデルの読み込みに失敗しました。")
                
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"モデル読み込み中にエラーが発生しました:\n{str(e)}")

    # ---------- TTS / その他（既存） ----------
    def on_text_row_added(self, row_id, row_number):
        self.tabbed_audio_control.add_text_row(row_id, row_number)

    def on_text_row_removed(self, row_id):
        self.tabbed_audio_control.remove_text_row(row_id)

    def on_row_numbers_updated(self, row_mapping):
        self.tabbed_audio_control.update_tab_numbers(row_mapping)

    def on_parameters_changed(self, row_id, parameters):
        """パラメータ変更時の処理（必要に応じて実装）"""
        # 現在は何もしないが、将来的にリアルタイムプレビューなどに使用可能
        pass

    def on_cleaner_settings_changed(self, cleaner_settings):
        """クリーナー設定変更時の処理"""
        # 現在は何もしないが、将来的に設定保存などに使用可能
        pass

    def on_effects_settings_changed(self, effects_settings):
        """エフェクト設定変更時の処理（新規追加）"""
        # サイレント処理 - ログ出力なし
        pass

    def load_last_model(self):
            """前回のモデルを自動読み込み（感情UI更新対応版）"""
            models = self.model_manager.get_all_models()
            if not models:
                return
            last = models[0]  # 先頭が直近
            if not self.model_manager.validate_model_files(last):
                return
            paths = {
                "model_path": last["model_path"],
                "config_path": last["config_path"],
                "style_path": last["style_path"],
            }
            success = self.tts_engine.load_model(
                paths["model_path"], paths["config_path"], paths["style_path"]
            )
            if success:
                self.sequential_play_btn.setEnabled(True)
                self.save_individual_btn.setEnabled(True)
                self.save_continuous_btn.setEnabled(True)
                
                # ウィンドウタイトル更新
                model_name = Path(paths["model_path"]).parent.name
                self.setWindowTitle(f"TTSスタジオ - {model_name}")
                
                # 感情情報をコンソールに表示
                print("\n" + "="*50)
                print("🎭 自動モデル読み込み完了 - 感情情報:")
                print("="*50)
                available_styles = self.tts_engine.get_available_styles()
                print(f"📋 利用可能感情: {available_styles}")
                
                # fear関連の感情をチェック
                fear_emotions = [e for e in available_styles if 'fear' in e.lower()]
                if fear_emotions:
                    print(f"😰 Fear関連感情: {fear_emotions}")
                else:
                    print("⚠️ Fear関連感情が見つかりません")
                
                print("="*50 + "\n")
                
                # 感情UIを更新
                self.update_emotion_ui_after_model_load()
    
    # ================================
    # 音声処理統合メソッド（クリーナー + エフェクト）
    # ================================
    def apply_audio_cleaning(self, audio, sample_rate):
        """音声クリーナーを適用（実装版）"""
        if not self.tabbed_audio_control.is_cleaner_enabled():
            return audio
        
        try:
            # クリーナー設定を取得
            cleaner_settings = self.tabbed_audio_control.get_cleaner_settings()
            
            # 音声処理を適用
            cleaned_audio = self.audio_processor.process_audio(audio, sample_rate, cleaner_settings)
            
            # ログ出力（デバッグ用）
            print(f"🔧 音声クリーナーが適用されました:")
            print(f"  - ハイパスフィルタ: {cleaner_settings.get('highpass_freq')}Hz")
            print(f"  - ハム除去: {'有効' if cleaner_settings.get('hum_removal') else '無効'}")
            print(f"  - ノイズ除去: {'有効' if cleaner_settings.get('noise_reduction') else '無効'}")
            print(f"  - ラウドネス正規化: {'有効' if cleaner_settings.get('loudness_norm') else '無効'}")
            
            return cleaned_audio
            
        except Exception as e:
            print(f"音声クリーナーエラー: {e}")
            return audio  # エラー時は元の音声を返す

    def apply_audio_effects(self, audio, sample_rate):
        """音声エフェクトを適用（新規実装 - AudioEffectsProcessor使用）"""
        if not self.tabbed_audio_control.is_effects_enabled():
            return audio
        
        try:
            # エフェクト設定を取得
            effects_settings = self.tabbed_audio_control.get_effects_settings()
            
            # AudioEffectsProcessorを使用してエフェクト処理
            processed_audio = self.audio_effects_processor.process_effects(
                audio, sample_rate, effects_settings
            )
            
            # 適用されたエフェクトの情報をログ出力
            active_effects = self.audio_effects_processor.get_effects_info(effects_settings)
            if active_effects:
                print(f"🎛️ 音声エフェクトが適用されました: {', '.join(active_effects)}")
            
            return processed_audio
            
        except Exception as e:
            print(f"音声エフェクトエラー: {e}")
            return audio  # エラー時は元の音声を返す

    def play_single_text(self, row_id, text, parameters):
        if not self.tts_engine.is_loaded:
            QMessageBox.warning(self, "エラー", "モデルが読み込まれていません。")
            return
        
        tab_parameters = self.tabbed_audio_control.get_parameters(row_id) or parameters
        try:
            sr, audio = self.tts_engine.synthesize(text, **tab_parameters)
            
            # 音声クリーナー適用
            if self.tabbed_audio_control.is_cleaner_enabled():
                audio = self.apply_audio_cleaning(audio, sr)
            
            # 音声エフェクト適用（新規追加）
            if self.tabbed_audio_control.is_effects_enabled():
                audio = self.apply_audio_effects(audio, sr)
            
            # 最新音声を保存（解析用）
            self.last_generated_audio = audio
            self.last_sample_rate = sr
            
            import sounddevice as sd
            sd.play(audio, sr, blocking=False)
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"音声合成に失敗しました: {str(e)}")

    def trim_silence(self, audio, sample_rate, threshold=0.01):
        """音声の末尾無音部分を削除"""
        import numpy as np
        
        # 音声の絶対値を計算
        abs_audio = np.abs(audio)
        
        # 閾値以上の値がある最後の位置を見つける
        non_silent = np.where(abs_audio > threshold)[0]
        
        if len(non_silent) > 0:
            # 末尾の無音を削除（少し余裕を持たせる）
            end_idx = min(len(audio), non_silent[-1] + int(sample_rate * 0.1))  # 0.1秒の余裕
            return audio[:end_idx]
        else:
            return audio

    def play_sequential(self):
        """連続して再生（1→2→3の順で、各タブのパラメータ使用）"""
        if not self.tts_engine.is_loaded:
            QMessageBox.warning(self, "エラー", "モデルが読み込まれていません。")
            return
        
        # 全テキストを取得
        texts_data = self.multi_text.get_all_texts_and_parameters()
        if not texts_data:
            QMessageBox.information(self, "情報", "再生するテキストがありません。")
            return
        
        try:
            # ボタンを一時無効化
            self.sequential_play_btn.setEnabled(False)
            self.sequential_play_btn.setText("再生中...")
            
            # 全ての音声を合成（各行の個別パラメータ使用）
            all_audio = []
            sample_rate = None
            
            for i, data in enumerate(texts_data, 1):
                text = data['text']
                row_id = data['row_id']
                
                # 対応するタブのパラメータを取得
                tab_parameters = self.tabbed_audio_control.get_parameters(row_id)
                if not tab_parameters:
                    # デフォルトパラメータ
                    tab_parameters = {
                        'style': 'Neutral', 'style_weight': 1.0,
                        'length_scale': 0.85, 'pitch_scale': 1.0,
                        'intonation_scale': 1.0, 'sdp_ratio': 0.25, 'noise': 0.35
                    }
                
                sr, audio = self.tts_engine.synthesize(text, **tab_parameters)
                
                # 音声クリーナー適用
                if self.tabbed_audio_control.is_cleaner_enabled():
                    audio = self.apply_audio_cleaning(audio, sr)
                
                # 音声エフェクト適用（新規追加）
                if self.tabbed_audio_control.is_effects_enabled():
                    audio = self.apply_audio_effects(audio, sr)
                
                if sample_rate is None:
                    sample_rate = sr
                
                all_audio.append(audio)
            
            # 音声を結合（末尾無音削除）
            import numpy as np
            
            combined_audio = []
            for i, audio in enumerate(all_audio):
                # 音声データをfloat32に正規化
                if audio.dtype != np.float32:
                    audio = audio.astype(np.float32)
                
                # 音量を制限（クリッピング防止）
                max_val = np.abs(audio).max()
                if max_val > 0.8:
                    audio = audio * (0.8 / max_val)
                
                # 末尾無音を削除
                audio = self.trim_silence(audio, sample_rate)
                
                combined_audio.append(audio)
            
            final_audio = np.concatenate(combined_audio).astype(np.float32)
            
            # 最終的なクリッピング防止
            max_final = np.abs(final_audio).max()
            if max_final > 0.9:
                final_audio = final_audio * (0.9 / max_final)
            
            # 最新音声を保存（解析用）
            self.last_generated_audio = final_audio
            self.last_sample_rate = sample_rate
            
            # バックグラウンドで再生
            import sounddevice as sd
            sd.play(final_audio, sample_rate, blocking=False)
            
            # ボタンを元に戻す
            self.sequential_play_btn.setEnabled(True)
            self.sequential_play_btn.setText("連続して再生(Ctrl + R)")
            
        except Exception as e:
            self.sequential_play_btn.setEnabled(True)
            self.sequential_play_btn.setText("連続して再生(Ctrl + R)")
            QMessageBox.critical(self, "エラー", f"連続再生に失敗しました: {str(e)}")
    
    def save_individual(self):
        """個別保存（フォルダ内に個別ファイル）"""
        if not self.tts_engine.is_loaded:
            QMessageBox.warning(self, "エラー", "モデルが読み込まれていません。")
            return
        
        texts_data = self.multi_text.get_all_texts_and_parameters()
        if not texts_data:
            QMessageBox.information(self, "情報", "保存するテキストがありません。")
            return
        
        try:
            import soundfile as sf
            
            # フォルダ選択
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "個別保存フォルダを選択"
            )
            
            if folder_path:
                # 保存ボタンを一時無効化
                self.save_individual_btn.setEnabled(False)
                self.save_individual_btn.setText("保存中...")
                
                # 各行を個別に保存
                for i, data in enumerate(texts_data, 1):
                    text = data['text']
                    row_id = data['row_id']
                    
                    # 対応するタブのパラメータを取得
                    tab_parameters = self.tabbed_audio_control.get_parameters(row_id)
                    if not tab_parameters:
                        tab_parameters = {
                            'style': 'Neutral', 'style_weight': 1.0,
                            'length_scale': 0.85, 'pitch_scale': 1.0,
                            'intonation_scale': 1.0, 'sdp_ratio': 0.25, 'noise': 0.35
                        }
                    
                    sr, audio = self.tts_engine.synthesize(text, **tab_parameters)
                    
                    # 音声クリーナー適用
                    if self.tabbed_audio_control.is_cleaner_enabled():
                        audio = self.apply_audio_cleaning(audio, sr)
                    
                    # 音声エフェクト適用（新規追加）
                    if self.tabbed_audio_control.is_effects_enabled():
                        audio = self.apply_audio_effects(audio, sr)
                    
                    # ファイル名生成
                    safe_text = "".join(c for c in text[:20] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    if not safe_text:
                        safe_text = f"text_{i}"
                    
                    # 処理適用状況をファイル名に反映
                    suffix_parts = []
                    if self.tabbed_audio_control.is_cleaner_enabled():
                        suffix_parts.append("cleaned")
                    if self.tabbed_audio_control.is_effects_enabled():
                        suffix_parts.append("effects")
                    
                    suffix = "_" + "_".join(suffix_parts) if suffix_parts else ""
                    filename = f"{i:02d}_{safe_text}{suffix}.wav"
                    file_path = os.path.join(folder_path, filename)
                    
                    sf.write(file_path, audio, sr)
                
                # ボタンを元に戻す
                self.save_individual_btn.setEnabled(True)
                self.save_individual_btn.setText("個別保存(Ctrl + S)")
                
                # 適用された処理の情報
                processing_info = []
                if self.tabbed_audio_control.is_cleaner_enabled():
                    processing_info.append("🔧 音声クリーナー")
                if self.tabbed_audio_control.is_effects_enabled():
                    processing_info.append("🎛️ 音声エフェクト")
                
                info_text = "\n適用された処理: " + ", ".join(processing_info) if processing_info else ""
                QMessageBox.information(self, "完了", f"個別ファイルを保存しました。\n保存先: {folder_path}{info_text}")
                
        except Exception as e:
            self.save_individual_btn.setEnabled(True)
            self.save_individual_btn.setText("個別保存(Ctrl + S)")
            QMessageBox.critical(self, "エラー", f"個別保存に失敗しました: {str(e)}")
    
    def save_continuous(self):
        """連続保存（1つのWAVファイルに統合）"""
        if not self.tts_engine.is_loaded:
            QMessageBox.warning(self, "エラー", "モデルが読み込まれていません。")
            return
        
        texts_data = self.multi_text.get_all_texts_and_parameters()
        if not texts_data:
            QMessageBox.information(self, "情報", "保存するテキストがありません。")
            return
        
        try:
            import soundfile as sf
            import numpy as np
            
            # ファイル保存先選択
            suffix_parts = []
            if self.tabbed_audio_control.is_cleaner_enabled():
                suffix_parts.append("cleaned")
            if self.tabbed_audio_control.is_effects_enabled():
                suffix_parts.append("effects")
            
            suffix = "_" + "_".join(suffix_parts) if suffix_parts else ""
            default_filename = f"continuous_output{suffix}.wav"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "連続音声ファイルを保存",
                default_filename,
                "WAV files (*.wav);;All files (*.*)"
            )
            
            if file_path:
                # 保存ボタンを一時無効化
                self.save_continuous_btn.setEnabled(False)
                self.save_continuous_btn.setText("保存中...")
                
                # 全ての音声を合成
                all_audio = []
                sample_rate = None
                
                for i, data in enumerate(texts_data, 1):
                    text = data['text']
                    row_id = data['row_id']
                    
                    # 対応するタブのパラメータを取得
                    tab_parameters = self.tabbed_audio_control.get_parameters(row_id)
                    if not tab_parameters:
                        tab_parameters = {
                            'style': 'Neutral', 'style_weight': 1.0,
                            'length_scale': 0.85, 'pitch_scale': 1.0,
                            'intonation_scale': 1.0, 'sdp_ratio': 0.25, 'noise': 0.35
                        }
                    
                    sr, audio = self.tts_engine.synthesize(text, **tab_parameters)
                    
                    # 音声クリーナー適用
                    if self.tabbed_audio_control.is_cleaner_enabled():
                        audio = self.apply_audio_cleaning(audio, sr)
                    
                    # 音声エフェクト適用（新規追加）
                    if self.tabbed_audio_control.is_effects_enabled():
                        audio = self.apply_audio_effects(audio, sr)
                    
                    if sample_rate is None:
                        sample_rate = sr
                    
                    all_audio.append(audio)
                
                # 音声を結合（末尾無音削除）
                combined_audio = []
                for i, audio in enumerate(all_audio):
                    # 音声データをfloat32に正規化
                    if audio.dtype != np.float32:
                        audio = audio.astype(np.float32)
                    
                    # 音量を制限（クリッピング防止）
                    max_val = np.abs(audio).max()
                    if max_val > 0.8:
                        audio = audio * (0.8 / max_val)
                    
                    # 末尾無音を削除
                    audio = self.trim_silence(audio, sample_rate)
                    
                    combined_audio.append(audio)
                
                final_audio = np.concatenate(combined_audio).astype(np.float32)
                
                # 最終的なクリッピング防止
                max_final = np.abs(final_audio).max()
                if max_final > 0.9:
                    final_audio = final_audio * (0.9 / max_final)
                
                # 最新音声を保存（解析用）
                self.last_generated_audio = final_audio
                self.last_sample_rate = sample_rate
                
                # ファイル保存
                sf.write(file_path, final_audio, sample_rate)
                
                # ボタンを元に戻す
                self.save_continuous_btn.setEnabled(True)
                self.save_continuous_btn.setText("連続保存(Ctrl + Shift + S)")
                
                # 適用された処理の情報
                processing_info = []
                if self.tabbed_audio_control.is_cleaner_enabled():
                    processing_info.append("🔧 音声クリーナー")
                if self.tabbed_audio_control.is_effects_enabled():
                    processing_info.append("🎛️ 音声エフェクト")
                
                info_text = "\n適用された処理: " + ", ".join(processing_info) if processing_info else ""
                QMessageBox.information(self, "完了", f"連続音声ファイルを保存しました。\n保存先: {file_path}{info_text}")
                
        except Exception as e:
            self.save_continuous_btn.setEnabled(True)
            self.save_continuous_btn.setText("連続保存(Ctrl + Shift + S)")
            QMessageBox.critical(self, "エラー", f"連続保存に失敗しました: {str(e)}")
    
    # モデル読み込み時の感情UI更新
    def update_emotion_ui_after_model_load(self):
        """モデル読み込み後に感情UIを更新（簡素化版）"""
        if not self.tts_engine.is_loaded:
            return
        
        try:
            # 利用可能な感情を取得
            available_styles = self.tts_engine.get_available_styles()
            print(f"📄 感情UI更新開始: {available_styles}")
            
            # タブ式感情コントロールを更新
            emotion_control = self.tabbed_audio_control.emotion_control
            emotion_control.update_emotion_list(available_styles)
            
            print(f"✅ 感情UI更新完了")
            
        except Exception as e:
            print(f"❌ 感情UI更新エラー: {e}")
            import traceback
            traceback.print_exc()
    
    # アプリケーション終了時の処理
    def closeEvent(self, event):
        """アプリケーション終了時の処理（改良版）"""
        try:
            print("📄 アプリケーション終了処理開始...")
            
            # 解析スレッドが実行中の場合は強制終了
            cleaner_control = self.tabbed_audio_control.cleaner_control
            if hasattr(cleaner_control, 'analysis_thread') and cleaner_control.analysis_thread:
                if cleaner_control.analysis_thread.isRunning():
                    print("⚠️ 解析スレッドを強制終了中...")
                    cleaner_control.analysis_thread.stop()  # 停止フラグ設定
                    cleaner_control.analysis_thread.quit()  # スレッド終了要求
                    
                    # 少し待つ
                    if not cleaner_control.analysis_thread.wait(3000):  # 3秒待機
                        print("⚠️ 解析スレッドを強制終了...")
                        cleaner_control.analysis_thread.terminate()  # 強制終了
                        cleaner_control.analysis_thread.wait(1000)  # 1秒待機
            
            # モデルをアンロード
            if self.tts_engine:
                print("🤖 TTSエンジンをアンロード中...")
                self.tts_engine.unload_model()
                
            # 設定保存
            print("💾 設定保存中...")
            self.model_manager.save_history(quiet=True)
            
            print("✅ 終了処理完了")
            
        except Exception as e:
            print(f"❌ 終了処理中にエラー: {e}")
        
        event.accept()