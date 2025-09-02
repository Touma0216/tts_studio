# ui/audio_cleaner_control.py (UI改良版)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
                            QGroupBox, QGridLayout, QPushButton, QSlider, QDoubleSpinBox,
                            QTabWidget, QFrame, QComboBox, QTextEdit, QProgressBar, QMessageBox, QApplication, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont
import numpy as np

# 新しく追加するモジュール
from core.audio_analyzer import AudioAnalyzer
from core.audio_processor import AudioProcessor

class AudioAnalysisThread(QThread):
    """音声解析用のワーカースレッド"""
    
    analysis_completed = pyqtSignal(dict, dict)  # analysis_result, recommended_preset
    analysis_failed = pyqtSignal(str)  # error_message
    progress_updated = pyqtSignal(int)  # progress_percentage
    
    def __init__(self, audio_data: np.ndarray, sample_rate: int):
        super().__init__()
        self.audio_data = audio_data.copy()
        self.sample_rate = sample_rate
        self.analyzer = None
        self._stop_requested = False
    
    def stop(self):
        """解析停止要求"""
        self._stop_requested = True
        
    def run(self):
        """バックグラウンドで音声解析を実行"""
        try:
            print("🔍 解析スレッド開始")
            
            if self._stop_requested:
                return
                
            self.progress_updated.emit(10)
            
            # 解析器をスレッド内で作成
            from core.audio_analyzer import AudioAnalyzer
            analyzer = AudioAnalyzer()
            
            if self._stop_requested:
                return
                
            self.progress_updated.emit(30)
            
            # 解析実行
            print(f"📊 解析実行中: audio shape={self.audio_data.shape}, sr={self.sample_rate}")
            analysis_result = analyzer.analyze_audio(self.audio_data, self.sample_rate)
            
            if self._stop_requested:
                return
                
            self.progress_updated.emit(70)
            
            # プリセット生成
            recommended_preset = analyzer.get_recommended_preset()
            
            if self._stop_requested:
                return
                
            self.progress_updated.emit(100)
            
            print("✅ 解析スレッド完了")
            # 結果を送信
            self.analysis_completed.emit(analysis_result, recommended_preset)
            
        except Exception as e:
            print(f"❌ 解析スレッドエラー: {e}")
            import traceback
            traceback.print_exc()
            self.analysis_failed.emit(str(e))

class ToggleSwitchWidget(QWidget):
    """緑/赤のON/OFFトグルスイッチ"""
    
    toggled = pyqtSignal(bool)
    
    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 40)
        self._checked = checked
        
    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QBrush, QPen, QColor
        from PyQt6.QtCore import QRectF
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 背景の描画
        bg_rect = QRectF(0, 0, 80, 40)
        if self._checked:
            # ONの場合は緑
            painter.setBrush(QBrush(QColor(76, 175, 80)))  # #4caf50
        else:
            # OFFの場合は赤
            painter.setBrush(QBrush(QColor(244, 67, 54)))  # #f44336
        
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.drawRoundedRect(bg_rect, 20, 20)
        
        # スイッチの描画
        if self._checked:
            # 右側
            switch_rect = QRectF(45, 5, 30, 30)
        else:
            # 左側
            switch_rect = QRectF(5, 5, 30, 30)
        
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(switch_rect)
        
        # テキストの描画
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("", 10, QFont.Weight.Bold))
        
        if self._checked:
            painter.drawText(10, 25, "ON")
        else:
            painter.drawText(50, 25, "OFF")
    
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

