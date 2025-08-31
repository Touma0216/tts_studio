from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                            QLabel, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from .tabbed_emotion_control import TabbedEmotionControl
from .audio_cleaner_control import AudioCleanerControl

class TabbedAudioControl(QWidget):
    """音声パラメータ・クリーナータブ統合ウィジェット"""
    
    parameters_changed = pyqtSignal(str, dict)  # row_id, parameters
    cleaner_settings_changed = pyqtSignal(dict)  # cleaner_settings
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # メインタブウィジェット（音声パラメータ vs 音声クリーナー）
        self.main_tab_widget = QTabWidget()
        self.main_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                background-color: white;
                border: 2px solid #4a90e2;
                border-radius: 4px;
                margin-top: 0px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar {
                background-color: transparent;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ccc;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 10px 20px;
                margin-right: 2px;
                margin-bottom: -2px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background-color: #4a90e2;
                color: white;
                border: 2px solid #4a90e2;
                border-bottom: none;
                margin-bottom: -2px;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e6f2ff;
                border-color: #4a90e2;
                color: #4a90e2;
            }
        """)
        
        # 1. 音声パラメータタブ
        self.emotion_control = TabbedEmotionControl()
        self.emotion_control.parameters_changed.connect(self.parameters_changed)
        self.main_tab_widget.addTab(self.emotion_control, "🎭 音声パラメータ")
        
        # 2. 音声クリーナータブ
        self.cleaner_control = AudioCleanerControl()
        self.cleaner_control.settings_changed.connect(self.cleaner_settings_changed)
        self.main_tab_widget.addTab(self.cleaner_control, "🔧 音声クリーナー")
        
        layout.addWidget(self.main_tab_widget)
    
    # ================================
    # 音声パラメータ関連のプロキシメソッド
    # ================================
    
    def add_text_row(self, row_id, row_number, parameters=None):
        """テキスト行に対応するタブを追加"""
        self.emotion_control.add_text_row(row_id, row_number, parameters)
    
    def remove_text_row(self, row_id):
        """テキスト行に対応するタブを削除"""
        self.emotion_control.remove_text_row(row_id)
    
    def update_tab_numbers(self, row_mapping):
        """タブ番号を更新"""
        self.emotion_control.update_tab_numbers(row_mapping)
    
    def get_parameters(self, row_id):
        """指定行のパラメータを取得"""
        return self.emotion_control.get_parameters(row_id)
    
    def get_master_parameters(self):
        """マスターパラメータを取得"""
        return self.emotion_control.get_master_parameters()
    
    def set_current_row(self, row_id):
        """指定行のタブをアクティブに"""
        # 音声パラメータタブを選択してから行を設定
        self.main_tab_widget.setCurrentIndex(0)
        self.emotion_control.set_current_row(row_id)
    
    # ================================
    # 音声クリーナー関連
    # ================================
    
    def get_cleaner_settings(self):
        """クリーナー設定を取得"""
        return self.cleaner_control.get_current_settings()
    
    def is_cleaner_enabled(self):
        """クリーナーが有効かどうか"""
        return self.cleaner_control.is_enabled()