from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, 
                            QComboBox, QDoubleSpinBox, QGroupBox, QGridLayout, QPushButton, QTabWidget,
                            QInputDialog, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import json
import os
from pathlib import Path
from .history_manager import ParameterHistory


class EmotionPresetManager:
    """感情パラメータプリセット管理クラス（統一版）"""
    
    def __init__(self):
        self.settings_file = Path("user_settings.json")
        self.default_presets = {
            'standard': {
                'name': '標準',
                'parameters': {
                    'style': 'Neutral', 'style_weight': 1.0, 'length_scale': 0.85,
                    'pitch_scale': 1.0, 'intonation_scale': 1.0, 'sdp_ratio': 0.25, 'noise': 0.35
                }
            }
        }
        self.settings = self.load_settings()
    
    def load_settings(self):
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if 'emotion_presets' not in loaded:
                        loaded['emotion_presets'] = {
                            'presets': self.default_presets.copy(),
                            'last_selected': 'standard'
                        }
                    return loaded
            else:
                return {
                    'emotion_presets': {
                        'presets': self.default_presets.copy(),
                        'last_selected': 'standard'
                    }
                }
        except:
            return {
                'emotion_presets': {
                    'presets': self.default_presets.copy(),
                    'last_selected': 'standard'
                }
            }
    
    def save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def get_all_presets(self):
        return self.settings.get('emotion_presets', {}).get('presets', {})
    
    def get_preset(self, preset_key):
        presets = self.get_all_presets()
        return presets.get(preset_key)
    
    def save_preset(self, preset_key, name, parameters):
        if 'emotion_presets' not in self.settings:
            self.settings['emotion_presets'] = {'presets': {}, 'last_selected': 'standard'}
        
        self.settings['emotion_presets']['presets'][preset_key] = {
            'name': name,
            'parameters': parameters.copy()
        }
        self.save_settings()
    
    def delete_preset(self, preset_key):
        if preset_key in self.default_presets:
            return False
        
        presets = self.settings.get('emotion_presets', {}).get('presets', {})
        if preset_key in presets:
            del presets[preset_key]
            self.save_settings()
            return True
        return False
    
    def rename_preset(self, preset_key, new_name):
        presets = self.settings.get('emotion_presets', {}).get('presets', {})
        if preset_key in presets:
            presets[preset_key]['name'] = new_name
            self.save_settings()
            return True
        return False
    
    def is_default_preset(self, preset_key):
        return preset_key in self.default_presets

# グローバル統一プリセット管理器
_global_preset_manager = None

def get_global_preset_manager():
    global _global_preset_manager
    if _global_preset_manager is None:
        _global_preset_manager = EmotionPresetManager()
    return _global_preset_manager

