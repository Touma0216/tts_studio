from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QGroupBox, QTabWidget, QFileDialog,
                             QListWidget, QListWidgetItem, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from pathlib import Path


class VideoRecordingItem(QWidget):
    """録画済み動画アイテム"""
    save_clicked = pyqtSignal(str)  # file_path
    delete_clicked = pyqtSignal(str)  # file_path
    
    def __init__(self, file_path: str, file_size: int, duration: float, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_size = file_size
        self.duration = duration
        
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # ファイル情報
        file_name = Path(self.file_path).name
        size_mb = self.file_size / (1024 * 1024)
        minutes = int(self.duration // 60)
        seconds = int(self.duration % 60)
        
        info_label = QLabel(f"{file_name}\n{size_mb:.1f}MB  {minutes:02d}:{seconds:02d}")
        info_label.setStyleSheet("color: #333; font-size: 11px; border: none;")
        
        # 保存ボタン
        save_btn = QPushButton("💾 保存")
        save_btn.setFixedSize(70, 30)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:pressed { background-color: #3d8b40; }
        """)
        save_btn.clicked.connect(lambda: self.save_clicked.emit(self.file_path))
        
        # 削除ボタン
        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedSize(30, 30)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #da190b; }
            QPushButton:pressed { background-color: #c41808; }
        """)
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.file_path))
        
        layout.addWidget(info_label, 1)
        layout.addWidget(save_btn)
        layout.addWidget(delete_btn)


class RecordingTab(QWidget):
    """録画タブ"""
    start_recording = pyqtSignal()
    stop_recording = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.recording_time = 0
        self.is_recording = False
        
        self.init_ui()
        
        # タイマー
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_recording_time)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 録画時間表示
        time_group = QGroupBox("⏱️ 録画時間")
        time_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                background-color: white;
                color: #2196F3;
            }
        """)
        
        time_layout = QVBoxLayout(time_group)
        
        self.time_label = QLabel("00:00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setFont(QFont("", 32, QFont.Weight.Bold))
        self.time_label.setStyleSheet("color: #333; border: none;")
        
        time_layout.addWidget(self.time_label)
        
        # 録画ボタン
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.record_btn = QPushButton("🔴 録画開始")
        self.record_btn.setMinimumHeight(50)
        self.record_btn.setMinimumWidth(150)
        self.record_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e53935, stop:1 #c62828);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ef5350, stop:1 #e53935);
            }
            QPushButton:pressed { background: #b71c1c; }
        """)
        self.record_btn.clicked.connect(self.on_record_btn_clicked)
        
        button_layout.addWidget(self.record_btn)
        button_layout.addStretch()
        
        # レイアウト組み立て
        layout.addWidget(time_group)
        layout.addLayout(button_layout)
        layout.addStretch()
    
    def on_record_btn_clicked(self):
        if not self.is_recording:
            self.start_recording_ui()
        else:
            self.stop_recording_ui()
    
    def start_recording_ui(self):
        self.is_recording = True
        self.recording_time = 0
        self.time_label.setText("00:00:00")
        self.timer.start(1000)  # 1秒ごと
        
        self.record_btn.setText("⏹️ 停止")
        self.record_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #757575, stop:1 #616161);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9e9e9e, stop:1 #757575);
            }
            QPushButton:pressed { background: #424242; }
        """)
        
        self.start_recording.emit()
    
    def stop_recording_ui(self):
        self.is_recording = False
        self.timer.stop()
        
        self.record_btn.setText("🔴 録画開始")
        self.record_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e53935, stop:1 #c62828);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ef5350, stop:1 #e53935);
            }
            QPushButton:pressed { background: #b71c1c; }
        """)
        
        self.stop_recording.emit()
    
    def update_recording_time(self):
        self.recording_time += 1
        hours = self.recording_time // 3600
        minutes = (self.recording_time % 3600) // 60
        seconds = self.recording_time % 60
        self.time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")


