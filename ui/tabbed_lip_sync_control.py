from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QGroupBox, QSlider, QLabel, QCheckBox, QPushButton,
                             QComboBox, QDoubleSpinBox, QSpinBox, QFrame, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Dict, Any
import traceback

class BasicLipSyncWidget(QWidget):
    """基本リップシンク設定"""
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = {
            'enabled': True,
            'sensitivity': 120,
            'response_speed': 85,
            'mouth_open_scale': 150,
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
        enable_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a90e2;
                border-radius: 8px;
                margin: 8px 0;
                padding-top: 15px;
                color: #2c5898;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #4a90e2;
                background-color: white;
            }
        """)
        enable_layout = QVBoxLayout(enable_group)
        
        self.enable_checkbox = QCheckBox("リップシンクを有効にする")
        self.enable_checkbox.setChecked(self.settings['enabled'])
        self.enable_checkbox.setStyleSheet("QCheckBox { font-size: 12px; color: #333; }")
        self.enable_checkbox.toggled.connect(self.on_settings_changed)
        enable_layout.addWidget(self.enable_checkbox)
        
        # 基本調整
        basic_group = QGroupBox("基本調整")
        basic_group.setFont(QFont("", 10, QFont.Weight.Bold))
        basic_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a90e2;
                border-radius: 8px;
                margin: 8px 0;
                padding-top: 15px;
                color: #2c5898;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #4a90e2;
                background-color: white;
            }
        """)
        basic_layout = QVBoxLayout(basic_group)
        
        # 感度調整
        sens_layout = QHBoxLayout()
        sens_label = QLabel("反応感度:")
        sens_label.setFixedWidth(100)
        sens_label.setStyleSheet("QLabel { font-size: 11px; color: #333; font-weight: bold; }")
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(10, 300)
        self.sensitivity_slider.setValue(self.settings['sensitivity'])
        self.sensitivity_slider.setStyleSheet(self._get_unified_slider_style())
        self.sensitivity_value = QLabel(f"{self.settings['sensitivity']}%")
        self.sensitivity_value.setFixedWidth(50)
        self.sensitivity_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sensitivity_value.setStyleSheet(self._get_unified_value_style())
        
        sens_layout.addWidget(sens_label)
        sens_layout.addWidget(self.sensitivity_slider)
        sens_layout.addWidget(self.sensitivity_value)
        basic_layout.addLayout(sens_layout)
        
        # 反応速度
        speed_layout = QHBoxLayout()
        speed_label = QLabel("反応速度:")
        speed_label.setFixedWidth(100)
        speed_label.setStyleSheet("QLabel { font-size: 11px; color: #333; font-weight: bold; }")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 100)
        self.speed_slider.setValue(self.settings['response_speed'])
        self.speed_slider.setStyleSheet(self._get_unified_slider_style())
        self.speed_value = QLabel(f"{self.settings['response_speed']}%")
        self.speed_value.setFixedWidth(50)
        self.speed_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speed_value.setStyleSheet(self._get_unified_value_style())
        
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_value)
        basic_layout.addLayout(speed_layout)
        
        # 口の開き調整
        mouth_layout = QHBoxLayout()
        mouth_label = QLabel("口の開き:")
        mouth_label.setFixedWidth(100)
        mouth_label.setStyleSheet("QLabel { font-size: 11px; color: #333; font-weight: bold; }")
        self.mouth_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.mouth_scale_slider.setRange(50, 300)
        self.mouth_scale_slider.setValue(self.settings['mouth_open_scale'])
        self.mouth_scale_slider.setStyleSheet(self._get_unified_slider_style())
        self.mouth_scale_value = QLabel(f"{self.settings['mouth_open_scale']}%")
        self.mouth_scale_value.setFixedWidth(50)
        self.mouth_scale_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mouth_scale_value.setStyleSheet(self._get_unified_value_style())
        
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
        try:
            self.settings = {
                'enabled': self.enable_checkbox.isChecked(),
                'sensitivity': self.sensitivity_slider.value(),
                'response_speed': self.speed_slider.value(),
                'mouth_open_scale': self.mouth_scale_slider.value(),
                'auto_optimize': self.auto_optimize_checkbox.isChecked()
            }
            self.settings_changed.emit(self.settings)
        except Exception as e:
            print(f"❌ 基本設定エラー: {e}")
        
    def _get_unified_slider_style(self):
        """🎨 統一スライダースタイル（音声パラメータタブと同じ明るい灰色）"""
        return """
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #eee, stop: 1 #ccc);
                border: 1px solid #777;
                width: 18px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #f0f0f0, stop: 1 #ddd);
                border: 1px solid #888;
            }
            QSlider::handle:horizontal:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #ccc, stop: 1 #aaa);
                border: 1px solid #666;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #66e, stop: 1 #bbf);
                border: 1px solid #777;
                height: 6px;
                border-radius: 3px;
            }
        """
    
    def _get_unified_value_style(self):
        """🎨 統一された値表示スタイル"""
        return """
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f5f5f5);
                border: 1px solid #4a90e2;
                border-radius: 4px;
                padding: 4px 6px;
                font-weight: bold;
                font-size: 11px;
                color: #2c5898;
            }
        """
        
    def get_settings(self) -> Dict[str, Any]:
        return self.settings.copy()
        
    def set_settings(self, settings: Dict[str, Any]):
        try:
            self.settings.update(settings)
            self.enable_checkbox.setChecked(self.settings['enabled'])
            self.sensitivity_slider.setValue(self.settings['sensitivity'])
            self.speed_slider.setValue(self.settings['response_speed'])
            self.mouth_scale_slider.setValue(self.settings['mouth_open_scale'])
            self.auto_optimize_checkbox.setChecked(self.settings['auto_optimize'])
        except Exception as e:
            print(f"❌ 基本設定適用エラー: {e}")

