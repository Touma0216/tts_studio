from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QSlider, QFileDialog, QCheckBox, QGroupBox,
                             QMessageBox, QPlainTextEdit, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from pathlib import Path
from typing import Optional

class WAVPlaybackControl(QWidget):
    """WAV音声再生制御UI（リップシンク連動 + 文字起こし対応）"""
    
    # シグナル定義
    wav_loaded = pyqtSignal(str)  # ファイルパス
    playback_started = pyqtSignal(float)  # 開始位置
    playback_paused = pyqtSignal()
    playback_stopped = pyqtSignal()
    position_changed = pyqtSignal(float)  # 再生位置（秒）
    volume_changed = pyqtSignal(float)  # 音量（0.0-2.0）
    lipsync_enabled_changed = pyqtSignal(bool)  # リップシンク有効/無効
    
    # 🆕 文字起こし関連シグナル
    transcription_text_edited = pyqtSignal(str)  # テキスト編集
    re_analyze_requested = pyqtSignal(str)  # 再解析リクエスト
    save_transcription_requested = pyqtSignal()  # 🆕 保存リクエスト
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 状態管理
        self.is_wav_loaded = False
        self.is_playing = False
        self.is_paused = False
        self.current_file_path = ""
        self.duration = 0.0
        self.current_position = 0.0
        self.transcribed_text = ""  # 🆕
        self.transcription_segments = []  # 🆕 タイムスタンプ付きセグメント
        self._typing_timer = QTimer()
        self._typing_timer.timeout.connect(self._on_typing_timer)
        self._typing_text = ""
        self._typing_index = 0
        
        self.init_ui()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # ========================================
        # 1. ファイル選択エリア
        # ========================================
        file_group = QGroupBox("🎵 WAVファイル")
        file_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a90e2;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        file_layout = QVBoxLayout()
        
        # ファイル選択ボタン
        select_layout = QHBoxLayout()
        self.select_file_btn = QPushButton("📁 WAVファイルを選択")
        self.select_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2868a8;
            }
        """)
        self.select_file_btn.clicked.connect(self.select_wav_file)
        select_layout.addWidget(self.select_file_btn)
        select_layout.addStretch()
        
        # ファイル情報表示
        self.file_info_label = QLabel("ファイル未選択")
        self.file_info_label.setStyleSheet("color: #666; font-size: 11px;")
        self.file_info_label.setWordWrap(True)
        
        file_layout.addLayout(select_layout)
        file_layout.addWidget(self.file_info_label)
        file_group.setLayout(file_layout)
        
        # ========================================
        # 2. 再生制御エリア
        # ========================================
        control_group = QGroupBox("🎮 再生制御")
        control_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a90e2;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        control_layout = QVBoxLayout()
        
        # 再生ボタン群
        button_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("▶️ 再生")
        self.play_btn.setEnabled(False)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #218838;
            }
            QPushButton:pressed:enabled {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #d0d0d0;
                color: #888;
            }
        """)
        self.play_btn.clicked.connect(self.toggle_play_pause)
        
        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #c82333;
            }
            QPushButton:pressed:enabled {
                background-color: #bd2130;
            }
            QPushButton:disabled {
                background-color: #d0d0d0;
                color: #888;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_playback)
        
        button_layout.addWidget(self.play_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addStretch()
        
        # 時間表示
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #333;")
        time_separator = QLabel("/")
        time_separator.setStyleSheet("color: #999;")
        self.total_time_label = QLabel("00:00")
        self.total_time_label.setStyleSheet("font-size: 12px; color: #666;")
        
        time_layout.addWidget(self.current_time_label)
        time_layout.addWidget(time_separator)
        time_layout.addWidget(self.total_time_label)
        time_layout.addStretch()
        
        # シークバー
        seek_layout = QVBoxLayout()
        seek_label = QLabel("再生位置")
        seek_label.setStyleSheet("color: #666; font-size: 11px;")
        
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        self.seek_slider.setEnabled(False)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #4a90e2;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #fff;
                border: 2px solid #4a90e2;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #e6f2ff;
            }
        """)
        self.seek_slider.sliderPressed.connect(self.on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self.on_seek_released)
        self.seek_slider.valueChanged.connect(self.on_seek_changed)
        
        seek_layout.addWidget(seek_label)
        seek_layout.addWidget(self.seek_slider)
        
        control_layout.addLayout(button_layout)
        control_layout.addLayout(time_layout)
        control_layout.addLayout(seek_layout)
        control_group.setLayout(control_layout)
        
        # ========================================
        # 3. 音量・オプション
        # ========================================
        options_group = QGroupBox("⚙️ オプション")
        options_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a90e2;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        options_layout = QVBoxLayout()
        
        # 音量調整
        volume_layout = QVBoxLayout()
        volume_header = QHBoxLayout()
        volume_label = QLabel("音量")
        volume_label.setStyleSheet("color: #666; font-size: 11px;")
        self.volume_value_label = QLabel("100%")
        self.volume_value_label.setStyleSheet("color: #4a90e2; font-size: 11px; font-weight: bold;")
        volume_header.addWidget(volume_label)
        volume_header.addStretch()
        volume_header.addWidget(self.volume_value_label)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 200)
        self.volume_slider.setValue(100)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #28a745;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #fff;
                border: 2px solid #28a745;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #e6f9ea;
            }
        """)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        
        volume_layout.addLayout(volume_header)
        volume_layout.addWidget(self.volume_slider)
        
        # リップシンク連動
        self.lipsync_checkbox = QCheckBox("💋 リップシンク連動")
        self.lipsync_checkbox.setChecked(True)
        self.lipsync_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 12px;
                font-weight: bold;
                color: #333;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        self.lipsync_checkbox.stateChanged.connect(self.on_lipsync_changed)
        
        options_layout.addLayout(volume_layout)
        options_layout.addWidget(self.lipsync_checkbox)
        options_group.setLayout(options_layout)
        
        # ========================================
        # 🆕 4. 文字起こしエリア
        # ========================================
        transcription_group = QGroupBox("📝 文字起こし")
        transcription_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ff6b6b;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #ff6b6b;
            }
        """)
        transcription_layout = QVBoxLayout()
        
        # ステータス表示
        status_layout = QHBoxLayout()
        self.transcription_status_label = QLabel("待機中...")
        self.transcription_status_label.setStyleSheet("color: #999; font-size: 11px;")
        status_layout.addWidget(self.transcription_status_label)
        status_layout.addStretch()
        
        # 進捗バー
        self.transcription_progress = QProgressBar()
        self.transcription_progress.setRange(0, 100)
        self.transcription_progress.setValue(0)
        self.transcription_progress.setVisible(False)
        self.transcription_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #ff6b6b;
                border-radius: 2px;
            }
        """)
        
        # テキスト表示エリア
        text_label = QLabel("認識されたテキスト（編集可能）:")
        text_label.setStyleSheet("color: #666; font-size: 11px; margin-top: 5px;")
        
        self.transcription_text_edit = QPlainTextEdit()
        self.transcription_text_edit.setPlaceholderText("WAVファイル読み込み後、自動的に文字起こしが開始されます...")
        self.transcription_text_edit.setMaximumHeight(120)
        self.transcription_text_edit.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
                background-color: #fafafa;
            }
            QPlainTextEdit:focus {
                border: 2px solid #ff6b6b;
                background-color: white;
            }
        """)
        self.transcription_text_edit.textChanged.connect(self.on_transcription_text_changed)
        
        # 再解析＆保存ボタン
        button_layout = QHBoxLayout()
        
        self.reanalyze_btn = QPushButton("🔄 再解析してリップシンク更新")
        self.reanalyze_btn.setEnabled(False)
        self.reanalyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #ee5a52;
            }
            QPushButton:pressed:enabled {
                background-color: #dc4a3d;
            }
            QPushButton:disabled {
                background-color: #d0d0d0;
                color: #888;
            }
        """)
        self.reanalyze_btn.clicked.connect(self.on_reanalyze_clicked)
        
        # 🆕 保存ボタン
        self.save_transcription_btn = QPushButton("💾 タイムスタンプ付きで保存")
        self.save_transcription_btn.setEnabled(False)
        self.save_transcription_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #218838;
            }
            QPushButton:pressed:enabled {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #d0d0d0;
                color: #888;
            }
        """)
        self.save_transcription_btn.clicked.connect(self.on_save_transcription_clicked)
        
        button_layout.addWidget(self.reanalyze_btn)
        button_layout.addWidget(self.save_transcription_btn)  # 🆕
        button_layout.addStretch()
        
        transcription_layout.addLayout(status_layout)
        transcription_layout.addWidget(self.transcription_progress)
        transcription_layout.addWidget(text_label)
        transcription_layout.addWidget(self.transcription_text_edit)
        transcription_layout.addLayout(button_layout)  # 🆕 reanalyze_layout → button_layout
        transcription_group.setLayout(transcription_layout)
        
        # レイアウト組み立て
        layout.addWidget(file_group)
        layout.addWidget(control_group)
        layout.addWidget(options_group)
        layout.addWidget(transcription_group)  # 🆕
        layout.addStretch()
        
        # 内部状態
        self._seek_dragging = False
    
    # ========================================
    # 🆕 文字起こし関連メソッド
    # ========================================
    
    def set_transcription_status(self, status: str, is_processing: bool = False):
        """文字起こしステータスを設定"""
        self.transcription_status_label.setText(status)
        self.transcription_progress.setVisible(is_processing)
        
        if is_processing:
            # 不確定プログレスバー（処理中アニメーション）
            self.transcription_progress.setRange(0, 0)
        else:
            self.transcription_progress.setRange(0, 100)
            self.transcription_progress.setValue(100 if "完了" in status else 0)
    
    def set_transcription_text(self, text: str, segments: list = None, animated: bool = True):
        """文字起こし結果をセット
        
        Args:
            text: 全文テキスト
            segments: タイムスタンプ付きセグメントリスト（オプション）
            animated: タイピングアニメーション有効/無効
        """
        self.transcribed_text = text
        self.transcription_segments = segments or []
        
        if animated and text:
            # タイピングアニメーションで表示
            self._start_typing_animation(text)
        else:
            # 一気に表示
            self.transcription_text_edit.blockSignals(True)
            self.transcription_text_edit.setPlainText(text)
            self.transcription_text_edit.blockSignals(False)
        
        # ボタンを有効化
        self.reanalyze_btn.setEnabled(True)
        self.save_transcription_btn.setEnabled(len(self.transcription_segments) > 0)

    def _start_typing_animation(self, text: str):
        """タイピングアニメーション開始"""
        self._typing_timer.stop()
        
        self.transcription_text_edit.blockSignals(True)
        self.transcription_text_edit.clear()
        self.transcription_text_edit.blockSignals(False)
        
        self._typing_text = text
        self._typing_index = 0
        self._typing_timer.start(30)

    def _on_typing_timer(self):
        """タイピングアニメーションのタイマー処理"""
        if self._typing_index < len(self._typing_text):
            current_text = self._typing_text[:self._typing_index + 1]
            
            self.transcription_text_edit.blockSignals(True)
            self.transcription_text_edit.setPlainText(current_text)
            
            cursor = self.transcription_text_edit.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.transcription_text_edit.setTextCursor(cursor)
            
            self.transcription_text_edit.blockSignals(False)
            self._typing_index += 1
        else:
            self._typing_timer.stop()
    
    def get_transcription_text(self) -> str:
        """現在の文字起こしテキストを取得"""
        return self.transcription_text_edit.toPlainText().strip()
    
    def on_transcription_text_changed(self):
        """テキスト編集時"""
        current_text = self.transcription_text_edit.toPlainText()
        if current_text != self.transcribed_text:
            self.transcription_text_edited.emit(current_text)
    
    def on_reanalyze_clicked(self):
        """再解析ボタンクリック"""
        edited_text = self.get_transcription_text()
        if not edited_text:
            QMessageBox.warning(self, "警告", "テキストが空です")
            return
        
        self.re_analyze_requested.emit(edited_text)
        print(f"🔄 再解析リクエスト: {edited_text[:50]}...")
    
    def on_save_transcription_clicked(self):
        """💾 保存ボタンクリック"""
        if not self.transcription_segments:
            QMessageBox.warning(self, "警告", "保存するデータがありません")
            return
        
        self.save_transcription_requested.emit()
        print("💾 文字起こし保存リクエスト")
    
    # ========================================
    # 既存メソッド（元のまま）
    # ========================================
    
    def select_wav_file(self):
        """WAVファイル選択ダイアログ"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "WAVファイルを選択",
            str(Path.home()),
            "WAVファイル (*.wav)"
        )
        
        if file_path:
            self.load_wav_file(file_path)
    
    def load_wav_file(self, file_path: str):
        """WAVファイルを読み込み（外部から呼ばれる）"""
        try:
            path = Path(file_path)
            if not path.exists():
                QMessageBox.warning(self, "エラー", f"ファイルが見つかりません:\n{file_path}")
                return
            
            self.current_file_path = file_path
            self.is_wav_loaded = True
            
            # UIを有効化
            self.play_btn.setEnabled(True)
            self.seek_slider.setEnabled(True)
            
            # ファイル情報を更新（後で外部から設定される）
            self.file_info_label.setText(f"📁 {path.name}\n読み込み完了")
            
            # 🆕 文字起こしステータスをリセット
            self.set_transcription_status("🎤 文字起こし処理中...", is_processing=True)
            self.transcription_text_edit.clear()
            self.reanalyze_btn.setEnabled(False)
            
            # シグナル発火
            self.wav_loaded.emit(file_path)
            
            print(f"✅ WAVファイル選択: {path.name}")
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"ファイル読み込みエラー:\n{str(e)}")
            print(f"❌ WAVファイル読み込みエラー: {e}")
    
    def set_duration(self, duration: float):
        """総再生時間を設定"""
        self.duration = duration
        self.total_time_label.setText(self._format_time(duration))
        
        # ファイル情報更新
        if self.current_file_path:
            path = Path(self.current_file_path)
            self.file_info_label.setText(
                f"📁 {path.name}\n"
                f"⏱️ 長さ: {self._format_time(duration)}"
            )
    
    def toggle_play_pause(self):
        """再生/一時停止トグル"""
        if not self.is_wav_loaded:
            return
        
        if self.is_playing:
            # 一時停止
            self.is_playing = False
            self.is_paused = True
            self.play_btn.setText("▶️ 再生")
            self.stop_btn.setEnabled(True)
            self.playback_paused.emit()
            print("⏸️ 一時停止")
        else:
            # 再生開始
            self.is_playing = True
            self.is_paused = False
            self.play_btn.setText("⏸️ 一時停止")
            self.stop_btn.setEnabled(True)
            
            start_pos = self.current_position if self.is_paused else 0.0
            self.playback_started.emit(start_pos)
            print(f"▶️ 再生開始: {start_pos:.2f}秒から")
    
    def stop_playback(self):
        """再生停止"""
        if not self.is_wav_loaded:
            return
        
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0.0
        
        self.play_btn.setText("▶️ 再生")
        self.stop_btn.setEnabled(False)
        self.seek_slider.setValue(0)
        self.current_time_label.setText("00:00")
        
        self.playback_stopped.emit()
        print("⏹️ 停止")
    
    def update_position(self, position: float):
        """再生位置を更新（外部から呼ばれる）"""
        self.current_position = position
        
        # シークバー更新（ドラッグ中は更新しない）
        if not self._seek_dragging and self.duration > 0:
            slider_value = int((position / self.duration) * 1000)
            self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(slider_value)
            self.seek_slider.blockSignals(False)
        
        # 時間表示更新
        self.current_time_label.setText(self._format_time(position))
    
    def on_seek_pressed(self):
        """シークバードラッグ開始"""
        self._seek_dragging = True
    
    def on_seek_released(self):
        """シークバードラッグ終了"""
        self._seek_dragging = False
        
        if self.duration > 0:
            new_position = (self.seek_slider.value() / 1000.0) * self.duration
            self.position_changed.emit(new_position)
            print(f"🎯 シーク: {new_position:.2f}秒")
    
    def on_seek_changed(self, value):
        """シークバー値変更"""
        if self._seek_dragging and self.duration > 0:
            new_position = (value / 1000.0) * self.duration
            self.current_time_label.setText(self._format_time(new_position))
    
    def on_volume_changed(self, value):
        """音量変更"""
        volume_percent = value
        self.volume_value_label.setText(f"{volume_percent}%")
        
        volume_float = value / 100.0
        self.volume_changed.emit(volume_float)
    
    def on_lipsync_changed(self, state):
        """リップシンク連動切り替え"""
        enabled = (state == Qt.CheckState.Checked.value)
        self.lipsync_enabled_changed.emit(enabled)
        print(f"💋 リップシンク連動: {'有効' if enabled else '無効'}")
    
    def on_playback_finished(self):
        """再生終了時（外部から呼ばれる）"""
        self.stop_playback()
        print("✅ 再生完了")
    
    def _format_time(self, seconds: float) -> str:
        """秒数を mm:ss 形式に変換"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def is_lipsync_enabled(self) -> bool:
        """リップシンク連動が有効か"""
        return self.lipsync_checkbox.isChecked()
    
    def get_current_file_path(self) -> str:
        """現在のファイルパスを取得"""
        return self.current_file_path