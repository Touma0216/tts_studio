# ui/audio_cleaner_control.py (改善版 - 設定保存対応)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
                            QGroupBox, QGridLayout, QPushButton, QSlider, QDoubleSpinBox,
                            QTabWidget, QFrame, QComboBox, QTextEdit, QProgressBar, QMessageBox, QApplication, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont
import numpy as np
import json
import os
from pathlib import Path

# 新しく追加するモジュール
from core.audio_analyzer import AudioAnalyzer
from core.audio_processor import AudioProcessor

class AudioAnalysisThread(QThread):
    """音声解析用のワーカースレッド"""
    
    analysis_completed = pyqtSignal(dict)  # analysis_result only
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
        """バックグラウンドで音声解析を実行（分析のみ）"""
        try:
            print("🔍 音声分析スレッド開始")
            
            if self._stop_requested:
                return
                
            self.progress_updated.emit(10)
            
            # 解析器をスレッド内で作成
            from core.audio_analyzer import AudioAnalyzer
            analyzer = AudioAnalyzer()
            
            if self._stop_requested:
                return
                
            self.progress_updated.emit(30)
            
            # 音声分析実行（プリセット生成はしない）
            print(f"📊 音声分析実行中: audio shape={self.audio_data.shape}, sr={self.sample_rate}")
            analysis_result = analyzer.analyze_audio(self.audio_data, self.sample_rate)
            
            if self._stop_requested:
                return
                
            self.progress_updated.emit(100)
            
            print("✅ 音声分析スレッド完了")
            # 分析結果のみを送信
            self.analysis_completed.emit(analysis_result)
            
        except Exception as e:
            print(f"❌ 音声分析スレッドエラー: {e}")
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
            # 右側（ON時）
            switch_rect = QRectF(45, 5, 30, 30)
        else:
            # 左側（OFF時）
            switch_rect = QRectF(5, 5, 30, 30)
        
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(switch_rect)
        
        # テキストの描画（位置調整）
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("", 9, QFont.Weight.Bold))
        
        if self._checked:
            # ONの場合は左側にテキスト表示
            painter.drawText(12, 25, "ON")
        else:
            # OFFの場合は右側にテキスト表示（左にずらす）
            painter.drawText(45, 25, "OFF")
    
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

class UserSettingsManager:
    """ユーザー設定管理クラス"""
    
    def __init__(self):
        self.settings_file = Path("user_settings.json")
        self.default_settings = {
            'audio_cleaner': {
                'enabled': False,  # 👈 デフォルトはOFF
                'last_preset': 'standard_processing'
            },
            'ui_preferences': {
                'window_geometry': None,
                'last_tab_index': 0
            }
        }
        self.settings = self.load_settings()
    
    def load_settings(self):
        """設定を読み込み"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # デフォルト設定とマージ
                    settings = self.default_settings.copy()
                    settings.update(loaded)
                    print(f"📁 ユーザー設定を読み込み: {self.settings_file}")
                    return settings
            else:
                print("📄 新規ユーザー設定ファイルを作成します")
                return self.default_settings.copy()
        except Exception as e:
            print(f"⚠️ 設定読み込みエラー: {e} - デフォルト設定を使用")
            return self.default_settings.copy()
    
    def save_settings(self):
        """設定を保存"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            print(f"💾 ユーザー設定を保存: {self.settings_file}")
        except Exception as e:
            print(f"❌ 設定保存エラー: {e}")
    
    def get_cleaner_enabled(self):
        """クリーナー有効状態を取得"""
        return self.settings.get('audio_cleaner', {}).get('enabled', False)
    
    def set_cleaner_enabled(self, enabled):
        """クリーナー有効状態を設定"""
        if 'audio_cleaner' not in self.settings:
            self.settings['audio_cleaner'] = {}
        self.settings['audio_cleaner']['enabled'] = enabled
        self.save_settings()
    
    def get_last_preset(self):
        """最後に使用したプリセットを取得"""
        return self.settings.get('audio_cleaner', {}).get('last_preset', 'standard_processing')
    
    def set_last_preset(self, preset_key):
        """最後に使用したプリセットを設定"""
        if 'audio_cleaner' not in self.settings:
            self.settings['audio_cleaner'] = {}
        self.settings['audio_cleaner']['last_preset'] = preset_key
        self.save_settings()