class PhonemeMappingWidget(QWidget):
    """音素マッピング調整 - 灰色スライダー版"""
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.phoneme_settings = {
            'a': {'mouth_open': 150, 'mouth_form': 0},
            'i': {'mouth_open': 45, 'mouth_form': -150},
            'u': {'mouth_open': 60, 'mouth_form': -105},
            'e': {'mouth_open': 90, 'mouth_form': -45},
            'o': {'mouth_open': 120, 'mouth_form': 105},
            'n': {'mouth_open': 15, 'mouth_form': 0}
        }
        self.phoneme_sliders = {}
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 🎨 統一された説明文
        info_label = QLabel("各母音の口の動きを調整できます\n• 縦開き: 口の縦方向の開き具合\n• 横形状: 口の横方向の形（マイナス=横広げ、プラス=すぼめ）")
        info_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e7f3ff, stop:1 #d0e8ff);
                border: 1px solid #4a90e2;
                border-radius: 6px;
                padding: 12px;
                font-size: 11px;
                color: #2c5898;
                font-weight: normal;
            }
        """)
        layout.addWidget(info_label)
        
        # 音素調整グループ - シンプルテーブル風
        phoneme_group = QGroupBox("あいうえお調整")
        phoneme_group.setFont(QFont("", 11, QFont.Weight.Bold))
        phoneme_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a90e2;
                border-radius: 8px;
                margin: 8px 0;
                padding-top: 15px;
                color: #2c5898;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #4a90e2;
                background-color: white;
            }
        """)
        
        # グリッドレイアウトで整理
        grid_layout = QGridLayout(phoneme_group)
        grid_layout.setSpacing(12)
        grid_layout.setContentsMargins(15, 20, 15, 15)
        
        # ヘッダー
        headers = ["音素", "縦開き", "値", "横形状", "値", "プレビュー"]
        for col, header in enumerate(headers):
            header_label = QLabel(header)
            header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header_label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 11px;
                    color: #4a90e2;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f8f9fa);
                    border: 1px solid #4a90e2;
                    padding: 8px;
                    border-radius: 4px;
                }
            """)
            grid_layout.addWidget(header_label, 0, col)
        
        # 各音素の設定行
        vowel_info = [
            ('a', 'あ', "口を大きく開く"),
            ('i', 'い', "横に広げる"),
            ('u', 'う', "口をすぼめる"),
            ('e', 'え', "中程度に開く"),
            ('o', 'お', "丸く開く"),
            ('n', 'ん', "ほぼ閉じる")
        ]
        
        for row, (phoneme, japanese, description) in enumerate(vowel_info, 1):
            # 🎨 統一された音素ラベル（グリッド用）
            phoneme_label = QLabel(f"{japanese}\n({phoneme.upper()})")
            phoneme_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            phoneme_label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 12px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f5f5f5);
                    border: 1px solid #4a90e2;
                    border-radius: 6px;
                    padding: 8px;
                    color: #2c5898;
                }
            """)
            grid_layout.addWidget(phoneme_label, row, 0)
            
            # 縦開きスライダー
            open_slider = QSlider(Qt.Orientation.Horizontal)
            open_slider.setRange(0, 200)
            open_slider.setValue(self.phoneme_settings[phoneme]['mouth_open'])
            open_slider.setStyleSheet(self.get_slider_style())
            grid_layout.addWidget(open_slider, row, 1)
            
            # 縦開き値表示
            open_value = QLabel(str(self.phoneme_settings[phoneme]['mouth_open']))
            open_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            open_value.setStyleSheet(self.get_value_style())
            open_value.setFixedWidth(40)
            grid_layout.addWidget(open_value, row, 2)
            
            # 横形状スライダー
            form_slider = QSlider(Qt.Orientation.Horizontal)
            form_slider.setRange(-200, 200)
            form_slider.setValue(self.phoneme_settings[phoneme]['mouth_form'])
            form_slider.setStyleSheet(self.get_slider_style())
            grid_layout.addWidget(form_slider, row, 3)
            
            # 横形状値表示
            form_value = QLabel(str(self.phoneme_settings[phoneme]['mouth_form']))
            form_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            form_value.setStyleSheet(self.get_value_style())
            form_value.setFixedWidth(40)
            grid_layout.addWidget(form_value, row, 4)
            
            # 🎨 統一された説明ラベル
            desc_label = QLabel(description)
            desc_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    color: #666;
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8f9fa, stop:1 #f0f1f2);
                    border: 1px solid #e9ecef;
                    border-radius: 4px;
                    padding: 4px 6px;
                }
            """)
            grid_layout.addWidget(desc_label, row, 5)
            
            # スライダー情報を保存
            self.phoneme_sliders[phoneme] = {
                'open_slider': open_slider,
                'open_value': open_value,
                'form_slider': form_slider,
                'form_value': form_value
            }
            
            # シグナル接続 - lambdaを使わない安全な方法
            open_slider.valueChanged.connect(self.create_open_handler(phoneme))
            form_slider.valueChanged.connect(self.create_form_handler(phoneme))
        
        # ボタン類
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # リセットボタン群
        normal_reset_btn = QPushButton("標準に戻す")
        normal_reset_btn.setStyleSheet(self.get_button_style("#6c757d", "#545b62"))
        normal_reset_btn.clicked.connect(self.reset_to_normal)
        
        strong_reset_btn = QPushButton("強化版に戻す")
        strong_reset_btn.setStyleSheet(self.get_button_style("#dc3545", "#c82333"))
        strong_reset_btn.clicked.connect(self.reset_to_strong)
        
        test_btn = QPushButton("テスト再生")
        test_btn.setStyleSheet(self.get_button_style("#28a745", "#1e7e34"))
        test_btn.clicked.connect(self.test_phonemes)
        
        button_layout.addStretch()
        button_layout.addWidget(normal_reset_btn)
        button_layout.addWidget(strong_reset_btn)
        button_layout.addWidget(test_btn)
        
        layout.addWidget(phoneme_group)
        layout.addLayout(button_layout)
        layout.addStretch()
        
    def get_slider_style(self):
        """🎨 統一スライダースタイル（音声パラメータタブと同じ明るい灰色）"""
        return """
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #eee, stop: 1 #ccc);
                border: 1px solid #777;
                width: 18px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #f0f0f0, stop: 1 #ddd);
                border: 1px solid #888;
            }
            QSlider::handle:horizontal:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #ccc, stop: 1 #aaa);
                border: 1px solid #666;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #66e, stop: 1 #bbf);
                border: 1px solid #777;
                height: 6px;
                border-radius: 3px;
            }
        """
        
    def get_value_style(self):
        """🎨 既存のタブに合わせた統一値表示スタイル"""
        return """
            QLabel {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f5f5f5);
                border: 1px solid #4a90e2;
                border-radius: 4px;
                padding: 4px 6px;
                font-weight: bold;
                font-size: 11px;
                color: #2c5898;
                min-width: 35px;
            }
        """
        
    def get_button_style(self, bg_color, hover_color):
        """🎨 既存のタブに合わせた統一ボタンスタイル"""
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {bg_color}, stop:1 {hover_color});
                color: white;
                border: 1px solid {hover_color};
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
                padding: 8px 16px;
                min-width: 80px;
                min-height: 28px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {hover_color}, stop:1 {bg_color});
                border: 1px solid {bg_color};
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {hover_color}, stop:1 {hover_color});
                padding-top: 9px;
                padding-bottom: 7px;
            }}
        """
    
    def create_open_handler(self, phoneme):
        """縦開きハンドラー生成 - lambdaエラー回避"""
        def handler(value):
            try:
                self.phoneme_sliders[phoneme]['open_value'].setText(str(value))
                self.on_settings_changed()
            except Exception as e:
                print(f"❌ 縦開き調整エラー ({phoneme}): {e}")
        return handler
    
    def create_form_handler(self, phoneme):
        """横形状ハンドラー生成 - lambdaエラー回避"""
        def handler(value):
            try:
                self.phoneme_sliders[phoneme]['form_value'].setText(str(value))
                self.on_settings_changed()
            except Exception as e:
                print(f"❌ 横形状調整エラー ({phoneme}): {e}")
        return handler
        
    def reset_to_normal(self):
        """標準設定に戻す"""
        try:
            normal_settings = {
                'a': {'mouth_open': 100, 'mouth_form': 0},
                'i': {'mouth_open': 30, 'mouth_form': -100},
                'u': {'mouth_open': 40, 'mouth_form': -70},
                'e': {'mouth_open': 60, 'mouth_form': -30},
                'o': {'mouth_open': 80, 'mouth_form': 70},
                'n': {'mouth_open': 10, 'mouth_form': 0}
            }
            self.apply_settings(normal_settings)
            print("✅ 標準設定に戻しました")
        except Exception as e:
            print(f"❌ 標準設定リセットエラー: {e}")
        
    def reset_to_strong(self):
        """強化設定に戻す"""
        try:
            strong_settings = {
                'a': {'mouth_open': 150, 'mouth_form': 0},
                'i': {'mouth_open': 45, 'mouth_form': -150},
                'u': {'mouth_open': 60, 'mouth_form': -105},
                'e': {'mouth_open': 90, 'mouth_form': -45},
                'o': {'mouth_open': 120, 'mouth_form': 105},
                'n': {'mouth_open': 15, 'mouth_form': 0}
            }
            self.apply_settings(strong_settings)
            print("✅ 強化設定に戻しました")
        except Exception as e:
            print(f"❌ 強化設定リセットエラー: {e}")
            
    def apply_settings(self, settings):
        """設定を適用"""
        for phoneme, values in settings.items():
            if phoneme in self.phoneme_sliders:
                sliders = self.phoneme_sliders[phoneme]
                sliders['open_slider'].setValue(values['mouth_open'])
                sliders['form_slider'].setValue(values['mouth_form'])
        
    def test_phonemes(self):
        """音素テスト"""
        print("🔊 音素テスト実行: あいうえおん")
        print("現在の設定:")
        for phoneme, settings in self.get_settings().items():
            print(f"  {phoneme}: 縦開き={settings['mouth_open']}, 横形状={settings['mouth_form']}")
        
    def on_settings_changed(self):
        try:
            for phoneme, sliders in self.phoneme_sliders.items():
                self.phoneme_settings[phoneme] = {
                    'mouth_open': sliders['open_slider'].value(),
                    'mouth_form': sliders['form_slider'].value()
                }
            self.settings_changed.emit(self.phoneme_settings)
        except Exception as e:
            print(f"❌ 音素設定変更エラー: {e}")
            traceback.print_exc()
        
    def get_settings(self) -> Dict[str, Any]:
        return self.phoneme_settings.copy()

