import os
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QFileDialog, QStyle, QFrame, QApplication, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QAction

# 自作モジュール
from .model_history import ModelHistoryWidget
from .model_loader import ModelLoaderDialog
from .tabbed_emotion_control import TabbedEmotionControl
from .multi_text import MultiTextWidget
from .keyboard_shortcuts import KeyboardShortcutManager
from .sliding_menu import SlidingMenuWidget
from core.tts_engine import TTSEngine
from core.model_manager import ModelManager
from .help_dialog import HelpDialog


class TTSStudioMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tts_engine = TTSEngine()
        self.model_manager = ModelManager()
        self.init_ui()
        self.help_dialog = HelpDialog(self)

        
        # スライド式メニューを作成
        self.sliding_menu = SlidingMenuWidget(self)
        self.sliding_menu.load_model_clicked.connect(self.open_model_loader)
        self.sliding_menu.load_from_history_clicked.connect(self.show_model_history_dialog)
        
        # キーボードショートカット設定
        self.keyboard_shortcuts = KeyboardShortcutManager(self)
        
        self.load_last_model()

    def init_ui(self):
        self.setWindowTitle("TTSスタジオ - ほのかちゃん")
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

        params_label = QLabel("音声パラメータ:")
        params_label.setFont(QFont("", 10, QFont.Weight.Bold))

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setStyleSheet("color: #dee2e6;")

        self.tabbed_emotion_control = TabbedEmotionControl()
        self.tabbed_emotion_control.parameters_changed.connect(self.on_parameters_changed)
        self.tabbed_emotion_control.add_text_row("initial", 1)

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

        left.addWidget(self.multi_text, 1)
        left.addWidget(params_label)
        left.addWidget(divider)
        left.addWidget(self.tabbed_emotion_control, 1)
        left.addLayout(controls)

        # 右ペイン（ダミー）
        self.live2d_widget = QWidget()
        self.live2d_widget.setMaximumWidth(300)
        self.live2d_widget.setMinimumWidth(250)
        self.live2d_widget.setStyleSheet("""
            QWidget { background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 4px; }
        """)
        live2d_layout = QVBoxLayout(self.live2d_widget)
        live2d_label = QLabel("Live2D\nリップシンクエリア")
        live2d_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        live2d_label.setStyleSheet("color: #666; font-size: 14px; border: none;")
        live2d_layout.addWidget(live2d_label)

        content.addLayout(left, 1)
        content.addWidget(self.live2d_widget, 0)
        main.addLayout(content)

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
        """モデルを読み込む"""
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
                
                QMessageBox.information(self, "成功", "モデルを読み込みました。")
                
            else:
                QMessageBox.critical(self, "エラー", "モデルの読み込みに失敗しました。")
                
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"モデル読み込み中にエラーが発生しました: {str(e)}")

    # ---------- TTS / そのほか（既存） ----------
    def on_text_row_added(self, row_id, row_number):
        self.tabbed_emotion_control.add_text_row(row_id, row_number)

    def on_text_row_removed(self, row_id):
        self.tabbed_emotion_control.remove_text_row(row_id)

    def on_row_numbers_updated(self, row_mapping):
        self.tabbed_emotion_control.update_tab_numbers(row_mapping)

    def on_parameters_changed(self, row_id, parameters):
        """パラメータ変更時の処理（必要に応じて実装）"""
        # 現在は何もしないが、将来的にリアルタイムプレビューなどに使用可能
        pass

    def load_last_model(self):
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

    def play_single_text(self, row_id, text, parameters):
        if not self.tts_engine.is_loaded:
            QMessageBox.warning(self, "エラー", "モデルが読み込まれていません。")
            return
        tab_parameters = self.tabbed_emotion_control.get_parameters(row_id) or parameters
        try:
            sr, audio = self.tts_engine.synthesize(text, **tab_parameters)
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
                tab_parameters = self.tabbed_emotion_control.get_parameters(row_id)
                if not tab_parameters:
                    # デフォルトパラメータ
                    tab_parameters = {
                        'style': 'Neutral', 'style_weight': 1.0,
                        'length_scale': 0.85, 'pitch_scale': 1.0,
                        'intonation_scale': 1.0, 'sdp_ratio': 0.25, 'noise': 0.35
                    }
                
                sr, audio = self.tts_engine.synthesize(text, **tab_parameters)
                
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
            
            # バックグラウンドで再生
            import sounddevice as sd
            sd.play(final_audio, sample_rate, blocking=False)
            
            # ボタンを元に戻す
            self.sequential_play_btn.setEnabled(True)
            self.sequential_play_btn.setText("連続して再生")
            
        except Exception as e:
            self.sequential_play_btn.setEnabled(True)
            self.sequential_play_btn.setText("連続して再生")
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
                    tab_parameters = self.tabbed_emotion_control.get_parameters(row_id)
                    if not tab_parameters:
                        tab_parameters = {
                            'style': 'Neutral', 'style_weight': 1.0,
                            'length_scale': 0.85, 'pitch_scale': 1.0,
                            'intonation_scale': 1.0, 'sdp_ratio': 0.25, 'noise': 0.35
                        }
                    
                    sr, audio = self.tts_engine.synthesize(text, **tab_parameters)
                    
                    # ファイル名生成
                    safe_text = "".join(c for c in text[:20] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    if not safe_text:
                        safe_text = f"text_{i}"
                    filename = f"{i:02d}_{safe_text}.wav"
                    file_path = os.path.join(folder_path, filename)
                    
                    sf.write(file_path, audio, sr)
                
                # ボタンを元に戻す
                self.save_individual_btn.setEnabled(True)
                self.save_individual_btn.setText("個別保存")
                
                QMessageBox.information(self, "完了", f"個別ファイルを保存しました。\n保存先: {folder_path}")
                
        except Exception as e:
            self.save_individual_btn.setEnabled(True)
            self.save_individual_btn.setText("個別保存")
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
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "連続音声ファイルを保存",
                "continuous_output.wav",
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
                    tab_parameters = self.tabbed_emotion_control.get_parameters(row_id)
                    if not tab_parameters:
                        tab_parameters = {
                            'style': 'Neutral', 'style_weight': 1.0,
                            'length_scale': 0.85, 'pitch_scale': 1.0,
                            'intonation_scale': 1.0, 'sdp_ratio': 0.25, 'noise': 0.35
                        }
                    
                    sr, audio = self.tts_engine.synthesize(text, **tab_parameters)
                    
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
                
                # ファイル保存
                sf.write(file_path, final_audio, sample_rate)
                
                # ボタンを元に戻す
                self.save_continuous_btn.setEnabled(True)
                self.save_continuous_btn.setText("連続保存")
                
                QMessageBox.information(self, "完了", f"連続音声ファイルを保存しました。\n保存先: {file_path}")
                
        except Exception as e:
            self.save_continuous_btn.setEnabled(True)
            self.save_continuous_btn.setText("連続保存")
            QMessageBox.critical(self, "エラー", f"連続保存に失敗しました: {str(e)}")