class AudioCleanerControl(QWidget):
    """音声クリーナー制御ウィジェット（UI改良版）"""
    
    settings_changed = pyqtSignal(dict)  # cleaner_settings
    analyze_requested = pyqtSignal()  # 解析リクエスト
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # クリーナー設定（最小限）
        self.cleaner_settings = {
            'enabled': False,  # デフォルトOFF
            'auto_generated': False,
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
        
        # 解析関連
        self.analyzer = AudioAnalyzer()
        self.processor = AudioProcessor()
        self.analysis_thread = None
        self.current_analysis = None
        
        # カスタムプリセット管理
        self.custom_presets = {}  # name -> settings
        
        self.init_ui()
        
    def init_ui(self):
        """UIを初期化（改良版）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # タブウィジェット（音声解析｜プリセット）
        self.cleaner_tab_widget = QTabWidget()
        self.cleaner_tab_widget.setStyleSheet("""
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
        
        # 音声解析タブ
        analysis_tab = self.create_analysis_tab()
        self.cleaner_tab_widget.addTab(analysis_tab, "音声解析")
        
        # プリセットタブ
        preset_tab = self.create_preset_tab()
        self.cleaner_tab_widget.addTab(preset_tab, "プリセット")
        
        layout.addWidget(self.cleaner_tab_widget)
    
    def create_analysis_tab(self):
        """音声解析タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # [音声クリーナー] ON/OFFスイッチ
        cleaner_group = QGroupBox("音声クリーナー")
        cleaner_layout = QHBoxLayout(cleaner_group)
        
        switch_label = QLabel("音声クリーナーを有効化")
        switch_label.setFont(QFont("", 12, QFont.Weight.Bold))
        
        self.toggle_switch = ToggleSwitchWidget(self.cleaner_settings['enabled'])
        self.toggle_switch.toggled.connect(self.on_enable_toggled)
        
        cleaner_layout.addWidget(switch_label)
        cleaner_layout.addStretch()
        cleaner_layout.addWidget(self.toggle_switch)
        
        # 音声解析ボタン（横長）
        self.analyze_button = QPushButton("🔍 音声を解析してプリセットを生成")
        self.analyze_button.setMinimumHeight(50)
        self.analyze_button.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.analyze_button.clicked.connect(self.start_analysis)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 8px;
                text-align: center;
                background-color: white;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4caf50;
                border-radius: 7px;
            }
        """)
        
        # [解析結果]
        results_group = QGroupBox("解析結果")
        results_layout = QVBoxLayout(results_group)
        
        self.results_display = QTextEdit()
        self.results_display.setMaximumHeight(120)
        self.results_display.setReadOnly(True)
        self.results_display.setPlaceholderText("音声解析を実行すると、ここに結果が表示されます...")
        self.results_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 10px;
                font-family: "Yu Gothic", sans-serif;
                font-size: 12px;
            }
        """)
        
        results_layout.addWidget(self.results_display)
        
        # [プリセット化] 名前入力＋適用ボタン
        preset_group = QGroupBox("プリセット化")
        preset_layout = QHBoxLayout(preset_group)
        
        preset_name_label = QLabel("名前:")
        self.preset_name_input = QLineEdit()
        self.preset_name_input.setPlaceholderText("カスタムプリセット名を入力...")
        self.preset_name_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
            }
        """)
        
        self.save_preset_button = QPushButton("適用")
        self.save_preset_button.setEnabled(False)
        self.save_preset_button.setStyleSheet("""
            QPushButton:enabled {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #aaaaaa;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px 16px;
            }
        """)
        self.save_preset_button.clicked.connect(self.save_custom_preset)
        
        preset_layout.addWidget(preset_name_label)
        preset_layout.addWidget(self.preset_name_input, 1)
        preset_layout.addWidget(self.save_preset_button)
        
        layout.addWidget(cleaner_group)
        layout.addWidget(self.analyze_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(results_group)
        layout.addWidget(preset_group)
        layout.addStretch()
        
        return widget
    
    def create_preset_tab(self):
        """プリセットタブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # [プリセット選択]
        preset_group = QGroupBox("プリセット選択")
        preset_layout = QVBoxLayout(preset_group)
        
        # プリセット選択行
        selection_layout = QHBoxLayout()
        
        preset_label = QLabel("プリセット:")
        preset_label.setFont(QFont("", 11, QFont.Weight.Bold))
        
        self.preset_combo = QComboBox()
        self.preset_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
                min-width: 200px;
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
        
        # 編集ボタン（✎マーク）
        self.edit_preset_button = QPushButton("✎")
        self.edit_preset_button.setFixedSize(30, 30)
        self.edit_preset_button.setToolTip("プリセット名を編集")
        self.edit_preset_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 15px;
                font-size: 14px;
                font-weight: bold;
                color: #666;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                color: #333;
            }
        """)
        self.edit_preset_button.clicked.connect(self.edit_preset_name)
        
        # 削除ボタン（🗑️マーク）
        self.delete_preset_button = QPushButton("🗑️")
        self.delete_preset_button.setFixedSize(30, 30)
        self.delete_preset_button.setToolTip("プリセットを削除")
        self.delete_preset_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 15px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #ffebee;
                border-color: #f44336;
            }
        """)
        self.delete_preset_button.clicked.connect(self.delete_preset)
        
        selection_layout.addWidget(preset_label)
        selection_layout.addWidget(self.preset_combo, 1)
        selection_layout.addWidget(self.edit_preset_button)
        selection_layout.addWidget(self.delete_preset_button)
        
        # プリセット適用ボタン
        self.apply_preset_button = QPushButton("プリセットを適用")
        self.apply_preset_button.setMinimumHeight(40)
        self.apply_preset_button.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
        """)
        self.apply_preset_button.clicked.connect(self.apply_preset)
        
        preset_layout.addLayout(selection_layout)
        preset_layout.addWidget(self.apply_preset_button)
        
        layout.addWidget(preset_group)
        layout.addStretch()
        
        # プリセットリストを初期化
        self.load_preset_list()
        
        return widget
    
    def load_preset_list(self):
        """プリセットリストを読み込み"""
        self.preset_combo.clear()
        
        # デフォルトプリセット
        default_presets = [
            ("🤖 自動生成プリセット", "auto_generated"),
            ("ほのかちゃん最適化", "honoka_optimized"),
            ("軽め処理", "light_processing"),
            ("強力クリーニング", "heavy_cleaning"),
            ("配信用", "streaming_optimized")
        ]
        
        for name, key in default_presets:
            self.preset_combo.addItem(name, key)
        
        # カスタムプリセット
        for name, settings in self.custom_presets.items():
            self.preset_combo.addItem(f"💾 {name}", f"custom_{name}")
    
    # 解析関連メソッド
    def start_analysis(self):
        """音声解析を開始"""
        self.analyze_requested.emit()
    
    def run_simple_analysis_safe(self, audio_data: np.ndarray, sample_rate: int):
        """安全な簡易解析"""
        from PyQt6.QtCore import QTimer
        
        timeout_timer = QTimer()
        timeout_timer.setSingleShot(True)
        timeout_timer.timeout.connect(self.on_analysis_timeout)
        
        try:
            print("🚀 安全な簡易解析モード開始")
            
            # UI状態を解析中に変更
            self.analyze_button.setEnabled(False)
            self.analyze_button.setText("🔄 解析中...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # 10秒タイムアウト設定
            timeout_timer.start(10000)
            
            # 解析実行
            from core.audio_analyzer import AudioAnalyzer
            analyzer = AudioAnalyzer()
            
            print("📊 音声解析実行中...")
            analysis_result = analyzer.analyze_audio(audio_data, sample_rate)
            recommended_preset = analyzer.get_recommended_preset()
            
            # タイムアウトタイマー停止
            timeout_timer.stop()
            
            # 完了処理
            self.progress_bar.setValue(100)
            
            # 結果処理を直接実行
            self.process_analysis_results(analysis_result, recommended_preset)
            
            print("✅ 安全な解析完了")
            
        except Exception as e:
            timeout_timer.stop()
            print(f"❌ 安全な解析エラー: {e}")
            self.reset_analysis_ui()
            QMessageBox.critical(self, "解析エラー", f"音声解析に失敗しました:\n{str(e)}")
    
    def on_analysis_timeout(self):
        """解析タイムアウト時の処理"""
        print("⏰ 解析タイムアウト - UI復旧中...")
        self.reset_analysis_ui()
        self.results_display.setPlainText("⏰ 解析がタイムアウトしました。音声データが大きすぎる可能性があります。")
        QMessageBox.warning(self, "解析タイムアウト", "音声解析がタイムアウトしました。")
    
    def process_analysis_results(self, analysis_result: dict, recommended_preset: dict):
        """解析結果を処理"""
        try:
            self.current_analysis = analysis_result
            
            # 解析結果をテキストで表示
            from core.audio_analyzer import AudioAnalyzer
            temp_analyzer = AudioAnalyzer()
            temp_analyzer.analysis_result = analysis_result
            summary = temp_analyzer.get_analysis_summary()
            self.results_display.setPlainText(summary)
            
            # 自動プリセットを保存
            if recommended_preset:
                self.auto_generated_preset = recommended_preset
                self.save_preset_button.setEnabled(True)
                print("🤖 自動プリセット生成完了")
            
            # UI状態をリセット
            self.reset_analysis_ui()
            
            print("🎉 解析結果処理完了")
            
        except Exception as e:
            print(f"❌ 解析結果処理エラー: {e}")
            self.reset_analysis_ui()
    
    def reset_analysis_ui(self):
        """解析UI状態をリセット"""
        self.analyze_button.setEnabled(True)
        self.analyze_button.setText("🔍 音声を解析してプリセットを生成")
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
    
    # プリセット関連メソッド
    def save_custom_preset(self):
        """カスタムプリセットを保存"""
        name = self.preset_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "入力エラー", "プリセット名を入力してください。")
            return
        
        if hasattr(self, 'auto_generated_preset') and self.auto_generated_preset:
            self.custom_presets[name] = self.auto_generated_preset.copy()
            self.load_preset_list()
            self.preset_name_input.clear()
            self.save_preset_button.setEnabled(False)
            QMessageBox.information(self, "保存完了", f"プリセット '{name}' を保存しました！")
        else:
            QMessageBox.warning(self, "エラー", "保存するプリセットがありません。\n先に音声解析を実行してください。")
    
    def edit_preset_name(self):
        """プリセット名を編集"""
        current_data = self.preset_combo.currentData()
        if current_data and current_data.startswith("custom_"):
            old_name = current_data.replace("custom_", "")
            from PyQt6.QtWidgets import QInputDialog
            new_name, ok = QInputDialog.getText(self, "プリセット名編集", "新しい名前:", text=old_name)
            if ok and new_name.strip() and new_name.strip() != old_name:
                # 名前変更
                settings = self.custom_presets[old_name]
                del self.custom_presets[old_name]
                self.custom_presets[new_name.strip()] = settings
                self.load_preset_list()
                QMessageBox.information(self, "変更完了", f"プリセット名を '{new_name}' に変更しました。")
        else:
            QMessageBox.information(self, "編集不可", "デフォルトプリセットは編集できません。")
    
    def delete_preset(self):
        """プリセットを削除"""
        current_data = self.preset_combo.currentData()
        if current_data and current_data.startswith("custom_"):
            name = current_data.replace("custom_", "")
            reply = QMessageBox.question(self, "削除確認", f"プリセット '{name}' を削除しますか？")
            if reply == QMessageBox.StandardButton.Yes:
                del self.custom_presets[name]
                self.load_preset_list()
                QMessageBox.information(self, "削除完了", f"プリセット '{name}' を削除しました。")
        else:
            QMessageBox.information(self, "削除不可", "デフォルトプリセットは削除できません。")
    
    def apply_preset(self):
        """選択されたプリセットを適用"""
        preset_key = self.preset_combo.currentData()
        
        if preset_key == "auto_generated":
            if hasattr(self, 'auto_generated_preset') and self.auto_generated_preset:
                self.cleaner_settings.update(self.auto_generated_preset)
                self.toggle_switch.setChecked(self.auto_generated_preset.get('enabled', False))
                self.emit_settings_changed()
                QMessageBox.information(self, "適用完了", "自動生成プリセットを適用しました！")
            else:
                QMessageBox.warning(self, "プリセットなし", "自動生成プリセットがありません。\n音声解析を先に実行してください。")
            return
        
        if preset_key.startswith("custom_"):
            name = preset_key.replace("custom_", "")
            if name in self.custom_presets:
                settings = self.custom_presets[name]
                self.cleaner_settings.update(settings)
                self.toggle_switch.setChecked(settings.get('enabled', False))
                self.emit_settings_changed()
                QMessageBox.information(self, "適用完了", f"カスタムプリセット '{name}' を適用しました！")
            return
        
        # デフォルトプリセット
        presets = {
            "honoka_optimized": {
                'enabled': True, 'auto_generated': False, 'highpass_freq': 80,
                'hum_removal': True, 'hum_frequencies': [50, 60, 100, 120, 150, 180, 200, 240],
                'hum_gains': [-20, -20, -12, -12, -9, -9, -6, -6], 'noise_reduction': True,
                'noise_floor': -28, 'loudness_norm': True, 'target_lufs': -20.0, 'true_peak': -1.0,
            },
            "light_processing": {
                'enabled': True, 'auto_generated': False, 'highpass_freq': 60,
                'hum_removal': False, 'noise_reduction': True, 'noise_floor': -35,
                'loudness_norm': True, 'target_lufs': -18.0, 'true_peak': -1.0,
            },
            "heavy_cleaning": {
                'enabled': True, 'auto_generated': False, 'highpass_freq': 100,
                'hum_removal': True, 'hum_frequencies': [50, 60, 100, 120, 150, 180, 200, 240, 300],
                'hum_gains': [-25, -25, -18, -18, -15, -15, -12, -12, -9], 'noise_reduction': True,
                'noise_floor': -25, 'loudness_norm': True, 'target_lufs': -20.0, 'true_peak': -2.0,
            },
            "streaming_optimized": {
                'enabled': True, 'auto_generated': False, 'highpass_freq': 80,
                'hum_removal': True, 'hum_frequencies': [50, 60, 100, 120],
                'hum_gains': [-15, -15, -10, -10], 'noise_reduction': True, 'noise_floor': -30,
                'loudness_norm': True, 'target_lufs': -16.0, 'true_peak': -1.0,
            }
        }
        
        if preset_key in presets:
            preset_settings = presets[preset_key]
            self.cleaner_settings.update(preset_settings)
            self.toggle_switch.setChecked(preset_settings['enabled'])
            self.emit_settings_changed()
            QMessageBox.information(self, "適用完了", f"プリセット '{self.preset_combo.currentText()}' を適用しました！")
    
    # イベントハンドラー
    def on_enable_toggled(self, enabled):
        """クリーナー有効/無効切り替え"""
        self.cleaner_settings['enabled'] = enabled
        self.emit_settings_changed()
    
    def emit_settings_changed(self):
        """設定変更シグナルを送信"""
        self.settings_changed.emit(self.cleaner_settings.copy())
    
    def get_current_settings(self):
        """現在の設定を取得"""
        return self.cleaner_settings.copy()
    
    def is_enabled(self):
        """クリーナーが有効かどうか"""
        return self.cleaner_settings['enabled']
    
    # 外部から音声データを設定するメソッド
    def set_audio_data_for_analysis(self, audio_data: np.ndarray, sample_rate: int):
        """外部から音声データを受け取って解析実行"""
        
        # 簡単な検証
        if audio_data is None or len(audio_data) == 0:
            QMessageBox.warning(self, "解析エラー", "音声データが無効です。")
            return
        
        # データサイズチェック
        data_size_mb = audio_data.nbytes / (1024 * 1024)
        if data_size_mb > 100:  # 100MB以上
            reply = QMessageBox.question(self, "大きなデータ", 
                                       f"音声データが大きいです（{data_size_mb:.1f}MB）。\n処理に時間がかかる可能性があります。続行しますか？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        print(f"🔍 音声解析開始（データサイズ: {data_size_mb:.1f}MB, 長さ: {len(audio_data)/sample_rate:.2f}秒）")
        self.run_simple_analysis_safe(audio_data, sample_rate)