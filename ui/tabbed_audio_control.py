from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                            QLabel, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from .tabbed_modeling_control import TabbedModelingControl
from .tabbed_emotion_control import TabbedEmotionControl
from .audio_cleaner_control import AudioCleanerControl
from .audio_effects_control import AudioEffectsControl
from .wav_playback_control import WAVPlaybackControl
from .tabbed_lip_sync_control import TabbedLipSyncControl
from .tabbed_wav_export_control import WavExportControl

class TabbedAudioControl(QWidget):
    """音声パラメータ・クリーナー・エフェクト・リップシンクタブ統合ウィジェット"""
    
    parameters_changed = pyqtSignal(str, dict)
    cleaner_settings_changed = pyqtSignal(dict)
    effects_settings_changed = pyqtSignal(dict)
    lip_sync_settings_changed = pyqtSignal(dict)
    modeling_parameter_changed = pyqtSignal(str, float)
    modeling_parameters_changed = pyqtSignal(dict)
    # 🆕 ドラッグ制御シグナル追加
    drag_control_toggled = pyqtSignal(bool)
    drag_sensitivity_changed = pyqtSignal(float)
    
    # 🆕 アイドルモーションシグナル追加
    idle_motion_toggled = pyqtSignal(str, bool)  # (motion_type, enabled)
    idle_motion_param_changed = pyqtSignal(str, float)  # (param_name, value)

    # 🆕 WAV再生関連シグナル
    wav_file_loaded = pyqtSignal(str)  # ファイルパス
    wav_playback_started = pyqtSignal(float)  # 開始位置
    wav_playback_paused = pyqtSignal()
    wav_playback_stopped = pyqtSignal()
    wav_position_changed = pyqtSignal(float)  # 再生位置
    wav_volume_changed = pyqtSignal(float)  # 音量

    # 🆕 物理演算シグナル
    physics_toggled = pyqtSignal(bool)
    physics_weight_changed = pyqtSignal(float)

    wav_export_requested = pyqtSignal(dict)    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # メインタブウィジェット（音声パラメータ vs 音声クリーナー vs 音声エフェクト vs リップシンク）
        self.main_tab_widget = QTabWidget()
        self.main_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                background-color: white;
                border: 2px solid #4a90e2;
                border-radius: 4px;
                margin-top: 0px;
            }
            QTabWidget::tab-bar {
                alignment: left;
                left: 10px;
            }
            QTabBar {
                background-color: transparent;
                alignment: left;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ccc;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 10px 16px;
                margin-right: 2px;
                margin-bottom: -2px;
                font-size: 13px;
                font-weight: bold;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #333;
                border: 2px solid #4a90e2;
                border-bottom: none;
                margin-bottom: -2px;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e6f2ff;
                border-color: #4a90e2;
                color: #4a90e2;
            }
        """)
        
        # 1. 音声パラメータタブ
        self.emotion_control = TabbedEmotionControl()
        self.emotion_control.parameters_changed.connect(self.parameters_changed)
        self.main_tab_widget.addTab(self.emotion_control, "🎭 音声パラメータ")
        
        # 2. 音声クリーナータブ
        self.cleaner_control = AudioCleanerControl()
        self.cleaner_control.settings_changed.connect(self.cleaner_settings_changed)
        self.main_tab_widget.addTab(self.cleaner_control, "🔧 音声クリーナー")
        
        # 3. 音声エフェクトタブ
        self.effects_control = AudioEffectsControl()
        self.effects_control.effects_settings_changed.connect(self.effects_settings_changed)
        self.effects_control.undo_executed.connect(self.on_effects_undo_executed)
        self.main_tab_widget.addTab(self.effects_control, "🎛️ 音声エフェクト")

        # 🆕 4. WAV再生タブ
        self.wav_playback_control = WAVPlaybackControl()
        self.wav_playback_control.wav_loaded.connect(self.wav_file_loaded)
        self.wav_playback_control.playback_started.connect(self.wav_playback_started)
        self.wav_playback_control.playback_paused.connect(self.wav_playback_paused)
        self.wav_playback_control.playback_stopped.connect(self.wav_playback_stopped)
        self.wav_playback_control.position_changed.connect(self.wav_position_changed)
        self.wav_playback_control.volume_changed.connect(self.wav_volume_changed)
        self.main_tab_widget.addTab(self.wav_playback_control, "🎵 音声再生")

        # 5. 音声書き出しタブ
        self.wav_export_control = WavExportControl()
        self.wav_export_control.export_requested.connect(self.wav_export_requested)
        self.main_tab_widget.addTab(self.wav_export_control, "📼 音声書き出し")
        
        # 6. リップシンクタブ
        self.lip_sync_control = TabbedLipSyncControl()
        self.lip_sync_control.settings_changed.connect(self.on_lip_sync_settings_changed)
        self.main_tab_widget.addTab(self.lip_sync_control, "💋 リップシンク")
        
        # 7. モデリングタブ
        self.modeling_control = TabbedModelingControl()
        self.modeling_control.parameter_changed.connect(self.on_modeling_parameter_changed)
        self.modeling_control.parameters_changed.connect(self.on_modeling_parameters_changed)
        #ドラッグ制御シグナル接続（中継）
        self.modeling_control.drag_control_toggled.connect(self.drag_control_toggled)
        self.modeling_control.drag_sensitivity_changed.connect(self.drag_sensitivity_changed)
        
        # 🆕 アイドルモーションシグナル接続（中継）
        self.modeling_control.idle_motion_toggled.connect(self.idle_motion_toggled)
        self.modeling_control.idle_motion_param_changed.connect(self.idle_motion_param_changed)

        # 🆕 物理演算シグナル接続（中継）
        self.modeling_control.physics_toggled.connect(self.physics_toggled)
        self.modeling_control.physics_weight_changed.connect(self.physics_weight_changed)
        
        self.main_tab_widget.addTab(self.modeling_control, "🎨 モデリング")

        layout.addWidget(self.main_tab_widget)
    
    def on_effects_undo_executed(self):
        """エフェクトUndo実行通知"""
        pass
    
    def on_lip_sync_settings_changed(self, settings):
        """リップシンク設定変更時の処理"""
        self.lip_sync_settings_changed.emit(settings)
    
    # ================================
    # 改良版Undo/Redo機能の公開メソッド
    # ================================
    
    def undo_current_tab(self):
        """現在のタブでUndo実行（改良版）"""
        current_index = self.main_tab_widget.currentIndex()
        
        if current_index == 0:  # 音声パラメータタブ
            return self.emotion_control.undo_current_tab_parameters()
        elif current_index == 1:  # 音声クリーナータブ
            # クリーナータブにはUndo機能なし
            return False
        elif current_index == 2:  # 音声エフェクトタブ
            return self.effects_control.undo_effects_parameters()
        elif current_index == 3:  # リップシンクタブ
            # リップシンクタブにはUndo機能なし（今後の拡張で追加可能）
            return False
        
        return False
    
    def redo_current_tab(self):
        """現在のタブでRedo実行（新機能）"""
        current_index = self.main_tab_widget.currentIndex()
        
        if current_index == 0:  # 音声パラメータタブ
            # 現在のタブウィジェット取得
            current_widget = self.emotion_control.tab_widget.currentWidget()
            if current_widget and hasattr(current_widget, 'history'):
                if current_widget.history.has_redo_available():
                    # Redo実行
                    current_widget.history.set_undoing_flag(True)
                    next_state = current_widget.history.get_next_state()
                    if next_state:
                        current_widget.current_params = next_state
                        current_widget.load_parameters()
                        current_widget.emit_parameters_changed()
                    current_widget.history.set_undoing_flag(False)
                    return True
            return False
        elif current_index == 1:  # 音声クリーナータブ
            return False
        elif current_index == 2:  # 音声エフェクトタブ
            # エフェクト制御でRedo実行
            if hasattr(self.effects_control, 'history') and self.effects_control.history.has_redo_available():
                self.effects_control.history.set_undoing_flag(True)
                next_state = self.effects_control.history.get_next_state()
                if next_state:
                    self.effects_control.set_settings(next_state)
                    self.effects_control.emit_settings_changed()
                self.effects_control.history.set_undoing_flag(False)
                return True
            return False
        elif current_index == 3:  # リップシンクタブ
            # リップシンクタブにはRedo機能なし（今後の拡張で追加可能）
            return False
        
        return False
    
    def has_current_tab_undo_available(self):
        """現在のタブでUndoが可能かどうか"""
        current_index = self.main_tab_widget.currentIndex()
        
        if current_index == 0:  # 音声パラメータタブ
            return self.emotion_control.has_current_tab_undo_available()
        elif current_index == 1:  # 音声クリーナータブ
            return False
        elif current_index == 2:  # 音声エフェクトタブ
            return self.effects_control.has_undo_available()
        elif current_index == 3:  # リップシンクタブ
            return False
        
        return False
    
    def has_current_tab_redo_available(self):
        """現在のタブでRedoが可能かどうか（新機能）"""
        current_index = self.main_tab_widget.currentIndex()
        
        if current_index == 0:  # 音声パラメータタブ
            current_widget = self.emotion_control.tab_widget.currentWidget()
            if current_widget and hasattr(current_widget, 'history'):
                return current_widget.history.has_redo_available()
            return False
        elif current_index == 1:  # 音声クリーナータブ
            return False
        elif current_index == 2:  # 音声エフェクトタブ
            if hasattr(self.effects_control, 'history'):
                return self.effects_control.history.has_redo_available()
            return False
        elif current_index == 3:  # リップシンクタブ
            return False
        
        return False
    
    # ================================
    # 音声パラメータ関連のプロキシメソッド
    # ================================
    
    def add_text_row(self, row_id, row_number, parameters=None):
        """テキスト行に対応するタブを追加"""
        self.emotion_control.add_text_row(row_id, row_number, parameters)
    
    def remove_text_row(self, row_id):
        """テキスト行に対応するタブを削除"""
        self.emotion_control.remove_text_row(row_id)
    
    def update_tab_numbers(self, row_mapping):
        """タブ番号を更新"""
        self.emotion_control.update_tab_numbers(row_mapping)
    
    def get_parameters(self, row_id):
        """指定行のパラメータを取得"""
        return self.emotion_control.get_parameters(row_id)
    
    def get_master_parameters(self):
        """マスターパラメータを取得"""
        return self.emotion_control.get_master_parameters()
    
    def set_current_row(self, row_id):
        """指定行のタブをアクティブに"""
        # 音声パラメータタブを選択してから行を設定
        self.main_tab_widget.setCurrentIndex(0)
        self.emotion_control.set_current_row(row_id)
    
    # ================================
    # 音声クリーナー関連
    # ================================
    
    def get_cleaner_settings(self):
        """クリーナー設定を取得"""
        return self.cleaner_control.get_current_settings()
    
    def is_cleaner_enabled(self):
        """クリーナーが有効かどうか"""
        return self.cleaner_control.is_enabled()
    
    # ================================
    # 音声エフェクト関連
    # ================================
    
    def get_effects_settings(self):
        """エフェクト設定を取得"""
        return self.effects_control.get_current_settings()
    
    def is_effects_enabled(self):
        """エフェクトが有効かどうか"""
        return self.effects_control.is_effects_enabled()
    
    def set_effects_settings(self, settings):
        """エフェクト設定を適用"""
        self.effects_control.set_settings(settings)
    
    def load_effects_preset(self, preset_name):
        """エフェクトプリセットを読み込み"""
        # エフェクトタブにはプリセット機能がないので、将来の拡張用
        return False
    
    # ================================
    # リップシンク関連
    # ================================
    
    def get_lip_sync_settings(self):
        """リップシンク設定を取得"""
        return self.lip_sync_control.get_all_settings()
    
    def is_lip_sync_enabled(self):
        """リップシンクが有効かどうか"""
        return self.lip_sync_control.is_enabled()
    
    def set_lip_sync_enabled(self, enabled: bool):
        """リップシンクの有効/無効を設定"""
        basic_settings = self.lip_sync_control.basic_widget.get_settings()
        basic_settings['enabled'] = enabled
        self.lip_sync_control.basic_widget.set_settings(basic_settings)
    
    def get_lip_sync_sensitivity(self):
        """リップシンク感度を取得"""
        basic_settings = self.lip_sync_control.basic_widget.get_settings()
        return basic_settings.get('sensitivity', 80)
    
    def get_phoneme_settings(self):
        """音素設定を取得"""
        return self.lip_sync_control.phoneme_widget.get_settings()
    
    def get_lip_sync_advanced_settings(self):
        """リップシンク高度設定を取得"""
        return self.lip_sync_control.advanced_widget.get_settings()
    
    def set_lip_sync_tab_active(self):
        """リップシンクタブをアクティブに設定"""
        self.main_tab_widget.setCurrentIndex(3)

    # ================================
    # モデリング関連
    # ================================
    
    def on_modeling_parameter_changed(self, param_id: str, value: float):
        """モデリングパラメータ変更時"""
        self.modeling_parameter_changed.emit(param_id, value)
    
    def on_modeling_parameters_changed(self, parameters: dict):
        """モデリング全パラメータ変更時"""
        self.modeling_parameters_changed.emit(parameters)
    
    def load_model_parameters(self, parameters: list, model_id: str):
        """Live2Dモデルのパラメータをモデリングタブに読み込み"""
        self.modeling_control.load_model_parameters(parameters, model_id)

    
    def get_modeling_parameters(self) -> dict:
        """モデリングパラメータを取得"""
        return self.modeling_control.get_all_parameters()

    
    def set_modeling_tab_active(self):
        """モデリングタブをアクティブに設定"""
        self.main_tab_widget.setCurrentIndex(4)


    # ================================
    # 🆕 WAV再生関連
    # ================================
    
    def get_wav_playback_control(self):
        """WAV再生コントロールウィジェットを取得"""
        return self.wav_playback_control
    
    def is_wav_loaded(self) -> bool:
        """WAVファイルが読み込まれているか"""
        return self.wav_playback_control.is_wav_loaded
    
    def is_wav_playing(self) -> bool:
        """WAV再生中か"""
        return self.wav_playback_control.is_playing
    
    def get_wav_file_path(self) -> str:
        """現在のWAVファイルパスを取得"""
        return self.wav_playback_control.get_current_file_path()
    
    def is_wav_lipsync_enabled(self) -> bool:
        """WAV再生時のリップシンク連動が有効か"""
        return self.wav_playback_control.is_lipsync_enabled()
    
    def set_wav_playback_tab_active(self):
        """WAV再生タブをアクティブに設定"""
        self.main_tab_widget.setCurrentIndex(3)

    # ================================
    # 🆕 音声書き出し関連
    # ================================
    
    def get_wav_export_control(self):
        """音声書き出しコントロールウィジェットを取得"""
        return self.wav_export_control
    
    def set_wav_export_processing(self, is_processing: bool):
        """音声書き出し処理状態を設定"""
        self.wav_export_control.set_processing_state(is_processing)
    
    def update_wav_export_progress(self, current: int, total: int):
        """音声書き出し進捗を更新"""
        self.wav_export_control.update_progress(current, total)
    
    def add_wav_export_log(self, message: str):
        """音声書き出しログを追加"""
        self.wav_export_control.add_log(message)
    
    def set_wav_export_tab_active(self):
        """音声書き出しタブをアクティブに設定"""
        self.main_tab_widget.setCurrentIndex(4)  # 音声書き出しタブ