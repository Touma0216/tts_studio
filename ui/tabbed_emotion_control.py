from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                            QComboBox, QDoubleSpinBox, QGroupBox, QGridLayout, QTabWidget,
                            QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal
from .history_manager import ParameterHistory


class SingleEmotionControl(QWidget):
    """単一行の感情制御ウィジェット（複数Undo対応版）"""
    
    parameters_changed = pyqtSignal(str, dict)
    undo_executed = pyqtSignal(str)  # Undo実行通知
    
    def __init__(self, row_id, parameters=None, is_master=False, parent=None):
        super().__init__(parent)
        
        self.row_id = row_id
        self.is_master = is_master
        self.current_params = parameters or {
            'style': 'Neutral', 'style_weight': 1.0, 'length_scale': 0.85,
            'pitch_scale': 1.0, 'intonation_scale': 1.0, 'sdp_ratio': 0.25, 'noise': 0.35
        }
        
        # 改良版履歴管理（複数Undo対応）
        self.history = ParameterHistory(max_history=20)
        self.is_loading_parameters = False  # パラメータ読み込み中フラグ
        self.slider_dragging = False  # スライダードラッグ中フラグ
        self.temp_state_before_drag = None  # ドラッグ開始前の状態
        
        # 利用可能感情（モデル読み込み後に更新）
        self.available_styles = ['Neutral']  # デフォルト
        
        self.init_ui()
        self.load_parameters()
        
        # 初期状態を履歴に保存
        self.history.save_current_state(self.current_params)
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        emotion_group = self.create_emotion_group()
        layout.addWidget(emotion_group)
        
        params_group = self.create_params_group()
        layout.addWidget(params_group)


        if self.is_master:
            info_label = QLabel("★ デフォルトパラメータ - ここを変更すると全てのタブに反映されます")
            info_label.setStyleSheet("""
                QLabel {
                    background-color: #fff3cd;
                    color: #856404;
                    border: 1px solid #ffeaa7;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: bold;
                }
            """)
            layout.addWidget(info_label)
        
        layout.addStretch()
        
    def create_emotion_group(self):
        group = QGroupBox("感情制御")
        if self.is_master:
            group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #ffd700;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 5px;
                    background-color: #fffef7;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    background-color: #fffef7;
                    color: #b8860b;
                }
            """)
        else:
            group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #ccc;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 5px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    background-color: white;
                }
            """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        emotion_layout = QHBoxLayout()
        emotion_label = QLabel("感情:")
        emotion_label.setMinimumWidth(80)
        
        self.emotion_combo = QComboBox()
        self.emotion_combo.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
                min-width: 150px;
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
        
        # 👈 初期化時は空のコンボボックス（モデル読み込み後に感情を設定）
        self.emotion_combo.addItem("😐 モデル読み込み待ち", "Neutral")
        self.emotion_combo.currentTextChanged.connect(self.on_emotion_changed)
        
        emotion_layout.addWidget(emotion_label)
        emotion_layout.addWidget(self.emotion_combo, 1)
        
        intensity_layout = QHBoxLayout()
        intensity_label = QLabel("感情強度:")
        intensity_label.setMinimumWidth(80)
        
        self.intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.intensity_slider.setRange(0, 200)
        self.intensity_slider.setValue(100)
        
        # 高品質スライダースタイル
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
        
        if self.is_master:
            slider_style = """
                QSlider::groove:horizontal {
                    border: 1px solid #daa520;
                    background: white;
                    height: 6px;
                    border-radius: 3px;
                }
                QSlider::sub-page:horizontal {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                        stop: 0 #ffd700, stop: 1 #ffed4e);
                    border: 1px solid #daa520;
                    height: 6px;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                        stop: 0 #fff, stop: 1 #ffd700);
                    border: 1px solid #daa520;
                    width: 18px;
                    margin-top: -6px;
                    margin-bottom: -6px;
                    border-radius: 9px;
                }
            """
        
        self.intensity_slider.setStyleSheet(slider_style)
        self.intensity_slider.valueChanged.connect(self.on_intensity_slider_changed)
        # スライダードラッグ検出
        self.intensity_slider.sliderPressed.connect(self.on_slider_pressed)
        self.intensity_slider.sliderReleased.connect(self.on_slider_released)
        
        self.intensity_spinbox = QDoubleSpinBox()
        self.intensity_spinbox.setRange(0.0, 2.0)
        self.intensity_spinbox.setSingleStep(0.1)
        self.intensity_spinbox.setValue(1.0)
        self.intensity_spinbox.setDecimals(2)
        self.intensity_spinbox.setFixedWidth(70)
        self.intensity_spinbox.valueChanged.connect(self.on_intensity_spinbox_changed)
        
        intensity_layout.addWidget(intensity_label)
        intensity_layout.addWidget(self.intensity_slider, 1)
        intensity_layout.addWidget(self.intensity_spinbox)
        
        layout.addLayout(emotion_layout)
        layout.addLayout(intensity_layout)
        
        return group
    
    def create_params_group(self):
        group = QGroupBox("音声パラメータ")
        if self.is_master:
            group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #ffd700;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 5px;
                    background-color: #fffef7;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    background-color: #fffef7;
                    color: #b8860b;
                }
            """)
        else:
            group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #ccc;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 5px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    background-color: white;
                }
            """)
        
        layout = QGridLayout(group)
        layout.setSpacing(8)
        
        params = [
            ("話速", "length_scale", 0.3, 1.8, 0.85, "超速い ← → 超遅い"),
            ("ピッチ", "pitch_scale", 0.5, 1.5, 1.0, "低音 ← → 高音"),
            ("抑揚", "intonation_scale", 0.5, 1.5, 1.0, "平坦 ← → 抑揚"),
            ("SDP比率", "sdp_ratio", 0.0, 0.8, 0.25, "単調 ← → 変化"),
            ("ノイズ", "noise", 0.0, 1.0, 0.35, "クリア ← → 自然")
        ]
        
        self.param_sliders = {}
        self.param_spinboxes = {}
        
        base_slider_style = """
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
        
        master_slider_style = """
            QSlider::groove:horizontal {
                border: 1px solid #daa520;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffd700, stop: 1 #ffed4e);
                border: 1px solid #daa520;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #fff, stop: 1 #ffd700);
                border: 1px solid #daa520;
                width: 18px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 9px;
            }
        """
        
        for i, (name, key, min_val, max_val, default, desc) in enumerate(params):
            label = QLabel(name + ":")
            label.setMinimumWidth(80)
            
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(int(min_val * 100), int(max_val * 100))
            slider.setValue(int(default * 100))
            slider.setStyleSheet(master_slider_style if self.is_master else base_slider_style)
            
            spinbox = QDoubleSpinBox()
            spinbox.setRange(min_val, max_val)
            spinbox.setSingleStep(0.01)
            spinbox.setValue(default)
            spinbox.setDecimals(2)
            spinbox.setFixedWidth(70)
            
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #666; font-size: 9pt;")
            
            slider.valueChanged.connect(lambda v, k=key: self.on_param_slider_changed(k, v))
            # スライダードラッグ検出
            slider.sliderPressed.connect(self.on_slider_pressed)
            slider.sliderReleased.connect(self.on_slider_released)
            spinbox.valueChanged.connect(lambda v, k=key: self.on_param_spinbox_changed(k, v))
            
            self.param_sliders[key] = slider
            self.param_spinboxes[key] = spinbox
            
            layout.addWidget(label, i, 0)
            layout.addWidget(slider, i, 1)
            layout.addWidget(spinbox, i, 2)
            layout.addWidget(desc_label, i, 3)
        
        return group
    
    # ================================
    # 改良版Undo機能の実装
    # ================================
    
    def save_current_state_to_history(self):
        """現在の状態を履歴に保存"""
        if not self.is_loading_parameters:
            self.history.save_current_state(self.current_params)
    
    def undo_parameters(self):
        """パラメータをUndoする（改良版）"""
        if not self.history.has_undo_available():
            return False
        
        self.history.set_undoing_flag(True)
        previous_state = self.history.get_previous_state()
        
        if previous_state:
            # 前の状態に復元
            self.current_params = previous_state
            self.load_parameters()
            
            # パラメータ変更通知
            self.emit_parameters_changed()
            
            # Undo通知
            self.undo_executed.emit(self.row_id)
            
        self.history.set_undoing_flag(False)
        return True
    
    def has_undo_available(self):
        """Undoが可能かどうか"""
        return self.history.has_undo_available()
    
    # ================================
    # スライダードラッグ検出
    # ================================
    
    def on_slider_pressed(self):
        """スライダー押下開始時"""
        if not self.is_loading_parameters:
            self.slider_dragging = True
            self.temp_state_before_drag = self.current_params.copy()
    
    def on_slider_released(self):
        """スライダー押下終了時"""
        if not self.is_loading_parameters and self.slider_dragging:
            self.slider_dragging = False
            # ドラッグ開始前の状態を履歴に保存
            if self.temp_state_before_drag:
                self.history.save_current_state(self.temp_state_before_drag)
            self.temp_state_before_drag = None
    
    # ================================
    # 既存のイベントハンドラー（改良版）
    # ================================
    
    def on_emotion_changed(self, text):
        current_data = self.emotion_combo.currentData()
        if current_data and not self.is_loading_parameters:
            # 変更前の状態を履歴に保存
            self.save_current_state_to_history()
            
            self.current_params['style'] = current_data
            self.emit_parameters_changed()
    
    def on_intensity_slider_changed(self, value):
        if not self.is_loading_parameters and not self.slider_dragging:
            # SpinBoxからの変更時のみ履歴保存
            self.save_current_state_to_history()
        
        float_value = value / 100.0
        self.intensity_spinbox.blockSignals(True)
        self.intensity_spinbox.setValue(float_value)
        self.intensity_spinbox.blockSignals(False)
        
        self.current_params['style_weight'] = float_value
        if not self.is_loading_parameters:
            self.emit_parameters_changed()
    
    def on_intensity_spinbox_changed(self, value):
        if not self.is_loading_parameters:
            # SpinBox変更時は即座に履歴保存
            self.save_current_state_to_history()
        
        int_value = int(value * 100)
        self.intensity_slider.blockSignals(True)
        self.intensity_slider.setValue(int_value)
        self.intensity_slider.blockSignals(False)
        
        self.current_params['style_weight'] = value
        if not self.is_loading_parameters:
            self.emit_parameters_changed()
    
    def on_param_slider_changed(self, param_key, value):
        if not self.is_loading_parameters and not self.slider_dragging:
            # SpinBoxからの変更時のみ履歴保存
            self.save_current_state_to_history()
        
        float_value = value / 100.0
        
        spinbox = self.param_spinboxes[param_key]
        spinbox.blockSignals(True)
        spinbox.setValue(float_value)
        spinbox.blockSignals(False)
        
        self.current_params[param_key] = float_value
        if not self.is_loading_parameters:
            self.emit_parameters_changed()
    
    def on_param_spinbox_changed(self, param_key, value):
        if not self.is_loading_parameters:
            # SpinBox変更時は即座に履歴保存
            self.save_current_state_to_history()
        
        int_value = int(value * 100)
        
        slider = self.param_sliders[param_key]
        slider.blockSignals(True)
        slider.setValue(int_value)
        slider.blockSignals(False)
        
        self.current_params[param_key] = value
        if not self.is_loading_parameters:
            self.emit_parameters_changed()
    
    def load_parameters(self):
        self.is_loading_parameters = True
        
        # 感情選択を更新（available_stylesに基づく）
        for i in range(self.emotion_combo.count()):
            if self.emotion_combo.itemData(i) == self.current_params['style']:
                self.emotion_combo.setCurrentIndex(i)
                break
        
        style_weight = self.current_params['style_weight']
        self.intensity_slider.setValue(int(style_weight * 100))
        self.intensity_spinbox.setValue(style_weight)
        
        for key, value in self.current_params.items():
            if key in self.param_sliders:
                self.param_sliders[key].setValue(int(value * 100))
                self.param_spinboxes[key].setValue(value)
        
        self.is_loading_parameters = False
    
    def emit_parameters_changed(self):
        self.parameters_changed.emit(self.row_id, self.current_params.copy())
    
    def get_current_parameters(self):
        return self.current_params.copy()
    
    def update_parameters_from_master(self, master_params):
        # マスターからの更新は履歴に保存
        self.save_current_state_to_history()
        
        self.current_params.update(master_params)
        self.load_parameters()
    
    def update_emotion_combo(self, available_styles):
        """モデルから取得した感情リストでコンボボックスを更新（統一版）"""
        try:
            # 現在の選択を保存
            current_selection = self.emotion_combo.currentData()
            
            # 利用可能感情を更新
            self.available_styles = available_styles
            
            # コンボボックスをクリアして再構築
            self.emotion_combo.blockSignals(True)
            self.emotion_combo.clear()
            
            # Style-Bert-VITS2 公式感情マッピング（JVNV基準）
            emotion_mapping = {
                'neutral': ('😐', 'Neutral'),
                'angry': ('😠', 'Angry'),
                'disgust': ('😖', 'Disgust'),
                'fear': ('😰', 'Fear'),
                'happy': ('😊', 'Happy'),
                'sad': ('😢', 'Sad'),
                'surprise': ('😲', 'Surprise'),
                # エイリアス（互換性のため）
                'happiness': ('😊', 'Happy'),
                'sadness': ('😢', 'Sad'),
                'anger': ('😠', 'Angry'),
            }
            
            # モデルの感情を追加
            for style in available_styles:
                emoji, japanese = emotion_mapping.get(style.lower(), ('🎭', style))
                display_name = f"{emoji} {japanese}"
                self.emotion_combo.addItem(display_name, style)
            
            # 以前の選択を復元
            if current_selection and current_selection in available_styles:
                for i in range(self.emotion_combo.count()):
                    if self.emotion_combo.itemData(i) == current_selection:
                        self.emotion_combo.setCurrentIndex(i)
                        break
            else:
                # デフォルト選択（Neutral系を優先）
                for i in range(self.emotion_combo.count()):
                    if self.emotion_combo.itemData(i).lower() in ['neutral', 'ニュートラル']:
                        self.emotion_combo.setCurrentIndex(i)
                        break
                else:
                    # Neutralがない場合は最初の項目
                    if self.emotion_combo.count() > 0:
                        self.emotion_combo.setCurrentIndex(0)
            
            # パラメータを更新
            current_style = self.emotion_combo.currentData()
            if current_style:
                self.current_params['style'] = current_style
            
            self.emotion_combo.blockSignals(False)
            
        except Exception as e:
            print(f"❌ 感情UI更新エラー ({self.row_id}): {e}")

class TabbedEmotionControl(QWidget):
    """タブ式感情制御ウィジェット（複数Undo対応版）"""
    
    parameters_changed = pyqtSignal(str, dict)
    master_parameters_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.emotion_controls = {}
        self.master_control = None
        self.current_available_styles = ['Neutral']  # デフォルト
        self.init_ui()
        self.setup_master_tab()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #5ba8f2;
                border-radius: 4px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                margin-right: 2px;
                margin-bottom: -1px;
            }
            QTabBar::tab:selected {
                background-color: #5ba8f2;
                color: white;
                border: 1px solid #5ba8f2;
                border-bottom: none;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e6f2ff;
                border-color: #5ba8f2;
                color: #5ba8f2;
            }
            QTabBar::tab:first {
                background-color: #fffef7;
                border: 2px solid #ffd700;
                color: #b8860b;
                font-weight: bold;
            }
            QTabBar::tab:first:selected {
                background-color: #ffd700;
                color: #b8860b;
                border: 2px solid #ffd700;
                border-bottom: none;
            }
            QTabBar::tab:first:hover:!selected {
                background-color: #fff9c4;
                border-color: #daa520;
            }
        """)
        
        # 🆕 標準の三角ボタンを非表示にする
        tab_bar = self.tab_widget.tabBar()
        tab_bar.setUsesScrollButtons(False)
        
        layout.addWidget(self.tab_widget)
        
        # 🆕 タブナビゲーション（スライダー + ◁▷ボタン）
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(10, 2, 10, 5)
        nav_layout.setSpacing(8)
        
        slider_label = QLabel("タブ位置:")
        slider_label.setStyleSheet("font-size: 10px; color: #666;")
        nav_layout.addWidget(slider_label)
        
        # タブスクロール用スライダー
        self.tab_scroll_slider = QSlider(Qt.Orientation.Horizontal)
        self.tab_scroll_slider.setRange(0, 0)
        self.tab_scroll_slider.setValue(0)
        self.tab_scroll_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #ccc;
                background: #f5f5f5;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #5ba8f2;
                border: 1px solid #4a90e2;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #5ba8f2;
                border: 1px solid #4a90e2;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
        """)
        self.tab_scroll_slider.valueChanged.connect(self.on_tab_scroll_slider_changed)
        
        nav_layout.addWidget(self.tab_scroll_slider, 1)  # スライダーは伸縮
        
        # ◁ ボタン（前のタブへ）
        self.prev_tab_btn = QPushButton("◁")
        self.prev_tab_btn.setFixedSize(28, 28)
        self.prev_tab_btn.setStyleSheet("""
            QPushButton {
                background-color: #5ba8f2;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a90e2;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #999;
            }
        """)
        self.prev_tab_btn.clicked.connect(self.on_prev_tab_clicked)
        nav_layout.addWidget(self.prev_tab_btn)
        
        # ▷ ボタン（次のタブへ）
        self.next_tab_btn = QPushButton("▷")
        self.next_tab_btn.setFixedSize(28, 28)
        self.next_tab_btn.setStyleSheet("""
            QPushButton {
                background-color: #5ba8f2;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a90e2;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #999;
            }
        """)
        self.next_tab_btn.clicked.connect(self.on_next_tab_clicked)
        nav_layout.addWidget(self.next_tab_btn)
        
        layout.addLayout(nav_layout)
    
    def setup_master_tab(self):
        self.master_control = SingleEmotionControl("master", is_master=True)
        self.master_control.parameters_changed.connect(self.on_master_parameters_changed)
        self.master_control.undo_executed.connect(self.on_undo_executed)
        
        self.tab_widget.insertTab(0, self.master_control, "★")
        self.tab_widget.setTabToolTip(0, "デフォルトパラメータ - ここを変更すると全てのタブに反映されます")
        self.update_tab_scroll_range()
    
    def on_master_parameters_changed(self, row_id, parameters):
        for control in self.emotion_controls.values():
            control.update_parameters_from_master(parameters)
        
        self.master_parameters_changed.emit(parameters)

    def on_undo_executed(self, row_id):
        """Undo実行通知"""
        pass
    
    # ================================
    # 改良版Undo機能の公開メソッド
    # ================================
    
    def undo_current_tab_parameters(self):
        """現在のタブのパラメータをUndoする"""
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, SingleEmotionControl):
            success = current_widget.undo_parameters()
            if success:
                return True
            else:
                return False
        
        return False
    
    def has_current_tab_undo_available(self):
        """現在のタブでUndoが可能かどうか"""
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, SingleEmotionControl):
            return current_widget.has_undo_available()
        return False
    
    def add_text_row(self, row_id, row_number, parameters=None):
        if row_id not in self.emotion_controls:
            base_params = self.master_control.get_current_parameters() if self.master_control else {}
            if parameters:
                base_params.update(parameters)
            
            control = SingleEmotionControl(row_id, base_params)
            control.parameters_changed.connect(self.parameters_changed)
            control.undo_executed.connect(self.on_undo_executed)
            
            if hasattr(self, 'current_available_styles'):
                control.update_emotion_combo(self.current_available_styles)
            
            self.emotion_controls[row_id] = control
            self.tab_widget.addTab(control, str(row_number))
            
            # 🆕 スライダー範囲を更新
            self.update_tab_scroll_range()

    def remove_text_row(self, row_id):
        if row_id in self.emotion_controls:
            control = self.emotion_controls[row_id]
            index = self.tab_widget.indexOf(control)
            if index != -1:
                self.tab_widget.removeTab(index)
            del self.emotion_controls[row_id]
            
            # 🆕 スライダー範囲を更新
            self.update_tab_scroll_range()
        
    def update_tab_numbers(self, row_mapping):
        for row_id, row_number in row_mapping.items():
            if row_id in self.emotion_controls:
                control = self.emotion_controls[row_id]
                index = self.tab_widget.indexOf(control)
                if index != -1:
                    self.tab_widget.setTabText(index, str(row_number))
    
    def get_parameters(self, row_id):
        if row_id in self.emotion_controls:
            return self.emotion_controls[row_id].get_current_parameters()
        elif self.master_control:
            return self.master_control.get_current_parameters()
        return {}
    
    def get_master_parameters(self):
        if self.master_control:
            return self.master_control.get_current_parameters()
        return {}
    
    def set_current_row(self, row_id):
        if row_id in self.emotion_controls:
            control = self.emotion_controls[row_id]
            index = self.tab_widget.indexOf(control)
            if index != -1:
                self.tab_widget.setCurrentIndex(index)
    
    def update_emotion_list(self, available_styles):
        """モデル読み込み後に全タブの感情リストを更新"""
        try:
            # 現在の利用可能感情を保存
            self.current_available_styles = available_styles
            
            # マスタータブを更新
            if self.master_control:
                self.master_control.update_emotion_combo(available_styles)
            
            # 各個別タブを更新
            for row_id, control in self.emotion_controls.items():
                control.update_emotion_combo(available_styles)
            
        except Exception as e:
            print(f"❌ 全タブ感情更新エラー: {e}")

    def on_tab_scroll_slider_changed(self, value):
        """スライダーでタブを選択"""
        if self.tab_widget.count() > 0:
            target_index = min(value, self.tab_widget.count() - 1)
            self.tab_widget.setCurrentIndex(target_index)
            self.update_nav_buttons()

    def on_prev_tab_clicked(self):
        """前のタブに移動"""
        current_index = self.tab_widget.currentIndex()
        if current_index > 0:
            self.tab_widget.setCurrentIndex(current_index - 1)
            self.tab_scroll_slider.setValue(current_index - 1)
            self.update_nav_buttons()

    def on_next_tab_clicked(self):
        """次のタブに移動"""
        current_index = self.tab_widget.currentIndex()
        if current_index < self.tab_widget.count() - 1:
            self.tab_widget.setCurrentIndex(current_index + 1)
            self.tab_scroll_slider.setValue(current_index + 1)
            self.update_nav_buttons()

    def update_nav_buttons(self):
        """ナビゲーションボタンの有効/無効を更新"""
        current_index = self.tab_widget.currentIndex()
        tab_count = self.tab_widget.count()
        
        # 最初のタブなら◁を無効化
        self.prev_tab_btn.setEnabled(current_index > 0)
        
        # 最後のタブなら▷を無効化
        self.next_tab_btn.setEnabled(current_index < tab_count - 1)

    def update_tab_scroll_range(self):
        """タブ数に応じてスライダーの範囲を更新"""
        tab_count = self.tab_widget.count()
        if tab_count > 0:
            self.tab_scroll_slider.setMaximum(tab_count - 1)
            self.tab_scroll_slider.setEnabled(True)
            
            # 現在のタブインデックスに合わせる
            current_index = self.tab_widget.currentIndex()
            self.tab_scroll_slider.blockSignals(True)
            self.tab_scroll_slider.setValue(current_index)
            self.tab_scroll_slider.blockSignals(False)
        else:
            self.tab_scroll_slider.setMaximum(0)
            self.tab_scroll_slider.setEnabled(False)
        
        self.update_nav_buttons()