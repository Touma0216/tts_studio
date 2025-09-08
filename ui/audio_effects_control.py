# ui/audio_effects_control.py (完全版 - 音声エフェクト｜環境エフェクト)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTabWidget, QFrame, QSlider, QGroupBox, QGridLayout, QDoubleSpinBox)
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
    """音声エフェクト制御ウィジェット（音声エフェクト｜環境エフェクト）"""
    
    effects_settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.default_settings = {
            # 音声エフェクト
            'robot_enabled': False,
            'robot_intensity': 0.5,
            'distortion_enabled': False,
            'distortion_intensity': 0.4,
            'voice_change_enabled': False,
            'voice_change_intensity': 0.0,  # 半音単位
            'echo_enabled': False,
            'echo_intensity': 0.3,
            # 環境エフェクト
            'phone_enabled': False,
            'phone_intensity': 0.5,
            'through_wall_enabled': False,
            'through_wall_intensity': 0.3,
            'reverb_enabled': False,
            'reverb_intensity': 0.5
        }
        
        self.init_ui()
        
    def init_ui(self):
        """UIの初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # タブウィジェット（音声エフェクト｜環境エフェクト）
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
        
        # 2. 環境エフェクトタブ
        environmental_effects_tab = self.create_environmental_effects_tab()
        self.effects_tab_widget.addTab(environmental_effects_tab, "環境エフェクト")
        
        layout.addWidget(self.effects_tab_widget)
        
    def create_audio_effects_tab(self):
        """音声エフェクトタブを作成（声質変更系）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 音声エフェクト全体のグループ
        effects_group = QGroupBox("音声エフェクト")
        effects_group.setStyleSheet("""
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
        
        # GridLayoutで音声パラメータと同じ形式に
        effects_layout = QGridLayout(effects_group)
        effects_layout.setSpacing(8)
        
        # スライダースタイル（音声パラメータと統一）
        slider_style = """
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #66e, stop: 1 #bbf);
                border: 1px solid #777;
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
        """
        
        # 音声エフェクト設定：(名前, key, 最小値, 最大値, デフォルト値, 説明)
        audio_effects_params = [
            ("ロボット音声", "robot", 0.0, 1.0, 0.5, "人間 ← → ロボット"),
            ("ディストーション", "distortion", 0.1, 1.0, 0.4, "クリア ← → 歪み"),
            ("ボイスチェンジ", "voice_change", -12.0, 12.0, 0.0, "低音 ← → 高音"),
            ("やまびこ", "echo", 0.1, 1.0, 0.3, "弱い ← → 強い")
        ]
        
        # 各エフェクトを作成
        for i, (name, key, min_val, max_val, default, desc) in enumerate(audio_effects_params):
            # 名前ラベル
            label = QLabel(name + ":")
            label.setFont(QFont("", 12, QFont.Weight.Bold))
            label.setMinimumWidth(100)
            
            # スライダー
            slider = QSlider(Qt.Orientation.Horizontal)
            if key == "voice_change":  # ボイスチェンジは半音単位
                slider.setRange(int(min_val), int(max_val))
                slider.setValue(int(default))
            else:
                slider.setRange(int(min_val * 100), int(max_val * 100))
                slider.setValue(int(default * 100))
            slider.setStyleSheet(slider_style)
            
            # 数値入力（SpinBox）
            spinbox = QDoubleSpinBox()
            spinbox.setRange(min_val, max_val)
            if key == "voice_change":
                spinbox.setSingleStep(1.0)
                spinbox.setDecimals(0)
                spinbox.setSuffix(" 半音")
            else:
                spinbox.setSingleStep(0.01)
                spinbox.setDecimals(2)
            spinbox.setValue(default)
            spinbox.setFixedWidth(90)
            
            # 説明ラベル
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #666; font-size: 9pt;")
            
            # ON/OFFトグルスイッチ
            toggle = ToggleSwitchWidget(False)
            
            # シグナル接続
            if key == "robot":
                self.robot_slider = slider
                self.robot_spinbox = spinbox
                self.robot_toggle = toggle
                slider.valueChanged.connect(self.on_robot_slider_changed)
                spinbox.valueChanged.connect(self.on_robot_spinbox_changed)
                toggle.toggled.connect(self.emit_settings_changed)
            elif key == "distortion":
                self.distortion_slider = slider
                self.distortion_spinbox = spinbox
                self.distortion_toggle = toggle
                slider.valueChanged.connect(self.on_distortion_slider_changed)
                spinbox.valueChanged.connect(self.on_distortion_spinbox_changed)
                toggle.toggled.connect(self.emit_settings_changed)
            elif key == "voice_change":
                self.voice_change_slider = slider
                self.voice_change_spinbox = spinbox
                self.voice_change_toggle = toggle
                slider.valueChanged.connect(self.on_voice_change_slider_changed)
                spinbox.valueChanged.connect(self.on_voice_change_spinbox_changed)
                toggle.toggled.connect(self.emit_settings_changed)
            elif key == "echo":
                self.echo_slider = slider
                self.echo_spinbox = spinbox
                self.echo_toggle = toggle
                slider.valueChanged.connect(self.on_echo_slider_changed)
                spinbox.valueChanged.connect(self.on_echo_spinbox_changed)
                toggle.toggled.connect(self.emit_settings_changed)
            
            # GridLayoutに配置：名前 | スライダー | 数値 | 説明 | ON/OFF
            effects_layout.addWidget(label, i, 0)
            effects_layout.addWidget(slider, i, 1)
            effects_layout.addWidget(spinbox, i, 2)
            effects_layout.addWidget(desc_label, i, 3)
            effects_layout.addWidget(toggle, i, 4)
        
        layout.addWidget(effects_group)
        layout.addStretch()
        
        return widget
        
    def create_environmental_effects_tab(self):
        """環境エフェクトタブを作成（空間・状況再現系）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 環境エフェクト全体のグループ
        env_effects_group = QGroupBox("環境エフェクト")
        env_effects_group.setStyleSheet("""
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
        
        # GridLayoutで音声パラメータと同じ形式に
        env_effects_layout = QGridLayout(env_effects_group)
        env_effects_layout.setSpacing(8)
        
        # スライダースタイル（音声パラメータと統一）
        slider_style = """
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #66e, stop: 1 #bbf);
                border: 1px solid #777;
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
        """
        
        # 環境エフェクト設定：(名前, key, 最小値, 最大値, デフォルト値, 説明)
        env_effects_params = [
            ("電話音声", "phone", 0.0, 1.0, 0.5, "通常 ← → 電話音質"),
            ("壁越し音声", "through_wall", 0.0, 1.0, 0.3, "直接 ← → 壁越し"),
            ("閉鎖空間", "reverb", 0.1, 1.0, 0.5, "ドライ ← → 残響")
        ]
        
        # 各環境エフェクトを作成
        for i, (name, key, min_val, max_val, default, desc) in enumerate(env_effects_params):
            # 名前ラベル
            label = QLabel(name + ":")
            label.setFont(QFont("", 12, QFont.Weight.Bold))
            label.setMinimumWidth(100)
            
            # スライダー
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(int(min_val * 100), int(max_val * 100))
            slider.setValue(int(default * 100))
            slider.setStyleSheet(slider_style)
            
            # 数値入力（SpinBox）
            spinbox = QDoubleSpinBox()
            spinbox.setRange(min_val, max_val)
            spinbox.setSingleStep(0.01)
            spinbox.setValue(default)
            spinbox.setDecimals(2)
            spinbox.setFixedWidth(90)
            
            # 説明ラベル
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #666; font-size: 9pt;")
            
            # ON/OFFトグルスイッチ
            toggle = ToggleSwitchWidget(False)
            
            # シグナル接続
            if key == "phone":
                self.phone_slider = slider
                self.phone_spinbox = spinbox
                self.phone_toggle = toggle
                slider.valueChanged.connect(self.on_phone_slider_changed)
                spinbox.valueChanged.connect(self.on_phone_spinbox_changed)
                toggle.toggled.connect(self.emit_settings_changed)
            elif key == "through_wall":
                self.through_wall_slider = slider
                self.through_wall_spinbox = spinbox
                self.through_wall_toggle = toggle
                slider.valueChanged.connect(self.on_through_wall_slider_changed)
                spinbox.valueChanged.connect(self.on_through_wall_spinbox_changed)
                toggle.toggled.connect(self.emit_settings_changed)
            elif key == "reverb":
                self.reverb_slider = slider
                self.reverb_spinbox = spinbox
                self.reverb_toggle = toggle
                slider.valueChanged.connect(self.on_reverb_slider_changed)
                spinbox.valueChanged.connect(self.on_reverb_spinbox_changed)
                toggle.toggled.connect(self.emit_settings_changed)
            
            # GridLayoutに配置：名前 | スライダー | 数値 | 説明 | ON/OFF
            env_effects_layout.addWidget(label, i, 0)
            env_effects_layout.addWidget(slider, i, 1)
            env_effects_layout.addWidget(spinbox, i, 2)
            env_effects_layout.addWidget(desc_label, i, 3)
            env_effects_layout.addWidget(toggle, i, 4)
        
        layout.addWidget(env_effects_group)
        layout.addStretch()
        
        return widget
    
    # ================================
    # 音声エフェクトパラメータ変更処理
    # ================================
    
    def on_robot_slider_changed(self, value):
        """ロボット音声スライダー変更時"""
        float_value = value / 100.0
        self.robot_spinbox.blockSignals(True)
        self.robot_spinbox.setValue(float_value)
        self.robot_spinbox.blockSignals(False)
        self.emit_settings_changed()
        
    # ================================
    # リセット機能
    # ================================
    
    def reset_audio_effects(self):
        """音声エフェクトをデフォルト値にリセット"""
        try:
            self.blockSignals(True)
            
            # ロボット音声
            self.robot_toggle.setChecked(False)
            self.robot_slider.setValue(int(0.5 * 100))
            self.robot_spinbox.setValue(0.5)
            
            # ディストーション
            self.distortion_toggle.setChecked(False)
            self.distortion_slider.setValue(int(0.4 * 100))
            self.distortion_spinbox.setValue(0.4)
            
            # ボイスチェンジ
            self.voice_change_toggle.setChecked(False)
            self.voice_change_slider.setValue(0)
            self.voice_change_spinbox.setValue(0.0)
            
            # やまびこ
            self.echo_toggle.setChecked(False)
            self.echo_slider.setValue(int(0.3 * 100))
            self.echo_spinbox.setValue(0.3)
            
            self.blockSignals(False)
            self.emit_settings_changed()
            
            print("🔄 音声エフェクトをリセットしました")
            
        except Exception as e:
            print(f"音声エフェクトリセットエラー: {e}")
    
    def reset_environmental_effects(self):
        """環境エフェクトをデフォルト値にリセット"""
        try:
            self.blockSignals(True)
            
            # 電話音声
            self.phone_toggle.setChecked(False)
            self.phone_slider.setValue(int(0.5 * 100))
            self.phone_spinbox.setValue(0.5)
            
            # 壁越し音声
            self.through_wall_toggle.setChecked(False)
            self.through_wall_slider.setValue(int(0.3 * 100))
            self.through_wall_spinbox.setValue(0.3)
            
            # 閉鎖空間
            self.reverb_toggle.setChecked(False)
            self.reverb_slider.setValue(int(0.5 * 100))
            self.reverb_spinbox.setValue(0.5)
            
            self.blockSignals(False)
            self.emit_settings_changed()
            
            print("🔄 環境エフェクトをリセットしました")
            
        except Exception as e:
            print(f"環境エフェクトリセットエラー: {e}")
    
    def reset_all_effects(self):
        """全エフェクトをリセット（外部から呼び出し可能）"""
        self.reset_audio_effects()
        self.reset_environmental_effects()
        print("🔄 全エフェクトをリセットしました")
    
    def on_robot_spinbox_changed(self, value):
        """ロボット音声SpinBox変更時"""
        int_value = int(value * 100)
        self.robot_slider.blockSignals(True)
        self.robot_slider.setValue(int_value)
        self.robot_slider.blockSignals(False)
        self.emit_settings_changed()
    
    def on_distortion_slider_changed(self, value):
        """ディストーションスライダー変更時"""
        float_value = value / 100.0
        self.distortion_spinbox.blockSignals(True)
        self.distortion_spinbox.setValue(float_value)
        self.distortion_spinbox.blockSignals(False)
        self.emit_settings_changed()
    
    def on_distortion_spinbox_changed(self, value):
        """ディストーションSpinBox変更時"""
        int_value = int(value * 100)
        self.distortion_slider.blockSignals(True)
        self.distortion_slider.setValue(int_value)
        self.distortion_slider.blockSignals(False)
        self.emit_settings_changed()
    
    def on_voice_change_slider_changed(self, value):
        """ボイスチェンジスライダー変更時"""
        float_value = float(value)  # 半音単位なのでそのまま
        self.voice_change_spinbox.blockSignals(True)
        self.voice_change_spinbox.setValue(float_value)
        self.voice_change_spinbox.blockSignals(False)
        self.emit_settings_changed()
    
    def on_voice_change_spinbox_changed(self, value):
        """ボイスチェンジSpinBox変更時"""
        int_value = int(value)
        self.voice_change_slider.blockSignals(True)
        self.voice_change_slider.setValue(int_value)
        self.voice_change_slider.blockSignals(False)
        self.emit_settings_changed()
    
    def on_echo_slider_changed(self, value):
        """やまびこスライダー変更時"""
        float_value = value / 100.0
        self.echo_spinbox.blockSignals(True)
        self.echo_spinbox.setValue(float_value)
        self.echo_spinbox.blockSignals(False)
        self.emit_settings_changed()
    
    def on_echo_spinbox_changed(self, value):
        """やまびこSpinBox変更時"""
        int_value = int(value * 100)
        self.echo_slider.blockSignals(True)
        self.echo_slider.setValue(int_value)
        self.echo_slider.blockSignals(False)
        self.emit_settings_changed()
    
    # ================================
    # 環境エフェクトパラメータ変更処理
    # ================================
    
    def on_phone_slider_changed(self, value):
        """電話音声スライダー変更時"""
        float_value = value / 100.0
        self.phone_spinbox.blockSignals(True)
        self.phone_spinbox.setValue(float_value)
        self.phone_spinbox.blockSignals(False)
        self.emit_settings_changed()
    
    def on_phone_spinbox_changed(self, value):
        """電話音声SpinBox変更時"""
        int_value = int(value * 100)
        self.phone_slider.blockSignals(True)
        self.phone_slider.setValue(int_value)
        self.phone_slider.blockSignals(False)
        self.emit_settings_changed()
    
    def on_through_wall_slider_changed(self, value):
        """壁越し音声スライダー変更時"""
        float_value = value / 100.0
        self.through_wall_spinbox.blockSignals(True)
        self.through_wall_spinbox.setValue(float_value)
        self.through_wall_spinbox.blockSignals(False)
        self.emit_settings_changed()
    
    def on_through_wall_spinbox_changed(self, value):
        """壁越し音声SpinBox変更時"""
        int_value = int(value * 100)
        self.through_wall_slider.blockSignals(True)
        self.through_wall_slider.setValue(int_value)
        self.through_wall_slider.blockSignals(False)
        self.emit_settings_changed()

    def on_reverb_slider_changed(self, value):
        """リバーブスライダー変更時"""
        float_value = value / 100.0
        self.reverb_spinbox.blockSignals(True)
        self.reverb_spinbox.setValue(float_value)
        self.reverb_spinbox.blockSignals(False)
        self.emit_settings_changed()
    
    def on_reverb_spinbox_changed(self, value):
        """リバーブSpinBox変更時"""
        int_value = int(value * 100)
        self.reverb_slider.blockSignals(True)
        self.reverb_slider.setValue(int_value)
        self.reverb_slider.blockSignals(False)
        self.emit_settings_changed()
        
    def emit_settings_changed(self):
        """設定変更シグナルを発信（サイレント）"""
        settings = self.get_current_settings()
        self.effects_settings_changed.emit(settings)
    
    # ================================
    # 設定管理メソッド
    # ================================
        
    def get_current_settings(self):
        """現在の設定を取得"""
        return {
            # 音声エフェクト
            'robot_enabled': self.robot_toggle.isChecked(),
            'robot_intensity': self.robot_spinbox.value(),
            'distortion_enabled': self.distortion_toggle.isChecked(),
            'distortion_intensity': self.distortion_spinbox.value(),
            'voice_change_enabled': self.voice_change_toggle.isChecked(),
            'voice_change_intensity': self.voice_change_spinbox.value(),
            'echo_enabled': self.echo_toggle.isChecked(),
            'echo_intensity': self.echo_spinbox.value(),
            # 環境エフェクト
            'phone_enabled': self.phone_toggle.isChecked(),
            'phone_intensity': self.phone_spinbox.value(),
            'through_wall_enabled': self.through_wall_toggle.isChecked(),
            'through_wall_intensity': self.through_wall_spinbox.value(),
            'reverb_enabled': self.reverb_toggle.isChecked(),
            'reverb_intensity': self.reverb_spinbox.value()
        }
        
    def set_settings(self, settings):
        """設定を適用"""
        self.blockSignals(True)
        
        # 音声エフェクト
        # ロボット音声
        self.robot_toggle.setChecked(settings.get('robot_enabled', False))
        robot_intensity = settings.get('robot_intensity', 0.5)
        self.robot_slider.setValue(int(robot_intensity * 100))
        self.robot_spinbox.setValue(robot_intensity)
        
        # ディストーション
        self.distortion_toggle.setChecked(settings.get('distortion_enabled', False))
        distortion_intensity = settings.get('distortion_intensity', 0.4)
        self.distortion_slider.setValue(int(distortion_intensity * 100))
        self.distortion_spinbox.setValue(distortion_intensity)
        
        # ボイスチェンジ
        self.voice_change_toggle.setChecked(settings.get('voice_change_enabled', False))
        voice_change_intensity = settings.get('voice_change_intensity', 0.0)
        self.voice_change_slider.setValue(int(voice_change_intensity))
        self.voice_change_spinbox.setValue(voice_change_intensity)
        
        # やまびこ
        self.echo_toggle.setChecked(settings.get('echo_enabled', False))
        echo_intensity = settings.get('echo_intensity', 0.3)
        self.echo_slider.setValue(int(echo_intensity * 100))
        self.echo_spinbox.setValue(echo_intensity)
        
        # 環境エフェクト
        # 電話音声
        self.phone_toggle.setChecked(settings.get('phone_enabled', False))
        phone_intensity = settings.get('phone_intensity', 0.5)
        self.phone_slider.setValue(int(phone_intensity * 100))
        self.phone_spinbox.setValue(phone_intensity)
        
        # 壁越し音声
        self.through_wall_toggle.setChecked(settings.get('through_wall_enabled', False))
        through_wall_intensity = settings.get('through_wall_intensity', 0.3)
        self.through_wall_slider.setValue(int(through_wall_intensity * 100))
        self.through_wall_spinbox.setValue(through_wall_intensity)
        
        # 閉鎖空間
        self.reverb_toggle.setChecked(settings.get('reverb_enabled', False))
        reverb_intensity = settings.get('reverb_intensity', 0.5)
        self.reverb_slider.setValue(int(reverb_intensity * 100))
        self.reverb_spinbox.setValue(reverb_intensity)
        
        self.blockSignals(False)
        
    def is_effects_enabled(self):
        """エフェクトが有効かどうか"""
        return (# 音声エフェクト
                self.robot_toggle.isChecked() or 
                self.distortion_toggle.isChecked() or 
                self.voice_change_toggle.isChecked() or
                self.echo_toggle.isChecked() or
                # 環境エフェクト
                self.phone_toggle.isChecked() or
                self.through_wall_toggle.isChecked() or
                self.reverb_toggle.isChecked())