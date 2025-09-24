from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QGroupBox, QSlider, QLabel, QCheckBox, QPushButton,
                             QComboBox, QDoubleSpinBox, QSpinBox, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Dict, Any

class BasicLipSyncWidget(QWidget):
    """基本リップシンク設定"""
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = {
            'enabled': True,
            'sensitivity': 80,
            'response_speed': 70,
            'mouth_open_scale': 100,
            'auto_optimize': True
        }
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # リップシンク有効/無効
        enable_group = QGroupBox("リップシンク制御")
        enable_group.setFont(QFont("", 10, QFont.Weight.Bold))
        enable_layout = QVBoxLayout(enable_group)
        
        self.enable_checkbox = QCheckBox("リップシンクを有効にする")
        self.enable_checkbox.setChecked(self.settings['enabled'])
        self.enable_checkbox.setStyleSheet("QCheckBox { font-size: 12px; }")
        self.enable_checkbox.toggled.connect(self.on_settings_changed)
        enable_layout.addWidget(self.enable_checkbox)
        
        # 基本調整
        basic_group = QGroupBox("基本調整")
        basic_group.setFont(QFont("", 10, QFont.Weight.Bold))
        basic_layout = QVBoxLayout(basic_group)
        
        # 感度調整
        sens_layout = QHBoxLayout()
        sens_label = QLabel("反応感度:")
        sens_label.setFixedWidth(100)
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(10, 200)
        self.sensitivity_slider.setValue(self.settings['sensitivity'])
        self.sensitivity_value = QLabel(f"{self.settings['sensitivity']}%")
        self.sensitivity_value.setFixedWidth(50)
        self.sensitivity_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        sens_layout.addWidget(sens_label)
        sens_layout.addWidget(self.sensitivity_slider)
        sens_layout.addWidget(self.sensitivity_value)
        basic_layout.addLayout(sens_layout)
        
        # 反応速度
        speed_layout = QHBoxLayout()
        speed_label = QLabel("反応速度:")
        speed_label.setFixedWidth(100)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 100)
        self.speed_slider.setValue(self.settings['response_speed'])
        self.speed_value = QLabel(f"{self.settings['response_speed']}%")
        self.speed_value.setFixedWidth(50)
        self.speed_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_value)
        basic_layout.addLayout(speed_layout)
        
        # 口の開き調整
        mouth_layout = QHBoxLayout()
        mouth_label = QLabel("口の開き:")
        mouth_label.setFixedWidth(100)
        self.mouth_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.mouth_scale_slider.setRange(50, 200)
        self.mouth_scale_slider.setValue(self.settings['mouth_open_scale'])
        self.mouth_scale_value = QLabel(f"{self.settings['mouth_open_scale']}%")
        self.mouth_scale_value.setFixedWidth(50)
        self.mouth_scale_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        mouth_layout.addWidget(mouth_label)
        mouth_layout.addWidget(self.mouth_scale_slider)
        mouth_layout.addWidget(self.mouth_scale_value)
        basic_layout.addLayout(mouth_layout)
        
        # 自動最適化
        self.auto_optimize_checkbox = QCheckBox("TTSに合わせて自動最適化")
        self.auto_optimize_checkbox.setChecked(self.settings['auto_optimize'])
        self.auto_optimize_checkbox.setStyleSheet("QCheckBox { font-size: 11px; color: #666; }")
        self.auto_optimize_checkbox.toggled.connect(self.on_settings_changed)
        basic_layout.addWidget(self.auto_optimize_checkbox)
        
        # レイアウト組み立て
        layout.addWidget(enable_group)
        layout.addWidget(basic_group)
        layout.addStretch()
        
        # シグナル接続
        self.sensitivity_slider.valueChanged.connect(self.update_sensitivity_value)
        self.speed_slider.valueChanged.connect(self.update_speed_value)
        self.mouth_scale_slider.valueChanged.connect(self.update_mouth_scale_value)
        
        self.sensitivity_slider.valueChanged.connect(self.on_settings_changed)
        self.speed_slider.valueChanged.connect(self.on_settings_changed)
        self.mouth_scale_slider.valueChanged.connect(self.on_settings_changed)
        
    def update_sensitivity_value(self, value):
        self.sensitivity_value.setText(f"{value}%")
        
    def update_speed_value(self, value):
        self.speed_value.setText(f"{value}%")
        
    def update_mouth_scale_value(self, value):
        self.mouth_scale_value.setText(f"{value}%")
        
    def on_settings_changed(self):
        self.settings = {
            'enabled': self.enable_checkbox.isChecked(),
            'sensitivity': self.sensitivity_slider.value(),
            'response_speed': self.speed_slider.value(),
            'mouth_open_scale': self.mouth_scale_slider.value(),
            'auto_optimize': self.auto_optimize_checkbox.isChecked()
        }
        self.settings_changed.emit(self.settings)
        
    def get_settings(self) -> Dict[str, Any]:
        return self.settings.copy()
        
    def set_settings(self, settings: Dict[str, Any]):
        self.settings.update(settings)
        self.enable_checkbox.setChecked(self.settings['enabled'])
        self.sensitivity_slider.setValue(self.settings['sensitivity'])
        self.speed_slider.setValue(self.settings['response_speed'])
        self.mouth_scale_slider.setValue(self.settings['mouth_open_scale'])
        self.auto_optimize_checkbox.setChecked(self.settings['auto_optimize'])

