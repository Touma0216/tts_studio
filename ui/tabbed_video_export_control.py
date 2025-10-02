from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class TabbedVideoExportControl(QWidget):
    """動画書き出し制御タブ"""
    
    # 将来的に必要になるシグナル（今は使わない）
    export_settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # タイトル
        title = QLabel("🎬 動画書き出し")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # プレースホルダー
        placeholder = QLabel("動画書き出し機能は実装中です...")
        placeholder.setStyleSheet("color: #999; font-size: 12pt;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(placeholder)
        layout.addStretch()