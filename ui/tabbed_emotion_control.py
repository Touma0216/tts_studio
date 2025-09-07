from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, 
                            QComboBox, QDoubleSpinBox, QGroupBox, QGridLayout, QPushButton, QTabWidget,
                            QInputDialog, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import json
import os
from pathlib import Path

class EmotionPresetManager:
    """感情パラメータプリセット管理クラス"""
    
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
        """設定を読み込み"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    
                    # emotion_presets が存在しない場合は作成
                    if 'emotion_presets' not in loaded:
                        loaded['emotion_presets'] = {
                            'presets': self.default_presets.copy(),
                            'last_selected': 'standard'
                        }
                    
                    print(f"📁 プリセット設定を読み込み: {self.settings_file}")
                    return loaded
            else:
                # 新規作成
                settings = {
                    'emotion_presets': {
                        'presets': self.default_presets.copy(),
                        'last_selected': 'standard'
                    }
                }
                print("📄 新規プリセット設定ファイルを作成します")
                return settings
                
        except Exception as e:
            print(f"⚠️ プリセット設定読み込みエラー: {e} - デフォルト設定を使用")
            return {
                'emotion_presets': {
                    'presets': self.default_presets.copy(),
                    'last_selected': 'standard'
                }
            }
    
    def save_settings(self):
        """設定を保存"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            print(f"💾 プリセット設定を保存: {self.settings_file}")
        except Exception as e:
            print(f"❌ プリセット設定保存エラー: {e}")
    
    def get_all_presets(self):
        """全プリセットを取得"""
        presets = self.settings.get('emotion_presets', {}).get('presets', {})
        
        # 防御的チェック：無効なエントリを除外
        valid_presets = {}
        for key, value in presets.items():
            if isinstance(value, dict) and 'name' in value and 'parameters' in value:
                valid_presets[key] = value
            else:
                print(f"⚠️ 無効なプリセットエントリを除外: {key} = {value}")
        
        return valid_presets
    
    def get_preset(self, preset_key):
        """指定プリセットを取得"""
        presets = self.get_all_presets()
        return presets.get(preset_key)
    
    def save_preset(self, preset_key, name, parameters):
        """プリセットを保存"""
        if 'emotion_presets' not in self.settings:
            self.settings['emotion_presets'] = {'presets': {}, 'last_selected': 'standard'}
        
        self.settings['emotion_presets']['presets'][preset_key] = {
            'name': name,
            'parameters': parameters.copy()
        }
        self.save_settings()
        print(f"💾 プリセット保存: {name} ({preset_key})")
    
    def delete_preset(self, preset_key):
        """プリセットを削除（デフォルトは削除不可）"""
        if preset_key in self.default_presets:
            return False  # デフォルトプリセットは削除不可
        
        presets = self.settings.get('emotion_presets', {}).get('presets', {})
        if preset_key in presets:
            del presets[preset_key]
            self.save_settings()
            print(f"🗑️ プリセット削除: {preset_key}")
            return True
        return False
    
    def rename_preset(self, preset_key, new_name):
        """プリセット名を変更"""
        presets = self.settings.get('emotion_presets', {}).get('presets', {})
        if preset_key in presets:
            presets[preset_key]['name'] = new_name
            self.save_settings()
            print(f"✏️ プリセット名変更: {preset_key} -> {new_name}")
            return True
        return False
    
    def get_last_selected(self):
        """最後に選択したプリセットを取得"""
        return self.settings.get('emotion_presets', {}).get('last_selected', 'standard')
    
    def set_last_selected(self, preset_key):
        """最後に選択したプリセットを設定"""
        if 'emotion_presets' not in self.settings:
            self.settings['emotion_presets'] = {'presets': {}, 'last_selected': 'standard'}
        
        self.settings['emotion_presets']['last_selected'] = preset_key
        self.save_settings()
    
    def is_default_preset(self, preset_key):
        """デフォルトプリセットかどうかを判定"""
        return preset_key in self.default_presets