class AdvancedLipSyncWidget(QWidget):
    """高度なリップシンク設定"""
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.advanced_settings = {
            'delay_compensation': 0,
            'smoothing_factor': 60,
            'prediction_enabled': True,
            'consonant_detection': True,
            'volume_threshold': 3,
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
        smooth_label.setStyleSheet("QLabel { font-size: 11px; color: #333; font-weight: bold; }")
        self.smoothing_slider = QSlider(Qt.Orientation.Horizontal)
        self.smoothing_slider.setRange(0, 100)
        self.smoothing_slider.setValue(self.advanced_settings['smoothing_factor'])
        self.smoothing_slider.setStyleSheet(self._get_unified_slider_style())
        self.smoothing_value = QLabel(f"{self.advanced_settings['smoothing_factor']}%")
        self.smoothing_value.setFixedWidth(50)
        self.smoothing_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.smoothing_value.setStyleSheet(self._get_unified_value_style())
        
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
        self.prediction_checkbox.setStyleSheet("QCheckBox { font-size: 11px; color: #333; }")
        
        self.consonant_checkbox = QCheckBox("子音検出を有効にする")
        self.consonant_checkbox.setChecked(self.advanced_settings['consonant_detection'])
        self.consonant_checkbox.setStyleSheet("QCheckBox { font-size: 11px; color: #333; }")
        
        # 音量閾値
        volume_layout = QHBoxLayout()
        volume_label = QLabel("音量閾値:")
        volume_label.setFixedWidth(100)
        volume_label.setStyleSheet("QLabel { font-size: 11px; color: #333; font-weight: bold; }")
        self.volume_spinbox = QSpinBox()
        self.volume_spinbox.setRange(0, 50)
        self.volume_spinbox.setSuffix("%")
        self.volume_spinbox.setValue(self.advanced_settings['volume_threshold'])
        self.volume_spinbox.setStyleSheet("""
            QSpinBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f5f5f5);
                border: 1px solid #4a90e2;
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
                color: #2c5898;
            }
        """)
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_spinbox)
        volume_layout.addStretch()
        
        # 品質モード
        quality_layout = QHBoxLayout()
        quality_label = QLabel("品質モード:")
        quality_label.setFixedWidth(100)
        quality_label.setStyleSheet("QLabel { font-size: 11px; color: #333; font-weight: bold; }")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["高速", "バランス", "高品質"])
        if self.advanced_settings['quality_mode'] == 'fast':
            self.quality_combo.setCurrentIndex(0)
        elif self.advanced_settings['quality_mode'] == 'balanced':
            self.quality_combo.setCurrentIndex(1)
        else:
            self.quality_combo.setCurrentIndex(2)
        self.quality_combo.setStyleSheet("""
            QComboBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f5f5f5);
                border: 1px solid #4a90e2;
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
                color: #2c5898;
            }
            QComboBox::drop-down {
                border: none;
                border-left: 1px solid #4a90e2;
                width: 20px;
            }
        """)
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
    
    def _get_unified_slider_style(self):
        """🎨 統一スライダースタイル（音声パラメータタブと同じ明るい灰色）"""
        return """
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #eee, stop: 1 #ccc);
                border: 1px solid #777;
                width: 18px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #f0f0f0, stop: 1 #ddd);
                border: 1px solid #888;
            }
            QSlider::handle:horizontal:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #ccc, stop: 1 #aaa);
                border: 1px solid #666;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #66e, stop: 1 #bbf);
                border: 1px solid #777;
                height: 6px;
                border-radius: 3px;
            }
        """
    
    def _get_unified_value_style(self):
        """🎨 統一された値表示スタイル"""
        return """
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f5f5f5);
                border: 1px solid #4a90e2;
                border-radius: 4px;
                padding: 4px 6px;
                font-weight: bold;
                font-size: 11px;
                color: #2c5898;
            }
        """
        
    def update_smoothing_value(self, value):
        self.smoothing_value.setText(f"{value}%")
        
    def on_settings_changed(self):
        try:
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
        except Exception as e:
            print(f"❌ 高度設定エラー: {e}")
        
    def get_settings(self) -> Dict[str, Any]:
        return self.advanced_settings.copy()

