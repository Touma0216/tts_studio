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
from core.wav_player import WAVPlayer
from core.whisper_transcriber import WhisperTranscriber

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
        self.lip_sync_engine = LipSyncEngine()
        self.setup_tts_worker()
        self.wav_player = WAVPlayer()
        self._wav_lipsync_timer = None
        self._wav_lipsync_data = None
        self.whisper_transcriber = WhisperTranscriber(model_size="small", device="cuda")

        
        self.setup_tts_worker()
        
        self.last_generated_audio = None
        self.last_sample_rate = None
        self._tts_busy = False
        
        self.init_ui()
        self.help_dialog = HelpDialog(self)
        self.setup_audio_processing_integration()
        
        # リップシンク統合設定
        self.setup_lipsync_integration()

        self.setup_wav_playback_integration()
        
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
        
        # 統合されたタブコントロール
        self.tabbed_audio_control = TabbedAudioControl()
        self.tabbed_audio_control.parameters_changed.connect(self.on_parameters_changed)
        self.tabbed_audio_control.cleaner_settings_changed.connect(self.on_cleaner_settings_changed)
        self.tabbed_audio_control.effects_settings_changed.connect(self.on_effects_settings_changed)
        self.tabbed_audio_control.lip_sync_settings_changed.connect(self.on_lipsync_settings_changed)
        # 🆕 モデリングシグナル接続
        self.tabbed_audio_control.modeling_parameter_changed.connect(self.on_modeling_parameter_changed)
        self.tabbed_audio_control.modeling_parameters_changed.connect(self.on_modeling_parameters_changed)
        self.tabbed_audio_control.drag_control_toggled.connect(self.on_drag_control_toggled)
        self.tabbed_audio_control.drag_sensitivity_changed.connect(self.on_drag_sensitivity_changed)
        # 統合されたリップシンク設定変更ハンドラー
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

    def on_lipsync_settings_changed(self, settings):
        """リップシンク設定変更時の処理 - 完全修正版"""
        try:
            print(f"🔧 リップシンク設定変更開始: {list(settings.keys())}")
            
            # リップシンクエンジンに設定を適用
            if self.lip_sync_engine:
                self.lip_sync_engine.update_settings(settings)
                
                # デバッグ：現在の音素マッピングを表示
                current_mapping = self.lip_sync_engine.get_vowel_mapping()
                print("📊 エンジン側音素マッピング:")
                for vowel, params in current_mapping.items():
                    if vowel != 'sil':
                        print(f"  {vowel}: 開き={params['mouth_open']}, 形={params['mouth_form']}")
            
            # 🔥 Live2D側に送信するデータを簡素化
            if (hasattr(self.character_display, 'live2d_webview') and 
                self.character_display.live2d_webview.is_model_loaded):
                
                self._send_simple_lipsync_settings(settings)
                
        except Exception as e:
            print(f"❌ リップシンク設定変更エラー: {e}")
            import traceback
            traceback.print_exc()

    def _send_simple_lipsync_settings(self, settings):
        """Live2D側にシンプルな設定を送信"""
        try:
            webview = self.character_display.live2d_webview
            
            # 🔥 シンプルな設定データを準備
            simple_settings = {}
            
            # 基本設定
            if 'basic' in settings:
                basic = settings['basic']
                simple_settings['enabled'] = basic.get('enabled', True)
                simple_settings['sensitivity'] = basic.get('sensitivity', 100) / 100.0
                simple_settings['mouth_scale'] = basic.get('mouth_open_scale', 100) / 100.0
            
            # 🔥 音素設定（0-1範囲に正規化）
            if 'phoneme' in settings:
                simple_settings['vowels'] = {}
                for vowel, params in settings['phoneme'].items():
                    if isinstance(params, dict):
                        # 0-1範囲に正規化（Live2D標準）
                        mouth_open = max(0, min(1, params.get('mouth_open', 0) / 100.0))
                        mouth_form = max(-1, min(1, params.get('mouth_form', 0) / 100.0))
                        
                        simple_settings['vowels'][vowel] = {
                            'open': round(mouth_open, 3),
                            'form': round(mouth_form, 3)
                        }
                        
                        print(f"  送信: {vowel} = 開き{mouth_open:.3f}, 形{mouth_form:.3f}")
            
            # JavaScriptに送信（シンプル版）
            import json
            settings_json = json.dumps(simple_settings, ensure_ascii=False)
            
            script = f"""
            (function() {{
                try {{
                    console.log('🔧 シンプル設定受信:', {settings_json});
                    
                    // グローバル変数に保存
                    if (!window.lipSyncSettings) {{
                        window.lipSyncSettings = {{}};
                    }}
                    Object.assign(window.lipSyncSettings, {settings_json});
                    
                    console.log('✅ 設定保存完了:', window.lipSyncSettings);
                    return true;
                }} catch (error) {{
                    console.error('❌ 設定保存エラー:', error);
                    return false;
                }}
            }})()
            """
            
            webview.page().runJavaScript(script, self._on_settings_sent)
            
        except Exception as e:
            print(f"❌ シンプル設定送信エラー: {e}")

    def _on_settings_sent(self, result):
        """設定送信結果を処理"""
        if result:
            print("✅ Live2D側設定保存完了")
        else:
            print("⚠️ Live2D側設定保存失敗")

    def test_lipsync_function(self):
        """リップシンク機能をテスト - 音声同期版"""
        try:
            print("🎭 リップシンクテスト開始（音声同期版）")
            
            # Live2Dモデルが読み込まれているかチェック
            if not hasattr(self.character_display, 'live2d_webview') or not self.character_display.live2d_webview.is_model_loaded:
                QMessageBox.warning(self, "リップシンクテスト", 
                    "Live2Dモデルが読み込まれていません。\n"
                    "先にLive2Dモデルを読み込んでからテストしてください。")
                return
            
            # TTSモデルが読み込まれているかチェック
            if not self.tts_engine.is_loaded:
                QMessageBox.warning(self, "リップシンクテスト",
                    "音声モデルが読み込まれていません。\n"
                    "先に音声モデルを読み込んでからテストしてください。")
                return
            
            # テキストを取得
            texts_data = self.multi_text.get_all_texts_and_parameters()
            if texts_data and texts_data[0]['text'].strip():
                test_text = texts_data[0]['text']
                row_id = texts_data[0]['row_id']
                test_params = self.tabbed_audio_control.get_parameters(row_id) or texts_data[0]['parameters']
            else:
                test_text = "こんにちは。リップシンクのテストをしています。あいうえお。"
                test_params = {
                    'style': 'Neutral',
                    'style_weight': 1.0,
                    'length_scale': 1.0,
                    'pitch_scale': 1.0,
                    'intonation_scale': 1.0
                }
                
            print(f"🎵 テストテキスト: '{test_text[:30]}...'")
            
            # ボタン状態変更
            self.test_lipsync_btn.setEnabled(False)
            self.test_lipsync_btn.setText("音声生成中...")
            QApplication.processEvents()
            
            # 🔥 1. TTS音声を生成
            sr, audio = self.tts_engine.synthesize(test_text, **test_params)
            print(f"✅ 音声生成完了: {len(audio)} samples, {sr}Hz, {len(audio)/sr:.3f}秒")
            
            self.test_lipsync_btn.setText("解析中...")
            QApplication.processEvents()
            
            # 🔥 2. 生成された音声データを使ってリップシンクデータを生成
            lipsync_data = self.lip_sync_engine.analyze_text_for_lipsync(
                text=test_text,
                audio_data=audio,
                sample_rate=sr
            )
            
            if lipsync_data:
                print(f"✅ リップシンクデータ生成成功: {len(lipsync_data.vowel_frames)}フレーム, {lipsync_data.total_duration:.3f}秒")
                
                # 音声を再生
                import sounddevice as sd
                sd.play(audio, sr, blocking=False)
                
                # リップシンクを送信
                self.send_lipsync_to_live2d(lipsync_data)
                
                self.test_lipsync_btn.setText("テスト実行中...")
                
                # タイマーで停止
                QTimer.singleShot(int(lipsync_data.total_duration * 1000) + 500, self._reset_test_button)
                
            else:
                print("❌ リップシンクデータ生成失敗")
                QMessageBox.warning(self, "リップシンクテスト", "リップシンクデータの生成に失敗しました。")
                self._reset_test_button()
                
        except Exception as e:
            print(f"❌ リップシンクテストエラー: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "エラー", f"リップシンクテストでエラーが発生しました:\n{str(e)}")
            self._reset_test_button()

    def _reset_test_button(self):
        """テストボタンをリセット"""
        self.test_lipsync_btn.setEnabled(True)
        self.test_lipsync_btn.setText("🎭 リップシンクテスト")

    def send_lipsync_to_live2d(self, lipsync_data):
        """Live2Dにリップシンクデータを送信 - 位置リセット防止版"""
        try:
            print(f"🎭 Live2Dリップシンク送信: {len(lipsync_data.vowel_frames)}フレーム, {lipsync_data.total_duration:.3f}秒")
            
            # 🔧 リップシンク開始：位置リセット防止を有効化
            self.character_display.mark_lipsync_in_progress(True)
            
            # シンプルなデータ準備
            simple_data = {
                'text': lipsync_data.text,
                'duration': lipsync_data.total_duration,
                'frames': [
                    {
                        'time': frame.timestamp,
                        'vowel': frame.vowel,
                        'intensity': frame.intensity,
                        'duration': frame.duration
                    }
                    for frame in lipsync_data.vowel_frames
                ]
            }
            
            webview = self.character_display.live2d_webview
            
            import json
            data_json = json.dumps(simple_data, ensure_ascii=False)

            script = f"""
            (function() {{
                try {{
                    const lipSyncData = {data_json};
                    console.log('🎭 リップシンクデータ受信:', lipSyncData.frames.length, 'フレーム');
                    
                    if (typeof window.startSimpleLipSync === 'function') {{
                        return window.startSimpleLipSync(lipSyncData);
                    }} else if (typeof window.startLipSync === 'function') {{
                        return window.startLipSync(lipSyncData);
                    }} else {{
                        console.error('❌ リップシンク関数が見つかりません');
                        return false;
                    }}
                }} catch (error) {{
                    console.error('❌ リップシンク送信エラー:', error);
                    return false;
                }}
            }})()
            """
            
            # JavaScriptにリップシンク開始命令を送信
            webview.page().runJavaScript(script)

            # ★★★ 追加した行 ★★★
            # JS呼び出し直後(10ミリ秒後)に、現在のUIスライダーの設定を強制的に再同期させる
            QTimer.singleShot(10, self.character_display.sync_current_live2d_settings_to_webview)
            
            # 🔧 リップシンク終了後に位置リセット防止を無効化（タイマー）
            QTimer.singleShot(int(lipsync_data.total_duration * 1000) + 500, 
                            lambda: self.character_display.mark_lipsync_in_progress(False))

        except Exception as e:
            print(f"❌ Live2Dリップシンク送信エラー: {e}")
            # エラー時も必ず無効化
            self.character_display.mark_lipsync_in_progress(False)

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
        self.character_display.live2d_model_loaded.connect(self.on_live2d_model_loaded)
        # 🆕 パラメータ読み込み完了シグナル接続
        self.character_display.live2d_parameters_loaded.connect(self.on_live2d_parameters_loaded)
        model_name = Path(model_path).name
        print(f"Live2Dモデルが読み込まれました: {model_name}")
        current_title = self.windowTitle()
        if " - " in current_title:
            base_title = current_title.split(" - ")[0]
        else:
            base_title = current_title
        self.setWindowTitle(f"{base_title} - {model_name} (Live2D)")
        # モデル読み込み直後にドラッグ制御の状態を同期
        QTimer.singleShot(100, self.sync_drag_control_state)

    def setup_audio_processing_integration(self):
            self.tabbed_audio_control.cleaner_control.analyze_requested.connect(self.handle_cleaner_analysis_request)
        
    # ========================================
    # 📍 ファイル: ui/main_window.py
    # 📍 場所: setup_wav_playback_integration() メソッド内、既存シグナル接続の下
    # ========================================

    def setup_wav_playback_integration(self):
        """WAV再生機能の統合設定"""
        try:
            print("🎵 WAV再生機能統合中...")
            
            # 既存のシグナル接続...
            self.tabbed_audio_control.wav_file_loaded.connect(self.on_wav_file_loaded)
            self.tabbed_audio_control.wav_playback_started.connect(self.on_wav_playback_started)
            self.tabbed_audio_control.wav_playback_paused.connect(self.on_wav_playback_paused)
            self.tabbed_audio_control.wav_playback_stopped.connect(self.on_wav_playback_stopped)
            self.tabbed_audio_control.wav_position_changed.connect(self.on_wav_position_changed)
            self.tabbed_audio_control.wav_volume_changed.connect(self.on_wav_volume_changed)
            
            # WAVプレイヤーシグナル接続
            self.wav_player.playback_position_changed.connect(self.on_wav_player_position_update)
            self.wav_player.playback_finished.connect(self.on_wav_player_finished)
            
            # 🆕 文字起こし関連シグナル接続
            wav_control = self.tabbed_audio_control.get_wav_playback_control()
            wav_control.re_analyze_requested.connect(self.on_wav_reanalyze_requested)
            wav_control.save_transcription_requested.connect(self.on_save_transcription_requested)  # 🆕 追加
            
            print("✅ WAV再生機能統合完了")
            
        except Exception as e:
            print(f"❌ WAV再生統合エラー: {e}")
        
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
        enable_lipsync = self.tabbed_audio_control.is_lip_sync_enabled()
        self.tts_synthesis_requested.emit(text, tab_parameters, enable_lipsync)

    def on_tts_synthesis_finished(self, sample_rate, audio, lipsync_data, error_message):
        """ワーカースレッドからの合成結果を受け取りUI側の処理を行う"""
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

            # リップシンク送信
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

    # ================================
    # 🆕 モデリング関連ハンドラー
    # ================================
    
    def on_live2d_parameters_loaded(self, parameters: list, model_id: str):
        """Live2Dモデルのパラメータ読み込み完了時"""
        try:
            print(f"🎨 パラメータ読み込み: {len(parameters)}個")
            self.tabbed_audio_control.load_model_parameters(parameters, model_id)
        except Exception as e:
            print(f"❌ パラメータ読み込みエラー: {e}")
    
    def on_modeling_parameter_changed(self, param_id: str, value: float):
        """モデリングパラメータ変更時（単一）"""
        try:
            if hasattr(self.character_display, 'set_live2d_parameter'):
                self.character_display.set_live2d_parameter(param_id, value)
        except Exception as e:
            print(f"❌ パラメータ設定エラー ({param_id}): {e}")
    
    def on_modeling_parameters_changed(self, parameters: dict):
        """モデリングパラメータ変更時（全体）"""
        try:
            if hasattr(self.character_display, 'set_live2d_parameters'):
                self.character_display.set_live2d_parameters(parameters)
        except Exception as e:
            print(f"❌ パラメータ一括設定エラー: {e}")

    def on_drag_control_toggled(self, enabled: bool):
        """ドラッグ制御ON/OFF切り替え"""
        try:
            if hasattr(self.character_display, 'enable_drag_control'):
                self.character_display.enable_drag_control(enabled)
        except Exception as e:
            print(f"❌ ドラッグ制御切り替えエラー: {e}")
    
    def on_drag_sensitivity_changed(self, sensitivity: float):
        """ドラッグ感度変更"""
        try:
            if hasattr(self.character_display, 'set_drag_sensitivity'):
                self.character_display.set_drag_sensitivity(sensitivity)
        except Exception as e:
            print(f"❌ ドラッグ感度変更エラー: {e}")

    def sync_drag_control_state(self):
        """UIとLive2Dドラッグ制御の状態を同期"""
        modeling_control = getattr(self.tabbed_audio_control, 'modeling_control', None)
        if not modeling_control:
            return

        try:
            self.on_drag_control_toggled(modeling_control.is_drag_enabled())
        except Exception as e:
            print(f"⚠️ ドラッグ制御状態同期エラー: {e}")

        try:
            self.on_drag_sensitivity_changed(modeling_control.get_drag_sensitivity())
        except Exception as e:
            print(f"⚠️ ドラッグ感度同期エラー: {e}")
    
    # ========================================
    # 📍 ファイル: ui/main_window.py
    # 📍 場所: on_wav_file_loaded() メソッドを完全に置き換え
    # ========================================

    def on_wav_file_loaded(self, file_path: str):
        """WAVファイル読み込み完了（Whisper文字起こし統合版）"""
        try:
            print(f"🎵 WAVファイル読み込み開始: {file_path}")
            
            # WAVプレイヤーで読み込み
            if not self.wav_player.load_wav_file(file_path):
                QMessageBox.warning(self, "エラー", "WAVファイルの読み込みに失敗しました。")
                return
            
            # UI側に長さを通知
            duration = self.wav_player.get_duration()
            wav_control = self.tabbed_audio_control.get_wav_playback_control()
            wav_control.set_duration(duration)
            
            print(f"✅ WAVファイル読み込み完了: {duration:.2f}秒")
            
            # 🆕 Whisperによる文字起こし実行
            if self.whisper_transcriber.is_ready():
                self._transcribe_and_generate_lipsync(file_path, wav_control)
            else:
                # Whisper利用不可時はフォールバック
                print("⚠️ Whisper利用不可、フォールバックモード")
                wav_control.set_transcription_status("⚠️ faster-whisperが利用できません", is_processing=False)
                self._generate_wav_lipsync_data_with_text(file_path, "こんにちは")
            
        except Exception as e:
            print(f"❌ WAVファイル読み込みエラー: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "エラー", f"WAVファイル読み込みエラー:\n{str(e)}")


    def _transcribe_and_generate_lipsync(self, file_path: str, wav_control):
        """Whisper文字起こし + リップシンク生成"""
        try:
            # ステータス表示更新
            wav_control.set_transcription_status("🎤 音声認識処理中...", is_processing=True)
            QApplication.processEvents()
            
            # Whisperで文字起こし実行
            success, transcribed_text, segments = self.whisper_transcriber.transcribe_wav(
                file_path, 
                language="ja"
            )
            
            if success:
                print(f"✅ 文字起こし成功: {transcribed_text[:50]}...")
                
                # UIにテキスト表示（タイピングアニメーション付き）
                wav_control.set_transcription_text(transcribed_text, segments, animated=True)  # 🆕 animated=True
                wav_control.set_transcription_status("✅ 文字起こし完了", is_processing=False)
                
                # リップシンクデータ生成
                self._generate_wav_lipsync_data_with_text(file_path, transcribed_text)
                
                # 🆕 自動保存（追記型）
                self._auto_save_transcription(file_path, segments)
                
            else:
                # エラー時
                error_msg = transcribed_text
                print(f"❌ 文字起こし失敗: {error_msg}")
                wav_control.set_transcription_status(f"❌ エラー: {error_msg[:30]}...", is_processing=False)
                
                # フォールバック
                self._generate_wav_lipsync_data_with_text(file_path, "こんにちは")
            
        except Exception as e:
            print(f"❌ 文字起こし処理エラー: {e}")
            import traceback
            traceback.print_exc()
            
            wav_control.set_transcription_status("❌ 処理エラー", is_processing=False)
            self._generate_wav_lipsync_data_with_text(file_path, "こんにちは")


    # 📍 新規メソッド追加（_transcribe_and_generate_lipsync の下）

    def _auto_save_transcription(self, wav_path: str, segments: list):
        """文字起こし結果を自動保存（追記型）
        
        Args:
            wav_path: 元のWAVファイルパス
            segments: セグメントリスト
        """
        try:
            if not segments:
                return
            
            # 保存先ファイルパス
            transcription_file = Path("transcriptions.txt")
            
            # ファイル名を取得
            file_name = Path(wav_path).name
            
            # 追記モードで保存
            success = self.whisper_transcriber.save_transcription_to_file(
                segments,
                str(transcription_file),
                include_timestamps=True,
                append_mode=True,  # 🆕 追記モード
                file_name=file_name  # 🆕 ヘッダー用
            )
            
            if success:
                print(f"💾 自動保存完了: {transcription_file}")
            
        except Exception as e:
            print(f"⚠️ 自動保存エラー（処理は継続）: {e}")

    def _generate_wav_lipsync_data_with_text(self, file_path: str, text: str):
        """指定されたテキストでWAV全体のリップシンクデータを生成
        
        Args:
            file_path: WAVファイルパス
            text: リップシンク用テキスト
        """
        try:
            print(f"🎭 WAVリップシンク解析開始: '{text[:50]}...'")
            
            audio_data = self.wav_player.get_audio_data()
            sample_rate = self.wav_player.get_sample_rate()
            
            if audio_data is None or sample_rate is None:
                print("⚠️ 音声データが取得できません")
                return
            
            # 🔥 実際のテキストでリップシンク解析実行
            self._wav_lipsync_data = self.lip_sync_engine.analyze_text_for_lipsync(
                text=text,
                audio_data=audio_data,
                sample_rate=sample_rate
            )
            
            if self._wav_lipsync_data:
                print(f"✅ WAVリップシンク解析完了: {len(self._wav_lipsync_data.vowel_frames)}フレーム, {self._wav_lipsync_data.total_duration:.3f}秒")
            else:
                print("⚠️ WAVリップシンク解析失敗")
                
        except Exception as e:
            print(f"❌ WAVリップシンク解析エラー: {e}")
            import traceback
            traceback.print_exc()


    def on_wav_reanalyze_requested(self, edited_text: str):
        """再解析ボタンクリック時（テキスト編集後）
        
        Args:
            edited_text: ユーザーが編集したテキスト
        """
        try:
            print(f"🔄 WAVリップシンク再解析: '{edited_text[:50]}...'")
            
            wav_control = self.tabbed_audio_control.get_wav_playback_control()
            
            # 再解析中表示
            wav_control.set_transcription_status("🔄 再解析中...", is_processing=True)
            QApplication.processEvents()
            
            # 現在のWAVファイルで再解析
            current_file = wav_control.get_current_file_path()
            if current_file:
                self._generate_wav_lipsync_data_with_text(current_file, edited_text)
                wav_control.set_transcription_status("✅ 再解析完了", is_processing=False)
            else:
                print("⚠️ WAVファイルが読み込まれていません")
                wav_control.set_transcription_status("⚠️ ファイル未読み込み", is_processing=False)
            
        except Exception as e:
            print(f"❌ WAV再解析エラー: {e}")
            wav_control.set_transcription_status("❌ 再解析エラー", is_processing=False)

    # 📍 ファイル: ui/main_window.py
    # 📍 場所: 新規メソッド追加（on_wav_reanalyze_requested の下）

    def on_save_transcription_requested(self):
        """💾 文字起こし保存リクエスト"""
        try:
            wav_control = self.tabbed_audio_control.get_wav_playback_control()
            
            # セグメントデータを取得
            segments = wav_control.transcription_segments
            if not segments:
                QMessageBox.warning(self, "エラー", "保存するデータがありません")
                return
            
            # 保存先を選択
            current_file = wav_control.get_current_file_path()
            default_name = Path(current_file).stem + "_transcription.txt" if current_file else "transcription.txt"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "文字起こしを保存",
                default_name,
                "テキストファイル (*.txt)"
            )
            
            if not file_path:
                return
            
            # ファイルに保存
            success = self.whisper_transcriber.save_transcription_to_file(
                segments,
                file_path,
                include_timestamps=True
            )
            
            if success:
                QMessageBox.information(self, "完了", f"文字起こしを保存しました:\n{file_path}")
            else:
                QMessageBox.critical(self, "エラー", "ファイル保存に失敗しました")
            
        except Exception as e:
            print(f"❌ 文字起こし保存エラー: {e}")
            QMessageBox.critical(self, "エラー", f"保存エラー:\n{str(e)}")
    
    def on_wav_playback_started(self, start_position: float):
        """WAV再生開始"""
        try:
            print(f"▶️ WAV再生開始: {start_position:.2f}秒から")
            
            # WAVプレイヤーで再生
            self.wav_player.play(start_position)
            
            # リップシンク連動開始
            wav_control = self.tabbed_audio_control.get_wav_playback_control()
            if wav_control.is_lipsync_enabled() and self._wav_lipsync_data:
                self._start_wav_lipsync(start_position)
            
        except Exception as e:
            print(f"❌ WAV再生開始エラー: {e}")
    
    def on_wav_playback_paused(self):
        """WAV再生一時停止"""
        try:
            print("⏸️ WAV一時停止")
            self.wav_player.pause()
            self._stop_wav_lipsync()
            
        except Exception as e:
            print(f"❌ WAV一時停止エラー: {e}")
    
    def on_wav_playback_stopped(self):
        """WAV再生停止"""
        try:
            print("⏹️ WAV停止")
            self.wav_player.stop()
            self._stop_wav_lipsync()
            
        except Exception as e:
            print(f"❌ WAV停止エラー: {e}")
    
    def on_wav_position_changed(self, position: float):
        """WAV再生位置変更（シーク）"""
        try:
            print(f"🎯 WAVシーク: {position:.2f}秒")
            self.wav_player.seek(position)
            
            # リップシンク再開
            wav_control = self.tabbed_audio_control.get_wav_playback_control()
            if wav_control.is_lipsync_enabled() and self._wav_lipsync_data:
                self._start_wav_lipsync(position)
            
        except Exception as e:
            print(f"❌ WAVシークエラー: {e}")
    
    def on_wav_volume_changed(self, volume: float):
        """WAV音量変更"""
        try:
            self.wav_player.set_volume(volume)
            
        except Exception as e:
            print(f"❌ WAV音量変更エラー: {e}")
    
    def on_wav_player_position_update(self, position: float):
        """WAVプレイヤーからの位置更新"""
        try:
            # UI側に通知
            wav_control = self.tabbed_audio_control.get_wav_playback_control()
            wav_control.update_position(position)
            
        except Exception as e:
            print(f"❌ WAV位置更新エラー: {e}")
    
    def on_wav_player_finished(self):
        """WAV再生完了"""
        try:
            print("✅ WAV再生完了")
            
            # UI側に通知
            wav_control = self.tabbed_audio_control.get_wav_playback_control()
            wav_control.on_playback_finished()
            
            # リップシンク停止
            self._stop_wav_lipsync()
            
        except Exception as e:
            print(f"❌ WAV完了処理エラー: {e}")
    
    def _start_wav_lipsync(self, start_position: float):
        """WAVリップシンク開始"""
        try:
            if not self._wav_lipsync_data:
                print("⚠️ リップシンクデータがありません")
                return
            
            if not (hasattr(self.character_display, 'live2d_webview') and 
                    self.character_display.live2d_webview.is_model_loaded):
                print("⚠️ Live2Dモデルが読み込まれていません")
                return
            
            # 開始位置からのフレームデータを抽出
            filtered_frames = [
                frame for frame in self._wav_lipsync_data.vowel_frames
                if frame.timestamp >= start_position
            ]
            
            if not filtered_frames:
                print("⚠️ 該当するリップシンクフレームがありません")
                return
            
            # タイムスタンプを調整（開始位置を0とする）
            adjusted_frames = []
            for frame in filtered_frames:
                from core.lip_sync_engine import VowelFrame
                adjusted_frame = VowelFrame(
                    timestamp=frame.timestamp - start_position,
                    vowel=frame.vowel,
                    intensity=frame.intensity,
                    duration=frame.duration,
                    is_ending=frame.is_ending
                )
                adjusted_frames.append(adjusted_frame)
            
            # シンプルなデータ準備
            simple_data = {
                'text': self._wav_lipsync_data.text,
                'duration': self._wav_lipsync_data.total_duration - start_position,
                'frames': [
                    {
                        'time': frame.timestamp,
                        'vowel': frame.vowel,
                        'intensity': frame.intensity,
                        'duration': frame.duration
                    }
                    for frame in adjusted_frames
                ]
            }
            
            # Live2Dに送信
            self.character_display.mark_lipsync_in_progress(True)
            
            webview = self.character_display.live2d_webview
            import json
            data_json = json.dumps(simple_data, ensure_ascii=False)
            
            script = f"""
            (function() {{
                try {{
                    const lipSyncData = {data_json};
                    console.log('🎭 WAVリップシンク開始:', lipSyncData.frames.length, 'フレーム');
                    
                    if (typeof window.startSimpleLipSync === 'function') {{
                        return window.startSimpleLipSync(lipSyncData);
                    }} else {{
                        console.error('❌ startSimpleLipSync関数が見つかりません');
                        return false;
                    }}
                }} catch (error) {{
                    console.error('❌ WAVリップシンクエラー:', error);
                    return false;
                }}
            }})()
            """
            
            webview.page().runJavaScript(script)
            
            # 設定を強制同期
            QTimer.singleShot(10, self.character_display.sync_current_live2d_settings_to_webview)
            
            print(f"🎭 WAVリップシンク送信完了: {len(adjusted_frames)}フレーム")
            
        except Exception as e:
            print(f"❌ WAVリップシンク開始エラー: {e}")
            import traceback
            traceback.print_exc()
            self.character_display.mark_lipsync_in_progress(False)
    
    def _stop_wav_lipsync(self):
        """WAVリップシンク停止"""
        try:
            if not (hasattr(self.character_display, 'live2d_webview') and 
                    self.character_display.live2d_webview.is_model_loaded):
                return
            
            webview = self.character_display.live2d_webview
            
            script = """
            (function() {
                try {
                    if (typeof window.stopSimpleLipSync === 'function') {
                        window.stopSimpleLipSync();
                        return true;
                    }
                    return false;
                } catch (error) {
                    console.error('❌ リップシンク停止エラー:', error);
                    return false;
                }
            })()
            """
            
            webview.page().runJavaScript(script)
            
            self.character_display.mark_lipsync_in_progress(False)
            
            print("⏹️ WAVリップシンク停止")
            
        except Exception as e:
            print(f"❌ WAVリップシンク停止エラー: {e}")