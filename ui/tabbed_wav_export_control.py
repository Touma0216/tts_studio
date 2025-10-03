from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QLineEdit, QSpinBox, QCheckBox,
                            QProgressBar, QTextEdit, QGroupBox, QFileDialog,
                            QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from pathlib import Path

class WavExportControl(QWidget):
    """音声書き出し制御ウィジェット"""
    
    export_requested = pyqtSignal(dict)  # 書き出し設定
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # タイトル
        title = QLabel("📼 音声書き出し")
        title.setFont(QFont("", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #1976d2;")
        layout.addWidget(title)
        
        # 説明
        description = QLabel(
            "複数のテキストを連続でTTS処理して1つのWAVファイルに書き出します。\n"
            "文と文の間に無音は挿入されません（編集は後で手動で行ってください）。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(description)
        
        # === 出力設定グループ ===
        output_group = QGroupBox("出力設定")
        output_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        output_layout = QVBoxLayout()
        
        # 出力ファイル名
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("出力ファイル:"))
        self.output_path_input = QLineEdit()
        self.output_path_input.setPlaceholderText("outputs/continuous.wav")
        self.output_path_input.setText("outputs/continuous.wav")
        file_layout.addWidget(self.output_path_input, 1)
        
        self.browse_btn = QPushButton("📁 参照")
        self.browse_btn.setFixedWidth(80)
        self.browse_btn.clicked.connect(self.browse_output_path)
        file_layout.addWidget(self.browse_btn)
        
        output_layout.addLayout(file_layout)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # === 処理設定グループ ===
        process_group = QGroupBox("処理設定")
        process_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        process_layout = QVBoxLayout()
        
        # チャンクサイズ
        chunk_layout = QHBoxLayout()
        chunk_layout.addWidget(QLabel("チャンクサイズ:"))
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(10, 500)
        self.chunk_size_spin.setValue(100)
        self.chunk_size_spin.setSuffix(" テキスト")
        self.chunk_size_spin.setToolTip(
            "一度に処理するテキスト数（メモリ管理用）\n"
            "RTX 4060 Ti 16GBなら100～200が推奨"
        )
        chunk_layout.addWidget(self.chunk_size_spin)
        chunk_layout.addStretch()
        process_layout.addLayout(chunk_layout)
        
        # レジューム機能
        self.resume_checkbox = QCheckBox("中断から再開する（レジューム機能）")
        self.resume_checkbox.setChecked(True)
        self.resume_checkbox.setToolTip(
            "処理が中断された場合、次回は続きから再開します"
        )
        process_layout.addWidget(self.resume_checkbox)
        
        process_group.setLayout(process_layout)
        layout.addWidget(process_group)
        
        # === 進捗表示 ===
        progress_group = QGroupBox("進捗")
        progress_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        progress_layout = QVBoxLayout()
        
        # 進捗バー
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4caf50;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        # ステータスラベル
        self.status_label = QLabel("準備完了")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        progress_layout.addWidget(self.status_label)
        
        # ログ表示
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
            }
        """)
        progress_layout.addWidget(self.log_text)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # === 実行ボタン ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.export_btn = QPushButton("🎬 書き出し開始")
        self.export_btn.setFixedHeight(40)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover:enabled {
                background-color: #f57c00;
            }
            QPushButton:pressed:enabled {
                background-color: #e65100;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.export_btn.clicked.connect(self.start_export)
        button_layout.addWidget(self.export_btn)
        
        self.cancel_btn = QPushButton("⏹️ キャンセル")
        self.cancel_btn.setFixedHeight(40)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover:enabled {
                background-color: #d32f2f;
            }
            QPushButton:pressed:enabled {
                background-color: #b71c1c;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        layout.addStretch()
    
    def browse_output_path(self):
        """出力ファイルパスを選択"""
        current_path = self.output_path_input.text() or "outputs/continuous.wav"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "書き出し先を選択",
            current_path,
            "WAV Files (*.wav)"
        )
        
        if file_path:
            self.output_path_input.setText(file_path)
    
    def start_export(self):
        """書き出し開始"""
        output_path = self.output_path_input.text().strip()
        
        if not output_path:
            QMessageBox.warning(self, "エラー", "出力ファイル名を指定してください")
            return
        
        # 設定を収集
        settings = {
            'output_path': output_path,
            'chunk_size': self.chunk_size_spin.value(),
            'resume': self.resume_checkbox.isChecked()
        }
        
        # シグナル送信
        self.export_requested.emit(settings)
    
    def set_processing_state(self, is_processing: bool):
        """処理状態を設定"""
        self.export_btn.setEnabled(not is_processing)
        self.cancel_btn.setEnabled(is_processing)
        self.output_path_input.setEnabled(not is_processing)
        self.browse_btn.setEnabled(not is_processing)
        self.chunk_size_spin.setEnabled(not is_processing)
        self.resume_checkbox.setEnabled(not is_processing)
        
        if is_processing:
            self.status_label.setText("🎵 処理中...")
        else:
            self.status_label.setText("準備完了")
    
    def update_progress(self, current: int, total: int):
        """進捗を更新"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.status_label.setText(f"処理中: {current}/{total} ({percentage}%)")
    
    def add_log(self, message: str):
        """ログを追加"""
        self.log_text.append(message)
        # 自動スクロール
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """ログをクリア"""
        self.log_text.clear()
    
    def reset_progress(self):
        """進捗をリセット"""
        self.progress_bar.setValue(0)
        self.status_label.setText("準備完了")
    
    def get_settings(self) -> dict:
        """現在の設定を取得"""
        return {
            'output_path': self.output_path_input.text().strip(),
            'chunk_size': self.chunk_size_spin.value(),
            'resume': self.resume_checkbox.isChecked()
        }