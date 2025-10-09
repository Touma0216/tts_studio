# ui/tabbed_modeling_control.py（ほのか専用・物理演算対応版）
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QGroupBox, QSlider, QLabel, QPushButton, QTabWidget,
                             QGridLayout, QDoubleSpinBox, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from copy import deepcopy
from typing import Dict, List, Any

from .history_manager import ParameterHistory

class TabbedModelingControl(QWidget):
    """零音ほのか専用モデリング制御（物理演算対応版）"""
    parameter_changed = pyqtSignal(str, float)
    parameters_changed = pyqtSignal(dict)
    
    # ドラッグ制御用シグナル
    drag_control_toggled = pyqtSignal(bool)
    drag_sensitivity_changed = pyqtSignal(float)
    
    # アイドルモーション用シグナル
    idle_motion_toggled = pyqtSignal(str, bool)
    idle_motion_param_changed = pyqtSignal(str, float)
    
    # 🆕 物理演算用シグナル
    physics_toggled = pyqtSignal(bool)
    physics_weight_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parameter_sliders = {}
        self.physics_sliders = {}  # 🆕 物理演算制御用スライダー
        self.is_loading = False
        self.physics_enabled = True  # 🆕 物理演算の状態

        from core.animation_manager import AnimationManager
        self.animation_manager = AnimationManager("animations")
        
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.emit_all_parameters)
        
        self.init_ui()

        # Undo/Redo 用履歴初期化
        self.history = ParameterHistory(max_history=20)
        self._history_timer = QTimer(self)
        self._history_timer.setSingleShot(True)
        self._history_timer.timeout.connect(self._commit_pending_history)
        self._pending_before_state: Dict[str, Any] | None = None
        self._applying_history = False
        self._last_committed_state = self._capture_state()
        self.history.save_current_state(self._last_committed_state)

        # 🔥 追加：瞬きと視線をデフォルトでON
        QTimer.singleShot(200, lambda: self.idle_motion_toggled.emit("blink", True))
        QTimer.singleShot(200, lambda: self.idle_motion_toggled.emit("gaze", True))
        
        # 初期化後、ドラッグ制御を有効化
        QTimer.singleShot(100, lambda: self.on_drag_toggle(True))

        QTimer.singleShot(300, self._activate_default_idle_motions)

    def _activate_default_idle_motions(self):
        """デフォルトのアイドルモーションを起動（風揺れ追加）"""
        try:
            print("🌟 デフォルトアイドルモーション起動開始")
            
            # 瞬きON
            if hasattr(self, 'blink_checkbox') and self.blink_checkbox.isChecked():
                print("  → 瞬きシグナル発火")
                self.idle_motion_toggled.emit("blink", True)
            
            # 視線揺れON
            if hasattr(self, 'gaze_checkbox') and self.gaze_checkbox.isChecked():
                print("  → 視線揺れシグナル発火")
                self.idle_motion_toggled.emit("gaze", True)
            
            # 🔥 追加：風揺れON
            if hasattr(self, 'wind_checkbox') and self.wind_checkbox.isChecked():
                print("  → 風揺れシグナル発火")
                self.idle_motion_toggled.emit("wind", True)
                # 風の強度も設定
                if hasattr(self, 'wind_strength_slider'):
                    self.on_wind_strength_slider_changed(self.wind_strength_slider.value())                
            print("✅ デフォルトアイドルモーション起動完了")
            
        except Exception as e:
            print(f"⚠️ デフォルトモーション起動エラー: {e}")

    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # ヘッダー
        header = QHBoxLayout()
        title = QLabel("🎨 モデリング制御")
        title.setFont(QFont("", 12, QFont.Weight.Bold))
        
        self.reset_btn = QPushButton("🔄 全リセット")
        self.reset_btn.setFixedHeight(35)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5722;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #f4511e; }
        """)
        self.reset_btn.clicked.connect(self.reset_all)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.reset_btn)
        
        # タブ
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ccc;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #5ba8f2;
                color: white;
            }
        """)
        
        self.tabs.addTab(self.create_face_tab(), "😊 顔")
        self.tabs.addTab(self.create_body_tab(), "🧍 体")
        self.tabs.addTab(self.create_emotion_tab(), "🎭 感情")
        self.tabs.addTab(self.create_motion_tab(), "🎬 モーション")
        self.tabs.addTab(self.create_animation_tab(), "🎞️ アニメーション")
        
        main_layout.addLayout(header)
        main_layout.addWidget(self.tabs, 1)
    
    def create_face_tab(self):
        """顔の制御タブ"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: white; }")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)
        
        # 顔の角度
        face_params = [
            ("角度X", "ParamAngleX", -30.0, 30.0, 0.0, "左 ← → 右"),
            ("角度Y", "ParamAngleY", -30.0, 30.0, 0.0, "下 ← → 上"),
            ("角度Z", "ParamAngleZ", -30.0, 30.0, 0.0, "左傾き ← → 右傾き")
        ]
        self.create_parameter_group(content_layout, "顔の角度", face_params)
        
        # 目
        eye_params = [
            ("左目 開閉", "ParamEyeLOpen", 0.0, 1.0, 1.0, "閉じ ← → 開き"),
            ("右目 開閉", "ParamEyeROpen", 0.0, 1.0, 1.0, "閉じ ← → 開き"),
        ]
        self.create_parameter_group(content_layout, "目", eye_params)
        
        # 目玉
        eyeball_params = [
            ("目玉 X", "ParamEyeBallX", -1.0, 1.0, 0.0, "左 ← → 右"),
            ("目玉 Y", "ParamEyeBallY", -1.0, 1.0, 0.0, "下 ← → 上")
        ]
        self.create_parameter_group(content_layout, "目玉", eyeball_params)
        
        # 眉
        brow_params = [
            ("左眉 上下", "ParamBrowLY", -1.0, 1.0, 0.0, "下 ← → 上"),
            ("右眉 上下", "ParamBrowRY", -1.0, 1.0, 0.0, "下 ← → 上")
        ]
        self.create_parameter_group(content_layout, "眉", brow_params)
        
        # 口
        mouth_params = [
            ("口 開閉", "ParamMouthOpenY", 0.0, 1.0, 0.0, "閉じ ← → 開き"),
            ("口 変形", "ParamMouthForm", -1.0, 1.0, 0.0, "怒り ← → 笑顔")
        ]
        self.create_parameter_group(content_layout, "口", mouth_params)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        return widget
    
    def create_body_tab(self):
        """体の制御タブ"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: white; }")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)
        
        # 呼吸
        breath_params = [
            ("呼吸", "ParamBreath", 0.0, 1.0, 0.0, "吐く ← → 吸う")
        ]
        self.create_parameter_group(content_layout, "呼吸", breath_params)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        return widget
    
    def create_emotion_tab(self):
        """感情制御タブ（スライダー削除版）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: white; }")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)
        
        # 説明
        info_label = QLabel("💡 表情プリセットボタンで感情表現を切り替えできます")
        info_label.setStyleSheet("""
            color: #5ba8f2;
            background-color: #e3f2fd;
            padding: 10px;
            border-radius: 6px;
            font-weight: bold;
        """)
        info_label.setWordWrap(True)
        content_layout.addWidget(info_label)
        
        # 表情プリセット
        preset_group = QGroupBox("表情プリセット")
        preset_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a90e2;
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
                color: #4a90e2;
            }
        """)
        
        preset_layout = QVBoxLayout(preset_group)
        
        # デフォルト表情ボタン
        default_btn = QPushButton("😐 デフォルト表情")
        default_btn.setMinimumHeight(45)
        default_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e8f4f8, stop:1 #d0e8f0);
                border: 2px solid #4a90e2;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
                color: #2c5898;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #d0e8f0, stop:1 #b8dce8);
            }
        """)
        default_btn.clicked.connect(self.reset_expression)
        preset_layout.addWidget(default_btn)
        
        # Scene1-4の表情ボタン
        expression_buttons_layout = QGridLayout()
        expression_buttons_layout.setSpacing(10)
        
        expression_names = [
            ("Scene1", "😄 喜び"),
            ("Scene2", "😲 驚き"),
            ("Scene3", "😨 恐怖"),
            ("Scene4", "😢 悲しみ")
        ]
        
        for i, (scene_id, label) in enumerate(expression_names):
            btn = QPushButton(label)
            btn.setMinimumHeight(50)
            btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #fff, stop:1 #f0f0f0);
                    border: 2px solid #ccc;
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: bold;
                    color: #333;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #fffacd, stop:1 #ffd700);
                    border-color: #ffa500;
                }
            """)
            btn.clicked.connect(lambda checked, sid=scene_id: self.set_expression(sid))
            
            row = i // 2
            col = i % 2
            expression_buttons_layout.addWidget(btn, row, col)
        
        preset_layout.addLayout(expression_buttons_layout)
        
        content_layout.addWidget(preset_group)
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        return widget
    
    def create_motion_tab(self):
        """モーションタブ（手動制御スライダー常時表示版）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: white; }")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(15)
        
        # 🎮 手動制御セクション（常時表示）
        manual_group = QGroupBox("🎮 手動制御")
        manual_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4caf50;
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
                color: #4caf50;
            }
        """)
        
        manual_layout = QVBoxLayout(manual_group)
        
        slider_style = """
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #81c784, stop:1 #4caf50);
                border: 1px solid #777;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #eee, stop:1 #ccc);
                border: 1px solid #777;
                width: 18px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 9px;
            }
        """
        
        # 髪・胸・瞳の手動制御パラメータ
        manual_params = [
            ("髪揺れ 前", "ParamHairFront", -1.0, 1.0, 0.0, "左 ← → 右"),
            ("髪揺れ 横", "ParamHairSide", -1.0, 1.0, 0.0, "左 ← → 右"),
            ("胸揺れ 横", "ParamHairBack", -1.0, 1.0, 0.0, "左 ← → 右"),
            ("胸揺れ 縦", "Param", -1.0, 1.0, 0.0, "下 ← → 上"),
            ("右目 瞳孔", "Param5", -1.0, 1.0, 0.0, "小 ← → 大"),
            ("右目 ハイライト", "Param6", -1.0, 1.0, 0.0, "暗 ← → 明"),
            ("左目 瞳孔", "Param7", -1.0, 1.0, 0.0, "小 ← → 大"),
            ("左目 ハイライト", "Param8", -1.0, 1.0, 0.0, "暗 ← → 明")
        ]
        
        grid = QGridLayout()
        grid.setSpacing(8)
        
        for i, (name, param_id, min_val, max_val, default, desc) in enumerate(manual_params):
            # 名前
            label = QLabel(name + ":")
            label.setFont(QFont("", 10, QFont.Weight.Bold))
            label.setMinimumWidth(100)
            
            # スライダー
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(int(min_val * 100), int(max_val * 100))
            slider.setValue(int(default * 100))
            slider.setStyleSheet(slider_style)
            
            # 数値
            spinbox = QDoubleSpinBox()
            spinbox.setRange(min_val, max_val)
            spinbox.setSingleStep(0.01)
            spinbox.setValue(default)
            spinbox.setDecimals(2)
            spinbox.setFixedWidth(70)
            
            # 説明
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #666; font-size: 9pt;")
            
            # リセット
            reset = QPushButton("↺")
            reset.setFixedSize(28, 28)
            reset.setToolTip(f"デフォルト: {default:.2f}")
            reset.setStyleSheet("""
                QPushButton {
                    background: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover { background: #e0e0e0; }
            """)
            
            # 保存
            self.parameter_sliders[param_id] = (slider, spinbox, default)
            
            # シグナル
            slider.valueChanged.connect(lambda v, pid=param_id: self.on_slider_changed(pid, v))
            spinbox.valueChanged.connect(lambda v, pid=param_id: self.on_spinbox_changed(pid, v))
            reset.clicked.connect(lambda _, pid=param_id: self.reset_param(pid))
            
            # 配置
            grid.addWidget(label, i, 0)
            grid.addWidget(slider, i, 1)
            grid.addWidget(spinbox, i, 2)
            grid.addWidget(desc_label, i, 3)
            grid.addWidget(reset, i, 4)
        
        manual_layout.addLayout(grid)
        content_layout.addWidget(manual_group)
        
        # ドラッグ制御セクション
        drag_group = QGroupBox("🎯 ドラッグ制御")
        drag_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #9c27b0;
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
                color: #9c27b0;
            }
        """)
        
        drag_layout = QVBoxLayout(drag_group)
        
        # ON/OFFトグル
        self.drag_toggle_btn = QPushButton("🎮 ドラッグ制御 ON")
        self.drag_toggle_btn.setCheckable(True)
        self.drag_toggle_btn.setChecked(True)
        self.drag_toggle_btn.setMinimumHeight(50)
        self.drag_toggle_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f0f0f0, stop:1 #d0d0d0);
                border: 2px solid #999;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                color: #666;
            }
            QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ba68c8, stop:1 #9c27b0);
                border-color: #7b1fa2;
                color: white;
            }
        """)
        self.drag_toggle_btn.toggled.connect(self.on_drag_toggle)
        drag_layout.addWidget(self.drag_toggle_btn)
        
        # 感度調整
        sensitivity_layout = QHBoxLayout()
        sensitivity_label = QLabel("感度:")
        sensitivity_label.setFont(QFont("", 11, QFont.Weight.Bold))
        sensitivity_label.setMinimumWidth(60)
        
        self.drag_sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.drag_sensitivity_slider.setRange(10, 100)
        self.drag_sensitivity_slider.setValue(30)
        self.drag_sensitivity_slider.setEnabled(True)
        self.drag_sensitivity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ba68c8, stop:1 #9c27b0);
                border: 1px solid #777;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #eee, stop:1 #ccc);
                border: 1px solid #777;
                width: 18px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 9px;
            }
        """)
        self.drag_sensitivity_slider.valueChanged.connect(self.on_sensitivity_changed)
        
        self.drag_sensitivity_value = QLabel("0.30")
        self.drag_sensitivity_value.setFont(QFont("", 11, QFont.Weight.Bold))
        self.drag_sensitivity_value.setMinimumWidth(50)
        self.drag_sensitivity_value.setStyleSheet("color: #9c27b0;")
        
        sensitivity_layout.addWidget(sensitivity_label)
        sensitivity_layout.addWidget(self.drag_sensitivity_slider)
        sensitivity_layout.addWidget(self.drag_sensitivity_value)
        drag_layout.addLayout(sensitivity_layout)
        
        # リセットボタン
        self.drag_reset_btn = QPushButton("↺ 角度リセット")
        self.drag_reset_btn.setMinimumHeight(40)
        self.drag_reset_btn.setEnabled(True)
        self.drag_reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 2px solid #ccc;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                color: #666;
            }
            QPushButton:enabled {
                background-color: white;
                border-color: #9c27b0;
                color: #9c27b0;
            }
            QPushButton:hover:enabled {
                background-color: #f3e5f5;
            }
        """)
        self.drag_reset_btn.clicked.connect(self.on_drag_reset)
        drag_layout.addWidget(self.drag_reset_btn)
        
        content_layout.addWidget(drag_group)
        
        # アイドルモーションセクション
        idle_group = QGroupBox("🌟 アイドルモーション")
        idle_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ff9800;
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
                color: #ff9800;
            }
        """)
        
        idle_layout = QVBoxLayout(idle_group)
        
        # 瞬き
        self.blink_checkbox = QCheckBox("👁️ 瞬き")
        self.blink_checkbox.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.blink_checkbox.setChecked(True)
        self.blink_checkbox.toggled.connect(lambda checked: self._emit_idle_motion_toggle("blink", checked))
        idle_layout.addWidget(self.blink_checkbox)
        
        blink_param_layout = QHBoxLayout()
        blink_param_layout.addWidget(QLabel("  周期:"))
        self.blink_period_slider = QSlider(Qt.Orientation.Horizontal)
        self.blink_period_slider.setRange(10, 100)
        self.blink_period_slider.setValue(30)
        self.blink_period_slider.valueChanged.connect(
            lambda v: self._emit_idle_motion_param("blink_period", v / 10.0)
        )
        blink_param_layout.addWidget(self.blink_period_slider)
        self.blink_period_label = QLabel("3.0秒")
        blink_param_layout.addWidget(self.blink_period_label)
        idle_layout.addLayout(blink_param_layout)
        
        # 視線揺れ
        self.gaze_checkbox = QCheckBox("👀 視線揺れ")
        self.gaze_checkbox.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.gaze_checkbox.setChecked(True)
        self.gaze_checkbox.toggled.connect(lambda checked: self._emit_idle_motion_toggle("gaze", checked))
        idle_layout.addWidget(self.gaze_checkbox)
        
        gaze_param_layout = QHBoxLayout()
        gaze_param_layout.addWidget(QLabel("  範囲:"))
        self.gaze_range_slider = QSlider(Qt.Orientation.Horizontal)
        self.gaze_range_slider.setRange(10, 100)
        self.gaze_range_slider.setValue(50)
        self.gaze_range_slider.valueChanged.connect(
            lambda v: self._emit_idle_motion_param("gaze_range", v / 100.0)
        )
        gaze_param_layout.addWidget(self.gaze_range_slider)
        self.gaze_range_label = QLabel("0.50")
        gaze_param_layout.addWidget(self.gaze_range_label)
        idle_layout.addLayout(gaze_param_layout)
        
        # 風揺れ
        self.wind_checkbox = QCheckBox("💨 風揺れ")
        self.wind_checkbox.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.wind_checkbox.setChecked(True)
        self.wind_checkbox.toggled.connect(lambda checked: self._emit_idle_motion_toggle("wind", checked))
        idle_layout.addWidget(self.wind_checkbox)
        
        wind_param_layout = QHBoxLayout()
        wind_param_layout.addWidget(QLabel("  強さ:"))
        self.wind_strength_slider = QSlider(Qt.Orientation.Horizontal)
        self.wind_strength_slider.setRange(10, 100)
        self.wind_strength_slider.setValue(100)
        self.wind_strength_slider.valueChanged.connect(self.on_wind_strength_slider_changed)

        wind_param_layout.addWidget(self.wind_strength_slider)
        self.wind_strength_label = QLabel("1.00")
        wind_param_layout.addWidget(self.wind_strength_label)
        idle_layout.addLayout(wind_param_layout)
        
        content_layout.addWidget(idle_group)
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        
        return widget
    
    def _emit_idle_motion_toggle(self, motion_type: str, enabled: bool) -> None:
        self.idle_motion_toggled.emit(motion_type, enabled)
        self._schedule_state_snapshot()

    def _emit_idle_motion_param(self, param_name: str, value: float) -> None:
        self.idle_motion_param_changed.emit(param_name, value)
        self._schedule_state_snapshot()
    
    def on_wind_strength_slider_changed(self, value: int):
        strength = value / 100.0
        if hasattr(self, 'wind_strength_label'):
            self.wind_strength_label.setText(f"{strength:.2f}")
        self.idle_motion_param_changed.emit("wind_strength", strength)
        self._schedule_state_snapshot()

    # ================================
    # 🆕 物理演算制御ハンドラー
    # ================================
    
    def on_physics_toggle(self, checked: bool):
        """物理演算ON/OFF切り替え"""
        self.physics_enabled = checked
        
        if checked:
            self.physics_toggle_btn.setText("💨 物理演算 ON")
            self.physics_weight_slider.setEnabled(True)
            self.manual_physics_group.hide()
        else:
            self.physics_toggle_btn.setText("💨 物理演算 OFF")
            self.physics_weight_slider.setEnabled(False)
            self.manual_physics_group.show()
        
        self.physics_toggled.emit(checked)
        print(f"💨 物理演算: {'ON' if checked else 'OFF'}")
        self._schedule_state_snapshot()
    
    def on_physics_weight_changed(self, value: int):
        """物理演算強度変更"""
        weight = value / 100.0
        self.physics_weight_value.setText(f"{weight:.2f}")
        
        if self.physics_enabled:
            self.physics_weight_changed.emit(weight)
        self._schedule_state_snapshot()

    
    # ================================
    # 物理演算用パラメータグループ作成
    # ================================
    
    def create_physics_parameter_group(self, parent_layout: QVBoxLayout, params: List[tuple]):
        """物理演算制御用パラメータグループを作成"""
        grid = QGridLayout()
        grid.setSpacing(8)
        
        slider_style = """
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffb74d, stop:1 #ff9800);
                border: 1px solid #777;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #eee, stop:1 #ccc);
                border: 1px solid #777;
                width: 18px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 9px;
            }
        """
        
        for i, (name, param_id, min_val, max_val, default, desc) in enumerate(params):
            # 名前
            label = QLabel(name + ":")
            label.setFont(QFont("", 10, QFont.Weight.Bold))
            label.setMinimumWidth(100)
            
            # スライダー
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(int(min_val * 100), int(max_val * 100))
            slider.setValue(int(default * 100))
            slider.setStyleSheet(slider_style)
            
            # 数値
            spinbox = QDoubleSpinBox()
            spinbox.setRange(min_val, max_val)
            spinbox.setSingleStep(0.01)
            spinbox.setValue(default)
            spinbox.setDecimals(2)
            spinbox.setFixedWidth(70)
            
            # 説明
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #666; font-size: 9pt;")
            
            # 保存
            self.physics_sliders[param_id] = (slider, spinbox, default)
            
            # シグナル
            slider.valueChanged.connect(lambda v, pid=param_id: self.on_physics_slider_changed(pid, v))
            spinbox.valueChanged.connect(lambda v, pid=param_id: self.on_physics_spinbox_changed(pid, v))
            
            # 配置
            grid.addWidget(label, i, 0)
            grid.addWidget(slider, i, 1)
            grid.addWidget(spinbox, i, 2)
            grid.addWidget(desc_label, i, 3)
        
        parent_layout.addLayout(grid)
    
    def on_physics_slider_changed(self, param_id: str, value: int):
        """物理演算スライダー変更"""
        if self.is_loading or self.physics_enabled:
            return
        val = value / 100.0
        slider, spinbox, _ = self.physics_sliders[param_id]
        spinbox.blockSignals(True)
        spinbox.setValue(val)
        spinbox.blockSignals(False)
        self.parameter_changed.emit(param_id, val)
        self._schedule_state_snapshot()
    
    def on_physics_spinbox_changed(self, param_id: str, value: float):
        """物理演算スピンボックス変更"""
        if self.is_loading or self.physics_enabled:
            return
        slider, spinbox, _ = self.physics_sliders[param_id]
        slider.blockSignals(True)
        slider.setValue(int(value * 100))
        slider.blockSignals(False)
        self.parameter_changed.emit(param_id, value)
        self._schedule_state_snapshot()

    
    # ================================
    # ドラッグ制御ハンドラー
    # ================================
    
    def on_drag_toggle(self, checked: bool):
        """ドラッグ制御ON/OFF"""
        if checked:
            self.drag_toggle_btn.setText("🎮 ドラッグ制御 ON")
            self.drag_sensitivity_slider.setEnabled(True)
            self.drag_reset_btn.setEnabled(True)
        else:
            self.drag_toggle_btn.setText("🎮 ドラッグ制御 OFF")
            self.drag_sensitivity_slider.setEnabled(False)
            self.drag_reset_btn.setEnabled(False)
        
        self.drag_control_toggled.emit(checked)
        self._schedule_state_snapshot()
    
    def on_sensitivity_changed(self, value: int):
        """感度変更"""
        sensitivity = value / 100.0
        self.drag_sensitivity_value.setText(f"{sensitivity:.2f}")
        
        if self.drag_toggle_btn.isChecked():
            self.drag_sensitivity_changed.emit(sensitivity)
        self._schedule_state_snapshot()

    
    def on_drag_reset(self):
        """ドラッグ角度リセット"""
        parent = self.parent()
        while parent and not hasattr(parent, 'character_display'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'character_display'):
            char_display = parent.character_display
            if hasattr(char_display, 'reset_drag_angles'):
                char_display.reset_drag_angles()
            else:
                print("⚠️ reset_drag_angles メソッドが見つかりません")
        else:
            print("⚠️ CharacterDisplayWidgetが見つかりません")
    
    # ================================
    # 表情関連
    # ================================
    
    def set_expression(self, expression_name: str):
        """表情を設定"""
        parent = self.parent()
        while parent and not hasattr(parent, 'character_display'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'character_display'):
            char_display = parent.character_display
            if hasattr(char_display, 'live2d_webview') and char_display.live2d_webview.is_model_loaded:
                char_display.live2d_webview.set_expression(expression_name)
                print(f"😊 表情切り替え: {expression_name}")
            else:
                QMessageBox.warning(self, "エラー", "Live2Dモデルが読み込まれていません")
        else:
            print("⚠️ CharacterDisplayWidgetが見つかりません")
    
    def reset_expression(self):
        """表情をデフォルトに戻す"""
        parent = self.parent()
        while parent and not hasattr(parent, 'character_display'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'character_display'):
            char_display = parent.character_display
            if hasattr(char_display, 'live2d_webview') and char_display.live2d_webview.is_model_loaded:
                script = "window.resetExpression();"
                char_display.live2d_webview.page().runJavaScript(script)
                print("✅ 表情リセット")
            else:
                QMessageBox.warning(self, "エラー", "Live2Dモデルが読み込まれていません")
        else:
            print("⚠️ CharacterDisplayWidgetが見つかりません")
    
    # ================================
    # パラメータグループ作成
    # ================================
    
    def create_parameter_group(self, parent_layout: QVBoxLayout, group_name: str, 
                               params: List[tuple]):
        """パラメータグループを作成"""
        group = QGroupBox(f"{group_name} ({len(params)}個)")
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
        
        grid = QGridLayout(group)
        grid.setSpacing(8)
        
        slider_style = """
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #66e, stop:1 #bbf);
                border: 1px solid #777;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #eee, stop:1 #ccc);
                border: 1px solid #777;
                width: 18px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 9px;
            }
        """
        
        for i, (name, param_id, min_val, max_val, default, desc) in enumerate(params):
            # 名前
            label = QLabel(name + ":")
            label.setFont(QFont("", 11, QFont.Weight.Bold))
            label.setMinimumWidth(120)
            
            # スライダー
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(int(min_val * 100), int(max_val * 100))
            slider.setValue(int(default * 100))
            slider.setStyleSheet(slider_style)
            
            # 数値
            spinbox = QDoubleSpinBox()
            spinbox.setRange(min_val, max_val)
            spinbox.setSingleStep(0.01)
            spinbox.setValue(default)
            spinbox.setDecimals(2)
            spinbox.setFixedWidth(80)
            
            # 説明
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #666; font-size: 9pt;")
            
            # リセット
            reset = QPushButton("↺")
            reset.setFixedSize(28, 28)
            reset.setToolTip(f"デフォルト: {default:.2f}")
            reset.setStyleSheet("""
                QPushButton {
                    background: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover { background: #e0e0e0; }
            """)
            
            # 保存
            self.parameter_sliders[param_id] = (slider, spinbox, default)
            
            # シグナル
            slider.valueChanged.connect(lambda v, pid=param_id: self.on_slider_changed(pid, v))
            spinbox.valueChanged.connect(lambda v, pid=param_id: self.on_spinbox_changed(pid, v))
            reset.clicked.connect(lambda _, pid=param_id: self.reset_param(pid))
            
            # 配置
            grid.addWidget(label, i, 0)
            grid.addWidget(slider, i, 1)
            grid.addWidget(spinbox, i, 2)
            grid.addWidget(desc_label, i, 3)
            grid.addWidget(reset, i, 4)
        
        parent_layout.addWidget(group)
    
    # ================================
    # パラメータ変更ハンドラー
    # ================================
    
    def on_slider_changed(self, param_id: str, value: int):
        """スライダー変更時の処理（物理演算制御付き）"""
        if self.is_loading:
            return
        
        val = value / 100.0
        slider, spinbox, _ = self.parameter_sliders[param_id]
        
        # スピンボックス更新
        spinbox.blockSignals(True)
        spinbox.setValue(val)
        spinbox.blockSignals(False)
        
        # CharacterDisplayWidgetを取得
        parent = self.parent()
        while parent and not hasattr(parent, 'character_display'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'character_display'):
            char_display = parent.character_display
            
            # 物理演算を無効化
            char_display.live2d_webview.page().runJavaScript("""
                (function() {
                    if (window.currentModel && window.currentModel.internalModel && window.currentModel.internalModel.physics) {
                        if (!window._manualPhysicsBackup) {
                            window._manualPhysicsBackup = window.currentModel.internalModel.physics;
                            window.currentModel.internalModel.physics = null;
                            console.log('🛡️ 手動制御開始：物理演算を一時無効化');
                        }
                    }
                })();
            """)
            
            # パラメータ設定（瞳は代替名も試す）
            if param_id in ['ParamEyeBallX', 'ParamEyeBallY']:
                char_display.live2d_webview.page().runJavaScript(f"""
                    (function() {{
                        let success = window.setLive2DParameter('{param_id}', {val});
                        
                        if (!success) {{
                            const alternatives = {{
                                'ParamEyeBallX': ['PARAM_EYE_BALL_X', 'EyeBallX', 'ParamEyeX', '目玉X', '目玉 X'],
                                'ParamEyeBallY': ['PARAM_EYE_BALL_Y', 'EyeBallY', 'ParamEyeY', '目玉Y', '目玉 Y']
                            }};
                            
                            const altNames = alternatives['{param_id}'] || [];
                            for (const altName of altNames) {{
                                if (window.setLive2DParameter(altName, {val})) {{
                                    console.log('✅ 代替パラメータで成功: ' + altName);
                                    break;
                                }}
                            }}
                        }}
                    }})();
                """)
            else:
                char_display.live2d_webview.page().runJavaScript(f"""
                    window.setLive2DParameter('{param_id}', {val});
                """)
            
            # 1秒後に物理演算を復元
            if hasattr(self, '_physics_restore_timer'):
                self._physics_restore_timer.stop()
            else:
                self._physics_restore_timer = QTimer()
                self._physics_restore_timer.setSingleShot(True)
                self._physics_restore_timer.timeout.connect(self._restore_physics)
            
            self._physics_restore_timer.start(1000)
        
        self.parameter_changed.emit(param_id, val)
        self.update_timer.start(100)
        self._schedule_state_snapshot()
    
    def on_spinbox_changed(self, param_id: str, value: float):
        if self.is_loading:
            return
        slider, spinbox, _ = self.parameter_sliders[param_id]
        slider.blockSignals(True)
        slider.setValue(int(value * 100))
        slider.blockSignals(False)
        self.parameter_changed.emit(param_id, value)
        self.update_timer.start(100)
        if not slider.isSliderDown():
            self._schedule_state_snapshot()
    
    def reset_param(self, param_id: str):
        slider, spinbox, default = self.parameter_sliders[param_id]
        
        slider.blockSignals(True)
        slider.setValue(int(default * 100))
        slider.blockSignals(False)

        spinbox.blockSignals(True)
        spinbox.setValue(default)
        spinbox.blockSignals(False)

        if not self.is_loading:
            self.parameter_changed.emit(param_id, default)
            self.update_timer.start(100)
            self._schedule_state_snapshot()
    
    def reset_all(self):
        self.is_loading = True
        for param_id in self.parameter_sliders:
            self.reset_param(param_id)
        for param_id in self.physics_sliders:
            slider, spinbox, default = self.physics_sliders[param_id]
            slider.setValue(int(default * 100))
            spinbox.setValue(default)
        self.is_loading = False
        self.emit_all_parameters()

        self._schedule_state_snapshot()

    # ================================
    # Undo/Redo 履歴管理
    # ================================

    def undo(self) -> bool:
        if self._history_timer.isActive():
            self._history_timer.stop()
            self._commit_pending_history()

        if not self.history.has_undo_available():
            return False

        self.history.set_undoing_flag(True)
        try:
            previous_state = self.history.get_previous_state()
            if previous_state is None:
                return False
            self._apply_state(previous_state)
            return True
        finally:
            self.history.set_undoing_flag(False)

    def redo(self) -> bool:
        if self._history_timer.isActive():
            self._history_timer.stop()
            self._commit_pending_history()

        if not self.history.has_redo_available():
            return False

        self.history.set_undoing_flag(True)
        try:
            next_state = self.history.get_next_state()
            if next_state is None:
                return False
            self._apply_state(next_state)
            return True
        finally:
            self.history.set_undoing_flag(False)

    def has_undo_available(self) -> bool:
        return self.history.has_undo_available()

    def has_redo_available(self) -> bool:
        return self.history.has_redo_available()

    def _capture_state(self) -> Dict[str, Any]:
        state: Dict[str, Any] = {
            "parameters": {pid: round(spinbox.value(), 4) for pid, (_, spinbox, _) in self.parameter_sliders.items()},
            "physics": {pid: round(spinbox.value(), 4) for pid, (_, spinbox, _) in self.physics_sliders.items()},
            "physics_enabled": bool(getattr(self, "physics_enabled", True)),
        }

        if hasattr(self, "drag_toggle_btn"):
            state["drag_enabled"] = self.drag_toggle_btn.isChecked()
        if hasattr(self, "drag_sensitivity_slider"):
            state["drag_sensitivity"] = int(self.drag_sensitivity_slider.value())

        idle_state: Dict[str, Any] = {}
        if hasattr(self, "blink_checkbox"):
            idle_state["blink"] = self.blink_checkbox.isChecked()
        if hasattr(self, "blink_period_slider"):
            idle_state["blink_period"] = int(self.blink_period_slider.value())
        if hasattr(self, "gaze_checkbox"):
            idle_state["gaze"] = self.gaze_checkbox.isChecked()
        if hasattr(self, "gaze_range_slider"):
            idle_state["gaze_range"] = int(self.gaze_range_slider.value())
        if hasattr(self, "wind_checkbox"):
            idle_state["wind"] = self.wind_checkbox.isChecked()
        if hasattr(self, "wind_strength_slider"):
            idle_state["wind_strength"] = int(self.wind_strength_slider.value())
        state["idle"] = idle_state

        if hasattr(self, "physics_weight_slider"):
            state["physics_weight"] = int(self.physics_weight_slider.value())
        if hasattr(self, "loop_checkbox"):
            state["loop"] = self.loop_checkbox.isChecked()
        if hasattr(self, "speed_slider"):
            state["speed"] = int(self.speed_slider.value())

        return state

    def _apply_state(self, state: Dict[str, Any]) -> None:
        if not state:
            return

        self._history_timer.stop()
        self._pending_before_state = None
        self._applying_history = True

        try:
            for pid, value in state.get("parameters", {}).items():
                if pid in self.parameter_sliders:
                    slider, spinbox, _ = self.parameter_sliders[pid]
                    slider.setValue(int(round(value * 100)))
                    spinbox.setValue(value)

            for pid, value in state.get("physics", {}).items():
                if pid in self.physics_sliders:
                    slider, spinbox, _ = self.physics_sliders[pid]
                    slider.setValue(int(round(value * 100)))
                    spinbox.setValue(value)

            if "drag_enabled" in state and hasattr(self, "drag_toggle_btn"):
                self.drag_toggle_btn.setChecked(bool(state["drag_enabled"]))
            if "drag_sensitivity" in state and hasattr(self, "drag_sensitivity_slider"):
                self.drag_sensitivity_slider.setValue(int(state["drag_sensitivity"]))

            idle_state = state.get("idle", {})
            if "blink" in idle_state and hasattr(self, "blink_checkbox"):
                self.blink_checkbox.setChecked(bool(idle_state["blink"]))
            if "blink_period" in idle_state and hasattr(self, "blink_period_slider"):
                self.blink_period_slider.setValue(int(idle_state["blink_period"]))
            if "gaze" in idle_state and hasattr(self, "gaze_checkbox"):
                self.gaze_checkbox.setChecked(bool(idle_state["gaze"]))
            if "gaze_range" in idle_state and hasattr(self, "gaze_range_slider"):
                self.gaze_range_slider.setValue(int(idle_state["gaze_range"]))
            if "wind" in idle_state and hasattr(self, "wind_checkbox"):
                self.wind_checkbox.setChecked(bool(idle_state["wind"]))
            if "wind_strength" in idle_state and hasattr(self, "wind_strength_slider"):
                self.wind_strength_slider.setValue(int(idle_state["wind_strength"]))

            if "physics_enabled" in state and hasattr(self, "physics_toggle_btn"):
                self.physics_toggle_btn.setChecked(bool(state["physics_enabled"]))
            if "physics_weight" in state and hasattr(self, "physics_weight_slider"):
                self.physics_weight_slider.setValue(int(state["physics_weight"]))

            if "loop" in state and hasattr(self, "loop_checkbox"):
                self.loop_checkbox.setChecked(bool(state["loop"]))
            if "speed" in state and hasattr(self, "speed_slider"):
                self.speed_slider.setValue(int(state["speed"]))

        finally:
            self._applying_history = False
            self._last_committed_state = deepcopy(state)
            self.emit_all_parameters()

    def _schedule_state_snapshot(self) -> None:
        if self.history.is_undoing or self._applying_history or self.is_loading:
            return

        if self._pending_before_state is None:
            self._pending_before_state = deepcopy(self._last_committed_state)

        self._history_timer.start(250)

    def _commit_pending_history(self) -> None:
        if self._pending_before_state is None:
            return

        after_state = self._capture_state()
        if after_state != self._pending_before_state:
            self.history.save_current_state(after_state)
            self._last_committed_state = deepcopy(after_state)

        self._pending_before_state = None

    def _reset_history_to_current_state(self) -> None:
        self._history_timer.stop()
        self._pending_before_state = None
        current_state = self._capture_state()
        self.history.clear_history()
        self.history.save_current_state(current_state)
        self._last_committed_state = deepcopy(current_state)
    
    def emit_all_parameters(self):
        self.parameters_changed.emit(self.get_all_parameters())
    
    def get_all_parameters(self) -> Dict[str, float]:
        params = {pid: spinbox.value() for pid, (_, spinbox, _) in self.parameter_sliders.items()}
        if not self.physics_enabled:
            params.update({pid: spinbox.value() for pid, (_, spinbox, _) in self.physics_sliders.items()})
        return params
    
    def load_parameters(self, parameters: Dict[str, float]):
        self.is_loading = True
        for pid, val in parameters.items():
            if pid in self.parameter_sliders:
                slider, spinbox, _ = self.parameter_sliders[pid]
                slider.setValue(int(val * 100))
                spinbox.setValue(val)
            elif pid in self.physics_sliders:
                slider, spinbox, _ = self.physics_sliders[pid]
                slider.setValue(int(val * 100))
                spinbox.setValue(val)
        self.is_loading = False
        self.emit_all_parameters()
    
    def load_model_parameters(self, parameters: List[Dict[str, Any]], model_id: str):
        """モデル読み込み時に呼ばれる"""
        self.is_loading = True
        for param in parameters:
            pid = param['id']
            if pid in self.parameter_sliders:
                val = param.get('currentValue', param['defaultValue'])
                slider, spinbox, _ = self.parameter_sliders[pid]
                slider.setValue(int(val * 100))
                spinbox.setValue(val)
            elif pid in self.physics_sliders:
                val = param.get('currentValue', param['defaultValue'])
                slider, spinbox, _ = self.physics_sliders[pid]
                slider.setValue(int(val * 100))
                spinbox.setValue(val)
        self.is_loading = False
        
        self._reset_history_to_current_state()

        print(f"✅ モデリング：{len(parameters)}個のパラメータ反映完了")
    
    # ================================
    # 状態取得ヘルパー
    # ================================
    
    def is_drag_enabled(self) -> bool:
        """現在のドラッグ制御のON/OFF状態を返す"""
        return self.drag_toggle_btn.isChecked()

    def get_drag_sensitivity(self) -> float:
        """現在のドラッグ感度（0.1〜1.0）を返す"""
        return self.drag_sensitivity_slider.value() / 100.0
    
    def _restore_physics(self):
        """物理演算を復元"""
        try:
            parent = self.parent()
            while parent and not hasattr(parent, 'character_display'):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'character_display'):
                char_display = parent.character_display
                char_display.live2d_webview.page().runJavaScript("""
                    (function() {
                        if (window._manualPhysicsBackup) {
                            window.currentModel.internalModel.physics = window._manualPhysicsBackup;
                            delete window._manualPhysicsBackup;
                            console.log('♻️ 手動制御終了：物理演算を復元');
                        }
                    })();
                """)
        except Exception as e:
            print(f"⚠️ 物理演算復元エラー: {e}")

    def create_animation_tab(self):
        """アニメーションタブ"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # ヘッダー
        header_layout = QHBoxLayout()
        title = QLabel("🎞️ アニメーション再生")
        title.setFont(QFont("", 13, QFont.Weight.Bold))
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(35, 35)
        refresh_btn.setToolTip("リスト更新")
        refresh_btn.clicked.connect(self.refresh_animation_list)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)
        layout.addLayout(header_layout)
        
        # アニメーション一覧
        from PyQt6.QtWidgets import QListWidget
        self.animation_list = QListWidget()
        self.animation_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #4a90e2;
                border-radius: 6px;
                background-color: white;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0e0e0;
            }
            QListWidget::item:selected {
                background-color: #4a90e2;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
            }
        """)
        self.animation_list.itemDoubleClicked.connect(self.on_animation_double_clicked)
        layout.addWidget(self.animation_list, 1)
        
        # 再生コントロール
        control_group = QGroupBox("再生制御")
        control_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a90e2;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
        """)
        
        control_layout = QVBoxLayout(control_group)
        
        # 再生ボタン
        buttons_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("▶️ 再生")
        self.play_btn.setMinimumHeight(40)
        self.play_btn.clicked.connect(self.play_animation)
        
        self.pause_btn = QPushButton("⏸️ 一時停止")
        self.pause_btn.setMinimumHeight(40)
        self.pause_btn.clicked.connect(self.pause_animation)
        
        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.clicked.connect(self.stop_animation)
        
        buttons_layout.addWidget(self.play_btn)
        buttons_layout.addWidget(self.pause_btn)
        buttons_layout.addWidget(self.stop_btn)
        control_layout.addLayout(buttons_layout)
        
        # ループ設定
        loop_layout = QHBoxLayout()
        self.loop_checkbox = QCheckBox("🔄 ループ再生")
        self.loop_checkbox.setChecked(False)
        self.loop_checkbox.stateChanged.connect(self.on_loop_changed)
        loop_layout.addWidget(self.loop_checkbox)
        loop_layout.addStretch()
        control_layout.addLayout(loop_layout)
        
        # 再生速度
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("速度:"))
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(10, 300)
        self.speed_slider.setValue(100)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        speed_layout.addWidget(self.speed_slider)
        
        self.speed_label = QLabel("1.0x")
        self.speed_label.setMinimumWidth(50)
        speed_layout.addWidget(self.speed_label)
        control_layout.addLayout(speed_layout)
        
        layout.addWidget(control_group)
        
        # 初期化
        self.refresh_animation_list()
        
        return widget

    def refresh_animation_list(self):
        """アニメーション一覧を更新"""
        self.animation_manager.refresh_list()
        animations = self.animation_manager.get_animation_list()
        
        self.animation_list.clear()
        for anim in animations:
            item_text = f"{anim['name']} ({anim['duration']:.1f}秒)"
            self.animation_list.addItem(item_text)
        
        print(f"✅ アニメーション一覧更新: {len(animations)}件")

    def on_animation_double_clicked(self, item):
        """アニメーション選択時（ダブルクリック）"""
        index = self.animation_list.row(item)
        animations = self.animation_manager.get_animation_list()
        
        if 0 <= index < len(animations):
            selected = animations[index]
            self.load_and_play_animation(selected['file_name'])

    def load_and_play_animation(self, file_name: str):
        """アニメーションを読み込んで再生"""
        animation_data = self.animation_manager.load_animation_by_name(file_name)
        
        if not animation_data:
            QMessageBox.warning(self, "エラー", f"アニメーション読み込み失敗: {file_name}")
            return
        
        # JavaScript側に送信
        parent = self.parent()
        while parent and not hasattr(parent, 'character_display'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'character_display'):
            char_display = parent.character_display
            
            import json
            animation_json = json.dumps(animation_data, ensure_ascii=False)
            
            script = f"""
            (function() {{
                const animData = {animation_json};
                const success = window.loadAnimation(animData);
                
                if (success) {{
                    window.playAnimation();
                    console.log('✅ アニメーション再生開始');
                }} else {{
                    console.error('❌ アニメーション読み込み失敗');
                }}
            }})();
            """
            
            char_display.live2d_webview.page().runJavaScript(script)
            print(f"▶️ アニメーション再生: {file_name}")
        else:
            QMessageBox.warning(self, "エラー", "Live2Dビューアーが見つかりません")

    def play_animation(self):
        """アニメーション再生"""
        parent = self.parent()
        while parent and not hasattr(parent, 'character_display'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'character_display'):
            char_display = parent.character_display
            char_display.live2d_webview.page().runJavaScript("window.playAnimation();")
            print("▶️ アニメーション再生")

    def pause_animation(self):
        """アニメーション一時停止"""
        parent = self.parent()
        while parent and not hasattr(parent, 'character_display'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'character_display'):
            char_display = parent.character_display
            char_display.live2d_webview.page().runJavaScript("window.pauseAnimation();")
            print("⏸️ アニメーション一時停止")

    def stop_animation(self):
        """アニメーション停止"""
        parent = self.parent()
        while parent and not hasattr(parent, 'character_display'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'character_display'):
            char_display = parent.character_display
            char_display.live2d_webview.page().runJavaScript("window.stopAnimation();")
            print("⏹️ アニメーション停止")

    def on_loop_changed(self, state):
        """ループ設定変更"""
        enabled = state == Qt.CheckState.Checked.value
        
        parent = self.parent()
        while parent and not hasattr(parent, 'character_display'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'character_display'):
            char_display = parent.character_display
            char_display.live2d_webview.page().runJavaScript(
                f"window.setAnimationLoop({str(enabled).lower()});"
            )
            print(f"🔄 ループ: {'ON' if enabled else 'OFF'}")

        self._schedule_state_snapshot()

    def on_speed_changed(self, value: int):
        """再生速度変更"""
        speed = value / 100.0
        self.speed_label.setText(f"{speed:.1f}x")
        
        parent = self.parent()
        while parent and not hasattr(parent, 'character_display'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'character_display'):
            char_display = parent.character_display
            char_display.live2d_webview.page().runJavaScript(
                f"window.setAnimationSpeed({speed});"
            )

        self._schedule_state_snapshot()