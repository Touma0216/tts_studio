import os
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QFileDialog, QGroupBox, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class ModelLoaderDialog(QDialog):
    # モデル読み込み完了シグナル（パスを送信）
    model_loaded = pyqtSignal(dict)  # {model_path, config_path, style_path}
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_paths = {
            'model': None,
            'config': None, 
            'style': None
        }
        self.init_ui()
        
    def init_ui(self):
        """UIの初期化"""
        self.setWindowTitle("モデル読み込み")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 説明ラベル
        description = QLabel("Style-Bert-VITS2のモデルファイルを選択してください")
        description.setFont(QFont("", 10, QFont.Weight.Bold))
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)
        
        # フォルダ選択部分
        folder_group = QGroupBox("フォルダ選択")
        folder_layout = QVBoxLayout(folder_group)
        
        self.folder_path_label = QLabel("フォルダが選択されていません")
        self.folder_path_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                color: #666;
            }
        """)
        
        self.select_folder_btn = QPushButton("📁 フォルダを選択")
        self.select_folder_btn.setMinimumHeight(35)
        self.select_folder_btn.clicked.connect(self.select_folder)
        
        folder_layout.addWidget(self.folder_path_label)
        folder_layout.addWidget(self.select_folder_btn)
        layout.addWidget(folder_group)
        
        # ファイルチェック結果
        files_group = QGroupBox("必要ファイルチェック")
        files_layout = QGridLayout(files_group)
        
        # ファイルチェック表示
        self.file_checks = {}
        required_files = [
            ('model', 'モデルファイル (.safetensors)', '*.safetensors'),
            ('config', 'コンフィグファイル (config.json)', 'config.json'),
            ('style', 'スタイルファイル (style_vectors.npy)', 'style_vectors.npy')
        ]
        
        for i, (key, desc, pattern) in enumerate(required_files):
            # ファイル名
            name_label = QLabel(desc)
            name_label.setFont(QFont("", 9))
            
            # ステータス
            status_label = QLabel("❌ 未確認")
            status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
            
            # パス表示
            path_label = QLabel("ファイルが見つかりません")
            path_label.setStyleSheet("color: #666; font-size: 8pt;")
            path_label.setWordWrap(True)
            
            self.file_checks[key] = {
                'status': status_label,
                'path': path_label,
                'pattern': pattern
            }
            
            files_layout.addWidget(name_label, i, 0)
            files_layout.addWidget(status_label, i, 1)
            files_layout.addWidget(path_label, i, 2)
        
        layout.addWidget(files_group)
        
        # ボタン
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.load_btn = QPushButton("読み込み")
        self.load_btn.setEnabled(False)
        self.load_btn.clicked.connect(self.load_model)
        self.load_btn.setStyleSheet("""
            QPushButton:enabled {
                background-color: #4caf50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
        """)
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.load_btn)
        layout.addLayout(button_layout)
        
    def select_folder(self):
        """フォルダ選択ダイアログ"""
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "モデルフォルダを選択",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder_path:
            self.folder_path_label.setText(folder_path)
            self.folder_path_label.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    background-color: #e3f2fd;
                    border: 1px solid #2196f3;
                    border-radius: 4px;
                    color: #1976d2;
                }
            """)
            self.check_files(folder_path)
    
    def check_files(self, folder_path):
        """必要ファイルの存在をチェック"""
        folder = Path(folder_path)
        all_found = True
        
        # モデルファイル (.safetensors)
        model_files = list(folder.glob("*.safetensors"))
        if model_files:
            self.model_paths['model'] = str(model_files[0])
            self.update_file_status('model', True, str(model_files[0]))
        else:
            self.update_file_status('model', False, "見つかりません")
            all_found = False
        
        # config.json
        config_file = folder / "config.json"
        if config_file.exists():
            self.model_paths['config'] = str(config_file)
            self.update_file_status('config', True, str(config_file))
        else:
            self.update_file_status('config', False, "見つかりません")
            all_found = False
            
        # style_vectors.npy
        style_file = folder / "style_vectors.npy"
        if style_file.exists():
            self.model_paths['style'] = str(style_file)
            self.update_file_status('style', True, str(style_file))
        else:
            self.update_file_status('style', False, "見つかりません")
            all_found = False
        
        # 読み込みボタンの有効/無効
        self.load_btn.setEnabled(all_found)
        
    def update_file_status(self, key, found, path):
        """ファイル状況表示を更新"""
        if found:
            self.file_checks[key]['status'].setText("✅ 見つかりました")
            self.file_checks[key]['status'].setStyleSheet("color: #2e7d32; font-weight: bold;")
            self.file_checks[key]['path'].setText(path)
            self.file_checks[key]['path'].setStyleSheet("color: #2e7d32; font-size: 8pt;")
        else:
            self.file_checks[key]['status'].setText("❌ 見つかりません")
            self.file_checks[key]['status'].setStyleSheet("color: #d32f2f; font-weight: bold;")
            self.file_checks[key]['path'].setText(path)
            self.file_checks[key]['path'].setStyleSheet("color: #d32f2f; font-size: 8pt;")
    
    def load_model(self):
        """モデル読み込みを実行"""
        if all(self.model_paths.values()):
            # シグナルでパスを送信
            self.model_loaded.emit({
                'model_path': self.model_paths['model'],
                'config_path': self.model_paths['config'],
                'style_path': self.model_paths['style']
            })
            self.accept()
        else:
            pass