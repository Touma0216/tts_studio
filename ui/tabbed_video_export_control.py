# ui/tabbed_video_export_control.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QCheckBox, QSpinBox, QComboBox, QLineEdit,
                             QPushButton, QProgressBar, QLabel, QFileDialog,
                             QScrollArea, QFrame, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from pathlib import Path
from typing import Optional, List


class TabbedVideoExportControl(QWidget):
    """動画書き出しタブUI"""
    
    # シグナル定義
    auto_save_toggled = pyqtSignal(bool)
    capture_requested = pyqtSignal(int)  # キャプチャ時間（秒）
    video_deleted = pyqtSignal(str)  # 動画ファイルパス
    all_videos_deleted = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.saved_videos: List[str] = []  # 保存済み動画リスト（最大3本）
        self.is_capturing = False
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # スクロールエリア
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: white; }")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(15)
        
        # ヘッダー
        header = QLabel("📹 動画書き出し設定")
        header.setFont(QFont("", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #333; padding: 5px 0;")
        content_layout.addWidget(header)
        
        # ━━━━━━━━━━━━━━━━━━━━
        # 形式設定グループ
        # ━━━━━━━━━━━━━━━━━━━━
        format_group = QGroupBox("形式設定")
        format_group.setStyleSheet(self._group_style())
        format_layout = QVBoxLayout(format_group)
        format_layout.setSpacing(12)
        
        # リップシンク起動時に自動保存
        self.auto_save_checkbox = QCheckBox("リップシンク起動時に自動保存")
        self.auto_save_checkbox.setFont(QFont("", 11, QFont.Weight.Bold))
        self.auto_save_checkbox.setChecked(False)
        self.auto_save_checkbox.toggled.connect(self.on_auto_save_toggled)
        format_layout.addWidget(self.auto_save_checkbox)
        
        # 区切り線
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #ddd;")
        format_layout.addWidget(line)
        
        # 手動キャプチャモード
        capture_label = QLabel("📹 手動キャプチャモード")
        capture_label.setFont(QFont("", 11, QFont.Weight.Bold))
        capture_label.setStyleSheet("color: #e91e63; padding-top: 5px;")
        format_layout.addWidget(capture_label)
        
        # キャプチャ時間設定
        capture_time_layout = QHBoxLayout()
        capture_time_label = QLabel("キャプチャ時間:")
        capture_time_label.setMinimumWidth(120)
        
        self.capture_duration_spinbox = QSpinBox()
        self.capture_duration_spinbox.setRange(1, 60)
        self.capture_duration_spinbox.setValue(5)
        self.capture_duration_spinbox.setSuffix(" 秒")
        self.capture_duration_spinbox.setFixedWidth(100)
        
        capture_time_layout.addWidget(capture_time_label)
        capture_time_layout.addWidget(self.capture_duration_spinbox)
        capture_time_layout.addStretch()
        format_layout.addLayout(capture_time_layout)
        
        # 説明テキスト
        info_label = QLabel("※ この間にモデルを自由に動かせるよ。TTS実行すれば音声も含まれるよ")
        info_label.setStyleSheet("color: #666; font-size: 10pt; font-style: italic;")
        info_label.setWordWrap(True)
        format_layout.addWidget(info_label)
        
        content_layout.addWidget(format_group)
        
        # ━━━━━━━━━━━━━━━━━━━━
        # 書き出し設定グループ
        # ━━━━━━━━━━━━━━━━━━━━
        export_group = QGroupBox("書き出し設定")
        export_group.setStyleSheet(self._group_style())
        export_layout = QVBoxLayout(export_group)
        export_layout.setSpacing(12)
        
        # 出力形式
        format_layout_h = QHBoxLayout()
        format_label = QLabel("出力形式:")
        format_label.setMinimumWidth(120)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "MOV (ProRes 4444)",
            "MP4 (H.264)",
            "WebM (VP9)"
        ])
        self.format_combo.setFixedWidth(200)
        
        format_layout_h.addWidget(format_label)
        format_layout_h.addWidget(self.format_combo)
        format_layout_h.addStretch()
        export_layout.addLayout(format_layout_h)
        
        # フレームレート
        fps_layout = QHBoxLayout()
        fps_label = QLabel("フレームレート:")
        fps_label.setMinimumWidth(120)
        
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["60fps", "30fps"])
        self.fps_combo.setFixedWidth(200)
        
        fps_layout.addWidget(fps_label)
        fps_layout.addWidget(self.fps_combo)
        fps_layout.addStretch()
        export_layout.addLayout(fps_layout)
        
        # 出力先
        output_layout = QHBoxLayout()
        output_label = QLabel("出力先:")
        output_label.setMinimumWidth(120)
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("出力先を選択してください")
        self.output_path_edit.setReadOnly(True)
        
        self.browse_btn = QPushButton("📁 参照")
        self.browse_btn.setFixedWidth(80)
        self.browse_btn.clicked.connect(self.browse_output_path)
        
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_path_edit, 1)
        output_layout.addWidget(self.browse_btn)
        export_layout.addLayout(output_layout)
        
        content_layout.addWidget(export_group)
        
        # ━━━━━━━━━━━━━━━━━━━━
        # 進行状況グループ
        # ━━━━━━━━━━━━━━━━━━━━
        progress_group = QGroupBox("進行状況")
        progress_group.setStyleSheet(self._group_style())
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #4a90e2;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a90e2, stop:1 #2ecc71);
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        content_layout.addWidget(progress_group)
        
        # ━━━━━━━━━━━━━━━━━━━━
        # 動画保存グループ（最大3本）
        # ━━━━━━━━━━━━━━━━━━━━
        saved_group = QGroupBox("動画保存（最大3本）")
        saved_group.setStyleSheet(self._group_style())
        saved_layout = QVBoxLayout(saved_group)
        saved_layout.setSpacing(8)
        
        # 動画リスト表示エリア
        self.video_list_layout = QVBoxLayout()
        self.video_list_layout.setSpacing(5)
        saved_layout.addLayout(self.video_list_layout)
        
        # 初期状態：空のメッセージ
        self.empty_label = QLabel("保存された動画はありません")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #999; font-style: italic; padding: 20px;")
        self.video_list_layout.addWidget(self.empty_label)
        
        # 全削除ボタン
        self.delete_all_btn = QPushButton("🗑️ 全削除")
        self.delete_all_btn.setEnabled(False)
        self.delete_all_btn.setMinimumHeight(35)
        self.delete_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #aaa;
            }
        """)
        self.delete_all_btn.clicked.connect(self.delete_all_videos)
        saved_layout.addWidget(self.delete_all_btn)
        
        content_layout.addWidget(saved_group)
        content_layout.addStretch()
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)
    
    def _group_style(self) -> str:
        return """
            QGroupBox {
                font-weight: bold;
                font-size: 12pt;
                border: 2px solid #4a90e2;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 18px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                background-color: white;
                color: #4a90e2;
            }
        """
    
    def on_auto_save_toggled(self, checked: bool):
        """自動保存トグル"""
        self.auto_save_toggled.emit(checked)
    
    def browse_output_path(self):
        """出力先フォルダを選択"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "出力先フォルダを選択",
            str(Path.home() / "Videos")
        )
        
        if folder:
            self.output_path_edit.setText(folder)
    
    def get_capture_duration(self) -> int:
        """キャプチャ時間を取得"""
        return self.capture_duration_spinbox.value()
    
    def get_output_format(self) -> str:
        """出力形式を取得"""
        formats = {
            "MOV (ProRes 4444)": "mov",
            "MP4 (H.264)": "mp4",
            "WebM (VP9)": "webm"
        }
        return formats[self.format_combo.currentText()]
    
    def get_fps(self) -> int:
        """フレームレートを取得"""
        return int(self.fps_combo.currentText().replace("fps", ""))
    
    def get_output_path(self) -> Optional[str]:
        """出力先パスを取得"""
        path = self.output_path_edit.text()
        return path if path else None
    
    def is_auto_save_enabled(self) -> bool:
        """自動保存が有効か"""
        return self.auto_save_checkbox.isChecked()
    
    def set_progress(self, value: int):
        """進行状況を更新"""
        self.progress_bar.setValue(value)
    
    def reset_progress(self):
        """進行状況をリセット"""
        self.progress_bar.setValue(0)
    
    def add_saved_video(self, video_path: str):
        """保存済み動画をリストに追加"""
        if len(self.saved_videos) >= 3:
            QMessageBox.warning(
                self,
                "保存上限",
                "動画は最大3本まで保存できます。\n古い動画を削除してから再度保存してください。"
            )
            return
        
        self.saved_videos.append(video_path)
        self.update_video_list()
    
    def update_video_list(self):
        """動画リストUIを更新"""
        # 既存のウィジェットをクリア
        while self.video_list_layout.count():
            child = self.video_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not self.saved_videos:
            # 空の場合
            self.empty_label = QLabel("保存された動画はありません")
            self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_label.setStyleSheet("color: #999; font-style: italic; padding: 20px;")
            self.video_list_layout.addWidget(self.empty_label)
            self.delete_all_btn.setEnabled(False)
        else:
            # 動画がある場合
            for video_path in self.saved_videos:
                video_widget = self.create_video_item(video_path)
                self.video_list_layout.addWidget(video_widget)
            
            self.delete_all_btn.setEnabled(True)
    
    def create_video_item(self, video_path: str) -> QWidget:
        """動画アイテムウィジェットを作成"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # 動画名ラベル
        name_label = QLabel(f"🎬 {Path(video_path).name}")
        name_label.setStyleSheet("""
            QLabel {
                background-color: #f0f8ff;
                border: 1px solid #4a90e2;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
        """)
        
        # 削除ボタン
        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedSize(35, 35)
        delete_btn.setToolTip("この動画を削除")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5252;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #ff1744;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_video(video_path))
        
        layout.addWidget(name_label, 1)
        layout.addWidget(delete_btn)
        
        return widget
    
    def delete_video(self, video_path: str):
        """動画を削除"""
        reply = QMessageBox.question(
            self,
            "動画削除",
            f"この動画を削除しますか?\n\n{Path(video_path).name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.saved_videos.remove(video_path)
            self.update_video_list()
            self.video_deleted.emit(video_path)
    
    def delete_all_videos(self):
        """全動画を削除"""
        if not self.saved_videos:
            return
        
        reply = QMessageBox.question(
            self,
            "全削除",
            f"保存された動画{len(self.saved_videos)}本をすべて削除しますか?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.saved_videos.clear()
            self.update_video_list()
            self.all_videos_deleted.emit()
    
    def set_capturing(self, capturing: bool):
        """キャプチャ中の状態を設定"""
        self.is_capturing = capturing
        self.capture_duration_spinbox.setEnabled(not capturing)
        self.browse_btn.setEnabled(not capturing)
        self.format_combo.setEnabled(not capturing)
        self.fps_combo.setEnabled(not capturing)