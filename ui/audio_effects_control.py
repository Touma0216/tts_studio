# ui/audio_effects_control.py (シンプル版)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTabWidget, QFrame, QSlider, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QBrush, QPen, QColor
from PyQt6.QtCore import QRectF

class ToggleSwitchWidget(QWidget):
    """緑/赤のON/OFFトグルスイッチ"""
    
    toggled = pyqtSignal(bool)
    
    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 30)
        self._checked = checked
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 背景の描画
        bg_rect = QRectF(0, 0, 60, 30)
        if self._checked:
            painter.setBrush(QBrush(QColor(76, 175, 80)))  # 緑
        else:
            painter.setBrush(QBrush(QColor(244, 67, 54)))  # 赤
        
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.drawRoundedRect(bg_rect, 15, 15)
        
        # スイッチの描画
        if self._checked:
            switch_rect = QRectF(32, 3, 24, 24)
        else:
            switch_rect = QRectF(4, 3, 24, 24)
        
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(switch_rect)
        
        # テキストの描画
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("", 8, QFont.Weight.Bold))
        
        if self._checked:
            painter.drawText(8, 20, "ON")
        else:
            painter.drawText(35, 20, "OFF")
    
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
    """音声エフェクト制御ウィジェット"""
    
    effects_settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.default_settings = {
            'echo_enabled': False,
            'echo_intensity': 0.3,
            'reverb_enabled': False,
            'reverb_intensity': 0.5,
            'distortion_enabled': False,
            'distortion_intensity': 0.4
        }
        
        self.init_ui()
        self.connect_signals()
        
    def init_ui(self):
        """UIの初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
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
        
        # 1. 音声エフェクトタブ
        audio_effects_tab = self.create_audio_effects_tab()
        self.effects_tab_widget.addTab(audio_effects_tab, "音声エフェクト")
        
        # 2. 背景エフェクトタブ（空）
        background_effects_tab = self.create_empty_tab()
        self.effects_tab_widget.addTab(background_effects_tab, "背景エフェクト")
        
        layout.addWidget(self.effects_tab_widget)
        
    def create_audio_effects_tab(self):
        """音声エフェクトタブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # エコーエフェクト
        echo_group = QGroupBox("エコー")
        echo_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 5px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: white;
            }
        """)
        echo_layout = QHBoxLayout(echo_group)
        echo_layout.setSpacing(15)
        
        echo_label = QLabel("強度")
        echo_label.setFont(QFont("", 12, QFont.Weight.Bold))
        echo_label.setMinimumWidth(60)
        
        self.echo_slider = QSlider(Qt.Orientation.Horizontal)
        self.echo_slider.setRange(10, 100)
        self.echo_slider.setValue(30)
        self.echo_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #007bff, stop: 1 #4dabf7);
                border: 1px solid #007bff;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #fff, stop: 1 #007bff);
                border: 1px solid #007bff;
                width: 18px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 9px;
            }
        """)
        
        self.echo_toggle = ToggleSwitchWidget(False)
        
        echo_layout.addWidget(echo_label)
        echo_layout.addWidget(self.echo_slider, 1)
        echo_layout.addWidget(self.echo_toggle)
        
        # リバーブエフェクト
        reverb_group = QGroupBox("リバーブ")
        reverb_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 5px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: white;
            }
        """)
        reverb_layout = QHBoxLayout(reverb_group)
        reverb_layout.setSpacing(15)
        
        reverb_label = QLabel("強度")
        reverb_label.setFont(QFont("", 12, QFont.Weight.Bold))
        reverb_label.setMinimumWidth(60)
        
        self.reverb_slider = QSlider(Qt.Orientation.Horizontal)
        self.reverb_slider.setRange(10, 100)
        self.reverb_slider.setValue(50)
        self.reverb_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #28a745, stop: 1 #6fdc6f);
                border: 1px solid #28a745;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #fff, stop: 1 #28a745);
                border: 1px solid #28a745;
                width: 18px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 9px;
            }
        """)
        
        self.reverb_toggle = ToggleSwitchWidget(False)
        
        reverb_layout.addWidget(reverb_label)
        reverb_layout.addWidget(self.reverb_slider, 1)
        reverb_layout.addWidget(self.reverb_toggle)
        
        # ディストーションエフェクト
        distortion_group = QGroupBox("ディストーション")
        distortion_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 5px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: white;
            }
        """)
        distortion_layout = QHBoxLayout(distortion_group)
        distortion_layout.setSpacing(15)
        
        distortion_label = QLabel("強度")
        distortion_label.setFont(QFont("", 12, QFont.Weight.Bold))
        distortion_label.setMinimumWidth(60)
        
        self.distortion_slider = QSlider(Qt.Orientation.Horizontal)
        self.distortion_slider.setRange(10, 100)
        self.distortion_slider.setValue(40)
        self.distortion_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #dc3545, stop: 1 #f1556c);
                border: 1px solid #dc3545;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #fff, stop: 1 #dc3545);
                border: 1px solid #dc3545;
                width: 18px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 9px;
            }
        """)
        
        self.distortion_toggle = ToggleSwitchWidget(False)
        
        distortion_layout.addWidget(distortion_label)
        distortion_layout.addWidget(self.distortion_slider, 1)
        distortion_layout.addWidget(self.distortion_toggle)
        
        # レイアウトに追加
        layout.addWidget(echo_group)
        layout.addWidget(reverb_group)
        layout.addWidget(distortion_group)
        layout.addStretch()
        
        return widget
        
    def create_empty_tab(self):
        """空のタブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addStretch()
        return widget
        
    def connect_signals(self):
        """シグナル接続"""
        # エコー
        self.echo_toggle.toggled.connect(self.emit_settings_changed)
        self.echo_slider.valueChanged.connect(self.emit_settings_changed)
        
        # リバーブ
        self.reverb_toggle.toggled.connect(self.emit_settings_changed)
        self.reverb_slider.valueChanged.connect(self.emit_settings_changed)
        
        # ディストーション
        self.distortion_toggle.toggled.connect(self.emit_settings_changed)
        self.distortion_slider.valueChanged.connect(self.emit_settings_changed)
        
    def emit_settings_changed(self):
        """設定変更シグナルを発信（サイレント）"""
        settings = self.get_current_settings()
        self.effects_settings_changed.emit(settings)
        
    def get_current_settings(self):
        """現在の設定を取得"""
        return {
            'echo_enabled': self.echo_toggle.isChecked(),
            'echo_intensity': self.echo_slider.value() * 0.01,
            'reverb_enabled': self.reverb_toggle.isChecked(),
            'reverb_intensity': self.reverb_slider.value() * 0.01,
            'distortion_enabled': self.distortion_toggle.isChecked(),
            'distortion_intensity': self.distortion_slider.value() * 0.01
        }
        
    def set_settings(self, settings):
        """設定を適用"""
        self.blockSignals(True)
        
        self.echo_toggle.setChecked(settings.get('echo_enabled', False))
        self.echo_slider.setValue(int(settings.get('echo_intensity', 0.3) * 100))
        
        self.reverb_toggle.setChecked(settings.get('reverb_enabled', False))
        self.reverb_slider.setValue(int(settings.get('reverb_intensity', 0.5) * 100))
        
        self.distortion_toggle.setChecked(settings.get('distortion_enabled', False))
        self.distortion_slider.setValue(int(settings.get('distortion_intensity', 0.4) * 100))
        
        self.blockSignals(False)
        
    def is_effects_enabled(self):
        """エフェクトが有効かどうか"""
        return (self.echo_toggle.isChecked() or 
                self.reverb_toggle.isChecked() or 
                self.distortion_toggle.isChecked())