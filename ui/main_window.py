# ui/main_window.py (エフェクトプロセッサー統合版 + 画像機能追加)
import os
import numpy as np
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QFileDialog, QStyle, QFrame, QApplication, QMessageBox, QScrollArea)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QAction, QPixmap

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
from core.audio_effects_processor import AudioEffectsProcessor  # 新規追加


class TTSStudioMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tts_engine = TTSEngine()
        self.model_manager = ModelManager()
        
        # 音声処理関連を追加
        self.audio_processor = AudioProcessor()
        self.audio_analyzer = AudioAnalyzer()
        self.audio_effects_processor = AudioEffectsProcessor()  # 新規追加
        self.last_generated_audio = None  # 解析用に最新の音声を保存
        self.last_sample_rate = None
        
        # 画像管理関連（新規追加）
        self.current_image_path = None  # 現在読み込まれている画像パス
        self.image_history = []  # 画像履歴（将来の実装用）
        
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

        content = QHBoxLayout()

        # 左ペイン
        left = QVBoxLayout()
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

        left.addWidget(self.multi_text, 2)
        left.addWidget(divider)
        left.addWidget(self.tabbed_audio_control, 1)
        left.addLayout(controls)

        # 右ペイン（キャラクター表示エリアに変更）
        self.character_display_widget = self.create_character_display_widget()

        content.addLayout(left, 1)
        content.addWidget(self.character_display_widget, 0)
        main.addLayout(content)

    def create_character_display_widget(self):
        """キャラクター表示ウィジェット作成（ズーム機能付き）"""
        widget = QWidget()
        widget.setMaximumWidth(300)
        widget.setMinimumWidth(250)
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
        
        # ヘッダーラベル
        header_label = QLabel("キャラクター表示")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setFont(QFont("", 12, QFont.Weight.Bold))
        header_label.setStyleSheet("color: #333; border: none; padding: 5px;")
        
        # ズームコントロール
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(4)
        
        # ズームアウトボタン
        self.zoom_out_btn = QPushButton("➖")
        self.zoom_out_btn.setFixedSize(24, 24)
        self.zoom_out_btn.setToolTip("縮小")
        self.zoom_out_btn.setEnabled(False)
        
        # ズーム率表示
        self.zoom_label = QLabel("フィット")
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setMinimumWidth(60)
        self.zoom_label.setStyleSheet("color: #666; font-size: 10px; border: none;")
        
        # ズームインボタン
        self.zoom_in_btn = QPushButton("➕")
        self.zoom_in_btn.setFixedSize(24, 24)
        self.zoom_in_btn.setToolTip("拡大")
        self.zoom_in_btn.setEnabled(False)
        
        # フィットボタン
        self.zoom_fit_btn = QPushButton("📐")
        self.zoom_fit_btn.setFixedSize(24, 24)
        self.zoom_fit_btn.setToolTip("枠内にフィット")
        self.zoom_fit_btn.setEnabled(False)
        
        zoom_btn_style = """
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 10px;
            }
            QPushButton:hover:enabled {
                background-color: #e2e6ea;
                border-color: #adb5bd;
            }
            QPushButton:disabled {
                color: #999;
                background-color: #f5f5f5;
            }
        """
        
        self.zoom_out_btn.setStyleSheet(zoom_btn_style)
        self.zoom_in_btn.setStyleSheet(zoom_btn_style)
        self.zoom_fit_btn.setStyleSheet(zoom_btn_style)
        
        # シグナル接続
        self.zoom_out_btn.clicked.connect(self.zoom_out_image)
        self.zoom_in_btn.clicked.connect(self.zoom_in_image)
        self.zoom_fit_btn.clicked.connect(self.zoom_fit_image)
        
        zoom_layout.addWidget(self.zoom_out_btn)
        zoom_layout.addWidget(self.zoom_label, 1)
        zoom_layout.addWidget(self.zoom_in_btn)
        zoom_layout.addWidget(self.zoom_fit_btn)
        
        # 画像表示エリア（スクロール対応）
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)  # 手動サイズ管理
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
        """)
        
        # 画像表示ラベル
        self.character_image_label = QLabel()
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
        
        self.scroll_area.setWidget(self.character_image_label)
        
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
        layout.addWidget(header_label)
        layout.addLayout(zoom_layout)
        layout.addWidget(self.scroll_area, 1)  # 伸縮
        layout.addWidget(self.image_info_label)
        layout.addLayout(button_layout)
        
        # ズーム関連の変数
        self.original_pixmap = None  # 元画像
        self.current_zoom_level = 0  # 0: フィット, 1-8: 固定サイズ
        self.zoom_levels = [25, 50, 75, 100, 150, 200, 300, 400]  # パーセント
        self.is_fit_mode = True  # フィットモードかどうか
        
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

    # ================================
    # 画像関連の新機能
    # ================================
    def load_character_image(self):
        """立ち絵画像を読み込む（ズーム機能対応版）"""
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
                
                # フィットモードで表示
                self.is_fit_mode = True
                self.current_zoom_level = 0
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
                    f"📏 {image_size.width()} × {image_size.height()}px\n"
                    f"💾 {file_info.stat().st_size // 1024} KB"
                )
                
                # 現在の画像パスを保存
                self.current_image_path = file_path
                
                # ボタンを有効化
                self.image_clear_btn.setEnabled(True)
                self.zoom_in_btn.setEnabled(True)
                self.zoom_out_btn.setEnabled(True)
                self.zoom_fit_btn.setEnabled(True)
                
                # ズーム表示更新
                self.update_zoom_label()
                
                # 将来の履歴機能用
                self.add_image_to_history(file_path)
                
                print(f"✅ 立ち絵画像読み込み完了: {file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"画像読み込み中にエラーが発生しました:\n{str(e)}")
            print(f"❌ 画像読み込みエラー: {e}")

    def clear_character_image(self):
        """キャラクター画像をクリア（ズーム機能対応版）"""
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
        self.current_zoom_level = 0
        self.is_fit_mode = True
        
        # 情報をクリア
        self.image_info_label.setText("")
        self.current_image_path = None
        
        # ボタンを無効化
        self.image_clear_btn.setEnabled(False)
        self.zoom_in_btn.setEnabled(False)
        self.zoom_out_btn.setEnabled(False)
        self.zoom_fit_btn.setEnabled(False)
        
        # ズーム表示をリセット
        self.zoom_label.setText("フィット")
        
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

    # ================================
    # ズーム機能の実装
    # ================================
    def update_image_display(self):
        """現在のズームレベルに基づいて画像を更新"""
        if not self.original_pixmap:
            return
        
        if self.is_fit_mode:
            # フィットモード：枠内に収まるようにリサイズ
            container_size = self.scroll_area.size()
            max_width = max(container_size.width() - 20, 200)
            max_height = max(container_size.height() - 20, 200)
            
            scaled_pixmap = self.original_pixmap.scaled(
                max_width, max_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        else:
            # 固定ズームモード：指定倍率で表示
            zoom_percent = self.zoom_levels[self.current_zoom_level]
            original_size = self.original_pixmap.size()
            new_width = int(original_size.width() * zoom_percent / 100)
            new_height = int(original_size.height() * zoom_percent / 100)
            
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
    
    def zoom_in_image(self):
        """画像をズームイン"""
        if not self.original_pixmap:
            return
        
        if self.is_fit_mode:
            # フィットモードから100%に変更
            self.is_fit_mode = False
            self.current_zoom_level = 3  # 100%
        else:
            # 次の拡大レベルに
            if self.current_zoom_level < len(self.zoom_levels) - 1:
                self.current_zoom_level += 1
        
        self.update_image_display()
        self.update_zoom_label()
        print(f"🔍 ズームイン: {self.get_current_zoom_text()}")
    
    def zoom_out_image(self):
        """画像をズームアウト"""
        if not self.original_pixmap:
            return
        
        if self.is_fit_mode:
            # フィットモードの場合は何もしない
            return
        else:
            # 前の縮小レベルに
            if self.current_zoom_level > 0:
                self.current_zoom_level -= 1
            else:
                # 最小レベルに達したらフィットモードに
                self.is_fit_mode = True
        
        self.update_image_display()
        self.update_zoom_label()
        print(f"🔍 ズームアウト: {self.get_current_zoom_text()}")
    
    def zoom_fit_image(self):
        """画像をフィット表示"""
        if not self.original_pixmap:
            return
        
        self.is_fit_mode = True
        self.current_zoom_level = 0
        
        self.update_image_display()
        self.update_zoom_label()
        print(f"📐 フィット表示")
    
    def update_zoom_label(self):
        """ズーム表示ラベルを更新"""
        if self.is_fit_mode:
            self.zoom_label.setText("フィット")
        else:
            zoom_percent = self.zoom_levels[self.current_zoom_level]
            self.zoom_label.setText(f"{zoom_percent}%")
    
    def get_current_zoom_text(self):
        """現在のズーム状態をテキストで取得"""
        if self.is_fit_mode:
            return "フィット"
        else:
            zoom_percent = self.zoom_levels[self.current_zoom_level]
            return f"{zoom_percent}%"
    
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

    # ---------- TTS / そのほか（既存） ----------
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
            print(f"🔄 感情UI更新開始: {available_styles}")
            
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
            print("🔄 アプリケーション終了処理開始...")
            
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