class PhonemeMappingWidget(QWidget):
    """音素マッピング調整"""
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.phoneme_settings = {
            'a': {'mouth_open': 100, 'mouth_form': 0},      # あ
            'i': {'mouth_open': 30, 'mouth_form': -100},    # い
            'u': {'mouth_open': 40, 'mouth_form': -70},     # う
            'e': {'mouth_open': 60, 'mouth_form': -30},     # え
            'o': {'mouth_open': 80, 'mouth_form': 70},      # お
            'n': {'mouth_open': 10, 'mouth_form': 0}        # ん
        }
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 音素調整グループ
        phoneme_group = QGroupBox("あいうえお調整")
        phoneme_group.setFont(QFont("", 10, QFont.Weight.Bold))
        phoneme_layout = QVBoxLayout(phoneme_group)
        
        # 各音素の調整スライダー
        self.phoneme_sliders = {}
        
        for phoneme, japanese, color in [
            ('a', 'あ', '#ff6b6b'), ('i', 'い', '#4ecdc4'), 
            ('u', 'う', '#45b7d1'), ('e', 'え', '#96ceb4'), 
            ('o', 'お', '#feca57'), ('n', 'ん', '#a0a0a0')
        ]:
            phoneme_frame = QFrame()
            phoneme_frame.setStyleSheet(f"QFrame {{ background-color: {color}20; border-radius: 6px; padding: 8px; }}")
            frame_layout = QVBoxLayout(phoneme_frame)
            frame_layout.setSpacing(8)
            
            # 音素ラベル
            phoneme_label = QLabel(f"{japanese} ({phoneme.upper()})")
            phoneme_label.setFont(QFont("", 12, QFont.Weight.Bold))
            phoneme_label.setStyleSheet(f"color: {color}; border: none; background: none;")
            frame_layout.addWidget(phoneme_label)
            
            # 口の開き調整
            open_layout = QHBoxLayout()
            open_label = QLabel("開き:")
            open_label.setFixedWidth(50)
            open_slider = QSlider(Qt.Orientation.Horizontal)
            open_slider.setRange(0, 100)
            open_slider.setValue(self.phoneme_settings[phoneme]['mouth_open'])
            open_value = QLabel(f"{self.phoneme_settings[phoneme]['mouth_open']}")
            open_value.setFixedWidth(30)
            open_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            open_layout.addWidget(open_label)
            open_layout.addWidget(open_slider)
            open_layout.addWidget(open_value)
            
            # 口の形調整
            form_layout = QHBoxLayout()
            form_label = QLabel("形:")
            form_label.setFixedWidth(50)
            form_slider = QSlider(Qt.Orientation.Horizontal)
            form_slider.setRange(-100, 100)
            form_slider.setValue(self.phoneme_settings[phoneme]['mouth_form'])
            form_value = QLabel(f"{self.phoneme_settings[phoneme]['mouth_form']}")
            form_value.setFixedWidth(30)
            form_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            form_layout.addWidget(form_label)
            form_layout.addWidget(form_slider)
            form_layout.addWidget(form_value)
            
            frame_layout.addLayout(open_layout)
            frame_layout.addLayout(form_layout)
            phoneme_layout.addWidget(phoneme_frame)
            
            # スライダーを保存
            self.phoneme_sliders[phoneme] = {
                'open_slider': open_slider,
                'open_value': open_value,
                'form_slider': form_slider,
                'form_value': form_value
            }
            
            # シグナル接続
            open_slider.valueChanged.connect(lambda v, p=phoneme: self.update_phoneme_open_value(p, v))
            form_slider.valueChanged.connect(lambda v, p=phoneme: self.update_phoneme_form_value(p, v))
            open_slider.valueChanged.connect(self.on_settings_changed)
            form_slider.valueChanged.connect(self.on_settings_changed)
        
        # リセットボタン
        button_layout = QHBoxLayout()
        reset_button = QPushButton("デフォルトに戻す")
        reset_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        reset_button.clicked.connect(self.reset_to_default)
        button_layout.addStretch()
        button_layout.addWidget(reset_button)
        
        layout.addWidget(phoneme_group)
        layout.addLayout(button_layout)
        layout.addStretch()
        
    def update_phoneme_open_value(self, phoneme, value):
        self.phoneme_sliders[phoneme]['open_value'].setText(str(value))
        
    def update_phoneme_form_value(self, phoneme, value):
        self.phoneme_sliders[phoneme]['form_value'].setText(str(value))
        
    def reset_to_default(self):
        default_settings = {
            'a': {'mouth_open': 100, 'mouth_form': 0},
            'i': {'mouth_open': 30, 'mouth_form': -100},
            'u': {'mouth_open': 40, 'mouth_form': -70},
            'e': {'mouth_open': 60, 'mouth_form': -30},
            'o': {'mouth_open': 80, 'mouth_form': 70},
            'n': {'mouth_open': 10, 'mouth_form': 0}
        }
        
        for phoneme, settings in default_settings.items():
            sliders = self.phoneme_sliders[phoneme]
            sliders['open_slider'].setValue(settings['mouth_open'])
            sliders['form_slider'].setValue(settings['mouth_form'])
            
        self.on_settings_changed()
        
    def on_settings_changed(self):
        for phoneme, sliders in self.phoneme_sliders.items():
            self.phoneme_settings[phoneme] = {
                'mouth_open': sliders['open_slider'].value(),
                'mouth_form': sliders['form_slider'].value()
            }
        self.settings_changed.emit(self.phoneme_settings)
        
    def get_settings(self) -> Dict[str, Any]:
        return self.phoneme_settings.copy()