class AudioCleanerControl(QWidget):
    """音声クリーナー制御ウィジェット（設定保存対応版）"""
    
    settings_changed = pyqtSignal(dict)  # cleaner_settings
    analyze_requested = pyqtSignal()  # 分析リクエスト
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 設定管理器
        self.settings_manager = UserSettingsManager()
        
        # クリーナー設定（前回の状態を復元）
        self.cleaner_settings = {
            'enabled': self.settings_manager.get_cleaner_enabled(),  # 👈 前回の設定を復元
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
        
        # 分析関連
        self.analyzer = AudioAnalyzer()
        self.processor = AudioProcessor()
        self.analysis_thread = None
        self.current_analysis = None
        
        # カスタムプリセット管理
        self.custom_presets = {}  # name -> settings
        
        self.init_ui()
        
        print(f"🔧 音声クリーナー初期化完了: 有効={self.cleaner_settings['enabled']}")
        
    def init_ui(self):
        """UIを初期化（説明追加版）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # タブウィジェット（音声解析｜音声クリーナー）
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
        
        # 音声クリーナータブ（実用的な処理）- 最初のタブに
        cleaner_tab = self.create_cleaner_tab()
        self.cleaner_tab_widget.addTab(cleaner_tab, "音声クリーナー")
        
        # 音声解析タブ（純粋な分析のみ）- 2番目のタブに
        analysis_tab = self.create_analysis_tab()
        self.cleaner_tab_widget.addTab(analysis_tab, "音声解析")
        
        layout.addWidget(self.cleaner_tab_widget)
    
    def create_analysis_tab(self):
        """音声解析タブを作成（純粋な分析のみ）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # 説明
        info_label = QLabel("音声データの詳細な品質分析を行います。ノイズ、クリッピング、周波数特性などを分析します。")
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
        
        # 音声分析ボタン（横長）
        self.analyze_button = QPushButton("📊 音声品質を詳細分析")
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
        
        # [詳細分析結果]
        results_group = QGroupBox("詳細分析結果")
        results_layout = QVBoxLayout(results_group)
        
        self.results_display = QTextEdit()
        self.results_display.setMinimumHeight(200)
        self.results_display.setReadOnly(True)
        self.results_display.setPlaceholderText("音声分析を実行すると、詳細な品質データが表示されます...")
        self.results_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 10px;
                font-family: "Consolas", "Yu Gothic", monospace;
                font-size: 11px;
            }
        """)
        
        results_layout.addWidget(self.results_display)
        
        layout.addWidget(info_label)
        layout.addWidget(self.analyze_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(results_group)
        layout.addStretch()
        
        return widget
    
    def create_cleaner_tab(self):
        """音声クリーナータブを作成（コンパクト版）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)  # 間隔を少し縮める
        
        # [音声クリーナー] ON/OFFスイッチ
        cleaner_group = QGroupBox("音声クリーナー")
        cleaner_layout = QHBoxLayout(cleaner_group)
        
        switch_label = QLabel("音声クリーナーを有効化")
        switch_label.setFont(QFont("", 12, QFont.Weight.Bold))
        
        # 前回の設定状態でスイッチを初期化
        initial_state = self.cleaner_settings['enabled']
        print(f"🔘 トグルスイッチ初期化: {initial_state}")
        self.toggle_switch = ToggleSwitchWidget(initial_state)
        self.toggle_switch.toggled.connect(self.on_enable_toggled)
        print(f"✅ トグルスイッチ作成完了: isChecked={self.toggle_switch.isChecked()}")
        
        cleaner_layout.addWidget(switch_label)
        cleaner_layout.addStretch()
        cleaner_layout.addWidget(self.toggle_switch)
        
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
        
        selection_layout.addWidget(preset_label)
        selection_layout.addWidget(self.preset_combo, 1)
        selection_layout.addStretch()
        
        # プリセット変更時の説明更新とプリセット適用（初期化時は適用しない）
        self.preset_combo.currentTextChanged.connect(self.update_preset_description)
        self.preset_combo.currentTextChanged.connect(self.apply_preset_automatically)
        
        preset_layout.addLayout(selection_layout)
        
        # プリセット説明（コンパクト化）
        desc_group = QGroupBox("プリセット説明")
        desc_layout = QVBoxLayout(desc_group)
        
        self.preset_description = QLabel()
        self.preset_description.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 10px;
                color: #495057;
                line-height: 1.3;
                font-size: 12px;
            }
        """)
        self.preset_description.setWordWrap(True)
        self.preset_description.setMinimumHeight(40)  # 高さを縮める
        
        desc_layout.addWidget(self.preset_description)
        
        # レイアウト追加（説明セクションを削除）
        layout.addWidget(cleaner_group)
        layout.addWidget(preset_group)
        layout.addWidget(desc_group)
        # 👈 about_group（音声クリーナーとは？）を削除
        layout.addStretch()
        
        # プリセットリストを初期化
        self.load_preset_list()
        # 前回選択していたプリセットを復元
        self.restore_last_preset()
        # 初期説明を設定
        self.update_preset_description()
        
        # 初期化完了
        self.is_initializing = False
        print("✅ 初期化完了 - プリセット自動適用を有効化")
        
        return widget
    
    def restore_last_preset(self):
        """前回選択していたプリセットを復元（デバッグログ付き）"""
        last_preset = self.settings_manager.get_last_preset()
        print(f"🔄 プリセット復元開始: {last_preset}")
        
        # 現在のenabled状態を確認
        current_enabled = self.cleaner_settings['enabled']
        print(f"🎛️ プリセット復元前のenabled状態: {current_enabled}")
        
        # コンボボックスから該当プリセットを探して選択
        for i in range(self.preset_combo.count()):
            if self.preset_combo.itemData(i) == last_preset:
                # シグナルを一時的に切断してプリセット適用を防ぐ
                self.preset_combo.currentTextChanged.disconnect()
                self.preset_combo.setCurrentIndex(i)
                # シグナルを再接続
                self.preset_combo.currentTextChanged.connect(self.apply_preset_automatically)
                
                print(f"🔄 前回のプリセットを復元: {last_preset} (enabled状態保持)")
                break
        
        # 復元後のenabled状態を確認
        print(f"🎛️ プリセット復元後のenabled状態: {self.cleaner_settings['enabled']}")
    
    def update_preset_description(self):
        """プリセットの説明を更新（改良版）"""
        preset_key = self.preset_combo.currentData()
        
        descriptions = {
            "light_processing": "軽微なノイズのみを除去します。音声の自然さを最大限保持したい場合に最適です。ハイパスフィルタとラウドネス正規化のみを適用。",
            "standard_processing": "バランスの取れた標準的な処理です。ハム除去、ノイズ除去、ラウドネス正規化を適用。多くの場合でお勧めの設定。",
            "heavy_cleaning": "ノイズが多い環境での録音に対応した強力な処理です。積極的なハム除去と厳しいノイズ除去を行います。音質よりもクリーンさを重視。",
            "streaming_optimized": "配信・放送用に最適化された設定です。音量を適切なレベルに調整し、聞き取りやすい音声に仕上げます。"
        }
        
        description = descriptions.get(preset_key, "プリセットを選択してください。")
        self.preset_description.setText(description)
    
    def load_preset_list(self):
        """プリセットリストを読み込み"""
        self.preset_combo.clear()
        
        # デフォルトプリセット（汎用的な名前）
        default_presets = [
            ("軽め処理", "light_processing"),
            ("標準処理", "standard_processing"),
            ("強力クリーニング", "heavy_cleaning"),
            ("配信用", "streaming_optimized")
        ]
        
        for name, key in default_presets:
            self.preset_combo.addItem(name, key)
    
    # 分析関連メソッド
    def start_analysis(self):
        """音声分析を開始"""
        self.analyze_requested.emit()
    
    def run_simple_analysis_safe(self, audio_data: np.ndarray, sample_rate: int):
        """安全な音声分析"""
        from PyQt6.QtCore import QTimer
        
        timeout_timer = QTimer()
        timeout_timer.setSingleShot(True)
        timeout_timer.timeout.connect(self.on_analysis_timeout)
        
        try:
            print("🚀 音声分析開始")
            
            # UI状態を分析中に変更
            self.analyze_button.setEnabled(False)
            self.analyze_button.setText("🔄 分析中...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # 10秒タイムアウト設定
            timeout_timer.start(10000)
            
            # 分析実行
            from core.audio_analyzer import AudioAnalyzer
            analyzer = AudioAnalyzer()
            
            print("📊 音声分析実行中...")
            analysis_result = analyzer.analyze_audio(audio_data, sample_rate)
            
            # タイムアウトタイマー停止
            timeout_timer.stop()
            
            # 完了処理
            self.progress_bar.setValue(100)
            
            # 分析結果を処理
            self.process_analysis_results(analysis_result)
            
            print("✅ 音声分析完了")
            
        except Exception as e:
            timeout_timer.stop()
            print(f"❌ 音声分析エラー: {e}")
            self.reset_analysis_ui()
            QMessageBox.critical(self, "分析エラー", f"音声分析に失敗しました:\n{str(e)}", QMessageBox.StandardButton.Ok)
    
    def on_analysis_timeout(self):
        """分析タイムアウト時の処理"""
        print("⏰ 分析タイムアウト - UI復旧中...")
        self.reset_analysis_ui()
        self.results_display.setPlainText("⏰ 分析がタイムアウトしました。音声データが大きすぎる可能性があります。")
        # タイムアウト通知（音なし）
        timeout_msg = QMessageBox(self)
        timeout_msg.setIcon(QMessageBox.Icon.Warning)
        timeout_msg.setWindowTitle("分析タイムアウト")
        timeout_msg.setText("音声分析がタイムアウトしました。")
        timeout_msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        timeout_msg.exec()
    
    def process_analysis_results(self, analysis_result: dict):
        """分析結果を処理（詳細表示）"""
        try:
            self.current_analysis = analysis_result
            
            # 詳細な分析結果を生成
            detailed_report = self.generate_detailed_analysis_report(analysis_result)
            self.results_display.setPlainText(detailed_report)
            
            # UI状態をリセット
            self.reset_analysis_ui()
            
            print("🎉 分析結果処理完了")
            
        except Exception as e:
            print(f"❌ 分析結果処理エラー: {e}")
            self.reset_analysis_ui()
    
    def generate_detailed_analysis_report(self, analysis: dict) -> str:
        """詳細な分析レポートを生成"""
        import numpy as np
        
        report = "🎵 音声品質詳細分析レポート\n"
        report += "=" * 50 + "\n\n"
        
        # 基本統計
        report += "📊 基本統計:\n"
        peak_db = 20*np.log10(np.max(analysis.get('peak_per_ch', [0.001])))
        rms_db = 20*np.log10(np.mean(analysis.get('rms_per_ch', [0.001])))
        report += f"  ピークレベル: {peak_db:.2f} dBFS\n"
        report += f"  RMSレベル: {rms_db:.2f} dBFS\n"
        report += f"  DCオフセット: {analysis.get('mean_per_ch', [0])[0]:.6f}\n\n"
        
        # 真ピーク
        true_peak = analysis.get('true_peak_est', 0)
        true_peak_db = 20*np.log10(true_peak) if true_peak > 0 else -float('inf')
        report += f"🎯 真ピーク推定: {true_peak_db:.2f} dBFS\n\n"
        
        # クリッピング分析
        clip_ratio = analysis.get('clip_ratio_per_ch', [0])
        clip_runs = analysis.get('clip_runs_total', 0)
        report += "✂️ クリッピング分析:\n"
        report += f"  クリップ率: {np.max(clip_ratio)*100:.4f}%\n"
        report += f"  連続クリップ箇所: {clip_runs}箇所\n\n"
        
        # ノイズ・SNR分析
        snr_db = analysis.get('snr_db')
        noise_floor = analysis.get('noise_floor_dbfs')
        report += "📡 ノイズ・SNR分析:\n"
        if snr_db is not None:
            report += f"  SNR: {snr_db:.2f} dB\n"
        if noise_floor is not None:
            report += f"  推定ノイズ床: {noise_floor:.2f} dBFS\n"
        report += "\n"
        
        # ハム検出
        hum_detection = analysis.get('hum_detection', {})
        report += "⚡ ハム検出:\n"
        for freq, strength in hum_detection.items():
            percentage = strength * 100
            if percentage > 1.0:  # 1%以上なら表示
                report += f"  {int(freq)}Hz系: {percentage:.2f}% (相対強度)\n"
        report += "\n"
        
        # スペクトル分析
        spectral_flatness = analysis.get('spectral_flatness', 0)
        report += f"🌊 スペクトル特性:\n"
        report += f"  スペクトルフラットネス: {spectral_flatness:.4f}\n"
        if spectral_flatness < 0.1:
            report += "    → トーナル（音楽的）な特性\n"
        elif spectral_flatness > 0.5:
            report += "    → ノイズ的な特性\n"
        else:
            report += "    → バランスの取れた特性\n"
        report += "\n"
        
        # 無音分析
        silence_ratio = analysis.get('silence_ratio', 0)
        leading_silence = analysis.get('leading_silence_sec', 0)
        trailing_silence = analysis.get('trailing_silence_sec', 0)
        report += "🔇 無音分析:\n"
        report += f"  無音率: {silence_ratio*100:.2f}%\n"
        report += f"  先頭無音: {leading_silence:.3f}秒\n"
        report += f"  末尾無音: {trailing_silence:.3f}秒\n\n"
        
        # 総合評価
        report += "🏆 総合品質評価:\n"
        issues = []
        good_points = []
        
        if peak_db > -1.0:
            issues.append("ピークレベルが高い")
        if np.max(clip_ratio) > 0.001:
            issues.append("クリッピングあり")
        if snr_db is not None and snr_db < 20:
            issues.append("SNRが低い")
        if max(hum_detection.values()) > 0.15:
            issues.append("ハム成分あり")
        
        if not issues:
            good_points.append("音質に大きな問題なし")
        
        if good_points:
            for point in good_points:
                report += f"  ✅ {point}\n"
        
        if issues:
            for issue in issues:
                report += f"  ⚠️ {issue}\n"
        
        return report
    
    def reset_analysis_ui(self):
        """分析UI状態をリセット"""
        self.analyze_button.setEnabled(True)
        self.analyze_button.setText("📊 音声品質を詳細分析")
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
    
    # プリセット関連メソッド（設定保存対応）
    def apply_preset_automatically(self):
        """プリセット選択時に自動適用（enabled状態保持版）"""
        preset_key = self.preset_combo.currentData()
        if not preset_key:
            return
        
        # 👈 現在のenabled状態を保存
        current_enabled = self.cleaner_settings['enabled']
        print(f"🎯 プリセット適用開始: {preset_key}, 現在のenabled: {current_enabled}")
        
        # デフォルトプリセット（enabledを削除）
        presets = {
            "standard_processing": {
                'auto_generated': False, 'highpass_freq': 80,
                'hum_removal': True, 'hum_frequencies': [50, 60, 100, 120, 150, 180, 200, 240],
                'hum_gains': [-20, -20, -12, -12, -9, -9, -6, -6], 'noise_reduction': True,
                'noise_floor': -28, 'loudness_norm': True, 'target_lufs': -20.0, 'true_peak': -1.0,
            },
            "light_processing": {
                'auto_generated': False, 'highpass_freq': 60,
                'hum_removal': False, 'noise_reduction': True, 'noise_floor': -35,
                'loudness_norm': True, 'target_lufs': -18.0, 'true_peak': -1.0,
            },
            "heavy_cleaning": {
                'auto_generated': False, 'highpass_freq': 100,
                'hum_removal': True, 'hum_frequencies': [50, 60, 100, 120, 150, 180, 200, 240, 300],
                'hum_gains': [-25, -25, -18, -18, -15, -15, -12, -12, -9], 'noise_reduction': True,
                'noise_floor': -25, 'loudness_norm': True, 'target_lufs': -20.0, 'true_peak': -2.0,
            },
            "streaming_optimized": {
                'auto_generated': False, 'highpass_freq': 80,
                'hum_removal': True, 'hum_frequencies': [50, 60, 100, 120],
                'hum_gains': [-15, -15, -10, -10], 'noise_reduction': True, 'noise_floor': -30,
                'loudness_norm': True, 'target_lufs': -16.0, 'true_peak': -1.0,
            }
        }
        
        if preset_key in presets:
            preset_settings = presets[preset_key]
            
            # プリセット設定を適用
            self.cleaner_settings.update(preset_settings)
            
            # 👈 enabled状態を元に戻す
            self.cleaner_settings['enabled'] = current_enabled
            
            # 👈 UIは更新しない（現在の状態を維持）
            # self.toggle_switch.setChecked(preset_settings['enabled'])  # この行を削除またはコメントアウト
            
            # 設定を保存
            self.settings_manager.set_last_preset(preset_key)
            
            self.emit_settings_changed()
            print(f"🎯 プリセット適用完了: {preset_key}, enabled維持: {current_enabled}")
    
    # イベントハンドラー（設定保存対応）
    def on_enable_toggled(self, enabled):
        """クリーナー有効/無効切り替え（設定保存対応）"""
        self.cleaner_settings['enabled'] = enabled
        
        # 設定を保存
        self.settings_manager.set_cleaner_enabled(enabled)
        
        self.emit_settings_changed()
        print(f"🔧 クリーナー切り替え: {'有効' if enabled else '無効'}")
    
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
        """外部から音声データを受け取って分析実行"""
        
        # 簡単な検証
        if audio_data is None or len(audio_data) == 0:
            print("❌ 音声データが無効です")
            return
        
        # データサイズチェック
        data_size_mb = audio_data.nbytes / (1024 * 1024)
        if data_size_mb > 100:  # 100MB以上でも強行
            print(f"⚠️ 大きなデータ（{data_size_mb:.1f}MB）ですが処理を続行します")
        
        print(f"🔍 音声分析開始（データサイズ: {data_size_mb:.1f}MB, 長さ: {len(audio_data)/sample_rate:.2f}秒）")
        self.run_simple_analysis_safe(audio_data, sample_rate)