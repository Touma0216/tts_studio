from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
                            QGroupBox, QGridLayout, QPushButton, QSlider, QDoubleSpinBox,
                            QTabWidget, QFrame, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class AudioCleanerControl(QWidget):
    """音声クリーナー制御ウィジェット"""
    
    settings_changed = pyqtSignal(dict)  # cleaner_settings
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # クリーナー設定
        self.cleaner_settings = {
            'enabled': False,  # デフォルトOFF
            'highpass_freq': 80,
            'hum_removal': True,
            'hum_frequencies': [50, 60, 100, 120, 150, 180, 200, 240],
            'hum_gains': [-20, -20, -12, -12, -9, -9, -6, -6],
            'noise_reduction': True,
            'noise_floor': -28,
            'loudness_norm': True,
            'target_lufs': -20.0,
            'true_peak': -1.0,
            'lra': 11.0
        }
        
        self.init_ui()
        
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # クリーナー内部でのタブ分け
        self.cleaner_tab_widget = QTabWidget()
        self.cleaner_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                background-color: white;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
                margin-top: 0px;
                padding-top: 0px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar {
                background-color: transparent;
            }
            QTabBar::tab {
                background-color: #f5f5f5;
                border: 1px solid #ccc;
                border-bottom: 1px solid #ccc;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                margin-right: 2px;
                margin-top: 1px;
                margin-bottom: 0px;
                min-width: 80px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-left: 1px solid #ccc;
                border-right: 1px solid #ccc;
                border-top: 1px solid #ccc;
                border-bottom: 0px none transparent;
                margin-top: 0px;
                margin-bottom: -1px;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e8f4fd;
                border-color: #64b5f6;
            }
        """)
        
        # 基本設定タブ
        basic_tab = self.create_basic_tab()
        self.cleaner_tab_widget.addTab(basic_tab, "🔧 基本設定")
        
        # 詳細調整タブ
        advanced_tab = self.create_advanced_tab()
        self.cleaner_tab_widget.addTab(advanced_tab, "📊 詳細調整")
        
        # プリセットタブ
        preset_tab = self.create_preset_tab()
        self.cleaner_tab_widget.addTab(preset_tab, "📋 プリセット")
        
        layout.addWidget(self.cleaner_tab_widget)
        
    def create_basic_tab(self):
        """基本設定タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # クリーナー有効/無効
        enable_group = QGroupBox("クリーナー制御")
        enable_layout = QVBoxLayout(enable_group)
        
        # ON/OFFボタン（大きめ）
        self.enable_button = QPushButton("🔧 音声クリーナーを有効化")
        self.enable_button.setCheckable(True)
        self.enable_button.setChecked(self.cleaner_settings['enabled'])
        self.enable_button.setMinimumHeight(50)
        self.update_enable_button_style()
        self.enable_button.toggled.connect(self.on_enable_toggled)
        
        info_label = QLabel("⚠️ 現在クリーナーは無効です - ボタンを押して有効化してください")
        info_label.setStyleSheet("""
            QLabel {
                background-color: #fff3cd;
                color: #856404;
                border: 1px solid #ffeaa7;
                border-radius: 4px;
                padding: 8px;
                font-style: italic;
            }
        """)
        
        enable_layout.addWidget(self.enable_button)
        enable_layout.addWidget(info_label)
        
        # 処理ステップ表示
        steps_group = QGroupBox("処理ステップ（自動実行）")
        steps_layout = QVBoxLayout(steps_group)
        
        steps = [
            "1️⃣ ハイパスフィルタ（80Hz以下カット）",
            "2️⃣ ハム除去（50/60Hz + 倍音）", 
            "3️⃣ ノイズ除去（-28dBフロア）",
            "4️⃣ ラウドネス正規化（-20 LUFS）"
        ]
        
        for step in steps:
            step_label = QLabel(step)
            step_label.setStyleSheet("color: #34495e; padding: 4px; font-size: 12px;")
            steps_layout.addWidget(step_label)
        
        layout.addWidget(enable_group)
        layout.addWidget(steps_group)
        layout.addStretch()
        
        return widget
        
    def create_advanced_tab(self):
        """詳細調整タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # ハイパスフィルタ
        highpass_group = QGroupBox("ハイパスフィルタ")
        highpass_layout = QGridLayout(highpass_group)
        
        freq_label = QLabel("カットオフ周波数:")
        self.highpass_slider = QSlider(Qt.Orientation.Horizontal)
        self.highpass_slider.setRange(40, 150)
        self.highpass_slider.setValue(self.cleaner_settings['highpass_freq'])
        self.highpass_spinbox = QDoubleSpinBox()
        self.highpass_spinbox.setRange(40.0, 150.0)
        self.highpass_spinbox.setValue(self.cleaner_settings['highpass_freq'])
        self.highpass_spinbox.setSuffix(" Hz")
        
        self.highpass_slider.valueChanged.connect(
            lambda v: self.sync_slider_spinbox(v, self.highpass_spinbox, 'highpass_freq'))
        self.highpass_spinbox.valueChanged.connect(
            lambda v: self.sync_spinbox_slider(v, self.highpass_slider, 'highpass_freq'))
        
        highpass_layout.addWidget(freq_label, 0, 0)
        highpass_layout.addWidget(self.highpass_slider, 0, 1)
        highpass_layout.addWidget(self.highpass_spinbox, 0, 2)
        
        # ノイズ除去
        noise_group = QGroupBox("ノイズ除去")
        noise_layout = QGridLayout(noise_group)
        
        noise_label = QLabel("ノイズフロア:")
        self.noise_slider = QSlider(Qt.Orientation.Horizontal)
        self.noise_slider.setRange(-40, -20)
        self.noise_slider.setValue(self.cleaner_settings['noise_floor'])
        self.noise_spinbox = QDoubleSpinBox()
        self.noise_spinbox.setRange(-40.0, -20.0)
        self.noise_spinbox.setValue(self.cleaner_settings['noise_floor'])
        self.noise_spinbox.setSuffix(" dB")
        
        self.noise_slider.valueChanged.connect(
            lambda v: self.sync_slider_spinbox(v, self.noise_spinbox, 'noise_floor'))
        self.noise_spinbox.valueChanged.connect(
            lambda v: self.sync_spinbox_slider(v, self.noise_slider, 'noise_floor'))
        
        noise_layout.addWidget(noise_label, 0, 0)
        noise_layout.addWidget(self.noise_slider, 0, 1)
        noise_layout.addWidget(self.noise_spinbox, 0, 2)
        
        # ラウドネス正規化
        loudness_group = QGroupBox("ラウドネス正規化")
        loudness_layout = QGridLayout(loudness_group)
        
        lufs_label = QLabel("目標 LUFS:")
        self.lufs_slider = QSlider(Qt.Orientation.Horizontal)
        self.lufs_slider.setRange(-30, -10)
        self.lufs_slider.setValue(int(self.cleaner_settings['target_lufs']))
        self.lufs_spinbox = QDoubleSpinBox()
        self.lufs_spinbox.setRange(-30.0, -10.0)
        self.lufs_spinbox.setValue(self.cleaner_settings['target_lufs'])
        self.lufs_spinbox.setSuffix(" LUFS")
        
        self.lufs_slider.valueChanged.connect(
            lambda v: self.sync_slider_spinbox(v, self.lufs_spinbox, 'target_lufs'))
        self.lufs_spinbox.valueChanged.connect(
            lambda v: self.sync_spinbox_slider(v, self.lufs_slider, 'target_lufs'))
        
        loudness_layout.addWidget(lufs_label, 0, 0)
        loudness_layout.addWidget(self.lufs_slider, 0, 1)
        loudness_layout.addWidget(self.lufs_spinbox, 0, 2)
        
        layout.addWidget(highpass_group)
        layout.addWidget(noise_group)
        layout.addWidget(loudness_group)
        layout.addStretch()
        
        return widget
        
    def create_preset_tab(self):
        """プリセットタブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # プリセット選択
        preset_group = QGroupBox("プリセット選択")
        preset_layout = QVBoxLayout(preset_group)
        
        self.preset_combo = QComboBox()
        presets = [
            ("ほのかちゃん最適化", "honoka_optimized"),
            ("軽め処理", "light_processing"),
            ("強力クリーニング", "heavy_cleaning"),
            ("配信用", "streaming_optimized")
        ]
        
        for name, key in presets:
            self.preset_combo.addItem(name, key)
        
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        
        apply_btn = QPushButton("プリセットを適用")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
        """)
        apply_btn.clicked.connect(self.apply_preset)
        
        preset_layout.addWidget(QLabel("プリセット:"))
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(apply_btn)
        
        # プリセット説明
        desc_group = QGroupBox("プリセット説明")
        desc_layout = QVBoxLayout(desc_group)
        
        self.preset_description = QLabel("ほのかちゃんの音声に最適化された設定です。ハム除去と自然な音量調整を行います。")
        self.preset_description.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 12px;
                color: #495057;
                line-height: 1.4;
            }
        """)
        self.preset_description.setWordWrap(True)
        
        desc_layout.addWidget(self.preset_description)
        
        layout.addWidget(preset_group)
        layout.addWidget(desc_group)
        layout.addStretch()
        
        return widget
    
    def sync_slider_spinbox(self, slider_value, spinbox, setting_key):
        """スライダー値をスピンボックスと設定に同期"""
        spinbox.blockSignals(True)
        spinbox.setValue(float(slider_value))
        spinbox.blockSignals(False)
        self.cleaner_settings[setting_key] = float(slider_value)
        self.emit_settings_changed()
    
    def sync_spinbox_slider(self, spinbox_value, slider, setting_key):
        """スピンボックス値をスライダーと設定に同期"""
        slider.blockSignals(True)
        slider.setValue(int(spinbox_value))
        slider.blockSignals(False)
        self.cleaner_settings[setting_key] = float(spinbox_value)
        self.emit_settings_changed()
    
    def update_enable_button_style(self):
        """有効/無効ボタンのスタイルを更新"""
        if self.cleaner_settings['enabled']:
            self.enable_button.setText("✅ 音声クリーナー有効")
            self.enable_button.setStyleSheet("""
                QPushButton {
                    background-color: #4caf50;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 12px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        else:
            self.enable_button.setText("❌ 音声クリーナー無効")
            self.enable_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 12px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
    
    def on_enable_toggled(self, enabled):
        """クリーナー有効/無効切り替え"""
        self.cleaner_settings['enabled'] = enabled
        self.update_enable_button_style()
        self.update_info_label()
        self.emit_settings_changed()
    
    def update_info_label(self):
        """情報ラベルを更新"""
        info_label = self.findChild(QLabel)  # 情報ラベルを取得
        if info_label:
            if self.cleaner_settings['enabled']:
                info_label.setText("✨ ほのかちゃん専用最適化設定が適用されます")
                info_label.setStyleSheet("""
                    QLabel {
                        background-color: #e8f5e8;
                        color: #2e7d32;
                        border: 1px solid #81c784;
                        border-radius: 4px;
                        padding: 8px;
                        font-style: italic;
                    }
                """)
            else:
                info_label.setText("⚠️ 現在クリーナーは無効です - ボタンを押して有効化してください")
                info_label.setStyleSheet("""
                    QLabel {
                        background-color: #fff3cd;
                        color: #856404;
                        border: 1px solid #ffeaa7;
                        border-radius: 4px;
                        padding: 8px;
                        font-style: italic;
                    }
                """)
    
    def on_preset_changed(self, preset_name):
        """プリセット変更時の説明更新"""
        descriptions = {
            "ほのかちゃん最適化": "ほのかちゃんの音声に最適化された設定です。ハム除去と自然な音量調整を行います。",
            "軽め処理": "軽微なノイズ除去のみを行います。元音声の特徴を最大限保持します。",
            "強力クリーニング": "ノイズが多い環境での録音に対応した強力な処理を行います。",
            "配信用": "配信プラットフォームに最適化された音量・品質に調整します。"
        }
        self.preset_description.setText(descriptions.get(preset_name, ""))
    
    def apply_preset(self):
        """選択されたプリセットを適用"""
        preset_key = self.preset_combo.currentData()
        
        presets = {
            "honoka_optimized": {
                'enabled': True,
                'highpass_freq': 80,
                'noise_floor': -28,
                'target_lufs': -20.0,
            },
            "light_processing": {
                'enabled': True,
                'highpass_freq': 60,
                'noise_floor': -35,
                'target_lufs': -18.0,
            },
            "heavy_cleaning": {
                'enabled': True,
                'highpass_freq': 100,
                'noise_floor': -25,
                'target_lufs': -20.0,
            },
            "streaming_optimized": {
                'enabled': True,
                'highpass_freq': 80,
                'noise_floor': -30,
                'target_lufs': -16.0,
            }
        }
        
        if preset_key in presets:
            preset_settings = presets[preset_key]
            self.cleaner_settings.update(preset_settings)
            self.update_ui_from_settings()
            self.emit_settings_changed()
    
    def update_ui_from_settings(self):
        """設定からUIを更新"""
        self.enable_button.setChecked(self.cleaner_settings['enabled'])
        self.update_enable_button_style()
        self.update_info_label()
        self.highpass_slider.setValue(int(self.cleaner_settings['highpass_freq']))
        self.highpass_spinbox.setValue(self.cleaner_settings['highpass_freq'])
        self.noise_slider.setValue(int(self.cleaner_settings['noise_floor']))
        self.noise_spinbox.setValue(self.cleaner_settings['noise_floor'])
        self.lufs_slider.setValue(int(self.cleaner_settings['target_lufs']))
        self.lufs_spinbox.setValue(self.cleaner_settings['target_lufs'])
    
    def emit_settings_changed(self):
        """設定変更シグナルを送信"""
        self.settings_changed.emit(self.cleaner_settings.copy())
    
    def get_current_settings(self):
        """現在の設定を取得"""
        return self.cleaner_settings.copy()
    
    def is_enabled(self):
        """クリーナーが有効かどうか"""
        return self.cleaner_settings['enabled']