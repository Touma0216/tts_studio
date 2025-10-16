from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                            QPushButton, QLabel, QScrollArea, QDoubleSpinBox,
                            QSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
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
        
        # 🆕 無音区間入力
        silence_container = QWidget()
        silence_layout = QVBoxLayout(silence_container)
        silence_layout.setContentsMargins(0, 0, 0, 0)
        silence_layout.setSpacing(2)

        silence_label = QLabel("後の無音:")
        silence_label.setStyleSheet("font-size: 10px; color: #666;")
        silence_layout.addWidget(silence_label)

        # 無音時間の入力とボタン
        silence_input_layout = QHBoxLayout()
        silence_input_layout.setContentsMargins(0, 0, 0, 0)
        silence_input_layout.setSpacing(2)

        self.silence_spin = QDoubleSpinBox()
        self.silence_spin.setRange(0.0, 3600.0)
        self.silence_spin.setValue(self.silence_after)
        self.silence_spin.setSuffix(" 秒")
        self.silence_spin.setDecimals(1)
        self.silence_spin.setSingleStep(0.5)
        self.silence_spin.setFixedWidth(60)
        self.silence_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.silence_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.silence_spin.setStyleSheet("""
            QDoubleSpinBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 2px;
                font-size: 11px;
            }
        """)
        silence_input_layout.addWidget(self.silence_spin)

        # 上ボタン（▲で増加/緑）
        silence_up_btn = QPushButton("▲")
        silence_up_btn.setFixedSize(20, 20)
        silence_up_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        silence_up_btn.clicked.connect(lambda: self.silence_spin.setValue(min(3600.0, self.silence_spin.value() + 0.5)))
        silence_input_layout.addWidget(silence_up_btn)

        # 下ボタン（▼で減少/赤）
        silence_down_btn = QPushButton("▼")
        silence_down_btn.setFixedSize(20, 20)
        silence_down_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        silence_down_btn.clicked.connect(lambda: self.silence_spin.setValue(max(0.0, self.silence_spin.value() - 0.5)))
        silence_input_layout.addWidget(silence_down_btn)

        silence_layout.addLayout(silence_input_layout)

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
    row_focus_requested = pyqtSignal(str)  # row_id

    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_rows = {}  # row_id -> TextRowWidget
        self.init_ui()
        
        # 初期行を1つ追加（固定ID "initial"）
        self.add_text_row_with_id("initial")
        
        # 初期タブ作成のためのシグナル送信
        self.row_added.emit("initial", 1)

        # 自動整理処理のステート
        self._auto_split_processing = False
        self._auto_split_lines = []
        self._auto_split_index = 0
        self._auto_split_required_rows = 0
        self._auto_split_stage = None
        self._auto_split_extra_ids = []
        self._auto_split_chunk_size = 50
    
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # ヘッダー
        header_layout = QHBoxLayout()

        header_label = QLabel("テキスト入力:")
        header_label.setFont(QFont("", 10, QFont.Weight.Bold))
        header_layout.addWidget(header_label)

        # 行ジャンプ入力（ボタンなしテキストボックス）
        self.jump_spin = QSpinBox()
        self.jump_spin.setRange(1, 1)
        self.jump_spin.setValue(1)
        self.jump_spin.setFixedWidth(50)
        self.jump_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.jump_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.jump_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 2px;
                font-size: 11px;
            }
        """)
        header_layout.addWidget(self.jump_spin)

        # 上ボタン（▲で増加/緑）
        self.jump_up_btn = QPushButton("▲")
        self.jump_up_btn.setFixedSize(24, 24)
        self.jump_up_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.jump_up_btn.clicked.connect(self.on_jump_up)
        header_layout.addWidget(self.jump_up_btn)

        # 下ボタン（▼で減少/赤）
        self.jump_down_btn = QPushButton("▼")
        self.jump_down_btn.setFixedSize(24, 24)
        self.jump_down_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.jump_down_btn.clicked.connect(lambda: self.jump_spin.setValue(max(1, self.jump_spin.value() - 1)))
        header_layout.addWidget(self.jump_down_btn)

        self.jump_button = QPushButton("移動")
        self.jump_button.setFixedHeight(24)
        self.jump_button.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
        """)
        self.jump_button.clicked.connect(self.on_jump_requested)
        self.jump_spin.editingFinished.connect(self.on_jump_requested)
        header_layout.addWidget(self.jump_button)

        # 自動整理ボタン（移動ボタンの右隣）
        self.auto_split_button = QPushButton("自動整理")
        self.auto_split_button.setFixedHeight(24)
        self.auto_split_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #43a047;
            }
        """)
        self.auto_split_button.clicked.connect(self.auto_split_texts)
        header_layout.addWidget(self.auto_split_button)
        header_layout.addStretch()

        # 🆕 テキスト数表示ラベル（右端に配置）
        self.text_count_label = QLabel("テキスト数: 1")
        self.text_count_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 10px;
                padding: 2px 8px;
                background-color: #f0f0f0;
                border-radius: 4px;
            }
        """)
        header_layout.addWidget(self.text_count_label)
        
        # スクロールエリア
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # テキスト行コンテナ
        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(5, 5, 5, 5)
        self.rows_layout.setSpacing(3)
        
        self.scroll_area.setWidget(self.rows_container)
        
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
        layout.addWidget(self.scroll_area, 1)  # 伸縮
        layout.addWidget(add_btn)
    
    def add_text_row(self, text="", parameters=None, silence_after=0.0):
        """テキスト行を追加"""
            
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
        
        # 🆕 テキスト数ラベルを更新
        row_count = len(self.text_rows)
        self.text_count_label.setText(f"テキスト数: {row_count}")
        
        # シグナル送信
        self.row_numbers_updated.emit(row_mapping)
        self.update_jump_range()
        
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

    def update_jump_range(self):
        """行ジャンプ入力の範囲を最新の行数に合わせて更新"""
        if not hasattr(self, 'jump_spin'):
            return

        row_count = max(1, len(self.text_rows))
        self.jump_spin.setMaximum(row_count)

        if self.jump_spin.value() > row_count:
            self.jump_spin.setValue(row_count)

    def on_jump_up(self):
        """ジャンプ上ボタン: 上限なら新規行追加、未満なら+1"""
        current = self.jump_spin.value()
        maximum = self.jump_spin.maximum()
        
        if current >= maximum:
            # 上限に達している → 新しい行を追加
            new_row_id = self.add_text_row()
            # 追加後の最新行（最後の行）に自動でジャンプ
            new_row_number = len(self.text_rows)
            self.jump_spin.setValue(new_row_number)
            self.focus_row_by_number(new_row_number)
        else:
            # 上限未満 → 単純に+1
            self.jump_spin.setValue(current + 1)

    def on_jump_requested(self):
        """ジャンプボタンまたは確定操作で指定行に移動"""
        if not self.text_rows:
            return

        target_number = self.jump_spin.value()
        self.focus_row_by_number(target_number)

    def focus_row_by_number(self, row_number):
        """指定された番号のテキスト行にフォーカス"""
        if not self.text_rows:
            return

        row_count = len(self.text_rows)
        target_number = max(1, min(row_number, row_count))

        # 順序付きで取得
        text_rows = list(self.text_rows.items())
        target_row_id, target_widget = text_rows[target_number - 1]

        # スクロール位置を調整
        if hasattr(self, 'scroll_area') and self.scroll_area:
            self.scroll_area.ensureWidgetVisible(target_widget)

        # テキスト入力にフォーカス
        target_widget.text_input.setFocus()

        # 現在値を更新
        if self.jump_spin.value() != target_number:
            self.jump_spin.blockSignals(True)
            self.jump_spin.setValue(target_number)
            self.jump_spin.blockSignals(False)

        # 音声パラメータタブの選択を連動
        self.row_focus_requested.emit(target_row_id)

    def auto_split_texts(self):
        """入力されたテキストを改行ごとに自動整理"""

        if self._auto_split_processing:
            return

        # 現在のテキストを行順で取得
        current_widgets = list(self.text_rows.values())
        lines = []
        for widget in current_widgets:
            text = widget.get_text()
            if not text:
                continue

            for raw_line in text.splitlines():
                stripped = raw_line.strip()
                if not stripped:
                    continue

                cleaned = " ".join(stripped.split())
                if cleaned:
                    lines.append(cleaned)

        self._auto_split_processing = True
        self.auto_split_button.setEnabled(False)

        self._auto_split_lines = lines
        self._auto_split_index = 0
        self._auto_split_required_rows = max(1, len(lines))
        self._auto_split_stage = "assign"
        self._auto_split_extra_ids = []

        current_count = len(self.text_rows)
        if current_count > self._auto_split_required_rows:
            # 削除対象行を保持
            self._auto_split_extra_ids = list(self.text_rows.keys())[self._auto_split_required_rows:]

        self._process_auto_split_batch()

    def _process_auto_split_batch(self):
        """自動整理の分割処理を実行"""
        if not self._auto_split_processing:
            return

        chunk_size = self._auto_split_chunk_size
        processed = 0

        if self._auto_split_stage == "assign":
            while processed < chunk_size and self._auto_split_index < self._auto_split_required_rows:
                target_index = self._auto_split_index

                # 必要数まで行を追加
                if len(self.text_rows) <= target_index:
                    self.add_text_row()
                    continue

                widgets = list(self.text_rows.values())
                widget = widgets[target_index]
                text = self._auto_split_lines[target_index] if target_index < len(self._auto_split_lines) else ""
                widget.set_text(text)

                self._auto_split_index += 1
                processed += 1

            if self._auto_split_index >= self._auto_split_required_rows:
                self._auto_split_stage = "remove"

        if self._auto_split_stage == "remove" and processed < chunk_size:
            while processed < chunk_size and self._auto_split_extra_ids:
                row_id = self._auto_split_extra_ids.pop(0)
                self.delete_text_row(row_id)
                processed += 1

            if not self._auto_split_extra_ids:
                self._auto_split_stage = "finalize"
                
        if self._auto_split_stage == "finalize":
            if not self.text_rows:
                self.add_text_row()

            self._auto_split_processing = False
            self.auto_split_button.setEnabled(True)
            self.update_row_numbers()
            return

        QTimer.singleShot(0, self._process_auto_split_batch)