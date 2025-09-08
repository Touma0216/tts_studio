# ui/audio_effects_control.py (修正版)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTabWidget, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QBrush, QPen, QColor
from PyQt6.QtCore import QRectF

class ToggleSwitchWidget(QWidget):
    """緑/赤のON/OFFトグルスイッチ（クリーナーと統一）"""
    
    toggled = pyqtSignal(bool)
    
    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 40)
        self._checked = checked
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 背景の描画
        bg_rect = QRectF(0, 0, 80, 40)
        if self._checked:
            # ONの場合は緑
            painter.setBrush(QBrush(QColor(76, 175, 80)))  # #4caf50
        else:
            # OFFの場合は赤
            painter.setBrush(QBrush(QColor(244, 67, 54)))  # #f44336
        
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.drawRoundedRect(bg_rect, 20, 20)
        
        # スイッチの描画
        if self._checked:
            # 右側（ON時）
            switch_rect = QRectF(45, 5, 30, 30)
        else:
            # 左側（OFF時）
            switch_rect = QRectF(5, 5, 30, 30)
        
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(switch_rect)
        
        # テキストの描画
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("", 9, QFont.Weight.Bold))
        
        if self._checked:
            painter.drawText(12, 25, "ON")
        else:
            painter.drawText(45, 25, "OFF")
    
    def mousePressEvent(self, event):
        self._checked = not self._checked
        self.update()
        self.toggled.emit(self._checked)
    
    def isChecked(self):
        return self._checked
    
    def setChecked(self, checked):
        if self._checked != checked:
            self._checked = checked
            self.update()

class AudioEffectsControl(QWidget):
    """音声エフェクト制御ウィジェット（簡素版）"""
    
    # シグナル定義
    effects_settings_changed = pyqtSignal(dict)  # エフェクト設定変更時
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # デフォルト設定
        self.default_settings = {
            'enabled': False
        }
        
        self.init_ui()
        self.connect_signals()
        
    def init_ui(self):
        """UIの初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 上部区切り線
        top_divider = QFrame()
        top_divider.setFrameShape(QFrame.Shape.HLine)
        top_divider.setFrameShadow(QFrame.Shadow.Sunken)
        top_divider.setStyleSheet("color: #dee2e6;")
        
        # メイン有効/無効スイッチ
        main_enable_layout = QHBoxLayout()
        switch_label = QLabel("音声エフェクトを有効化")
        switch_label.setFont(QFont("", 12, QFont.Weight.Bold))
        
        self.main_toggle_switch = ToggleSwitchWidget(False)
        self.main_toggle_switch.toggled.connect(self.on_main_enabled_changed)
        
        main_enable_layout.addWidget(switch_label)
        main_enable_layout.addStretch()
        main_enable_layout.addWidget(self.main_toggle_switch)
        
        # 下部区切り線
        bottom_divider = QFrame()
        bottom_divider.setFrameShape(QFrame.Shape.HLine)
        bottom_divider.setFrameShadow(QFrame.Shadow.Sunken)
        bottom_divider.setStyleSheet("color: #dee2e6;")
        
        # タブウィジェット（音声エフェクト｜背景エフェクト）
        self.effects_tab_widget = QTabWidget()
        self.effects_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                background-color: white;
                border: 1px solid #ccc;
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
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                margin-right: 2px;
                margin-bottom: -1px;
                font-size: 13px;
                font-weight: bold;
                min-width: 100px;
            }
            QTabBar::tab:selected {
                background-color: #5ba8f2;
                color: white;
                border: 1px solid #5ba8f2;
                border-bottom: none;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e6f2ff;
                border-color: #5ba8f2;
                color: #5ba8f2;
            }
        """)
        
        # 1. 音声エフェクトタブ（空）
        audio_effects_tab = self.create_empty_tab()
        self.effects_tab_widget.addTab(audio_effects_tab, "音声エフェクト")
        
        # 2. 背景エフェクトタブ（空）
        background_effects_tab = self.create_empty_tab()
        self.effects_tab_widget.addTab(background_effects_tab, "背景エフェクト")
        
        # レイアウト構築
        layout.addWidget(top_divider)
        layout.addLayout(main_enable_layout)
        layout.addWidget(bottom_divider)
        layout.addWidget(self.effects_tab_widget)
        
    def create_empty_tab(self):
        """空のタブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addStretch()  # 空のスペース
        return widget
        
    def connect_signals(self):
        """シグナル接続"""
        # メイン有効/無効のみ
        self.main_toggle_switch.toggled.connect(self.on_main_enabled_changed)
        
    def on_main_enabled_changed(self, enabled):
        """メインの有効/無効が変更された時"""
        self.emit_settings_changed()
        
    def emit_settings_changed(self):
        """設定変更シグナルを発信"""
        settings = self.get_current_settings()
        self.effects_settings_changed.emit(settings)
        
    def get_current_settings(self):
        """現在の設定を取得"""
        return {
            'enabled': self.main_toggle_switch.isChecked()
        }
        
    def set_settings(self, settings):
        """設定を適用"""
        # シグナルを一時的に無効化
        self.blockSignals(True)
        
        self.main_toggle_switch.setChecked(settings.get('enabled', False))
        
        # シグナルを再有効化
        self.blockSignals(False)
        
    def is_effects_enabled(self):
        """エフェクトが有効かどうかを返す"""
        return self.main_toggle_switch.isChecked()