class TabbedLipSyncControl(QWidget):
    """タブ式リップシンク制御ウィジェット - 灰色スライダー版"""
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
                background-color: white;
                border: 2px solid #4a90e2;
                border-radius: 4px;
                margin-top: 0px;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar {
                background-color: transparent;
                alignment: left;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f0f0f0, stop:1 #e0e0e0);
                color: #333;
                border: 1px solid #ccc;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 16px;
                margin-right: 2px;
                margin-bottom: -2px;
                font-size: 12px;
                font-weight: bold;
                min-width: 100px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f8f8f8);
                color: #4a90e2;
                border: 2px solid #4a90e2;
                border-bottom: none;
                margin-bottom: -2px;
            }
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e6f2ff, stop:1 #d0e8ff);
                border-color: #4a90e2;
                color: #4a90e2;
            }
        """)
        
        # 各タブの作成 - エラーハンドリング付き
        try:
            self.basic_widget = BasicLipSyncWidget()
            self.phoneme_widget = PhonemeMappingWidget()
            self.advanced_widget = AdvancedLipSyncWidget()
            
            self.tab_widget.addTab(self.basic_widget, "🎛️ 基本設定")
            self.tab_widget.addTab(self.phoneme_widget, "🗣️ あいうえお")
            self.tab_widget.addTab(self.advanced_widget, "⚙️ 高度設定")
            
            layout.addWidget(self.tab_widget)
            
            # シグナル接続
            self.basic_widget.settings_changed.connect(self.on_basic_settings_changed)
            self.phoneme_widget.settings_changed.connect(self.on_phoneme_settings_changed)
            self.advanced_widget.settings_changed.connect(self.on_advanced_settings_changed)
            
            print("✅ リップシンクUI初期化完了（灰色スライダー版）")
            
        except Exception as e:
            print(f"❌ リップシンクUI初期化エラー: {e}")
            traceback.print_exc()
            
            # フォールバック用のシンプルなUI
            error_label = QLabel(f"リップシンクUI読み込みエラー\n{str(e)}")
            error_label.setStyleSheet("""
                QLabel {
                    background-color: #f8d7da;
                    color: #721c24;
                    border: 1px solid #f5c6cb;
                    border-radius: 4px;
                    padding: 20px;
                    font-size: 12px;
                }
            """)
            layout.addWidget(error_label)
        
    def on_basic_settings_changed(self, settings):
        try:
            self.all_settings['basic'] = settings
            self.settings_changed.emit(self.all_settings)
        except Exception as e:
            print(f"❌ 基本設定変更エラー: {e}")
        
    def on_phoneme_settings_changed(self, settings):
        try:
            self.all_settings['phoneme'] = settings
            self.settings_changed.emit(self.all_settings)
        except Exception as e:
            print(f"❌ 音素設定変更エラー: {e}")
        
    def on_advanced_settings_changed(self, settings):
        try:
            self.all_settings['advanced'] = settings
            self.settings_changed.emit(self.all_settings)
        except Exception as e:
            print(f"❌ 高度設定変更エラー: {e}")
        
    def get_all_settings(self) -> Dict[str, Any]:
        """全リップシンク設定を取得 - エラー対策版"""
        try:
            return {
                'basic': self.basic_widget.get_settings() if hasattr(self, 'basic_widget') else {},
                'phoneme': self.phoneme_widget.get_settings() if hasattr(self, 'phoneme_widget') else {},
                'advanced': self.advanced_widget.get_settings() if hasattr(self, 'advanced_widget') else {}
            }
        except Exception as e:
            print(f"❌ 設定取得エラー: {e}")
            return {'basic': {}, 'phoneme': {}, 'advanced': {}}
        
    def is_enabled(self) -> bool:
        """リップシンクが有効かどうか - エラー対策版"""
        try:
            if hasattr(self, 'basic_widget'):
                return self.basic_widget.get_settings().get('enabled', False)
            return False
        except Exception as e:
            print(f"❌ 有効状態取得エラー: {e}")
            return False