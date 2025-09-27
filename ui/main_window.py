import os
import numpy as np
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QFileDialog, QFrame, QApplication, QMessageBox, QSplitter)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QAction

# 自作モジュール
from .model_history import ModelHistoryWidget
from .model_loader import ModelLoaderDialog
from .tabbed_audio_control import TabbedAudioControl
from .multi_text import MultiTextWidget
from .keyboard_shortcuts import KeyboardShortcutManager
from .sliding_menu import SlidingMenuWidget
from .help_dialog import HelpDialog
from .character_display import CharacterDisplayWidget
from .tts_worker import TTSWorker
from core.tts_engine import TTSEngine
from core.model_manager import ModelManager
from core.audio_processor import AudioProcessor
from core.audio_analyzer import AudioAnalyzer
from core.audio_effects_processor import AudioEffectsProcessor
from core.lip_sync_engine import LipSyncEngine

class TTSStudioMainWindow(QMainWindow):
    tts_synthesis_requested = pyqtSignal(str, dict, bool)
    def __init__(self, live2d_url=None, live2d_server_manager=None):
        super().__init__()
        self.live2d_url = live2d_url
        self.live2d_server_manager = live2d_server_manager
        self.tts_engine = TTSEngine()
        self.model_manager = ModelManager()
        self.audio_processor = AudioProcessor()
        self.audio_analyzer = AudioAnalyzer()
        self.audio_effects_processor = AudioEffectsProcessor()
        
        # リップシンクエンジン追加
        self.lip_sync_engine = LipSyncEngine()
        self.setup_tts_worker()
        
        self.last_generated_audio = None
        self.last_sample_rate = None
        self._tts_busy = False
        
        self.init_ui()
        self.help_dialog = HelpDialog(self)
        self.setup_audio_processing_integration()
        
        # リップシンク統合設定
        self.setup_lipsync_integration()
        
        self.sliding_menu = SlidingMenuWidget(self)
        self.sliding_menu.load_model_clicked.connect(self.open_model_loader)
        self.sliding_menu.load_from_history_clicked.connect(self.show_model_history_dialog)
        self.sliding_menu.load_image_clicked.connect(self.character_display.load_character_image)
        self.sliding_menu.load_image_from_history_clicked.connect(self.character_display.show_image_history_dialog)
        self.sliding_menu.load_live2d_clicked.connect(self.character_display.load_live2d_model)
        self.sliding_menu.load_live2d_from_history_clicked.connect(self.character_display.show_live2d_history_dialog)
        self.character_display.live2d_model_loaded.connect(self.on_live2d_model_loaded)
        self.keyboard_shortcuts = KeyboardShortcutManager(self)
        self.load_last_model()

    def init_ui(self):
        self.setWindowTitle("TTSスタジオ - ほのか")
        self.setGeometry(100, 100, 1200, 800)
        self.create_menu_bar()
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setSpacing(10)
        main.setContentsMargins(15, 15, 15, 15)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setStyleSheet("""
            QSplitter::handle { background-color: #dee2e6; width: 3px; }
            QSplitter::handle:hover { background-color: #adb5bd; }
        """)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # テキスト入力とタブエリアの間に縦方向スプリッターを追加
        self.vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.vertical_splitter.setStyleSheet("""
            QSplitter::handle { background-color: #dee2e6; height: 3px; }
            QSplitter::handle:hover { background-color: #adb5bd; }
        """)
        
        self.multi_text = MultiTextWidget()
        self.multi_text.play_single_requested.connect(self.play_single_text)
        self.multi_text.row_added.connect(self.on_text_row_added)
        self.multi_text.row_removed.connect(self.on_text_row_removed)
        self.multi_text.row_numbers_updated.connect(self.on_row_numbers_updated)
        
        # 🔧 修正：統合されたタブコントロール（リップシンク統合済み）
        self.tabbed_audio_control = TabbedAudioControl()
        self.tabbed_audio_control.parameters_changed.connect(self.on_parameters_changed)
        self.tabbed_audio_control.cleaner_settings_changed.connect(self.on_cleaner_settings_changed)
        self.tabbed_audio_control.effects_settings_changed.connect(self.on_effects_settings_changed)
        # 🔧 修正：統合されたリップシンク設定変更ハンドラー
        self.tabbed_audio_control.lip_sync_settings_changed.connect(self.on_lipsync_settings_changed)
        self.tabbed_audio_control.add_text_row("initial", 1)

        self.vertical_splitter.addWidget(self.multi_text)
        self.vertical_splitter.addWidget(self.tabbed_audio_control)

        self.multi_text.setMaximumHeight(360)
        self.vertical_splitter.setSizes([360, 340])
        self.multi_text.setMinimumHeight(40)
        self.tabbed_audio_control.setMinimumHeight(250)

        # 折りたたみ設定（上側のみ折りたたみ可能）
        self.vertical_splitter.setCollapsible(0, True)
        self.vertical_splitter.setCollapsible(1, False)
        
        controls = QHBoxLayout()
        controls.addStretch()
        self.sequential_play_btn = QPushButton("連続して再生(Ctrl + R)")
        self.sequential_play_btn.setStyleSheet(self._blue_btn_css())
        self.save_individual_btn = QPushButton("個別保存(Ctrl + S)")
        self.save_individual_btn.setStyleSheet(self._green_btn_css())
        self.save_continuous_btn = QPushButton("連続保存(Ctrl + Shift + S)")
        self.save_continuous_btn.setStyleSheet(self._orange_btn_css())
        
        # リップシンクテストボタン追加
        self.test_lipsync_btn = QPushButton("🎭 リップシンクテスト")
        self.test_lipsync_btn.setStyleSheet("""
            QPushButton { background-color: #6f42c1; color: white; border: none; border-radius: 4px; font-size: 13px; font-weight: bold; padding: 6px 16px; }
            QPushButton:hover:enabled { background-color: #5a359b; }
            QPushButton:pressed:enabled { background-color: #4e2a87; }
            QPushButton:disabled { background-color: #f0f0f0; color: #aaaaaa; }
        """)
        
        for btn in [self.sequential_play_btn, self.save_individual_btn, self.save_continuous_btn, self.test_lipsync_btn]:
            btn.setMinimumHeight(35)
            btn.setEnabled(False)
            controls.addWidget(btn)
            
        self.sequential_play_btn.clicked.connect(self.play_sequential)
        self.save_individual_btn.clicked.connect(self.save_individual)
        self.save_continuous_btn.clicked.connect(self.save_continuous)
        self.test_lipsync_btn.clicked.connect(self.test_lipsync_function)
        
        # 左側レイアウト組み立て
        left_layout.addWidget(self.vertical_splitter, 1)
        left_layout.addLayout(controls)
        
        self.character_display = CharacterDisplayWidget(
            live2d_url=self.live2d_url,
            live2d_server_manager=self.live2d_server_manager,
            parent=self
        )
        self.main_splitter.addWidget(left_widget)
        self.main_splitter.addWidget(self.character_display)
        self.main_splitter.setSizes([700, 300])
        left_widget.setMinimumWidth(500)
        self.character_display.setMinimumWidth(200)
        self.main_splitter.splitterMoved.connect(self.on_splitter_moved)
        main.addWidget(self.main_splitter)

    def _blue_btn_css(self) -> str:
        return """
            QPushButton { background-color: #1976d2; color: white; border: none; border-radius: 4px; font-size: 13px; font-weight: bold; padding: 6px 16px; }
            QPushButton:hover:enabled { background-color: #1565c0; }
            QPushButton:pressed:enabled { background-color: #0d47a1; }
            QPushButton:disabled { background-color: #f0f0f0; color: #aaaaaa; }
        """
    def _green_btn_css(self) -> str:
        return """
            QPushButton { background-color: #4caf50; color: white; border: none; border-radius: 4px; font-size: 13px; font-weight: bold; padding: 6px 16px; }
            QPushButton:hover:enabled { background-color: #388e3c; }
            QPushButton:pressed:enabled { background-color: #2e7d32; }
            QPushButton:disabled { background-color: #f0f0f0; color: #aaaaaa; }
        """
    def _orange_btn_css(self) -> str:
        return """
            QPushButton { background-color: #ff9800; color: white; border: none; border-radius: 4px; font-size: 13px; font-weight: bold; padding: 6px 16px; }
            QPushButton:hover:enabled { background-color: #f57c00; }
            QPushButton:pressed:enabled { background-color: #e65100; }
            QPushButton:disabled { background-color: #f0f0f0; color: #aaaaaa; }
        """

    def setup_lipsync_integration(self):
        """リップシンク機能の統合設定"""
        try:
            print("🎭 リップシンク機能統合中...")
            
            # リップシンクエンジンが利用可能かチェック
            if self.lip_sync_engine.is_available():
                print("✅ リップシンクエンジン利用可能")
            else:
                print("⚠️ リップシンクエンジン制限モード（pyopenjtalk不使用）")
                
        except Exception as e:
            print(f"❌ リップシンク統合エラー: {e}")

    def setup_tts_worker(self):
        """TTS合成をバックグラウンドで実行するワーカースレッドの初期化"""
        self.tts_thread = QThread(self)
        self.tts_worker = TTSWorker(self.tts_engine, self.lip_sync_engine)
        self.tts_worker.moveToThread(self.tts_thread)
        self.tts_worker.synthesis_finished.connect(self.on_tts_synthesis_finished)
        self.tts_synthesis_requested.connect(self.tts_worker.synthesize)
        self.tts_thread.finished.connect(self.tts_worker.deleteLater)
        self.tts_thread.start()

    def test_lipsync_function(self):
        """リップシンク機能をテスト（修正版：位置リセット問題解決）"""
        try:
            print("🎭 リップシンクテスト開始")
            
            # Live2Dモデルが読み込まれているかチェック
            if not hasattr(self.character_display, 'live2d_webview') or not self.character_display.live2d_webview.is_model_loaded:
                QMessageBox.warning(self, "リップシンクテスト", 
                    "Live2Dモデルが読み込まれていません。\n"
                    "先にLive2Dモデルを読み込んでからテストしてください。")
                return
            
            # テキストを取得（最初の行、または固定テスト文）
            texts_data = self.multi_text.get_all_texts_and_parameters()
            if texts_data and texts_data[0]['text'].strip():
                test_text = texts_data[0]['text']
            else:
                test_text = "あいうえおかきくけこさしすせそ。リップシンクのテストをしています。"
                
            print(f"🎵 テストテキスト: '{test_text[:30]}...'")
            
            # リップシンクデータを生成
            self.test_lipsync_btn.setEnabled(False)
            self.test_lipsync_btn.setText("解析中...")
            QApplication.processEvents()
            
            lipsync_data = self.lip_sync_engine.analyze_text_for_lipsync(test_text)
            
            if lipsync_data:
                print(f"✅ リップシンクデータ生成成功: {len(lipsync_data.vowel_frames)}フレーム")
                
                # JavaScriptに送信するデータを準備
                js_data = {
                    'text': lipsync_data.text,
                    'total_duration': lipsync_data.total_duration,
                    'vowel_frames': [
                        {
                            'timestamp': frame.timestamp,
                            'vowel': frame.vowel,
                            'intensity': frame.intensity,
                            'duration': frame.duration
                        }
                        for frame in lipsync_data.vowel_frames
                    ]
                }
                
                # Live2DのWebViewにリップシンクデータを送信
                webview = self.character_display.live2d_webview
                
                # 修正：設定同期は1回のみ、リップシンク前に実行
                if hasattr(self.character_display, 'sync_current_live2d_settings_to_webview'):
                    self.character_display.sync_current_live2d_settings_to_webview()
                
                script = f"""
                if (typeof window.startLipSync === 'function') {{
                    const lipSyncData = {js_data};
                    const result = window.startLipSync(lipSyncData);
                    console.log('リップシンクテスト結果:', result);
                    result;
                }} else {{
                    console.error('startLipSync関数が見つかりません');
                    false;
                }}
                """
                
                webview.page().runJavaScript(script, self.on_lipsync_test_result)

                # 修正：重複する設定同期を削除
                # QTimer.singleShot(0, ...)の部分を削除
                
                # タイマーで停止
                QTimer.singleShot(int(lipsync_data.total_duration * 1000) + 1000, self.stop_lipsync_test)
                
            else:
                print("❌ リップシンクデータ生成失敗")
                QMessageBox.warning(self, "リップシンクテスト", "リップシンクデータの生成に失敗しました。")
                self.test_lipsync_btn.setEnabled(True)
                self.test_lipsync_btn.setText("🎭 リップシンクテスト")
                
        except Exception as e:
            print(f"❌ リップシンクテストエラー: {e}")
            QMessageBox.critical(self, "エラー", f"リップシンクテストでエラーが発生しました:\n{str(e)}")
            self.test_lipsync_btn.setEnabled(True)
            self.test_lipsync_btn.setText("🎭 リップシンクテスト")

    def on_lipsync_test_result(self, result):
        """リップシンクテスト結果を処理"""
        if result:
            print("✅ リップシンクテスト開始成功")
            self.test_lipsync_btn.setText("テスト実行中...")
        else:
            print("❌ リップシンクテスト開始失敗")
            QMessageBox.warning(self, "リップシンクテスト", "リップシンクテストの開始に失敗しました。")
            self.test_lipsync_btn.setEnabled(True)
            self.test_lipsync_btn.setText("🎭 リップシンクテスト")

    def stop_lipsync_test(self):
        """リップシンクテストを停止"""
        try:
            webview = self.character_display.live2d_webview
            script = """
            if (typeof window.stopLipSync === 'function') {
                window.stopLipSync();
            }
            """
            webview.page().runJavaScript(script)
            
            self.test_lipsync_btn.setEnabled(True)
            self.test_lipsync_btn.setText("🎭 リップシンクテスト")
            print("✅ リップシンクテスト完了")
            
        except Exception as e:
            print(f"⚠️ リップシンクテスト停止エラー: {e}")

    def on_lipsync_settings_changed(self, settings):
        """リップシンク設定変更時の処理"""
        try:
            print(f"🔧 リップシンク設定変更: {settings}")
            
            # リップシンクエンジンに設定を適用
            if self.lip_sync_engine:
                self.lip_sync_engine.update_settings(settings)
            
            # Live2D側にも設定を送信
            if hasattr(self.character_display, 'live2d_webview') and self.character_display.live2d_webview.is_model_loaded:
                webview = self.character_display.live2d_webview
                script = f"""
                if (typeof window.updateLipSyncSettings === 'function') {{
                    window.updateLipSyncSettings({settings});
                }}
                """
                webview.page().runJavaScript(script)
                
        except Exception as e:
            print(f"❌ リップシンク設定変更エラー: {e}")

    def create_menu_bar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar { background-color: #f8f9fa; color: #333; border-bottom: 1px solid #dee2e6; padding: 4px; }
            QMenuBar::item { background-color: transparent; padding: 6px 12px; margin: 0px 2px; border-radius: 4px; }
            QMenuBar::item:selected { background-color: #e9ecef; }
            QMenuBar::item:pressed { background-color: #dee2e6; }
        """)
        menubar.addAction("ファイル(F)").triggered.connect(self.toggle_file_menu)
        menubar.addAction("説明(H)").triggered.connect(self.show_help_dialog)
        
    def show_help_dialog(self):
        self.help_dialog.show()
        self.help_dialog.raise_()
        self.help_dialog.activateWindow()
        
    def toggle_file_menu(self):
        self.sliding_menu.toggle_menu()
        
    def mousePressEvent(self, event):
        if self.sliding_menu.is_visible and not self.sliding_menu.geometry().contains(event.pos()):
            self.sliding_menu.hide_menu()
        super().mousePressEvent(event)
        
    def on_splitter_moved(self, pos, index):
        if hasattr(self, 'main_splitter'):
            sizes = self.main_splitter.sizes()
            total_width = sum(sizes)
            max_right_width = total_width * 0.3
            min_left_width = total_width * 0.7
            if len(sizes) >= 2:
                left_width, right_width = sizes[0], sizes[1]
                if right_width > max_right_width:
                    new_right_width = int(max_right_width)
                    new_left_width = total_width - new_right_width
                    self.main_splitter.setSizes([new_left_width, new_right_width])
                elif left_width < min_left_width:
                    new_left_width = int(min_left_width)
                    new_right_width = total_width - new_left_width
                    self.main_splitter.setSizes([new_left_width, new_right_width])
                    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        
    def on_live2d_model_loaded(self, model_path):
        model_name = Path(model_path).name
        print(f"Live2Dモデルが読み込まれました: {model_name}")
        current_title = self.windowTitle()
        if " - " in current_title:
            base_title = current_title.split(" - ")[0]
        else:
            base_title = current_title
        self.setWindowTitle(f"{base_title} - {model_name} (Live2D)")

    def setup_audio_processing_integration(self):
        self.tabbed_audio_control.cleaner_control.analyze_requested.connect(self.handle_cleaner_analysis_request)
        
    def handle_cleaner_analysis_request(self):
        if not self.tts_engine.is_loaded:
            QMessageBox.warning(self, "エラー", "モデルが読み込まれていません。\n先にモデルを読み込んでから解析してください。")
            return
        self.generate_test_audio_for_analysis()
        
    def generate_test_audio_for_analysis(self):
        texts_data = self.multi_text.get_all_texts_and_parameters()
        if texts_data and texts_data[0]['text'].strip():
            first_data = texts_data[0]
            test_text = first_data['text']
            row_id = first_data['row_id']
            test_params = self.tabbed_audio_control.get_parameters(row_id) or first_data['parameters']
        else:
            test_text = "これは音声解析用のサンプルテキストです。ほのかちゃんの声で品質をチェックします。"
            test_params = { 'style': 'Neutral', 'style_weight': 1.0, 'length_scale': 0.85, 'pitch_scale': 1.0, 'intonation_scale': 1.0, 'sdp_ratio': 0.25, 'noise': 0.35 }
            print("⚠️ テキストが未入力のため、サンプルテキストを使用")
        progress = None
        try:
            progress = QMessageBox(self)
            progress.setWindowTitle("音声生成中")
            progress.setText(f"解析用の音声を生成しています...\n\nテキスト: {test_text[:50]}...")
            progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress.setWindowModality(Qt.WindowModality.ApplicationModal)
            progress.show()
            QApplication.processEvents()
            sr, audio = self.tts_engine.synthesize(test_text, **test_params)
            self.last_generated_audio = audio
            self.last_sample_rate = sr
            if progress: progress.close()
            QApplication.processEvents()
            self.tabbed_audio_control.cleaner_control.set_audio_data_for_analysis(audio, sr)
        except Exception as e:
            if progress: progress.close()
            QApplication.processEvents()
            QMessageBox.critical(self, "エラー", f"解析用音声の生成に失敗しました:\n{str(e)}")
        finally:
            if progress: progress.deleteLater()

    def send_lipsync_to_live2d(self, lipsync_data):
        """Live2Dにリップシンクデータを送信（修正版：位置リセット問題解決）"""
        try:
            js_data = {
                'text': lipsync_data.text,
                'total_duration': lipsync_data.total_duration,
                'vowel_frames': [
                    {
                        'timestamp': frame.timestamp,
                        'vowel': frame.vowel,
                        'intensity': frame.intensity,
                        'duration': frame.duration
                    }
                    for frame in lipsync_data.vowel_frames
                ]
            }
            
            webview = self.character_display.live2d_webview
            
            # 修正：設定同期は1回のみ、リップシンク前に実行
            if hasattr(self.character_display, 'sync_current_live2d_settings_to_webview'):
                self.character_display.sync_current_live2d_settings_to_webview()

            script = f"""
            if (typeof window.startLipSync === 'function') {{
                window.startLipSync({js_data});
            }}
            """
            webview.page().runJavaScript(script)
            
            # 修正：重複する設定同期を削除
            # QTimer.singleShot(0, ...)の部分を削除

        except Exception as e:
            print(f"❌ Live2Dリップシンク送信エラー: {e}")
            
    def open_model_loader(self):
        dialog = ModelLoaderDialog(self)
        dialog.model_loaded.connect(self.load_model)
        dialog.exec()
        
    def show_model_history_dialog(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout
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
            paths = {k: model_data[k] for k in ['model_path', 'config_path', 'style_path']}
            dlg.accept()
            self.load_model(paths)
        widget.model_selected.connect(_on_selected)
        lay.addWidget(widget)
        dlg.exec()
        
    def load_model(self, paths):
        try:
            if self.tts_engine.load_model(**paths):
                self.model_manager.add_model(**paths)
                for btn in [self.sequential_play_btn, self.save_individual_btn, self.save_continuous_btn, self.test_lipsync_btn]:
                    btn.setEnabled(True)
                model_name = Path(paths["model_path"]).parent.name
                if hasattr(self.character_display, 'current_live2d_folder') and self.character_display.current_live2d_folder:
                    live2d_name = Path(self.character_display.current_live2d_folder).name
                    self.setWindowTitle(f"TTSスタジオ - {model_name} - {live2d_name} (Live2D)")
                else:
                    self.setWindowTitle(f"TTSスタジオ - {model_name}")
                available_styles = self.tts_engine.get_available_styles()
                QMessageBox.information(self, "成功", f"モデルを読み込みました。\n\n🎭 利用可能感情: {len(available_styles)}個")
                self.update_emotion_ui_after_model_load()
            else:
                QMessageBox.critical(self, "エラー", "モデルの読み込みに失敗しました。")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"モデル読み込み中にエラーが発生しました:\n{str(e)}")

    def load_last_model(self):
        """アプリ起動時の自動復元：音声モデル + Live2Dモデル"""
        # 1. 音声モデルの自動復元
        models = self.model_manager.get_all_models()
        if models:
            last = models[0]
            if self.model_manager.validate_model_files(last):
                paths = {k: last[k] for k in ["model_path", "config_path", "style_path"]}
                if self.tts_engine.load_model(**paths):
                    for btn in [self.sequential_play_btn, self.save_individual_btn, self.save_continuous_btn, self.test_lipsync_btn]:
                        btn.setEnabled(True)
                    model_name = Path(paths["model_path"]).parent.name
                    self.setWindowTitle(f"TTSスタジオ - {model_name}")
                    self.update_emotion_ui_after_model_load()
                    print(f"✅ 音声モデル自動復元完了: {model_name}")
        
        # 2. Live2Dモデルの自動復元
        self.load_last_live2d_model()

    def load_last_live2d_model(self):
        """最後に使用したLive2Dモデルを自動復元"""
        try:
            if hasattr(self.character_display, 'live2d_manager'):
                last_live2d = self.character_display.live2d_manager.get_last_model()
                
                if last_live2d:
                    model_folder_path = last_live2d['model_folder_path']
                    
                    if Path(model_folder_path).exists():
                        validation = self.character_display.live2d_manager.validate_model_folder(model_folder_path)
                        
                        if validation['is_valid']:
                            self.character_display.load_live2d_model_from_data(last_live2d)
                        else:
                            print(f"⚠️ Live2Dモデルファイルが不完全: {model_folder_path}")
                    else:
                        print(f"⚠️ Live2Dモデルフォルダが見つかりません: {model_folder_path}")
                else:
                    print("ℹ️ Live2D履歴なし")
        except Exception as e:
            print(f"Live2D自動復元エラー: {e}")

    def apply_audio_cleaning(self, audio, sample_rate):
        if not self.tabbed_audio_control.is_cleaner_enabled(): return audio
        try:
            settings = self.tabbed_audio_control.get_cleaner_settings()
            return self.audio_processor.process_audio(audio, sample_rate, settings)
        except Exception as e:
            print(f"音声クリーナーエラー: {e}")
            return audio
            
    def apply_audio_effects(self, audio, sample_rate):
        if not self.tabbed_audio_control.is_effects_enabled(): return audio
        try:
            settings = self.tabbed_audio_control.get_effects_settings()
            return self.audio_effects_processor.process_effects(audio, sample_rate, settings)
        except Exception as e:
            print(f"音声エフェクトエラー: {e}")
            return audio
            
    def play_single_text(self, row_id, text, parameters):
        """単一テキスト再生（リップシンク統合版）"""
        if not self.tts_engine.is_loaded:
            QMessageBox.warning(self, "エラー", "モデルが読み込まれていません。")
            return
        

        if self._tts_busy:
            print("⏳ 別の音声合成処理が実行中のため待機してください。")
            return

        
        tab_parameters = self.tabbed_audio_control.get_parameters(row_id) or parameters


        self._tts_busy = True
        self.statusBar().showMessage("音声合成中...")
        enable_lipsync = self.tabbed_audio_control.is_lip_sync_enabled()
        self.tts_synthesis_requested.emit(text, tab_parameters, enable_lipsync)

    def on_tts_synthesis_finished(self, sample_rate, audio, lipsync_data, error_message):
        """ワーカースレッドからの合成結果を受け取りUI側の処理を行う"""
        self.statusBar().clearMessage()
        self._tts_busy = False

        if error_message:
            print(error_message)
            QMessageBox.critical(self, "エラー", "音声合成に失敗しました。\n詳細はコンソールを確認してください。")
            return

        if audio is None or sample_rate is None:
            return
        
        try:
            audio = self.apply_audio_cleaning(audio, sample_rate)
            audio = self.apply_audio_effects(audio, sample_rate)
            self.last_generated_audio, self.last_sample_rate = audio, sample_rate

            
            # 音声再生
            import sounddevice as sd
            sd.play(audio, sample_rate, blocking=False)

            if (lipsync_data and
                self.tabbed_audio_control.is_lip_sync_enabled() and
                hasattr(self.character_display, 'live2d_webview') and
                self.character_display.live2d_webview.is_model_loaded):
                self.send_lipsync_to_live2d(lipsync_data)
                print(f"🎭 リップシンク実行: {len(lipsync_data.vowel_frames)}フレーム")
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"音声再生処理に失敗しました: {str(e)}")
            
    def trim_silence(self, audio, sample_rate, threshold=0.01):
        non_silent = np.where(np.abs(audio) > threshold)[0]
        if len(non_silent) > 0:
            return audio[:non_silent[-1] + int(sample_rate * 0.1)]
        return audio
        
    def _synthesize_and_process_all(self):
        texts_data = self.multi_text.get_all_texts_and_parameters()
        if not texts_data:
            QMessageBox.information(self, "情報", "処理するテキストがありません。")
            return None, None
        all_audio, sample_rate = [], None
        for data in texts_data:
            params = self.tabbed_audio_control.get_parameters(data['row_id']) or data['parameters']
            sr, audio = self.tts_engine.synthesize(data['text'], **params)
            if sample_rate is None: sample_rate = sr
            audio = self.apply_audio_cleaning(audio, sr)
            audio = self.apply_audio_effects(audio, sr)
            audio = self.trim_silence(audio, sr)
            all_audio.append(audio)
        final_audio = np.concatenate(all_audio).astype(np.float32)
        max_val = np.abs(final_audio).max()
        if max_val > 0.9: final_audio *= 0.9 / max_val
        self.last_generated_audio, self.last_sample_rate = final_audio, sample_rate
        return final_audio, sample_rate
        
    def play_sequential(self):
        if not self.tts_engine.is_loaded: return
        self.sequential_play_btn.setEnabled(False)
        final_audio, sr = self._synthesize_and_process_all()
        self.sequential_play_btn.setEnabled(True)
        if final_audio is not None:
            import sounddevice as sd
            sd.play(final_audio, sr, blocking=False)
            
    def save_individual(self):
        folder_path = QFileDialog.getExistingDirectory(self, "個別保存フォルダを選択")
        if not folder_path: return
        import soundfile as sf
        texts_data = self.multi_text.get_all_texts_and_parameters()
        self.save_individual_btn.setEnabled(False)
        for i, data in enumerate(texts_data, 1):
            params = self.tabbed_audio_control.get_parameters(data['row_id']) or data['parameters']
            sr, audio = self.tts_engine.synthesize(data['text'], **params)
            audio = self.apply_audio_cleaning(audio, sr)
            audio = self.apply_audio_effects(audio, sr)
            safe_text = "".join(c for c in data['text'][:20] if c.isalnum() or c in " -_").rstrip() or f"text_{i}"
            filename = f"{i:02d}_{safe_text}.wav"
            sf.write(os.path.join(folder_path, filename), audio, sr)
        self.save_individual_btn.setEnabled(True)
        QMessageBox.information(self, "完了", f"個別ファイルを保存しました。")
        
    def save_continuous(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "連続音声ファイルを保存", "continuous.wav", "WAV files (*.wav)")
        if not file_path: return
        self.save_continuous_btn.setEnabled(False)
        final_audio, sr = self._synthesize_and_process_all()
        self.save_continuous_btn.setEnabled(True)
        if final_audio is not None:
            import soundfile as sf
            sf.write(file_path, final_audio, sr)
            QMessageBox.information(self, "完了", f"連続音声ファイルを保存しました。")
            
    def on_text_row_added(self, row_id, row_number):
        self.tabbed_audio_control.add_text_row(row_id, row_number)
        
    def on_text_row_removed(self, row_id):
        self.tabbed_audio_control.remove_text_row(row_id)
        
    def on_row_numbers_updated(self, row_mapping):
        self.tabbed_audio_control.update_tab_numbers(row_mapping)
        
    def on_parameters_changed(self, row_id, parameters): pass
    def on_cleaner_settings_changed(self, cleaner_settings): pass
    def on_effects_settings_changed(self, effects_settings): pass
    
    def update_emotion_ui_after_model_load(self):
        if not self.tts_engine.is_loaded: return
        try:
            styles = self.tts_engine.get_available_styles()
            self.tabbed_audio_control.emotion_control.update_emotion_list(styles)
        except Exception as e:
            print(f"感情UI更新エラー: {e}")
            
    def closeEvent(self, event):
        try:
            cleaner_control = self.tabbed_audio_control.cleaner_control
            if hasattr(cleaner_control, 'analysis_thread') and cleaner_control.analysis_thread and cleaner_control.analysis_thread.isRunning():
                cleaner_control.analysis_thread.quit()
                cleaner_control.analysis_thread.wait(3000)
            if self.tts_engine: self.tts_engine.unload_model()
            self.model_manager.save_history()
            if hasattr(self.character_display, 'live2d_manager'):
                self.character_display.live2d_manager.save_history()
            if hasattr(self, 'tts_thread') and self.tts_thread.isRunning():
                self.tts_thread.quit()
                self.tts_thread.wait(5000)
                self.character_display.live2d_manager.save_history()
        except Exception as e:
            print(f"終了処理中にエラー: {e}")
        event.accept()