class AdvancedLipSyncWidget(QWidget):
    """高度なリップシンク設定"""
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.advanced_settings = {
            'delay_compensation': 0,
            'smoothing_factor': 70,
            'prediction_enabled': True,
            'consonant_detection': True,
            'volume_threshold': 5,
            'quality_mode': 'balanced'
        }
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # タイミング調整
        timing_group = QGroupBox("タイミング調整")
        timing_group.setFont(QFont("", 10, QFont.Weight.Bold))
        timing_layout = QVBoxLayout(timing_group)
        
        # 遅延補正
        delay_layout = QHBoxLayout()
        delay_label = QLabel("遅延補正:")
        delay_label.setFixedWidth(100)
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(-500, 500)
        self.delay_spinbox.setSuffix(" ms")
        self.delay_spinbox.setValue(self.advanced_settings['delay_compensation'])
        delay_layout.addWidget(delay_label)
        delay_layout.addWidget(self.delay_spinbox)
        delay_layout.addStretch()
        
        # スムージング
        smooth_layout = QHBoxLayout()
        smooth_label = QLabel("滑らかさ:")
        smooth_label.setFixedWidth(100)
        self.smoothing_slider = QSlider(Qt.Orientation.Horizontal)
        self.smoothing_slider.setRange(0, 100)
        self.smoothing_slider.setValue(self.advanced_settings['smoothing_factor'])
        self.smoothing_value = QLabel(f"{self.advanced_settings['smoothing_factor']}%")
        self.smoothing_value.setFixedWidth(50)
        self.smoothing_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        smooth_layout.addWidget(smooth_label)
        smooth_layout.addWidget(self.smoothing_slider)
        smooth_layout.addWidget(self.smoothing_value)
        
        timing_layout.addLayout(delay_layout)
        timing_layout.addLayout(smooth_layout)
        
        # 高度な機能
        advanced_group = QGroupBox("高度な機能")
        advanced_group.setFont(QFont("", 10, QFont.Weight.Bold))
        advanced_layout = QVBoxLayout(advanced_group)
        
        self.prediction_checkbox = QCheckBox("音素先読み機能を使用")
        self.prediction_checkbox.setChecked(self.advanced_settings['prediction_enabled'])
        self.prediction_checkbox.setStyleSheet("QCheckBox { font-size: 11px; }")
        
        self.consonant_checkbox = QCheckBox("子音検出を有効にする")
        self.consonant_checkbox.setChecked(self.advanced_settings['consonant_detection'])
        self.consonant_checkbox.setStyleSheet("QCheckBox { font-size: 11px; }")
        
        # 音量閾値
        volume_layout = QHBoxLayout()
        volume_label = QLabel("音量閾値:")
        volume_label.setFixedWidth(100)
        self.volume_spinbox = QSpinBox()
        self.volume_spinbox.setRange(0, 50)
        self.volume_spinbox.setSuffix("%")
        self.volume_spinbox.setValue(self.advanced_settings['volume_threshold'])
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_spinbox)
        volume_layout.addStretch()
        
        # 品質モード
        quality_layout = QHBoxLayout()
        quality_label = QLabel("品質モード:")
        quality_label.setFixedWidth(100)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["高速", "バランス", "高品質"])
        if self.advanced_settings['quality_mode'] == 'fast':
            self.quality_combo.setCurrentIndex(0)
        elif self.advanced_settings['quality_mode'] == 'balanced':
            self.quality_combo.setCurrentIndex(1)
        else:
            self.quality_combo.setCurrentIndex(2)
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addStretch()
        
        advanced_layout.addWidget(self.prediction_checkbox)
        advanced_layout.addWidget(self.consonant_checkbox)
        advanced_layout.addLayout(volume_layout)
        advanced_layout.addLayout(quality_layout)
        
        layout.addWidget(timing_group)
        layout.addWidget(advanced_group)
        layout.addStretch()
        
        # シグナル接続
        self.delay_spinbox.valueChanged.connect(self.on_settings_changed)
        self.smoothing_slider.valueChanged.connect(self.update_smoothing_value)
        self.smoothing_slider.valueChanged.connect(self.on_settings_changed)
        self.prediction_checkbox.toggled.connect(self.on_settings_changed)
        self.consonant_checkbox.toggled.connect(self.on_settings_changed)
        self.volume_spinbox.valueChanged.connect(self.on_settings_changed)
        self.quality_combo.currentTextChanged.connect(self.on_settings_changed)
        
    def update_smoothing_value(self, value):
        self.smoothing_value.setText(f"{value}%")
        
    def on_settings_changed(self):
        quality_map = {"高速": "fast", "バランス": "balanced", "高品質": "high_quality"}
        
        self.advanced_settings = {
            'delay_compensation': self.delay_spinbox.value(),
            'smoothing_factor': self.smoothing_slider.value(),
            'prediction_enabled': self.prediction_checkbox.isChecked(),
            'consonant_detection': self.consonant_checkbox.isChecked(),
            'volume_threshold': self.volume_spinbox.value(),
            'quality_mode': quality_map[self.quality_combo.currentText()]
        }
        self.settings_changed.emit(self.advanced_settings)
        
    def get_settings(self) -> Dict[str, Any]:
        return self.advanced_settings.copy()

