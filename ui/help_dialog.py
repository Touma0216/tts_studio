import os
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTextBrowser, QHBoxLayout, 
                            QPushButton, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

class HelpDialog(QDialog):
    """操作説明ダイアログ"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_help_content()
    
    def init_ui(self):
        """UIを初期化"""
        self.setWindowTitle("操作説明 - TTSスタジオ")
        self.setModal(True)
        self.resize(900, 700)
        
        # メインレイアウト
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # ヘッダー部分
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        # タイトル
        title_label = QLabel("操作説明")
        title_label.setFont(QFont("", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # HTML表示用ブラウザ
        self.help_browser = QTextBrowser()
        self.help_browser.setOpenExternalLinks(False)
        self.help_browser.setStyleSheet("""
            QTextBrowser {
                border: none;
                background-color: white;
                padding: 10px;
            }
        """)
        
        # フッター部分
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(15, 10, 15, 15)
        
        footer_info = QLabel("H で表示/非表示の切り替えができます")
        footer_info.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        
        footer_layout.addWidget(footer_info)
        footer_layout.addStretch()
        
        # レイアウトに追加
        layout.addLayout(header_layout)
        layout.addWidget(self.help_browser, 1)
        layout.addLayout(footer_layout)
        
        # ダイアログのスタイル
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
            }
        """)
    
    def load_help_content(self):
        """ヘルプHTMLを読み込む"""
        try:
            # HTMLファイルパスを取得
            current_dir = Path(__file__).parent
            html_file = current_dir / "operation_instructions.html"
            
            if html_file.exists():
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                self.help_browser.setHtml(html_content)
            else:
                # ファイルが見つからない場合のフォールバック
                self.help_browser.setHtml(self.get_fallback_content())
                
        except Exception as e:
            # エラー時のフォールバック
            self.help_browser.setHtml(f"""
                <div style="padding: 20px; color: #e74c3c;">
                <h2>エラー</h2>
                <p>操作説明の読み込みに失敗しました: {str(e)}</p>
                <p>operation_instructions.html ファイルが見つからないか、読み込みできません。</p>
                </div>
            """)
    
    def get_fallback_content(self):
        """ファイルが見つからない場合の簡易ヘルプ"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {
                    font-family: "Yu Gothic", "Meiryo", sans-serif;
                    margin: 20px;
                    background: white;
                    color: #333;
                    line-height: 1.6;
                }
                h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                h2 { color: #2980b9; margin-top: 25px; }
                .key {
                    background: #34495e; color: white; padding: 2px 6px;
                    border-radius: 3px; font-family: monospace; font-size: 12px;
                }
                table { border-collapse: collapse; width: 100%; margin: 15px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background: #f2f2f2; font-weight: bold; }
                .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>TTSスタジオ 操作説明</h1>
            
            <div class="warning">
                <strong>注意:</strong> operation_instructions.html ファイルが見つかりません。<br>
                詳細な操作説明を表示するには、HTMLファイルを適切な場所に配置してください。
            </div>
            
            <h2>基本ショートカット</h2>
            <table>
                <tr><th>ショートカット</th><th>機能</th></tr>
                <tr><td><span class="key">F</span></td><td>ファイルメニューを開く</td></tr>
                <tr><td><span class="key">H</span></td><td>この説明を表示/非表示</td></tr>
                <tr><td><span class="key">Ctrl+D</span></td><td>テキストをリセット</td></tr>
                <tr><td><span class="key">Ctrl+P</span></td><td>選択中のテキストを再生</td></tr>
                <tr><td><span class="key">Ctrl+R</span></td><td>テキストを連続再生</td></tr>
                <tr><td><span class="key">Ctrl+S</span></td><td>個別保存</td></tr>
                <tr><td><span class="key">Ctrl+Shift+S</span></td><td>連続保存</td></tr>
                <tr><td><span class="key">Ctrl+T</span></td><td>リップシンクテストを開始</td></tr>
                <tr><td><span class="key">Ctrl+Z</span></td><td>設定/テキストのUndo</td></tr>
                <tr><td><span class="key">Ctrl+Y</span></td><td>設定/テキストのRedo</td></tr>
            </table>
            
            <h2>基本的な使い方</h2>
            <ol>
                <li>テキストを入力</li>
                <li>★タブで全体的なパラメータを設定</li>
                <li>必要に応じて個別タブで微調整</li>
                <li>再生で確認</li>
                <li>保存</li>
            </ol>
        </body>
        </html>
        """
    
    def keyPressEvent(self, event):
        """キー押下イベント"""
        # H で閉じる
        if (event.key() == Qt.Key.Key_H and
            event.modifiers() == Qt.KeyboardModifier.NoModifier):
            self.close()
        # Escape でも閉じる
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)