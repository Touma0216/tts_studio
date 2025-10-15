from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtCore import Qt, QObject
from PyQt6.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit

class KeyboardShortcutManager(QObject):
    """キーボードショートカット管理クラス（Undo/Redo機能対応）"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.shortcuts = {}
        self.setup_shortcuts()
    
    def setup_shortcuts(self):
        """全ショートカットを設定（Undo/Redo機能追加）"""
        
        # ファイル操作（テキスト入力時は無効）
        self.add_shortcut("F", self.open_file_menu)

        # ヘルプ機能（テキスト入力時は無効）
        self.add_shortcut("H", self.toggle_help_dialog)

        # Live2D表情切り替え
        self.add_shortcut("F1", self.set_expression_default)
        self.add_shortcut("F2", self.set_expression_joy)
        self.add_shortcut("F3", self.set_expression_surprised)
        self.add_shortcut("F4", self.set_expression_fear)
        self.add_shortcut("F5", self.set_expression_sad)

        # テキスト操作
        self.add_shortcut("Ctrl+D", self.reset_text_inputs)

        
        # 再生系
        self.add_shortcut("Ctrl+P", self.play_current_row)
        self.add_shortcut("Ctrl+R", self.play_sequential)
        self.add_shortcut("Ctrl+E", self.play_streaming)  # 🆕 ストリーミング再生

        # 感情選択（ショートカット削除、必要なら別のキーに変更可能）
        # self.add_shortcut("Ctrl+Shift+E", self.open_emotion_combo)  # 👈 無効化
        
        # 保存系
        self.add_shortcut("Ctrl+S", self.save_individual)
        self.add_shortcut("Ctrl+Shift+S", self.save_continuous)

        # リップシンク
        self.add_shortcut("Ctrl+T", self.test_lipsync)

        # Undo/Redo機能
        self.add_shortcut("Ctrl+Z", self.undo_parameters)
        self.add_shortcut("Ctrl+Y", self.redo_parameters)
    
    def add_shortcut(self, key_sequence, callback):
        """ショートカットを追加（ApplicationShortcut で全画面有効）"""
        shortcut = QShortcut(QKeySequence(key_sequence), self.main_window)
        shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut.activated.connect(callback)
        self.shortcuts[key_sequence] = shortcut


    
    # ========================
    # Undo/Redo関連機能（改良版）
    # ========================
    
    def undo_parameters(self):
        """現在のタブのパラメータをUndo（改良版複数Undo対応）"""
        try:
            # フォーカスがテキスト入力にある場合は、テキストのUndoを優先
            focused_widget = self.main_window.focusWidget()
            
            # QTextEditの場合は標準のUndoを実行
            if hasattr(focused_widget, 'undo'):
                from PyQt6.QtWidgets import QTextEdit, QLineEdit
                if isinstance(focused_widget, (QTextEdit, QLineEdit)):
                    focused_widget.undo()
                    return
            
            # タブ統合コントロールでUndo実行
            tabbed_audio_control = self.main_window.tabbed_audio_control
            success = tabbed_audio_control.undo_current_tab()
            
            if success:
                current_index = tabbed_audio_control.main_tab_widget.currentIndex()
                tab_names = ["音声パラメータ", "音声クリーナー", "音声エフェクト"]
                tab_name = tab_names[current_index] if current_index < len(tab_names) else "不明"
                # print(f"🔄 {tab_name}タブでUndo実行")  # ログ出力を削除
                
        except Exception as e:
            print(f"❌ Undoエラー: {e}")
    
    def redo_parameters(self):
        """現在のタブのパラメータをRedo（新機能）"""
        try:
            # フォーカスがテキスト入力にある場合は、テキストのRedoを優先
            focused_widget = self.main_window.focusWidget()
            
            # QTextEditの場合は標準のRedoを実行
            if hasattr(focused_widget, 'redo'):
                from PyQt6.QtWidgets import QTextEdit, QLineEdit
                if isinstance(focused_widget, (QTextEdit, QLineEdit)):
                    focused_widget.redo()
                    return
            
            # タブ統合コントロールでRedo実行
            tabbed_audio_control = self.main_window.tabbed_audio_control
            
            # Redo機能をタブ統合コントロールに追加（動的）
            if not hasattr(tabbed_audio_control, 'redo_current_tab'):
                tabbed_audio_control.redo_current_tab = self._create_redo_method(tabbed_audio_control)
            
            success = tabbed_audio_control.redo_current_tab()
            
            if success:
                current_index = tabbed_audio_control.main_tab_widget.currentIndex()
                tab_names = ["音声パラメータ", "音声クリーナー", "音声エフェクト"]
                tab_name = tab_names[current_index] if current_index < len(tab_names) else "不明"
                # print(f"🔄 {tab_name}タブでRedo実行")  # ログ出力を削除
                
        except Exception as e:
            print(f"❌ Redoエラー: {e}")
    
    def _create_redo_method(self, tabbed_audio_control):
        """タブ統合コントロール用のRedo機能を動的作成"""
        def redo_current_tab():
            current_index = tabbed_audio_control.main_tab_widget.currentIndex()
            
            if current_index == 0:  # 音声パラメータタブ
                # 現在のタブがUndo可能な場合のみ実行
                current_widget = tabbed_audio_control.emotion_control.tab_widget.currentWidget()
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
                effects_control = tabbed_audio_control.effects_control
                if hasattr(effects_control, 'history') and effects_control.history.has_redo_available():
                    # Redo実行
                    effects_control.history.set_undoing_flag(True)
                    next_state = effects_control.history.get_next_state()
                    if next_state:
                        effects_control.set_settings(next_state)
                        effects_control.emit_settings_changed()
                    effects_control.history.set_undoing_flag(False)
                    return True
                return False
            
            return False
        
        return redo_current_tab
    
    # ========================
    # 既存のショートカット実行関数
    # ========================
    
    def _is_text_input_focused(self) -> bool:
        """テキスト入力系ウィジェットにフォーカスがあるか判定"""
        focused_widget = self.main_window.focusWidget()
        return isinstance(focused_widget, (QLineEdit, QTextEdit, QPlainTextEdit))

    def open_file_menu(self):
        """ファイルメニューを開く"""
        if self._is_text_input_focused():
            return
        self.main_window.toggle_file_menu()
    
    def toggle_help_dialog(self):
        """ヘルプダイアログを表示/非表示"""
        if self._is_text_input_focused():
            return
        if hasattr(self.main_window, 'help_dialog'):
            if self.main_window.help_dialog.isVisible():
                self.main_window.help_dialog.close()
            else:
                self.main_window.help_dialog.show()
                self.main_window.help_dialog.raise_()
                self.main_window.help_dialog.activateWindow()


    def reset_text_inputs(self):
        """テキストリセット"""
        if hasattr(self.main_window, 'reset_text_btn'):
            self.main_window.reset_text_btn.click()

    def set_expression_default(self):
        """デフォルト表情"""
        self.main_window.trigger_live2d_expression(None)

    def set_expression_joy(self):
        """喜び表情"""
        self.main_window.trigger_live2d_expression("Scene1")

    def set_expression_surprised(self):
        """驚き表情"""
        self.main_window.trigger_live2d_expression("Scene2")

    def set_expression_fear(self):
        """恐怖表情"""
        self.main_window.trigger_live2d_expression("Scene3")

    def set_expression_sad(self):
        """悲しみ表情"""
        self.main_window.trigger_live2d_expression("Scene4")
        
    
    def play_current_row(self):
        """現在フォーカス中の行を再生"""
        # アクティブなタブのIDを取得
        current_tab_index = self.main_window.tabbed_audio_control.emotion_control.tab_widget.currentIndex()
        
        # マスタータブ（★）の場合は何もしない
        if current_tab_index == 0:
            return
            
        if current_tab_index >= 0:
            # タブのrow_idを取得（タブウィジェットから逆引き）
            current_control = self.main_window.tabbed_audio_control.emotion_control.tab_widget.currentWidget()
            if current_control and hasattr(current_control, 'row_id') and not getattr(current_control, 'is_master', False):
                row_id = current_control.row_id
                # 対応するテキスト行を再生
                if row_id in self.main_window.multi_text.text_rows:
                    text_widget = self.main_window.multi_text.text_rows[row_id]
                    text_widget.play_btn.click()
    
    def play_sequential(self):
        """連続再生"""
        self.main_window.sequential_play_btn.click()
    
    def play_streaming(self):
        """🆕 ストリーミング再生"""
        if hasattr(self.main_window, 'streaming_play_btn'):
            self.main_window.streaming_play_btn.click()

    def save_individual(self):
        """個別保存"""
        if hasattr(self.main_window, 'save_individual_btn'):
            self.main_window.save_individual_btn.click()

    def save_continuous(self):
        """連続保存"""
        if hasattr(self.main_window, 'save_continuous_btn'):
            self.main_window.save_continuous_btn.click()

    def test_lipsync(self):
        """リップシンクテスト"""
        if hasattr(self.main_window, 'test_lipsync_btn'):
            self.main_window.test_lipsync_btn.click()
    
    def add_text_row(self):
        """テキスト行を追加"""
        self.main_window.multi_text.add_text_row()
    
    def focus_master_tab(self):
        """マスタータブ（★）にフォーカス"""
        # マスタータブは常にindex 0
        self.main_window.tabbed_audio_control.emotion_control.tab_widget.setCurrentIndex(0)
        
        # マスタータブ内の最初の入力要素にフォーカス
        master_control = self.main_window.tabbed_audio_control.emotion_control.master_control
        if master_control and hasattr(master_control, 'emotion_combo'):
            master_control.emotion_combo.setFocus()
    
    def focus_text_row(self, row_number):
        """指定番号のテキスト行にフォーカス"""
        if hasattr(self.main_window.multi_text, 'focus_row_by_number'):
            self.main_window.multi_text.focus_row_by_number(row_number)
        else:
            text_rows = list(self.main_window.multi_text.text_rows.values())
            if 0 < row_number <= len(text_rows):
                target_row = text_rows[row_number - 1]
                target_row.text_input.setFocus()

                row_id = target_row.row_id
                self.main_window.tabbed_audio_control.set_current_row_silent(row_id)
    
    def open_emotion_combo(self):
        """感情コンボボックスを開く（ショートカット無効化中）"""
        current_control = self.main_window.tabbed_audio_control.emotion_control.tab_widget.currentWidget()
        if current_control and hasattr(current_control, 'emotion_combo'):
            current_control.emotion_combo.setFocus()
            current_control.emotion_combo.showPopup()