class TabbedLipSyncControl(QWidget):
    """タブ式リップシンク制御ウィジェット"""
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_settings = {}
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background: #e9ecef;
                border: 1px solid #ccc;
                padding: 6px 12px;
                margin-right: 2px;
                border-radius: 4px 4px 0px 0px;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background: #fff;
                border-bottom-color: #fff;
            }
            QTabBar::tab:hover {
                background: #f8f9fa;
            }
        """)
        
        # 各タブの作成
        self.basic_widget = BasicLipSyncWidget()
        self.phoneme_widget = PhonemeMappingWidget()
        self.advanced_widget = AdvancedLipSyncWidget()
        
        self.tab_widget.addTab(self.basic_widget, "基本設定")
        self.tab_widget.addTab(self.phoneme_widget, "音素調整")
        self.tab_widget.addTab(self.advanced_widget, "高度設定")
        
        layout.addWidget(self.tab_widget)
        
        # シグナル接続
        self.basic_widget.settings_changed.connect(self.on_basic_settings_changed)
        self.phoneme_widget.settings_changed.connect(self.on_phoneme_settings_changed)
        self.advanced_widget.settings_changed.connect(self.on_advanced_settings_changed)
        
    def on_basic_settings_changed(self, settings):
        self.all_settings['basic'] = settings
        self.settings_changed.emit(self.all_settings)
        
    def on_phoneme_settings_changed(self, settings):
        self.all_settings['phoneme'] = settings
        self.settings_changed.emit(self.all_settings)
        
    def on_advanced_settings_changed(self, settings):
        self.all_settings['advanced'] = settings
        self.settings_changed.emit(self.all_settings)
        
    def get_all_settings(self) -> Dict[str, Any]:
        """全リップシンク設定を取得"""
        return {
            'basic': self.basic_widget.get_settings(),
            'phoneme': self.phoneme_widget.get_settings(),
            'advanced': self.advanced_widget.get_settings()
        }
        
    def is_enabled(self) -> bool:
        """リップシンクが有効かどうか"""
        return self.basic_widget.get_settings().get('enabled', False)