# ui/audio_effects_control.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QSlider, QCheckBox, QComboBox, QPushButton, 
                            QGroupBox, QFrame, QSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class AudioEffectsControl(QWidget):
    """音声エフェクト制御ウィジェット"""
    
    # シグナル定義
    effects_settings_changed = pyqtSignal(dict)  # エフェクト設定変更時
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.connect_signals()
        
        # デフォルト設定
        self.default_settings = {
            'enabled': False,
            'echo_enabled': False,
            'echo_delay': 0.5,
            'echo_decay': 0.3,
            'reverb_enabled': False,
            'reverb_room_size': 0.5,
            'reverb_damping': 0.3,
            'filter_enabled': False,
            'filter_type': 'lowpass',
            'filter_cutoff': 8000,
            'distortion_enabled': False,
            'distortion_drive': 5.0
        }
        
    def init_ui(self):
        """UIの初期化"""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #495057;
            }
            QLabel {
                color: #495057;
                font-size: 12px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #dee2e6;
                height: 6px;
                background: #f8f9fa;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #007bff;
                border: 1px solid #0056b3;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -6px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #0056b3;
            }
            QCheckBox {
                color: #495057;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #dee2e6;
                background-color: white;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #007bff;
                background-color: #007bff;
                border-radius: 3px;
            }
            QComboBox {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: white;
                color: #495057;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # === メイン有効/無効 ===
        self.main_enabled_cb = QCheckBox("音声エフェクトを有効にする")
        self.main_enabled_cb.setStyleSheet("font-weight: bold; font-size: 13px; color: #007bff;")
        layout.addWidget(self.main_enabled_cb)
        
        # 区切り線
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setStyleSheet("color: #dee2e6;")
        layout.addWidget(divider)
        
        # === エコーエフェクト ===
        echo_group = QGroupBox("エコー")
        echo_layout = QVBoxLayout(echo_group)
        
        self.echo_enabled_cb = QCheckBox("エコーを有効にする")
        echo_layout.addWidget(self.echo_enabled_cb)
        
        # エコー遅延
        echo_delay_layout = QHBoxLayout()
        echo_delay_layout.addWidget(QLabel("遅延:"))
        self.echo_delay_slider = QSlider(Qt.Orientation.Horizontal)
        self.echo_delay_slider.setRange(10, 200)  # 0.1秒〜2.0秒 (×0.01)
        self.echo_delay_slider.setValue(50)  # デフォルト0.5秒
        self.echo_delay_value = QLabel("0.50秒")
        self.echo_delay_value.setMinimumWidth(60)
        echo_delay_layout.addWidget(self.echo_delay_slider)
        echo_delay_layout.addWidget(self.echo_delay_value)
        echo_layout.addLayout(echo_delay_layout)
        
        # エコー減衰
        echo_decay_layout = QHBoxLayout()
        echo_decay_layout.addWidget(QLabel("減衰:"))
        self.echo_decay_slider = QSlider(Qt.Orientation.Horizontal)
        self.echo_decay_slider.setRange(10, 80)  # 0.1〜0.8
        self.echo_decay_slider.setValue(30)  # デフォルト0.3
        self.echo_decay_value = QLabel("0.30")
        self.echo_decay_value.setMinimumWidth(60)
        echo_decay_layout.addWidget(self.echo_decay_slider)
        echo_decay_layout.addWidget(self.echo_decay_value)
        echo_layout.addLayout(echo_decay_layout)
        
        layout.addWidget(echo_group)
        
        # === リバーブエフェクト ===
        reverb_group = QGroupBox("リバーブ")
        reverb_layout = QVBoxLayout(reverb_group)
        
        self.reverb_enabled_cb = QCheckBox("リバーブを有効にする")
        reverb_layout.addWidget(self.reverb_enabled_cb)
        
        # ルームサイズ
        room_size_layout = QHBoxLayout()
        room_size_layout.addWidget(QLabel("部屋の大きさ:"))
        self.room_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.room_size_slider.setRange(10, 100)  # 0.1〜1.0
        self.room_size_slider.setValue(50)  # デフォルト0.5
        self.room_size_value = QLabel("0.50")
        self.room_size_value.setMinimumWidth(60)
        room_size_layout.addWidget(self.room_size_slider)
        room_size_layout.addWidget(self.room_size_value)
        reverb_layout.addLayout(room_size_layout)
        
        # ダンピング
        damping_layout = QHBoxLayout()
        damping_layout.addWidget(QLabel("ダンピング:"))
        self.damping_slider = QSlider(Qt.Orientation.Horizontal)
        self.damping_slider.setRange(10, 90)  # 0.1〜0.9
        self.damping_slider.setValue(30)  # デフォルト0.3
        self.damping_value = QLabel("0.30")
        self.damping_value.setMinimumWidth(60)
        damping_layout.addWidget(self.damping_slider)
        damping_layout.addWidget(self.damping_value)
        reverb_layout.addLayout(damping_layout)
        
        layout.addWidget(reverb_group)
        
        # === フィルターエフェクト ===
        filter_group = QGroupBox("フィルター")
        filter_layout = QVBoxLayout(filter_group)
        
        self.filter_enabled_cb = QCheckBox("フィルターを有効にする")
        filter_layout.addWidget(self.filter_enabled_cb)
        
        # フィルタータイプ
        filter_type_layout = QHBoxLayout()
        filter_type_layout.addWidget(QLabel("種類:"))
        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItems(["ローパス", "ハイパス", "バンドパス"])
        self.filter_type_combo.setCurrentText("ローパス")
        filter_type_layout.addWidget(self.filter_type_combo)
        filter_type_layout.addStretch()
        filter_layout.addLayout(filter_type_layout)
        
        # カットオフ周波数
        cutoff_layout = QHBoxLayout()
        cutoff_layout.addWidget(QLabel("カットオフ:"))
        self.cutoff_slider = QSlider(Qt.Orientation.Horizontal)
        self.cutoff_slider.setRange(100, 2000)  # 1000Hz〜20000Hz (×10)
        self.cutoff_slider.setValue(800)  # デフォルト8000Hz
        self.cutoff_value = QLabel("8000Hz")
        self.cutoff_value.setMinimumWidth(60)
        cutoff_layout.addWidget(self.cutoff_slider)
        cutoff_layout.addWidget(self.cutoff_value)
        filter_layout.addLayout(cutoff_layout)
        
        layout.addWidget(filter_group)
        
        # === ディストーションエフェクト ===
        distortion_group = QGroupBox("ディストーション")
        distortion_layout = QVBoxLayout(distortion_group)
        
        self.distortion_enabled_cb = QCheckBox("ディストーションを有効にする")
        distortion_layout.addWidget(self.distortion_enabled_cb)
        
        # ドライブ
        drive_layout = QHBoxLayout()
        drive_layout.addWidget(QLabel("ドライブ:"))
        self.drive_slider = QSlider(Qt.Orientation.Horizontal)
        self.drive_slider.setRange(10, 200)  # 1.0〜20.0 (×0.1)
        self.drive_slider.setValue(50)  # デフォルト5.0
        self.drive_value = QLabel("5.0dB")
        self.drive_value.setMinimumWidth(60)
        drive_layout.addWidget(self.drive_slider)
        drive_layout.addWidget(self.drive_value)
        distortion_layout.addLayout(drive_layout)
        
        layout.addWidget(distortion_group)
        
        # === プリセット管理 ===
        preset_group = QGroupBox("プリセット")
        preset_layout = QVBoxLayout(preset_group)
        
        preset_buttons_layout = QHBoxLayout()
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["標準", "ホラー", "ファンタジー", "ロボット", "カスタム"])
        preset_buttons_layout.addWidget(self.preset_combo)
        
        self.load_preset_btn = QPushButton("読み込み")
        self.load_preset_btn.setStyleSheet(self._button_style("#007bff", "#0056b3"))
        preset_buttons_layout.addWidget(self.load_preset_btn)
        
        self.save_preset_btn = QPushButton("保存")
        self.save_preset_btn.setStyleSheet(self._button_style("#28a745", "#1e7e34"))
        preset_buttons_layout.addWidget(self.save_preset_btn)
        
        self.reset_btn = QPushButton("リセット")
        self.reset_btn.setStyleSheet(self._button_style("#6c757d", "#545b62"))
        preset_buttons_layout.addWidget(self.reset_btn)
        
        preset_layout.addLayout(preset_buttons_layout)
        layout.addWidget(preset_group)
        
        # 余白追加
        layout.addStretch()
        
        # 初期状態では全て無効
        self.set_controls_enabled(False)
        
    def _button_style(self, bg_color, hover_color):
        """ボタンのスタイルを生成"""
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                padding: 6px 12px;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {hover_color};
            }}
        """
        
    def connect_signals(self):
        """シグナル接続"""
        # メイン有効/無効
        self.main_enabled_cb.toggled.connect(self.on_main_enabled_changed)
        
        # エコー
        self.echo_enabled_cb.toggled.connect(self.emit_settings_changed)
        self.echo_delay_slider.valueChanged.connect(self.update_echo_delay_label)
        self.echo_delay_slider.valueChanged.connect(self.emit_settings_changed)
        self.echo_decay_slider.valueChanged.connect(self.update_echo_decay_label)
        self.echo_decay_slider.valueChanged.connect(self.emit_settings_changed)
        
        # リバーブ
        self.reverb_enabled_cb.toggled.connect(self.emit_settings_changed)
        self.room_size_slider.valueChanged.connect(self.update_room_size_label)
        self.room_size_slider.valueChanged.connect(self.emit_settings_changed)
        self.damping_slider.valueChanged.connect(self.update_damping_label)
        self.damping_slider.valueChanged.connect(self.emit_settings_changed)
        
        # フィルター
        self.filter_enabled_cb.toggled.connect(self.emit_settings_changed)
        self.filter_type_combo.currentTextChanged.connect(self.emit_settings_changed)
        self.cutoff_slider.valueChanged.connect(self.update_cutoff_label)
        self.cutoff_slider.valueChanged.connect(self.emit_settings_changed)
        
        # ディストーション
        self.distortion_enabled_cb.toggled.connect(self.emit_settings_changed)
        self.drive_slider.valueChanged.connect(self.update_drive_label)
        self.drive_slider.valueChanged.connect(self.emit_settings_changed)
        
        # プリセット
        self.load_preset_btn.clicked.connect(self.load_preset)
        self.save_preset_btn.clicked.connect(self.save_preset)
        self.reset_btn.clicked.connect(self.reset_settings)
        
    def on_main_enabled_changed(self, enabled):
        """メインの有効/無効が変更された時"""
        self.set_controls_enabled(enabled)
        self.emit_settings_changed()
        
    def set_controls_enabled(self, enabled):
        """全てのコントロールの有効/無効を設定"""
        controls = [
            self.echo_enabled_cb, self.echo_delay_slider, self.echo_decay_slider,
            self.reverb_enabled_cb, self.room_size_slider, self.damping_slider,
            self.filter_enabled_cb, self.filter_type_combo, self.cutoff_slider,
            self.distortion_enabled_cb, self.drive_slider,
            self.preset_combo, self.load_preset_btn, self.save_preset_btn, self.reset_btn
        ]
        
        for control in controls:
            control.setEnabled(enabled)
    
    def update_echo_delay_label(self, value):
        """エコー遅延ラベルを更新"""
        delay = value * 0.01
        self.echo_delay_value.setText(f"{delay:.2f}秒")
        
    def update_echo_decay_label(self, value):
        """エコー減衰ラベルを更新"""
        decay = value * 0.01
        self.echo_decay_value.setText(f"{decay:.2f}")
        
    def update_room_size_label(self, value):
        """ルームサイズラベルを更新"""
        size = value * 0.01
        self.room_size_value.setText(f"{size:.2f}")
        
    def update_damping_label(self, value):
        """ダンピングラベルを更新"""
        damping = value * 0.01
        self.damping_value.setText(f"{damping:.2f}")
        
    def update_cutoff_label(self, value):
        """カットオフ周波数ラベルを更新"""
        freq = value * 10
        self.cutoff_value.setText(f"{freq}Hz")
        
    def update_drive_label(self, value):
        """ドライブラベルを更新"""
        drive = value * 0.1
        self.drive_value.setText(f"{drive:.1f}dB")
        
    def emit_settings_changed(self):
        """設定変更シグナルを発信"""
        settings = self.get_current_settings()
        self.effects_settings_changed.emit(settings)
        
    def get_current_settings(self):
        """現在の設定を取得"""
        # フィルタータイプの変換
        filter_type_map = {
            "ローパス": "lowpass",
            "ハイパス": "highpass", 
            "バンドパス": "bandpass"
        }
        
        return {
            'enabled': self.main_enabled_cb.isChecked(),
            'echo_enabled': self.echo_enabled_cb.isChecked(),
            'echo_delay': self.echo_delay_slider.value() * 0.01,
            'echo_decay': self.echo_decay_slider.value() * 0.01,
            'reverb_enabled': self.reverb_enabled_cb.isChecked(),
            'reverb_room_size': self.room_size_slider.value() * 0.01,
            'reverb_damping': self.damping_slider.value() * 0.01,
            'filter_enabled': self.filter_enabled_cb.isChecked(),
            'filter_type': filter_type_map.get(self.filter_type_combo.currentText(), "lowpass"),
            'filter_cutoff': self.cutoff_slider.value() * 10,
            'distortion_enabled': self.distortion_enabled_cb.isChecked(),
            'distortion_drive': self.drive_slider.value() * 0.1
        }
        
    def set_settings(self, settings):
        """設定を適用"""
        # フィルタータイプの逆変換
        filter_type_map = {
            "lowpass": "ローパス",
            "highpass": "ハイパス",
            "bandpass": "バンドパス"
        }
        
        # シグナルを一時的に無効化
        self.blockSignals(True)
        
        self.main_enabled_cb.setChecked(settings.get('enabled', False))
        self.echo_enabled_cb.setChecked(settings.get('echo_enabled', False))
        self.echo_delay_slider.setValue(int(settings.get('echo_delay', 0.5) * 100))
        self.echo_decay_slider.setValue(int(settings.get('echo_decay', 0.3) * 100))
        self.reverb_enabled_cb.setChecked(settings.get('reverb_enabled', False))
        self.room_size_slider.setValue(int(settings.get('reverb_room_size', 0.5) * 100))
        self.damping_slider.setValue(int(settings.get('reverb_damping', 0.3) * 100))
        self.filter_enabled_cb.setChecked(settings.get('filter_enabled', False))
        
        filter_type = filter_type_map.get(settings.get('filter_type', 'lowpass'), "ローパス")
        self.filter_type_combo.setCurrentText(filter_type)
        
        self.cutoff_slider.setValue(int(settings.get('filter_cutoff', 8000) / 10))
        self.distortion_enabled_cb.setChecked(settings.get('distortion_enabled', False))
        self.drive_slider.setValue(int(settings.get('distortion_drive', 5.0) * 10))
        
        # ラベルを更新
        self.update_echo_delay_label(self.echo_delay_slider.value())
        self.update_echo_decay_label(self.echo_decay_slider.value())
        self.update_room_size_label(self.room_size_slider.value())
        self.update_damping_label(self.damping_slider.value())
        self.update_cutoff_label(self.cutoff_slider.value())
        self.update_drive_label(self.drive_slider.value())
        
        # コントロールの有効/無効を設定
        self.set_controls_enabled(settings.get('enabled', False))
        
        # シグナルを再有効化
        self.blockSignals(False)
        
    def load_preset(self):
        """プリセット読み込み"""
        preset_name = self.preset_combo.currentText()
        
        presets = {
            "標準": self.default_settings.copy(),
            "ホラー": {
                'enabled': True,
                'echo_enabled': True, 'echo_delay': 0.8, 'echo_decay': 0.5,
                'reverb_enabled': True, 'reverb_room_size': 0.9, 'reverb_damping': 0.2,
                'filter_enabled': True, 'filter_type': 'lowpass', 'filter_cutoff': 3000,
                'distortion_enabled': True, 'distortion_drive': 8.0
            },
            "ファンタジー": {
                'enabled': True,
                'echo_enabled': True, 'echo_delay': 0.3, 'echo_decay': 0.2,
                'reverb_enabled': True, 'reverb_room_size': 0.7, 'reverb_damping': 0.4,
                'filter_enabled': False, 'filter_type': 'lowpass', 'filter_cutoff': 8000,
                'distortion_enabled': False, 'distortion_drive': 5.0
            },
            "ロボット": {
                'enabled': True,
                'echo_enabled': False, 'echo_delay': 0.5, 'echo_decay': 0.3,
                'reverb_enabled': False, 'reverb_room_size': 0.5, 'reverb_damping': 0.3,
                'filter_enabled': True, 'filter_type': 'lowpass', 'filter_cutoff': 2000,
                'distortion_enabled': True, 'distortion_drive': 12.0
            }
        }
        
        if preset_name in presets:
            self.set_settings(presets[preset_name])
            print(f"🎛️ プリセット '{preset_name}' を読み込みました")
        
    def save_preset(self):
        """プリセット保存（将来の拡張用）"""
        # TODO: カスタムプリセットの保存機能を実装
        print("💾 プリセット保存機能は今後実装予定です")
        
    def reset_settings(self):
        """設定をリセット"""
        self.set_settings(self.default_settings.copy())
        print("🔄 エフェクト設定をリセットしました")
        
    def is_effects_enabled(self):
        """エフェクトが有効かどうかを返す"""
        return self.main_enabled_cb.isChecked()