class CaptureTab(QWidget):
    """撮影タブ（今後実装）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        placeholder = QLabel("📸 TTS単発撮影機能は今後実装予定です...")
        placeholder.setStyleSheet("color: #999; font-size: 14px; font-style: italic;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()
        layout.addWidget(placeholder)
        layout.addStretch()


class TabbedVideoExportControl(QWidget):
    """動画書き出し制御タブ"""
    
    export_settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.output_folder = str(Path.home() / "Videos" / "TTS_Studio")
        self.recorded_videos = []  # [(file_path, size, duration), ...]
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # サブタブ（一番上に移動）
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QTabBar::tab {
                background: #e9ecef;
                border: 1px solid #ccc;
                padding: 8px 16px;
                margin-right: 2px;
                font-size: 12px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #fff;
                border-bottom-color: #fff;
            }
        """)
        
        self.recording_tab = RecordingTab()
        self.recording_tab.start_recording.connect(self.on_start_recording)
        self.recording_tab.stop_recording.connect(self.on_stop_recording)
        
        self.capture_tab = CaptureTab()
        
        self.sub_tabs.addTab(self.recording_tab, "📹 録画")
        self.sub_tabs.addTab(self.capture_tab, "📸 撮影")
        
        # 録画済み動画リスト
        videos_group = self.create_videos_group()
        
        # 録画設定（共通エリア）
        settings_group = self.create_settings_group()
        
        # 録画済み動画リスト
        videos_group = self.create_videos_group()
        
        # レイアウト組み立て（サブタブを最上部に）
        layout.addWidget(self.sub_tabs)
        layout.addWidget(settings_group)
        layout.addWidget(videos_group)
    
    def create_settings_group(self):
        group = QGroupBox("📹 録画設定")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 8px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(5)
        
        # 解像度
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("解像度:"))
        self.resolution_label = QLabel("1920x1080 (自動)")
        self.resolution_label.setStyleSheet("color: #666; font-weight: normal;")
        resolution_layout.addWidget(self.resolution_label)
        resolution_layout.addStretch()
        
        # FPS
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("FPS:"))
        fps_label = QLabel("60fps")
        fps_label.setStyleSheet("color: #666; font-weight: normal;")
        fps_layout.addWidget(fps_label)
        fps_layout.addStretch()
        
        # 形式
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("形式:"))
        format_label = QLabel("HEVC (NVENC)")
        format_label.setStyleSheet("color: #666; font-weight: normal;")
        format_layout.addWidget(format_label)
        format_layout.addStretch()
        
        # 保存先
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("保存先:"))
        
        folder_btn = QPushButton("📁 フォルダ選択...")
        folder_btn.setFixedHeight(25)
        folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 11px;
                padding: 4px 8px;
            }
            QPushButton:hover { background-color: #e0e0e0; }
        """)
        folder_btn.clicked.connect(self.select_output_folder)
        folder_layout.addWidget(folder_btn)
        
        self.folder_label = QLabel(self.output_folder)
        self.folder_label.setStyleSheet("color: #666; font-size: 10px; font-weight: normal;")
        self.folder_label.setWordWrap(True)
        
        layout.addLayout(resolution_layout)
        layout.addLayout(fps_layout)
        layout.addLayout(format_layout)
        layout.addLayout(folder_layout)
        layout.addWidget(self.folder_label)
        
        return group
    
    def create_videos_group(self):
        group = QGroupBox("📦 録画済み動画（最大3件）")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 8px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout(group)
        
        # リストウィジェット
        self.videos_list = QListWidget()
        self.videos_list.setMaximumHeight(150)
        self.videos_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #fafafa;
            }
            QListWidget::item {
                border-bottom: 1px solid #eee;
                padding: 5px;
            }
        """)
        
        layout.addWidget(self.videos_list)
        
        # 空き状態表示
        self.update_videos_list()
        
        return group
    
    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, 
            "保存先フォルダを選択", 
            self.output_folder
        )
        if folder:
            self.output_folder = folder
            self.folder_label.setText(folder)
    
    def on_start_recording(self):
        print("🔴 録画開始")
        # TODO: 実際の録画処理を呼び出す
    
    def on_stop_recording(self):
        print("⏹️ 録画停止")
        # TODO: 録画停止＆ファイル保存
        
        # テスト用：ダミー動画を追加
        import time
        dummy_path = f"temp_recording_{int(time.time())}.mkv"
        self.add_recorded_video(dummy_path, 1024 * 1024 * 500, 150)  # 500MB, 2分30秒
    
    def add_recorded_video(self, file_path: str, file_size: int, duration: float):
        if len(self.recorded_videos) >= 3:
            QMessageBox.warning(self, "警告", "録画済み動画は最大3件までです。\n古い動画を削除してください。")
            return
        
        self.recorded_videos.append((file_path, file_size, duration))
        self.update_videos_list()
    
    def update_videos_list(self):
        self.videos_list.clear()
        
        if not self.recorded_videos:
            item = QListWidgetItem("（録画済み動画がありません）")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(Qt.GlobalColor.gray)
            self.videos_list.addItem(item)
            return
        
        for file_path, file_size, duration in self.recorded_videos:
            item = QListWidgetItem()
            self.videos_list.addItem(item)
            
            video_widget = VideoRecordingItem(file_path, file_size, duration)
            video_widget.save_clicked.connect(self.on_save_video)
            video_widget.delete_clicked.connect(self.on_delete_video)
            
            item.setSizeHint(video_widget.sizeHint())
            self.videos_list.setItemWidget(item, video_widget)
    
    def on_save_video(self, file_path: str):
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "動画を保存",
            str(Path(self.output_folder) / Path(file_path).name),
            "MKV動画 (*.mkv);;すべてのファイル (*)"
        )
        
        if save_path:
            print(f"💾 保存: {file_path} → {save_path}")
            # TODO: 実際のファイルコピー＆ProRes変換
            QMessageBox.information(self, "保存完了", f"動画を保存しました:\n{save_path}")
    
    def on_delete_video(self, file_path: str):
        self.recorded_videos = [(p, s, d) for p, s, d in self.recorded_videos if p != file_path]
        self.update_videos_list()
        print(f"🗑️ 削除: {file_path}")
        # TODO: 実際のファイル削除