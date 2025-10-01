# ui/tabbed_modeling_control.py（完全修正版：ドラッグ制御追加）
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QGroupBox, QSlider, QLabel, QPushButton, QTabWidget,
                             QGridLayout, QDoubleSpinBox, QMessageBox)

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from typing import Dict, List, Any


class TabbedModelingControl(QWidget):
    """タブ式モデリング制御（ドラッグ制御追加版）"""
    parameter_changed = pyqtSignal(str, float)
    parameters_changed = pyqtSignal(dict)
    
    # 🆕 ドラッグ制御用シグナル
    drag_control_toggled = pyqtSignal(bool)
    drag_sensitivity_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parameter_sliders = {}
        self.is_loading = False
        
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.emit_all_parameters)
        
        self.init_ui()
        
        # 初期化後、ドラッグ制御を明示的に有効化
        QTimer.singleShot(100, lambda: self.on_drag_toggle(True))
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        
        # ヘッダー
        header = QHBoxLayout()
        title = QLabel("🎨 モデリング")
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
        
        # サブタブ
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
        
        self.tabs.addTab(self.create_face_tab(), "😊 顔の制御")
        self.tabs.addTab(self.create_body_tab(), "🧍 体の制御")
        self.tabs.addTab(self.create_other_tab(), "✨ その他")
        self.tabs.addTab(self.create_motion_tab(), "🎭 モーション/表情")
        
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
        
        # 顔の角度グループ
        face_params = [
            ("角度X", "ParamAngleX", -30.0, 30.0, 0.0, "左 ← → 右"),
            ("角度Y", "ParamAngleY", -30.0, 30.0, 0.0, "下 ← → 上"),
            ("角度Z", "ParamAngleZ", -30.0, 30.0, 0.0, "左傾き ← → 右傾き")
        ]
        self.create_parameter_group(content_layout, "顔の角度", face_params)
        
        # 目グループ
        eye_params = [
            ("左目 開閉", "ParamEyeLOpen", 0.0, 1.0, 1.0, "閉じ ← → 開き"),
            ("右目 開閉", "ParamEyeROpen", 0.0, 1.0, 1.0, "閉じ ← → 開き"),
            ("左目 笑顔", "ParamEyeLSmile", 0.0, 1.0, 0.0, "通常 ← → 笑顔"),
            ("右目 笑顔", "ParamEyeRSmile", 0.0, 1.0, 0.0, "通常 ← → 笑顔")
        ]
        self.create_parameter_group(content_layout, "目", eye_params)
        
        # 目玉グループ
        eyeball_params = [
            ("目玉 X", "ParamEyeBallX", -1.0, 1.0, 0.0, "左 ← → 右"),
            ("目玉 Y", "ParamEyeBallY", -1.0, 1.0, 0.0, "下 ← → 上")
        ]
        self.create_parameter_group(content_layout, "目玉", eyeball_params)
        
        # 眉グループ
        brow_params = [
            ("左眉 上下", "ParamBrowLY", -1.0, 1.0, 0.0, "下 ← → 上"),
            ("右眉 上下", "ParamBrowRY", -1.0, 1.0, 0.0, "下 ← → 上"),
            ("左眉 角度", "ParamBrowLAngle", -1.0, 1.0, 0.0, "怒り ← → 困り"),
            ("右眉 角度", "ParamBrowRAngle", -1.0, 1.0, 0.0, "怒り ← → 困り")
        ]
        self.create_parameter_group(content_layout, "眉", brow_params)
        
        # 口グループ
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
        
        # 体の回転
        body_params = [
            ("体の回転 X", "ParamBodyAngleX", -10.0, 10.0, 0.0, "左 ← → 右"),
            ("体の回転 Y", "ParamBodyAngleY", -10.0, 10.0, 0.0, "下 ← → 上"),
            ("体の回転 Z", "ParamBodyAngleZ", -10.0, 10.0, 0.0, "左傾き ← → 右傾き")
        ]
        self.create_parameter_group(content_layout, "体の回転", body_params)
        
        # 呼吸
        breath_params = [
            ("呼吸", "ParamBreath", 0.0, 1.0, 0.0, "吐く ← → 吸う")
        ]
        self.create_parameter_group(content_layout, "呼吸", breath_params)
        
        # 腕
        arm_params = [
            ("左腕 A", "ParamArmLA", -30.0, 30.0, 0.0, "閉じ ← → 広げ"),
            ("右腕 A", "ParamArmRA", -30.0, 30.0, 0.0, "閉じ ← → 広げ"),
            ("左腕 B", "ParamArmLB", -30.0, 30.0, 0.0, "閉じ ← → 広げ"),
            ("右腕 B", "ParamArmRB", -30.0, 30.0, 0.0, "閉じ ← → 広げ")
        ]
        self.create_parameter_group(content_layout, "腕", arm_params)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        return widget
    
    def create_other_tab(self):
        """その他タブ"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: white; }")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)
        
        # 髪揺れ
        hair_params = [
            ("髪揺れ 前", "ParamHairFront", -1.0, 1.0, 0.0, "左 ← → 右"),
            ("髪揺れ 横", "ParamHairSide", -1.0, 1.0, 0.0, "左 ← → 右"),
            ("髪揺れ 後", "ParamHairBack", -1.0, 1.0, 0.0, "左 ← → 右")
        ]
        self.create_parameter_group(content_layout, "髪揺れ", hair_params)
        
        # 全体位置
        base_params = [
            ("全体 左右", "ParamBaseX", -10.0, 10.0, 0.0, "左 ← → 右"),
            ("全体 上下", "ParamBaseY", -10.0, 10.0, 0.0, "下 ← → 上")
        ]
        self.create_parameter_group(content_layout, "全体位置", base_params)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        return widget
    
    def create_motion_tab(self):
        """モーション/表情タブ（ドラッグ制御追加版）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 🆕 ドラッグ制御セクション
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
        
        # ON/OFFトグルボタン（初期状態：ON）
        self.drag_toggle_btn = QPushButton("🎮 ドラッグ制御 ON")
        self.drag_toggle_btn.setCheckable(True)
        self.drag_toggle_btn.setChecked(True)  # 初期状態をONに
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
            QPushButton:hover {
                border-color: #9c27b0;
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
        self.drag_sensitivity_slider.setValue(30)  # デフォルト0.3
        self.drag_sensitivity_slider.setEnabled(True)  # 初期状態で有効
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
        
        # リセットボタン（初期状態：有効）
        self.drag_reset_btn = QPushButton("↺ 角度リセット")
        self.drag_reset_btn.setMinimumHeight(40)
        self.drag_reset_btn.setEnabled(True)  # 初期状態で有効
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
        
        # 表情セクション
        expression_group = QGroupBox("😊 表情切り替え")
        expression_group.setStyleSheet("""
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
        
        expression_layout = QVBoxLayout(expression_group)
        
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
            QPushButton:pressed { background: #a0c8d8; }
        """)
        default_btn.clicked.connect(self.reset_expression)
        expression_layout.addWidget(default_btn)
        
        # Scene1-4の表情ボタン
        expression_buttons_layout = QGridLayout()
        expression_buttons_layout.setSpacing(10)
        
        expression_names = [
            ("Scene1", "笑顔"),
            ("Scene2", "驚き"),
            ("Scene3", "怖がり"),
            ("Scene4", "悲しみ")
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
                QPushButton:pressed { background: #ffc700; }
            """)
            btn.clicked.connect(lambda checked, sid=scene_id: self.set_expression(sid))
            
            row = i // 2
            col = i % 2
            expression_buttons_layout.addWidget(btn, row, col)
        
        expression_layout.addLayout(expression_buttons_layout)
        
        # モーションセクション（未実装）
        motion_group = QGroupBox("🎭 モーション再生")
        motion_group.setStyleSheet(expression_group.styleSheet())
        motion_layout = QVBoxLayout(motion_group)
        
        motion_info = QLabel("モーション機能は今後実装予定です")
        motion_info.setStyleSheet("color: #999; font-size: 11px; font-style: italic;")
        motion_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        motion_layout.addWidget(motion_info)
        
        # レイアウト組み立て
        layout.addWidget(drag_group)
        layout.addWidget(expression_group)
        layout.addWidget(motion_group)
        layout.addStretch()
        
        return widget

    # ================================
    # 🆕 ドラッグ制御ハンドラー
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
        print(f"🎯 ドラッグ制御: {'ON' if checked else 'OFF'}")
    
    def on_sensitivity_changed(self, value: int):
        """感度変更"""
        sensitivity = value / 100.0
        self.drag_sensitivity_value.setText(f"{sensitivity:.2f}")
        
        if self.drag_toggle_btn.isChecked():
            self.drag_sensitivity_changed.emit(sensitivity)
    
    def on_drag_reset(self):
        """ドラッグ角度リセット"""
        # 親ウィジェットを辿ってCharacterDisplayWidgetを探す
        parent = self.parent()
        while parent and not hasattr(parent, 'character_display'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'character_display'):
            char_display = parent.character_display
            if hasattr(char_display, 'reset_drag_angles'):
                char_display.reset_drag_angles()
                print("↺ ドラッグ角度リセット完了")
            else:
                print("⚠️ reset_drag_angles メソッドが見つかりません")
        else:
            print("⚠️ CharacterDisplayWidgetが見つかりません")

    # ================================
    # 状態取得ヘルパー
    # ================================

    def is_drag_enabled(self) -> bool:
        """現在のドラッグ制御のON/OFF状態を返す"""
        return self.drag_toggle_btn.isChecked()

    def get_drag_sensitivity(self) -> float:
        """現在のドラッグ感度（0.1〜1.0）を返す"""
        return self.drag_sensitivity_slider.value() / 100.0


    # ================================
    # 既存のメソッド
    # ================================

    def set_expression(self, expression_name: str):
        """表情を設定"""
        print(f"🔍 set_expression('{expression_name}') が呼ばれました")
        
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
        print("🔍 reset_expression() が呼ばれました")
        
        parent = self.parent()
        while parent and not hasattr(parent, 'character_display'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'character_display'):
            char_display = parent.character_display
            if hasattr(char_display, 'live2d_webview') and char_display.live2d_webview.is_model_loaded:
                script = "window.resetExpression();"
                char_display.live2d_webview.page().runJavaScript(script)
                print("✅ 表情リセットJS送信完了")
            else:
                print("❌ モデル未読み込み")
                QMessageBox.warning(self, "エラー", "Live2Dモデルが読み込まれていません")
        else:
            print("⚠️ CharacterDisplayWidgetが見つかりません")
    
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
    
    def on_slider_changed(self, param_id: str, value: int):
        if self.is_loading:
            return
        val = value / 100.0
        slider, spinbox, _ = self.parameter_sliders[param_id]
        spinbox.blockSignals(True)
        spinbox.setValue(val)
        spinbox.blockSignals(False)
        self.parameter_changed.emit(param_id, val)
        self.update_timer.start(100)
    
    def on_spinbox_changed(self, param_id: str, value: float):
        if self.is_loading:
            return
        slider, spinbox, _ = self.parameter_sliders[param_id]
        slider.blockSignals(True)
        slider.setValue(int(value * 100))
        slider.blockSignals(False)
        self.parameter_changed.emit(param_id, value)
        self.update_timer.start(100)
    
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
    
    def reset_all(self):
        self.is_loading = True
        for param_id in self.parameter_sliders:
            self.reset_param(param_id)
        self.is_loading = False
        self.emit_all_parameters()
    
    def emit_all_parameters(self):
        self.parameters_changed.emit(self.get_all_parameters())
    
    def get_all_parameters(self) -> Dict[str, float]:
        return {pid: spinbox.value() for pid, (_, spinbox, _) in self.parameter_sliders.items()}
    
    def load_parameters(self, parameters: Dict[str, float]):
        self.is_loading = True
        for pid, val in parameters.items():
            if pid in self.parameter_sliders:
                slider, spinbox, _ = self.parameter_sliders[pid]
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
        self.is_loading = False
        
        print(f"✅ モデリング：{len(parameters)}個のパラメータ反映完了")