class SingleEmotionControl(QWidget):
    """単一行の感情制御ウィジェット（プリセット機能付き）"""
    
    parameters_changed = pyqtSignal(str, dict)  # row_id, parameters
    
    def __init__(self, row_id, parameters=None, is_master=False, parent=None):
        super().__init__(parent)
        
        self.row_id = row_id
        self.is_master = is_master
        self.current_params = parameters or {
            'style': 'Neutral',
            'style_weight': 1.0,
            'length_scale': 0.85,
            'pitch_scale': 1.0,
            'intonation_scale': 1.0,
            'sdp_ratio': 0.25,
            'noise': 0.35
        }
        
        # プリセット管理器
        self.preset_manager = EmotionPresetManager()
        
        self.init_ui()
        self.load_parameters()
        self.load_preset_list()
        self.restore_last_preset()
        
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 感情制御グループ
        emotion_group = self.create_emotion_group()
        layout.addWidget(emotion_group)
        
        # 音声パラメータグループ
        params_group = self.create_params_group()
        layout.addWidget(params_group)
        
        # プリセットグループ（新しい実装）
        preset_group = self.create_preset_group()
        layout.addWidget(preset_group)

        # マスタータブの場合は説明を追加
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
        """感情制御グループを作成"""
        group = QGroupBox("感情制御")
        group_style = """
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
        """
        
        # マスタータブの場合は枠を金色に
        if self.is_master:
            group_style = """
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
            """
        
        group.setStyleSheet(group_style)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # 感情選択（初期化時は固定リスト）
        emotion_layout = QHBoxLayout()
        emotion_label = QLabel("感情:")
        emotion_label.setMinimumWidth(80)
        
        self.emotion_combo = QComboBox()
        self.emotion_combo.setToolTip("感情選択(E)")
        
        # 初期化時は固定の感情リスト（後でモデル読み込み時に更新）
        emotions = [
            ("Neutral", "😐 ニュートラル"),
            ("Happy", "😊 喜び"),
            ("Sad", "😢 悲しみ"), 
            ("Angry", "😠 怒り"),
            ("Fear", "😰 恐怖"),
            ("Disgust", "😖 嫌悪"),
            ("Surprise", "😲 驚き")
        ]
        
        for value, display in emotions:
            self.emotion_combo.addItem(display, value)
        
        self.emotion_combo.currentTextChanged.connect(self.on_emotion_changed)
        
        emotion_layout.addWidget(emotion_label)
        emotion_layout.addWidget(self.emotion_combo, 1)
        
        # 感情強度
        intensity_layout = QHBoxLayout()
        intensity_label = QLabel("感情強度:")
        intensity_label.setMinimumWidth(80)
        
        self.intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.intensity_slider.setRange(0, 200)
        self.intensity_slider.setValue(100)
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
        
        # マスタータブの場合はスライダーを金色に
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
        """音声パラメータグループを作成"""
        group = QGroupBox("音声パラメータ")
        group_style = """
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
        """
        
        # マスタータブの場合は枠を金色に
        if self.is_master:
            group_style = """
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
            """
        
        group.setStyleSheet(group_style)
        
        layout = QGridLayout(group)
        layout.setSpacing(8)
        
        # パラメータ定義
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
        
        # マスター用金色スライダー
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
            spinbox.valueChanged.connect(lambda v, k=key: self.on_param_spinbox_changed(k, v))
            
            self.param_sliders[key] = slider
            self.param_spinboxes[key] = spinbox
            
            layout.addWidget(label, i, 0)
            layout.addWidget(slider, i, 1)
            layout.addWidget(spinbox, i, 2)
            layout.addWidget(desc_label, i, 3)
        
        return group
    
    def create_preset_group(self):
        """プリセットグループを作成（新機能）"""
        group = QGroupBox("プリセット")
        group_style = """
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
        """
        
        # マスタータブの場合は枠を金色に
        if self.is_master:
            group_style = """
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
            """
        
        group.setStyleSheet(group_style)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # プリセット選択行
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
        
        # 名前変更ボタン（✎）
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
            QPushButton:pressed {
                background-color: #dae0e5;
            }
        """)
        self.rename_btn.clicked.connect(self.rename_current_preset)
        
        # 削除ボタン（🗑️）
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
            QPushButton:pressed {
                background-color: #f1aeb5;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_current_preset)
        
        selection_layout.addWidget(preset_label)
        selection_layout.addWidget(self.preset_combo, 1)
        selection_layout.addWidget(self.rename_btn)
        selection_layout.addWidget(self.delete_btn)
        
        # 保存ボタン（横長）
        self.save_btn = QPushButton("💾 現在の設定をプリセットとして保存")
        self.save_btn.setMinimumHeight(35)
        
        save_btn_style = """
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
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """
        
        # マスター用保存ボタンスタイル
        if self.is_master:
            save_btn_style = """
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
                QPushButton:pressed {
                    background-color: #d39e00;
                }
            """
        
        self.save_btn.setStyleSheet(save_btn_style)
        self.save_btn.clicked.connect(self.save_current_preset)
        
        layout.addLayout(selection_layout)
        layout.addWidget(self.save_btn)
        
        return group
    
    def load_preset_list(self):
        """プリセットリストを読み込み"""
        self.preset_combo.clear()
        
        presets = self.preset_manager.get_all_presets()
        for preset_key, preset_data in presets.items():
            self.preset_combo.addItem(preset_data['name'], preset_key)
    
    def restore_last_preset(self):
        """前回選択していたプリセットを復元"""
        last_preset = self.preset_manager.get_last_selected()
        
        # コンボボックスから該当プリセットを探して選択
        for i in range(self.preset_combo.count()):
            if self.preset_combo.itemData(i) == last_preset:
                self.preset_combo.setCurrentIndex(i)
                self.apply_preset_by_key(last_preset)
                break
    
    def on_preset_selected(self):
        """プリセット選択時の処理"""
        preset_key = self.preset_combo.currentData()
        if preset_key:
            self.apply_preset_by_key(preset_key)
            self.preset_manager.set_last_selected(preset_key)
            
            # ボタンの有効/無効を設定
            is_default = self.preset_manager.is_default_preset(preset_key)
            self.rename_btn.setEnabled(not is_default)
            self.delete_btn.setEnabled(not is_default)
    
    def apply_preset_by_key(self, preset_key):
        """プリセットキーから設定を適用"""
        preset = self.preset_manager.get_preset(preset_key)
        if preset:
            self.current_params.update(preset['parameters'])
            self.load_parameters()
            self.emit_parameters_changed()
    
    def save_current_preset(self):
        """現在の設定をプリセットとして保存"""
        # プリセット名を入力
        name, ok = QInputDialog.getText(
            self,
            "プリセット保存",
            "プリセット名を入力してください:",
            text="カスタムプリセット"
        )
        
        if ok and name.strip():
            # ユニークキーを生成
            import time
            preset_key = f"custom_{int(time.time())}"
            
            # プリセットを保存
            self.preset_manager.save_preset(preset_key, name.strip(), self.current_params)
            
            # リストを再読み込み
            self.load_preset_list()
            
            # 保存したプリセットを選択
            for i in range(self.preset_combo.count()):
                if self.preset_combo.itemData(i) == preset_key:
                    self.preset_combo.setCurrentIndex(i)
                    break
            
            # 保存完了（音なし）
            print(f"💾 プリセット保存完了: {name}")
    
    def rename_current_preset(self):
        """現在のプリセット名を変更"""
        preset_key = self.preset_combo.currentData()
        if not preset_key:
            return
        
        if self.preset_manager.is_default_preset(preset_key):
            print("⚠️ デフォルトプリセットの名前は変更できません")
            return
        
        current_preset = self.preset_manager.get_preset(preset_key)
        if not current_preset:
            return
        
        new_name, ok = QInputDialog.getText(
            self,
            "プリセット名変更",
            "新しいプリセット名を入力してください:",
            text=current_preset['name']
        )
        
        if ok and new_name.strip():
            self.preset_manager.rename_preset(preset_key, new_name.strip())
            self.load_preset_list()
            
            # 変更したプリセットを再選択
            for i in range(self.preset_combo.count()):
                if self.preset_combo.itemData(i) == preset_key:
                    self.preset_combo.setCurrentIndex(i)
                    break
            
            # 名前変更完了（音なし）
            print(f"✏️ プリセット名変更完了: '{new_name}'")
    
    def delete_current_preset(self):
        """現在のプリセットを削除"""
        preset_key = self.preset_combo.currentData()
        if not preset_key:
            return
        
        if self.preset_manager.is_default_preset(preset_key):
            print("⚠️ デフォルトプリセットは削除できません")
            return
        
        current_preset = self.preset_manager.get_preset(preset_key)
        if not current_preset:
            return
        
        # 確認なしで直接削除
        self.preset_manager.delete_preset(preset_key)
        self.load_preset_list()
        
        # 標準プリセットを選択
        for i in range(self.preset_combo.count()):
            if self.preset_combo.itemData(i) == 'standard':
                self.preset_combo.setCurrentIndex(i)
                break
        
        # 削除完了（ログなし）
    
    def on_emotion_changed(self, text):
        """感情変更時の処理"""
        current_data = self.emotion_combo.currentData()
        if current_data:
            self.current_params['style'] = current_data
            self.emit_parameters_changed()
    
    def on_intensity_slider_changed(self, value):
        """感情強度スライダー変更時"""
        float_value = value / 100.0
        self.intensity_spinbox.blockSignals(True)
        self.intensity_spinbox.setValue(float_value)
        self.intensity_spinbox.blockSignals(False)
        
        self.current_params['style_weight'] = float_value
        self.emit_parameters_changed()
    
    def on_intensity_spinbox_changed(self, value):
        """感情強度数値入力変更時"""
        int_value = int(value * 100)
        self.intensity_slider.blockSignals(True)
        self.intensity_slider.setValue(int_value)
        self.intensity_slider.blockSignals(False)
        
        self.current_params['style_weight'] = value
        self.emit_parameters_changed()
    
    def on_param_slider_changed(self, param_key, value):
        """パラメータスライダー変更時"""
        float_value = value / 100.0
        
        spinbox = self.param_spinboxes[param_key]
        spinbox.blockSignals(True)
        spinbox.setValue(float_value)
        spinbox.blockSignals(False)
        
        self.current_params[param_key] = float_value
        self.emit_parameters_changed()
    
    def on_param_spinbox_changed(self, param_key, value):
        """パラメータ数値入力変更時"""
        int_value = int(value * 100)
        
        slider = self.param_sliders[param_key]
        slider.blockSignals(True)
        slider.setValue(int_value)
        slider.blockSignals(False)
        
        self.current_params[param_key] = value
        self.emit_parameters_changed()
    
    def load_parameters(self):
        """現在のパラメータでUIを更新"""
        self.blockSignals(True)
        
        # 感情
        for i in range(self.emotion_combo.count()):
            if self.emotion_combo.itemData(i) == self.current_params['style']:
                self.emotion_combo.setCurrentIndex(i)
                break
        
        # 感情強度
        style_weight = self.current_params['style_weight']
        self.intensity_slider.setValue(int(style_weight * 100))
        self.intensity_spinbox.setValue(style_weight)
        
        # その他のパラメータ
        for key, value in self.current_params.items():
            if key in self.param_sliders:
                self.param_sliders[key].setValue(int(value * 100))
                self.param_spinboxes[key].setValue(value)
        
        self.blockSignals(False)
    
    def emit_parameters_changed(self):
        """パラメータ変更シグナルを送信"""
        self.parameters_changed.emit(self.row_id, self.current_params.copy())
    
    def get_current_parameters(self):
        """現在のパラメータを取得"""
        return self.current_params.copy()
    
    def update_parameters_from_master(self, master_params):
        """マスターパラメータから更新（UIも更新）"""
        self.current_params.update(master_params)
        self.load_parameters()
    
    def update_emotion_combo(self, available_styles):
        """感情コンボボックスを利用可能なスタイルで更新"""
        try:
            current_selection = self.emotion_combo.currentData()
            self.emotion_combo.clear()
            
            for style in available_styles:
                # 適切な絵文字を選択
                emoji = self._get_style_emoji(style)
                display_name = f"{emoji} {style}"
                self.emotion_combo.addItem(display_name, style)
            
            # 以前の選択を復元（可能なら）
            if current_selection:
                for i in range(self.emotion_combo.count()):
                    if self.emotion_combo.itemData(i) == current_selection:
                        self.emotion_combo.setCurrentIndex(i)
                        return
            
            # 復元できない場合はNeutralを選択
            for i in range(self.emotion_combo.count()):
                if self.emotion_combo.itemData(i) in ['Neutral', 'neutral']:
                    self.emotion_combo.setCurrentIndex(i)
                    break
            
            print(f"✅ 単一感情コンボ更新完了: {self.row_id}")
            
        except Exception as e:
            print(f"❌ 単一感情コンボ更新エラー({self.row_id}): {e}")
    
    def _get_style_emoji(self, style):
        """スタイルに対応する絵文字を取得"""
        style_lower = style.lower()
        
        emoji_map = {
            'neutral': '😐',
            'happy': '😊',
            'happiness': '😊',
            'sad': '😢',
            'sadness': '😢',
            'angry': '😠',
            'anger': '😠',
            'fear': '😰',
            'disgust': '😖',
            'surprise': '😲',
        }
        
        return emoji_map.get(style_lower, '🎭')

class TabbedEmotionControl(QWidget):
    """タブ式感情制御ウィジェット（統一プリセット機能付き）"""
    
    parameters_changed = pyqtSignal(str, dict)  # row_id, parameters
    master_parameters_changed = pyqtSignal(dict)  # master_parameters
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.emotion_controls = {}  # row_id -> SingleEmotionControl
        self.master_control = None  # マスターコントロール
        
        # 統一プリセット管理器
        self.preset_manager = EmotionPresetManager()
        
        self.init_ui()
        self.setup_master_tab()
        
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # タブウィジェット
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
            /* マスタータブ（最初のタブ）用のスタイル */
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
        """マスタータブを設定"""
        # マスターコントロールには統一プリセット管理器を渡す
        self.master_control = SingleEmotionControl("master", is_master=True)
        self.master_control.preset_manager = self.preset_manager  # 統一管理器を共有
        self.master_control.parameters_changed.connect(self.on_master_parameters_changed)
        
        # マスタータブを最初に追加
        self.tab_widget.insertTab(0, self.master_control, "★")
        self.tab_widget.setTabToolTip(0, "デフォルトパラメータ - ここを変更すると全てのタブに反映されます")
    
    def on_master_parameters_changed(self, row_id, parameters):
        """マスターパラメータが変更された時の処理"""
        # すべての個別タブに反映
        for control in self.emotion_controls.values():
            control.update_parameters_from_master(parameters)
        
        # マスターパラメータ変更シグナルを送信
        self.master_parameters_changed.emit(parameters)
    
    def add_text_row(self, row_id, row_number, parameters=None):
        """テキスト行に対応するタブを追加"""
        if row_id not in self.emotion_controls:
            # マスターパラメータをベースにする
            base_params = self.master_control.get_current_parameters() if self.master_control else {}
            if parameters:
                base_params.update(parameters)
            
            control = SingleEmotionControl(row_id, base_params)
            control.preset_manager = self.preset_manager  # 統一管理器を共有
            control.parameters_changed.connect(self.parameters_changed)
            control.parameters_changed.connect(self.on_individual_parameters_changed)  # 個別→マスター連動
            
            self.emotion_controls[row_id] = control
            self.tab_widget.addTab(control, str(row_number))
    
    def on_individual_parameters_changed(self, row_id, parameters):
        """個別パラメータが変更された時の処理（マスターへの連動）"""
        # 個別タブでプリセットが変更された場合、マスターにも反映
        if row_id != "master" and self.master_control:
            # プリセット選択の場合のみマスターに反映
            current_control = self.emotion_controls.get(row_id)
            if current_control and hasattr(current_control, 'preset_combo'):
                current_preset_key = current_control.preset_combo.currentData()
                if current_preset_key:
                    # マスターのプリセット選択も同期
                    for i in range(self.master_control.preset_combo.count()):
                        if self.master_control.preset_combo.itemData(i) == current_preset_key:
                            self.master_control.preset_combo.setCurrentIndex(i)
                            break
    
    def remove_text_row(self, row_id):
        """テキスト行に対応するタブを削除"""
        if row_id in self.emotion_controls:
            control = self.emotion_controls[row_id]
            index = self.tab_widget.indexOf(control)
            if index != -1:
                self.tab_widget.removeTab(index)
            del self.emotion_controls[row_id]
    
    def update_tab_numbers(self, row_mapping):
        """タブ番号を更新 {row_id: row_number}"""
        for row_id, row_number in row_mapping.items():
            if row_id in self.emotion_controls:
                control = self.emotion_controls[row_id]
                index = self.tab_widget.indexOf(control)
                if index != -1:
                    self.tab_widget.setTabText(index, str(row_number))
    
    def get_parameters(self, row_id):
        """指定行のパラメータを取得"""
        if row_id in self.emotion_controls:
            return self.emotion_controls[row_id].get_current_parameters()
        # マスターパラメータを返す
        elif self.master_control:
            return self.master_control.get_current_parameters()
        return {}
    
    def get_master_parameters(self):
        """マスターパラメータを取得"""
        if self.master_control:
            return self.master_control.get_current_parameters()
        return {}
    
    def set_current_row(self, row_id):
        """指定行のタブをアクティブに"""
        if row_id in self.emotion_controls:
            control = self.emotion_controls[row_id]
            index = self.tab_widget.indexOf(control)
            if index != -1:
                self.tab_widget.setCurrentIndex(index)
    
    def update_emotion_list(self, available_styles):
        """利用可能な感情リストでコンボボックスを更新（TabbedEmotionControl用）"""
        try:
            print(f"🔄 TabbedEmotionControl: 感情リストを更新中")
            
            # マスターコントロールを更新
            if self.master_control and hasattr(self.master_control, 'update_emotion_combo'):
                self.master_control.update_emotion_combo(available_styles)
            
            # 個別コントロールも更新
            for row_id, control in self.emotion_controls.items():
                if hasattr(control, 'update_emotion_combo'):
                    control.update_emotion_combo(available_styles)
            
            print(f"✅ TabbedEmotionControl: 感情リスト更新完了")
            
        except Exception as e:
            print(f"❌ TabbedEmotionControl感情リスト更新エラー: {e}")
            import traceback
            traceback.print_exc()