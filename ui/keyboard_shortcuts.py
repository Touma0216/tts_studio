from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtCore import Qt, QObject

class KeyboardShortcutManager(QObject):
    """キーボードショートカット管理クラス（Undo機能対応）"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.shortcuts = {}
        self.setup_shortcuts()
    
    def setup_shortcuts(self):
        """全ショートカットを設定（Undo機能追加）"""
        
        # ファイル操作
        self.add_shortcut("Ctrl+F", self.open_file_menu)
        
        # ヘルプ機能
        self.add_shortcut("Ctrl+H", self.toggle_help_dialog)
        
        # Undo機能（新規追加）
        self.add_shortcut("Ctrl+Z", self.undo_parameters)
        
        # 再生系
        self.add_shortcut("Ctrl+R", self.play_sequential)
        self.add_shortcut("Ctrl+P", self.play_current_row)
        
        # テキスト操作
        self.add_shortcut("Ctrl+N", self.add_text_row)
        
        # タブ切り替え
        self.add_shortcut("Ctrl+Tab", self.focus_master_tab)
        self.add_shortcut("Ctrl+1", lambda: self.focus_text_row(1))
        self.add_shortcut("Ctrl+2", lambda: self.focus_text_row(2))
        self.add_shortcut("Ctrl+3", lambda: self.focus_text_row(3))
        self.add_shortcut("Ctrl+4", lambda: self.focus_text_row(4))
        self.add_shortcut("Ctrl+5", lambda: self.focus_text_row(5))
        self.add_shortcut("Ctrl+6", lambda: self.focus_text_row(6))
        self.add_shortcut("Ctrl+7", lambda: self.focus_text_row(7))
        self.add_shortcut("Ctrl+8", lambda: self.focus_text_row(8))
        self.add_shortcut("Ctrl+9", lambda: self.focus_text_row(9))
        
        # 感情選択
        self.add_shortcut("Ctrl+E", self.open_emotion_combo)
        
        # 保存系
        self.add_shortcut("Ctrl+S", self.save_individual)
        self.add_shortcut("Ctrl+Shift+S", self.save_continuous)
    
    def add_shortcut(self, key_sequence, callback):
        """ショートカットを追加（ApplicationShortcut で全画面有効）"""
        shortcut = QShortcut(QKeySequence(key_sequence), self.main_window)
        shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut.activated.connect(callback)
        self.shortcuts[key_sequence] = shortcut
    
    # ========================
    # ショートカット実行関数
    # ========================
    
    def open_file_menu(self):
        """ファイルメニューを開く"""
        self.main_window.toggle_file_menu()
    
    def toggle_help_dialog(self):
        """ヘルプダイアログを表示/非表示"""
        if hasattr(self.main_window, 'help_dialog'):
            if self.main_window.help_dialog.isVisible():
                self.main_window.help_dialog.close()
            else:
                self.main_window.help_dialog.show()
                self.main_window.help_dialog.raise_()
                self.main_window.help_dialog.activateWindow()
    
    def undo_parameters(self):
        """現在のタブのパラメータをUndo（エフェクト対応版）"""
        try:
            # フォーカスがテキスト入力にある場合は、テキストのUndoを優先
            focused_widget = self.main_window.focusWidget()
            
            # QTextEditの場合は標準のUndoを実行
            if hasattr(focused_widget, 'undo'):
                from PyQt6.QtWidgets import QTextEdit, QLineEdit
                if isinstance(focused_widget, (QTextEdit, QLineEdit)):
                    focused_widget.undo()
                    print("📝 テキストUndo実行")
                    return
            
            # タブ統合コントロールでUndo実行
            tabbed_audio_control = self.main_window.tabbed_audio_control
            success = tabbed_audio_control.undo_current_tab()
            
            if success:
                current_index = tabbed_audio_control.main_tab_widget.currentIndex()
                tab_names = ["音声パラメータ", "音声クリーナー", "音声エフェクト"]
                tab_name = tab_names[current_index] if current_index < len(tab_names) else "不明"
                print(f"🔄 {tab_name}タブでUndo実行")
            else:
                print("⚠️ Undo履歴がありません")
                
        except Exception as e:
            print(f"❌ Undoエラー: {e}")
    
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
    
    def add_text_row(self):
        """テキスト行を追加"""
        # 9行制限チェック
        if len(self.main_window.multi_text.text_rows) >= 9:
            return
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
        text_rows = list(self.main_window.multi_text.text_rows.values())
        if 0 < row_number <= len(text_rows):
            target_row = text_rows[row_number - 1]
            target_row.text_input.setFocus()
            
            # 対応するパラメータタブもアクティブに（マスタータブの次のインデックス）
            row_id = target_row.row_id
            self.main_window.tabbed_audio_control.set_current_row(row_id)
    
    def open_emotion_combo(self):
        """感情コンボボックスを開く"""
        current_control = self.main_window.tabbed_audio_control.emotion_control.tab_widget.currentWidget()
        if current_control and hasattr(current_control, 'emotion_combo'):
            current_control.emotion_combo.setFocus()
            current_control.emotion_combo.showPopup()
    
    def save_individual(self):
        """個別保存"""
        self.main_window.save_individual_btn.click()
    
    def save_continuous(self):
        """連続保存"""
        self.main_window.save_continuous_btn.click()