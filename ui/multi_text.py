from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                            QPushButton, QLabel, QFrame, QScrollArea, QDoubleSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import uuid

class TextRowWidget(QWidget):
    """単一テキスト行ウィジェット（無音区間対応版）"""
    
    delete_requested = pyqtSignal(str)  # row_id
    parameters_changed = pyqtSignal(str, dict)  # row_id, parameters
    play_requested = pyqtSignal(str)  # row_id
    
    def __init__(self, row_id=None, text="", parameters=None, silence_after=0.0, parent=None):
        super().__init__(parent)
        
        self.row_id = row_id or str(uuid.uuid4())[:8]
        
        # デフォルトパラメータ
        self.parameters = parameters or {
            'style': 'Neutral',
            'style_weight': 1.0,
            'length_scale': 0.85,
            'pitch_scale': 1.0,
            'intonation_scale': 1.0,
            'sdp_ratio': 0.25,
            'noise': 0.35
        }
        
        self.silence_after = silence_after  # 🆕 後の無音時間
        
        self.init_ui()
        
        if text:
            self.text_input.setPlainText(text)
    
    def init_ui(self):
        """UIを初期化"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # 行番号表示
        self.row_label = QLabel(f"{self.row_id}.")
        self.row_label.setFixedWidth(40)
        self.row_label.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                color: #1976d2;
                font-weight: bold;
                padding: 4px;
                border-radius: 4px;
                text-align: center;
            }
        """)
        self.row_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # テキスト入力
        self.text_input = QTextEdit()
        self.text_input.setMaximumHeight(60)
        self.text_input.setPlaceholderText("テキストを入力...")
        self.text_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
            }
        """)
        
        # カスタムキーイベント処理
        self.text_input.keyPressEvent = self.text_input_key_press
        
        # 🆕 無音区間入力
        silence_container = QWidget()
        silence_layout = QVBoxLayout(silence_container)
        silence_layout.setContentsMargins(0, 0, 0, 0)
        silence_layout.setSpacing(2)
        
        silence_label = QLabel("後の無音:")
        silence_label.setStyleSheet("font-size: 10px; color: #666;")
        
        self.silence_spin = QDoubleSpinBox()
        self.silence_spin.setRange(0.0, 3600.0)  # 0秒～1時間
        self.silence_spin.setValue(self.silence_after)
        self.silence_spin.setSuffix(" 秒")
        self.silence_spin.setDecimals(1)
        self.silence_spin.setSingleStep(0.5)
        self.silence_spin.setFixedWidth(80)
        self.silence_spin.setToolTip("このテキストの後に挿入する無音時間")
        self.silence_spin.setStyleSheet("""
            QDoubleSpinBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 2px;
                font-size: 11px;
            }
        """)
        
        silence_layout.addWidget(silence_label)
        silence_layout.addWidget(self.silence_spin)
        
        # 再生ボタン
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(30, 30)
        self.play_btn.setToolTip("この行を再生(R)")
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.play_btn.clicked.connect(lambda: self.play_requested.emit(self.row_id))
        
        # 削除ボタン
        self.delete_btn = QPushButton("×")
        self.delete_btn.setFixedSize(30, 30)
        self.delete_btn.setToolTip("この行を削除")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.row_id))
        
        # レイアウト配置
        layout.addWidget(self.row_label, 0)
        layout.addWidget(self.text_input, 1)  # 伸縮
        layout.addWidget(silence_container, 0)  # 🆕 無音区間
        layout.addWidget(self.play_btn, 0)
        layout.addWidget(self.delete_btn, 0)
        
        # 区切り線
        self.setStyleSheet("""
            TextRowWidget {
                border-bottom: 1px solid #eee;
                margin: 2px 0;
            }
        """)
    
    def text_input_key_press(self, event):
        """テキスト入力のキーイベント処理"""
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QKeySequence
        
        # Ctrl+Enter: 改行挿入
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            cursor = self.text_input.textCursor()
            cursor.insertText("\n")
            return
        
        # Enter単体: フォーカスを外す（テキスト選択終了）
        elif event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self.text_input.clearFocus()
            return
        
        # その他のキーは通常処理
        QTextEdit.keyPressEvent(self.text_input, event)
    
    def get_text(self):
        """テキストを取得"""
        return self.text_input.toPlainText().strip()
    
    def set_text(self, text):
        """テキストを設定"""
        self.text_input.setPlainText(text)
    
    def get_parameters(self):
        """パラメータを取得"""
        return self.parameters.copy()
    
    def set_parameters(self, parameters):
        """パラメータを設定"""
        self.parameters.update(parameters)
    
    def get_silence_after(self):
        """後の無音時間を取得"""
        return self.silence_spin.value()
    
    def set_silence_after(self, seconds):
        """後の無音時間を設定"""
        self.silence_spin.setValue(seconds)
    
    def update_row_number(self, number):
        """行番号を更新"""
        self.row_label.setText(f"{number}.")

class MultiTextWidget(QWidget):
    """複数テキスト管理ウィジェット（無音区間対応版）"""
    
    play_single_requested = pyqtSignal(str, str, dict)  # row_id, text, parameters
    play_all_requested = pyqtSignal(list)  # [(text, parameters), ...]
    row_added = pyqtSignal(str, int)  # row_id, row_number
    row_removed = pyqtSignal(str)  # row_id
    row_numbers_updated = pyqtSignal(dict)  # {row_id: row_number}
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_rows = {}  # row_id -> TextRowWidget
        self.init_ui()
        
        # 初期行を1つ追加（固定ID "initial"）
        self.add_text_row_with_id("initial")
        
        # 初期タブ作成のためのシグナル送信
        self.row_added.emit("initial", 1)
    
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # ヘッダー
        header_layout = QHBoxLayout()
        
        header_label = QLabel("テキスト入力:")
        header_label.setFont(QFont("", 10, QFont.Weight.Bold))
        
        # 🆕 説明追加
        info_label = QLabel("💡 各行の後に挿入する無音時間を設定できます")
        info_label.setStyleSheet("color: #666; font-size: 10px;")
        
        header_layout.addWidget(header_label)
        header_layout.addWidget(info_label)
        header_layout.addStretch()
        
        # スクロールエリア
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # テキスト行コンテナ
        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(5, 5, 5, 5)
        self.rows_layout.setSpacing(3)
        
        scroll_area.setWidget(self.rows_container)
        
        # 追加ボタン
        add_btn = QPushButton("➕ テキスト行を追加(N)")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
        """)
        add_btn.clicked.connect(self.add_text_row)
        
        # レイアウト配置
        layout.addLayout(header_layout)
        layout.addWidget(scroll_area, 1)  # 伸縮
        layout.addWidget(add_btn)
    
    def add_text_row(self, text="", parameters=None, silence_after=0.0):
        """テキスト行を追加"""
        # 9行制限
        if len(self.text_rows) >= 9:
            return None
            
        row_widget = TextRowWidget(text=text, parameters=parameters, silence_after=silence_after)
        
        # シグナル接続
        row_widget.delete_requested.connect(self.delete_text_row)
        row_widget.parameters_changed.connect(self.on_row_parameters_changed)
        row_widget.play_requested.connect(self.play_single_row)
        
        # 保存・表示
        self.text_rows[row_widget.row_id] = row_widget
        self.rows_layout.addWidget(row_widget)
        
        # 行番号更新
        self.update_row_numbers()
        
        # シグナル送信
        row_count = len(self.text_rows)
        self.row_added.emit(row_widget.row_id, row_count)
        
        return row_widget.row_id
    
    def add_text_row_with_id(self, row_id, text="", parameters=None, silence_after=0.0):
        """指定IDでテキスト行を追加"""
        row_widget = TextRowWidget(row_id=row_id, text=text, parameters=parameters, silence_after=silence_after)
        
        # シグナル接続
        row_widget.delete_requested.connect(self.delete_text_row)
        row_widget.parameters_changed.connect(self.on_row_parameters_changed)
        row_widget.play_requested.connect(self.play_single_row)
        
        # 保存・表示
        self.text_rows[row_widget.row_id] = row_widget
        self.rows_layout.addWidget(row_widget)
        
        # 行番号更新
        self.update_row_numbers()
        
        # シグナル送信
        row_count = len(self.text_rows)
        self.row_added.emit(row_widget.row_id, row_count)
        
        return row_widget.row_id
    
    def delete_text_row(self, row_id):
        """テキスト行を削除"""
        if len(self.text_rows) <= 1:
            return  # 最低1行は残す
        
        if row_id in self.text_rows:
            widget = self.text_rows[row_id]
            self.rows_layout.removeWidget(widget)
            widget.deleteLater()
            del self.text_rows[row_id]
            
            # 行番号更新
            self.update_row_numbers()
            
            # シグナル送信
            self.row_removed.emit(row_id)
    
    def update_row_numbers(self):
        """行番号を更新"""
        row_mapping = {}
        for i, (row_id, widget) in enumerate(self.text_rows.items(), 1):
            widget.update_row_number(i)
            row_mapping[row_id] = i
        
        # シグナル送信
        self.row_numbers_updated.emit(row_mapping)
    
    def on_row_parameters_changed(self, row_id, parameters):
        """行のパラメータが変更された（現在は未使用）"""
        pass
    
    def play_single_row(self, row_id):
        """単一行を再生"""
        if row_id in self.text_rows:
            widget = self.text_rows[row_id]
            text = widget.get_text()
            parameters = widget.get_parameters()
            
            if text:
                self.play_single_requested.emit(row_id, text, parameters)
    
    def get_all_texts_and_parameters(self):
        """全てのテキストとパラメータを取得（無音区間含む）"""
        result = []
        for row_id, widget in self.text_rows.items():
            text = widget.get_text()
            if text:
                parameters = widget.get_parameters()
                silence_after = widget.get_silence_after()
                result.append({
                    'row_id': row_id,
                    'text': text,
                    'parameters': parameters,
                    'silence_after': silence_after  # 🆕 無音区間
                })
        return result
    
    def clear_all_rows(self):
        """全行をクリアし、1行だけを残して初期化"""
        remaining_ids = list(self.text_rows.keys())

        # 最初の1行以外を削除
        for row_id in remaining_ids[1:]:
            self.delete_text_row(row_id)
        
        first_row_id = None
        if self.text_rows:
            # 残った最初の行をクリア
            first_row_id, first_widget = next(iter(self.text_rows.items()))
            first_widget.set_text("")
            first_widget.set_silence_after(0.0)
        else:
            # すべて削除された場合は初期行を再生成
            first_row_id = self.add_text_row_with_id("initial")

        # 行番号をリフレッシュ
        self.update_row_numbers()

        return first_row_id