class SingleEmotionControl(QWidget):
    """単一行の感情制御ウィジェット（複数Undo対応版）"""
    
    parameters_changed = pyqtSignal(str, dict)
    preset_list_changed = pyqtSignal()  # プリセットリスト変更通知
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
        
        # 統一プリセット管理器
        self.preset_manager = get_global_preset_manager()
        
        self.init_ui()
        self.load_parameters()
        self.load_preset_list()
        
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
        
        preset_group = self.create_preset_group()
        layout.addWidget(preset_group)

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
    
    def create_preset_group(self):
        group = QGroupBox("プリセット")
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
        
        selection_layout = QHBoxLayout()
        selection_layout.setSpacing(8)
        
        preset_label = QLabel("プリセット:")
        preset_label.setMinimumWidth(80)
        
        self.preset_combo = QComboBox()
        self.preset_combo.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
                min-width: 120px;
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
        self.preset_combo.currentTextChanged.connect(self.on_preset_selected)
        
        self.rename_btn = QPushButton("✎")
        self.rename_btn.setFixedSize(28, 28)
        self.rename_btn.setToolTip("プリセット名を変更")
        self.rename_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e2e6ea;
                border-color: #adb5bd;
            }
        """)
        self.rename_btn.clicked.connect(self.rename_current_preset)
        
        self.delete_btn = QPushButton("🗑️")
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.setToolTip("プリセットを削除")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #f5c6cb;
                border-color: #f1556c;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_current_preset)
        
        selection_layout.addWidget(preset_label)
        selection_layout.addWidget(self.preset_combo, 1)
        selection_layout.addWidget(self.rename_btn)
        selection_layout.addWidget(self.delete_btn)
        
        self.save_btn = QPushButton("💾 現在の設定をプリセットとして保存")
        self.save_btn.setMinimumHeight(35)
        
        if self.is_master:
            self.save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffc107;
                    color: #212529;
                    border: 2px solid #ffd700;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #e0a800;
                    border-color: #daa520;
                }
            """)
        else:
            self.save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
        
        self.save_btn.clicked.connect(self.save_current_preset)
        
        layout.addLayout(selection_layout)
        layout.addWidget(self.save_btn)
        
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
    
    def load_preset_list(self):
        self.preset_combo.clear()
        
        presets = self.preset_manager.get_all_presets()
        for preset_key, preset_data in presets.items():
            if isinstance(preset_data, dict) and 'name' in preset_data:
                self.preset_combo.addItem(preset_data['name'], preset_key)
    
    def on_preset_selected(self):
        if self.is_loading_parameters:
            return
            
        preset_key = self.preset_combo.currentData()
        if preset_key:
            preset = self.preset_manager.get_preset(preset_key)
            if preset:
                # 現在の状態を履歴に保存してからプリセット適用
                self.save_current_state_to_history()
                
                self.current_params.update(preset['parameters'])
                self.load_parameters()
                self.emit_parameters_changed()
            
            is_default = self.preset_manager.is_default_preset(preset_key)
            self.rename_btn.setEnabled(not is_default)
            self.delete_btn.setEnabled(not is_default)
    
    def save_current_preset(self):
        name, ok = QInputDialog.getText(self, "プリセット保存", "プリセット名を入力してください:", text="カスタムプリセット")
        
        if ok and name.strip():
            import time
            preset_key = f"custom_{int(time.time())}"
            
            self.preset_manager.save_preset(preset_key, name.strip(), self.current_params)
            
            # 全タブにリスト更新を通知
            self.preset_list_changed.emit()
            
            # 保存したプリセットを選択
            self.load_preset_list()
            for i in range(self.preset_combo.count()):
                if self.preset_combo.itemData(i) == preset_key:
                    self.preset_combo.setCurrentIndex(i)
                    break
    
    def rename_current_preset(self):
        preset_key = self.preset_combo.currentData()
        if not preset_key or self.preset_manager.is_default_preset(preset_key):
            return
        
        current_preset = self.preset_manager.get_preset(preset_key)
        if not current_preset:
            return
        
        new_name, ok = QInputDialog.getText(self, "プリセット名変更", "新しいプリセット名を入力してください:", text=current_preset['name'])
        
        if ok and new_name.strip():
            self.preset_manager.rename_preset(preset_key, new_name.strip())
            
            # 全タブにリスト更新を通知
            self.preset_list_changed.emit()
            
            self.load_preset_list()
            for i in range(self.preset_combo.count()):
                if self.preset_combo.itemData(i) == preset_key:
                    self.preset_combo.setCurrentIndex(i)
                    break
    
    def delete_current_preset(self):
        preset_key = self.preset_combo.currentData()
        if not preset_key or self.preset_manager.is_default_preset(preset_key):
            return
        
        if self.preset_manager.delete_preset(preset_key):
            # 全タブにリスト更新を通知
            self.preset_list_changed.emit()
            
            self.load_preset_list()
            for i in range(self.preset_combo.count()):
                if self.preset_combo.itemData(i) == 'standard':
                    self.preset_combo.setCurrentIndex(i)
                    break
    
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
    
    def refresh_preset_list(self):
        """プリセットリストを更新（外部から呼ばれる）"""
        self.load_preset_list()
    
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
        
        layout.addWidget(self.tab_widget)
    
    def setup_master_tab(self):
        self.master_control = SingleEmotionControl("master", is_master=True)
        self.master_control.parameters_changed.connect(self.on_master_parameters_changed)
        self.master_control.preset_list_changed.connect(self.on_preset_list_changed)
        self.master_control.undo_executed.connect(self.on_undo_executed)
        
        self.tab_widget.insertTab(0, self.master_control, "★")
        self.tab_widget.setTabToolTip(0, "デフォルトパラメータ - ここを変更すると全てのタブに反映されます")
    
    def on_master_parameters_changed(self, row_id, parameters):
        for control in self.emotion_controls.values():
            control.update_parameters_from_master(parameters)
        
        self.master_parameters_changed.emit(parameters)
    
    def on_preset_list_changed(self):
        """プリセットリスト変更時 - 全タブを更新"""
        if self.master_control:
            self.master_control.refresh_preset_list()
        
        for control in self.emotion_controls.values():
            control.refresh_preset_list()
    
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
            control.preset_list_changed.connect(self.on_preset_list_changed)
            control.undo_executed.connect(self.on_undo_executed)
            
            # 👈 新しいタブにも現在の利用可能感情を適用
            if hasattr(self, 'current_available_styles'):
                control.update_emotion_combo(self.current_available_styles)
            
            self.emotion_controls[row_id] = control
            self.tab_widget.addTab(control, str(row_number))
    
    def remove_text_row(self, row_id):
        if row_id in self.emotion_controls:
            control = self.emotion_controls[row_id]
            index = self.tab_widget.indexOf(control)
            if index != -1:
                self.tab_widget.removeTab(index)
            del self.emotion_controls[row_id]
    
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