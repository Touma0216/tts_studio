# ui/audio_cleaner_control.py (強化版)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
                            QGroupBox, QGridLayout, QPushButton, QSlider, QDoubleSpinBox,
                            QTabWidget, QFrame, QComboBox, QTextEdit, QProgressBar, QMessageBox, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont
import numpy as np

# 新しく追加するモジュール
from core.audio_analyzer import AudioAnalyzer
from core.audio_processor import AudioProcessor

class AudioAnalysisThread(QThread):
    """音声解析用のワーカースレッド（修正版）"""
    
    analysis_completed = pyqtSignal(dict, dict)  # analysis_result, recommended_preset
    analysis_failed = pyqtSignal(str)  # error_message
    progress_updated = pyqtSignal(int)  # progress_percentage
    
    def __init__(self, audio_data: np.ndarray, sample_rate: int):
        super().__init__()
        self.audio_data = audio_data.copy()  # データをコピー
        self.sample_rate = sample_rate
        self.analyzer = None  # ここで作成しない
        self._stop_requested = False
    
    def stop(self):
        """解析停止要求"""
        self._stop_requested = True
        
    def run(self):
        """バックグラウンドで音声解析を実行（修正版）"""
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

class AudioCleanerControl(QWidget):
    """音声クリーナー制御ウィジェット（解析機能付き）"""
    
    settings_changed = pyqtSignal(dict)  # cleaner_settings
    analyze_requested = pyqtSignal()  # 解析リクエスト（親に音声データ要求）
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # クリーナー設定
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
                padding: 6px 12px;
                margin-right: 2px;
                margin-bottom: -1px;
                font-size: 12px;
                min-width: 80px;
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
        """)
        
        # 🆕 解析タブ
        analysis_tab = self.create_analysis_tab()
        self.cleaner_tab_widget.addTab(analysis_tab, "🔍 音声解析")
        
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
    
    def create_analysis_tab(self):
        """🆕 音声解析タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 解析実行セクション
        analysis_group = QGroupBox("音声解析・自動プリセット生成")
        analysis_layout = QVBoxLayout(analysis_group)
        
        # 説明ラベル
        info_label = QLabel("音声データを解析して、最適なクリーニング設定を自動生成します")
        info_label.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                color: #1976d2;
                border: 1px solid #2196f3;
                border-radius: 4px;
                padding: 12px;
                font-weight: bold;
            }
        """)
        info_label.setWordWrap(True)
        
        # 解析ボタン
        self.analyze_button = QPushButton("🔍 音声を解析してプリセットを生成")
        self.analyze_button.setMinimumHeight(50)
        self.analyze_button.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
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
                border-radius: 4px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: #4caf50;
                border-radius: 3px;
            }
        """)
        
        analysis_layout.addWidget(info_label)
        analysis_layout.addWidget(self.analyze_button)
        analysis_layout.addWidget(self.progress_bar)
        
        # 解析結果セクション
        results_group = QGroupBox("解析結果")
        results_layout = QVBoxLayout(results_group)
        
        # 結果表示エリア
        self.results_display = QTextEdit()
        self.results_display.setMaximumHeight(120)
        self.results_display.setReadOnly(True)
        self.results_display.setPlaceholderText("音声解析を実行すると、ここに結果が表示されます...")
        self.results_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-family: "Yu Gothic", sans-serif;
                font-size: 12px;
            }
        """)
        
        # 自動プリセット適用ボタン
        self.apply_auto_preset_button = QPushButton("✨ 自動生成されたプリセットを適用")
        self.apply_auto_preset_button.setEnabled(False)
        self.apply_auto_preset_button.setStyleSheet("""
            QPushButton:enabled {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
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
                padding: 10px;
            }
        """)
        self.apply_auto_preset_button.clicked.connect(self.apply_auto_generated_preset)
        
        results_layout.addWidget(self.results_display)
        results_layout.addWidget(self.apply_auto_preset_button)
        
        layout.addWidget(analysis_group)
        layout.addWidget(results_group)
        layout.addStretch()
        
        return widget
    
    def create_basic_tab(self):
        """基本設定タブを作成（既存コードをベースに微調整）"""
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
        
        # 自動生成プリセット表示
        self.auto_preset_info = QLabel("📋 手動設定が適用されています")
        self.auto_preset_info.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-style: italic;
            }
        """)
        
        enable_layout.addWidget(self.enable_button)
        enable_layout.addWidget(self.auto_preset_info)
        
        # 処理ステップ表示
        steps_group = QGroupBox("処理ステップ（自動実行）")
        steps_layout = QVBoxLayout(steps_group)
        
        steps = [
            "1️⃣ ハイパスフィルタ（低域ノイズカット）",
            "2️⃣ ハム除去（50/60Hz + 倍音）", 
            "3️⃣ ノイズ除去（スペクトルサブトラクション）",
            "4️⃣ ラウドネス正規化（EBU R128準拠）"
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
        """詳細調整タブを作成（既存コードベース）"""
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
        """プリセットタブを作成（既存＋自動生成プリセット追加）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # プリセット選択
        preset_group = QGroupBox("プリセット選択")
        preset_layout = QVBoxLayout(preset_group)
        
        self.preset_combo = QComboBox()
        presets = [
            ("🤖 自動生成プリセット", "auto_generated"),  # 🆕 追加
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
        
        self.preset_description = QLabel("🤖 音声解析結果に基づいて自動生成されたプリセットです。")
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
    
    # 🆕 解析関連の新しいメソッド
    def start_analysis(self):
        """音声解析を開始"""
        self.analyze_requested.emit()  # 親に音声データを要求
    
    def run_analysis_with_data(self, audio_data: np.ndarray, sample_rate: int):
        """実際の解析実行（親から音声データを受け取った後）修正版"""
        
        # 既に実行中の場合は停止してから新しく開始
        if self.analysis_thread and self.analysis_thread.isRunning():
            print("⚠️ 既存の解析を停止中...")
            self.analysis_thread.stop()
            self.analysis_thread.quit()
            self.analysis_thread.wait(2000)  # 2秒待機
            self.analysis_thread = None
        
        try:
            print(f"🔍 解析開始: audio shape={audio_data.shape}, sr={sample_rate}")
            
            # UI状態を解析中に変更
            self.analyze_button.setEnabled(False)
            self.analyze_button.setText("🔄 解析中...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # ワーカースレッド開始
            self.analysis_thread = AudioAnalysisThread(audio_data, sample_rate)
            
            # シグナル接続
            self.analysis_thread.analysis_completed.connect(self.on_analysis_completed)
            self.analysis_thread.analysis_failed.connect(self.on_analysis_failed)
            self.analysis_thread.progress_updated.connect(self.on_progress_updated)
            
            # スレッド終了時の処理
            self.analysis_thread.finished.connect(self.on_analysis_thread_finished)
            
            self.analysis_thread.start()
            
        except Exception as e:
            print(f"❌ 解析開始エラー: {e}")
            self.reset_analysis_ui()
            QMessageBox.critical(self, "エラー", f"解析の開始に失敗しました:\n{str(e)}")
    
    @pyqtSlot(int)
    def on_progress_updated(self, value):
        """プログレス更新"""
        self.progress_bar.setValue(value)
    
    @pyqtSlot()
    def on_analysis_thread_finished(self):
        """解析スレッド終了時の処理"""
        print("🏁 解析スレッド終了")
        self.analysis_thread = None
    
    def reset_analysis_ui(self):
        """解析UI状態をリセット"""
        self.analyze_button.setEnabled(True)
        self.analyze_button.setText("🔍 音声を解析してプリセットを生成")
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
    
    @pyqtSlot(dict, dict)
    def on_analysis_completed(self, analysis_result: dict, recommended_preset: dict):
        """解析完了時の処理（修正版）"""
        try:
            print("✅ 解析完了シグナル受信")
            
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
                self.apply_auto_preset_button.setEnabled(True)
                print("🤖 自動プリセット生成完了")
            
            # UI状態をリセット
            self.reset_analysis_ui()
            
            # 解析タブに自動切り替え
            self.cleaner_tab_widget.setCurrentIndex(0)
            
            print("🎉 解析処理完全完了")
            
        except Exception as e:
            print(f"❌ 解析完了処理エラー: {e}")
            import traceback
            traceback.print_exc()
            self.reset_analysis_ui()
    
    @pyqtSlot(str)
    def on_analysis_failed(self, error_message: str):
        """解析失敗時の処理（修正版）"""
        print(f"❌ 解析失敗: {error_message}")
        
        try:
            QMessageBox.critical(self, "解析エラー", f"音声解析に失敗しました:\n{error_message}")
        except Exception as e:
            print(f"❌ エラーダイアログ表示失敗: {e}")
        
        # UI状態をリセット
        self.reset_analysis_ui()
    
    def apply_auto_generated_preset(self):
        """自動生成プリセットを適用"""
        if hasattr(self, 'auto_generated_preset') and self.auto_generated_preset:
            self.cleaner_settings.update(self.auto_generated_preset)
            self.update_ui_from_settings()
            self.update_auto_preset_info(True)
            self.emit_settings_changed()
            QMessageBox.information(self, "適用完了", "自動生成されたプリセットが適用されました！")
    
    def update_auto_preset_info(self, is_auto: bool):
        """自動プリセット情報の更新"""
        if is_auto:
            self.auto_preset_info.setText("🤖 自動生成プリセットが適用されています")
            self.auto_preset_info.setStyleSheet("""
                QLabel {
                    background-color: #e8f5e8;
                    color: #2e7d32;
                    border: 1px solid #81c784;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: bold;
                }
            """)
        else:
            self.auto_preset_info.setText("📋 手動設定が適用されています")
            self.auto_preset_info.setStyleSheet("""
                QLabel {
                    background-color: #f8f9fa;
                    color: #495057;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 8px;
                    font-style: italic;
                }
            """)
    
    # 既存のメソッド群（微調整版）
    def sync_slider_spinbox(self, slider_value, spinbox, setting_key):
        """スライダー値をスピンボックスと設定に同期"""
        spinbox.blockSignals(True)
        spinbox.setValue(float(slider_value))
        spinbox.blockSignals(False)
        self.cleaner_settings[setting_key] = float(slider_value)
        self.cleaner_settings['auto_generated'] = False  # 手動変更フラグ
        self.update_auto_preset_info(False)
        self.emit_settings_changed()
    
    def sync_spinbox_slider(self, spinbox_value, slider, setting_key):
        """スピンボックス値をスライダーと設定に同期"""
        slider.blockSignals(True)
        slider.setValue(int(spinbox_value))
        slider.blockSignals(False)
        self.cleaner_settings[setting_key] = float(spinbox_value)
        self.cleaner_settings['auto_generated'] = False  # 手動変更フラグ
        self.update_auto_preset_info(False)
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
        self.emit_settings_changed()
    
    def on_preset_changed(self, preset_name):
        """プリセット変更時の説明更新"""
        descriptions = {
            "🤖 自動生成プリセット": "音声解析結果に基づいて自動生成されたプリセットです。あなたの音声に最適化されています。",
            "ほのかちゃん最適化": "ほのかちゃんの音声に最適化された設定です。ハム除去と自然な音量調整を行います。",
            "軽め処理": "軽微なノイズ除去のみを行います。元音声の特徴を最大限保持します。",
            "強力クリーニング": "ノイズが多い環境での録音に対応した強力な処理を行います。",
            "配信用": "配信プラットフォームに最適化された音量・品質に調整します。"
        }
        self.preset_description.setText(descriptions.get(preset_name, ""))
    
    def apply_preset(self):
        """選択されたプリセットを適用"""
        preset_key = self.preset_combo.currentData()
        
        if preset_key == "auto_generated":
            # 自動生成プリセットの場合
            if hasattr(self, 'auto_generated_preset') and self.auto_generated_preset:
                self.apply_auto_generated_preset()
            else:
                QMessageBox.warning(self, "プリセットなし", "自動生成プリセットがありません。\n音声解析を先に実行してください。")
            return
        
        # 手動プリセット
        presets = {
            "honoka_optimized": {
                'enabled': True,
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
            },
            "light_processing": {
                'enabled': True,
                'auto_generated': False,
                'highpass_freq': 60,
                'hum_removal': False,
                'noise_reduction': True,
                'noise_floor': -35,
                'loudness_norm': True,
                'target_lufs': -18.0,
                'true_peak': -1.0,
            },
            "heavy_cleaning": {
                'enabled': True,
                'auto_generated': False,
                'highpass_freq': 100,
                'hum_removal': True,
                'hum_frequencies': [50, 60, 100, 120, 150, 180, 200, 240, 300],
                'hum_gains': [-25, -25, -18, -18, -15, -15, -12, -12, -9],
                'noise_reduction': True,
                'noise_floor': -25,
                'loudness_norm': True,
                'target_lufs': -20.0,
                'true_peak': -2.0,
            },
            "streaming_optimized": {
                'enabled': True,
                'auto_generated': False,
                'highpass_freq': 80,
                'hum_removal': True,
                'hum_frequencies': [50, 60, 100, 120],
                'hum_gains': [-15, -15, -10, -10],
                'noise_reduction': True,
                'noise_floor': -30,
                'loudness_norm': True,
                'target_lufs': -16.0,
                'true_peak': -1.0,
            }
        }
        
        if preset_key in presets:
            preset_settings = presets[preset_key]
            self.cleaner_settings.update(preset_settings)
            self.update_ui_from_settings()
            self.update_auto_preset_info(False)
            self.emit_settings_changed()
            QMessageBox.information(self, "適用完了", f"プリセット '{self.preset_combo.currentText()}' が適用されました！")
    
    def update_ui_from_settings(self):
        """設定からUIを更新"""
        self.enable_button.setChecked(self.cleaner_settings['enabled'])
        self.update_enable_button_style()
        
        # 詳細調整タブの値を更新
        self.highpass_slider.setValue(int(self.cleaner_settings['highpass_freq']))
        self.highpass_spinbox.setValue(self.cleaner_settings['highpass_freq'])
        self.noise_slider.setValue(int(self.cleaner_settings['noise_floor']))
        self.noise_spinbox.setValue(self.cleaner_settings['noise_floor'])
        self.lufs_slider.setValue(int(self.cleaner_settings['target_lufs']))
        self.lufs_spinbox.setValue(self.cleaner_settings['target_lufs'])
        
        # 自動生成フラグに応じて情報を更新
        is_auto = self.cleaner_settings.get('auto_generated', False)
        self.update_auto_preset_info(is_auto)
    
    def emit_settings_changed(self):
        """設定変更シグナルを送信"""
        self.settings_changed.emit(self.cleaner_settings.copy())
    
    def get_current_settings(self):
        """現在の設定を取得"""
        return self.cleaner_settings.copy()
    
    def is_enabled(self):
        """クリーナーが有効かどうか"""
        return self.cleaner_settings['enabled']
    
    # 🆕 外部から音声データを設定するメソッド（改良版・タイムアウト付き）
    def set_audio_data_for_analysis(self, audio_data: np.ndarray, sample_rate: int):
        """外部から音声データを受け取って解析実行（改良版・タイムアウト付き）"""
        
        # 簡単な検証
        if audio_data is None or len(audio_data) == 0:
            QMessageBox.warning(self, "解析エラー", "音声データが無効です。")
            return
        
        # データサイズチェック（メモリ使用量対策）
        data_size_mb = audio_data.nbytes / (1024 * 1024)
        if data_size_mb > 100:  # 100MB以上
            reply = QMessageBox.question(self, "大きなデータ", 
                                       f"音声データが大きいです（{data_size_mb:.1f}MB）。\n処理に時間がかかる可能性があります。続行しますか？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        # 🆕 常に簡易モードで実行（スレッド問題を回避）
        print(f"🔍 音声解析開始（データサイズ: {data_size_mb:.1f}MB, 長さ: {len(audio_data)/sample_rate:.2f}秒）")
        
        # 10秒以上の長い音声でも簡易モードで処理（安全のため）
        self.run_simple_analysis_safe(audio_data, sample_rate)
    
    def run_simple_analysis_safe(self, audio_data: np.ndarray, sample_rate: int):
        """安全な簡易解析（タイムアウト・エラー回復付き）"""
        
        # タイムアウト用のタイマー
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
            timeout_timer.start(10000)  # 10秒
            
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
            import traceback
            traceback.print_exc()
            self.reset_analysis_ui()
            
            # エラーメッセージを表示（UIブロックを避けるため短時間で消える）
            error_msg = QMessageBox(self)
            error_msg.setWindowTitle("解析エラー")
            error_msg.setText(f"音声解析に失敗しました:\n{str(e)}")
            error_msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # 3秒後に自動で閉じる
            auto_close_timer = QTimer()
            auto_close_timer.setSingleShot(True)
            auto_close_timer.timeout.connect(error_msg.close)
            auto_close_timer.start(3000)
            
            error_msg.exec()
    
    def on_analysis_timeout(self):
        """解析タイムアウト時の処理"""
        print("⏰ 解析タイムアウト - UI復旧中...")
        self.reset_analysis_ui()
        self.results_display.setPlainText("⏰ 解析がタイムアウトしました。音声データが大きすぎる可能性があります。")
        
        # タイムアウト通知
        QMessageBox.warning(self, "解析タイムアウト", 
                          "音声解析がタイムアウトしました。\n音声データが大きすぎる可能性があります。")
    
    def process_analysis_results(self, analysis_result: dict, recommended_preset: dict):
        """解析結果を処理（UIブロック回避版）"""
        try:
            # 解析結果を保存
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
                self.apply_auto_preset_button.setEnabled(True)
                print("🤖 自動プリセット生成完了")
            
            # UI状態をリセット
            self.reset_analysis_ui()
            
            # 解析タブに切り替え
            self.cleaner_tab_widget.setCurrentIndex(0)
            
            print("🎉 解析結果処理完了")
            
        except Exception as e:
            print(f"❌ 解析結果処理エラー: {e}")
            self.reset_analysis_ui()