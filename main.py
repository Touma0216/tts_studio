import os
import sys
import threading
import http.server
import socketserver
from functools import partial # ★修正箇所: import を追加

# ログ関連の環境変数設定
os.environ["PYTHONPATH"] = os.pathsep.join([os.environ.get("PYTHONPATH", ""), "."])
os.environ["LOGURU_LEVEL"] = "CRITICAL"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

import logging
import warnings
from PyQt6.QtWidgets import QApplication

# ログ・警告の無効化
logging.disable(logging.CRITICAL)
logging.getLogger().disabled = True
warnings.filterwarnings("ignore")

from ui.main_window import TTSStudioMainWindow

# Live2DServerManagerをPython内蔵サーバー方式に完全に書き換え
class Live2DServerManager:
    """Live2D配信用ローカルHTTPサーバーを管理するクラス（Python内蔵版）"""

    def __init__(self):
        self.httpd = None
        self.server_thread = None
        self.host = "127.0.0.1"
        self.port = 0  # 0を指定すると空きポートを自動選択
        self.server_url = None
        
        # アプリケーションのルートからの相対パスでLive2D SDKの場所を指定
        self.sdk_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "live2d_dist")

    def _get_free_port(self):
        """利用可能なポートを自動で取得する"""
        with socketserver.TCPServer((self.host, 0), http.server.SimpleHTTPRequestHandler) as s:
            return s.server_address[1]

    # ★修正箇所: このメソッド全体を新しい安全なコードに置き換え
    def start_server(self):
        """サーバーをバックグラウンドスレッドで起動する"""
        if not os.path.exists(self.sdk_path):
            print(f"❌ Live2D SDK path not found: {self.sdk_path}")
            return None

        try:
            self.port = self._get_free_port()
            
            # functools.partialを使って、リクエストハンドラに公開ディレクトリを直接渡す
            handler = partial(http.server.SimpleHTTPRequestHandler, directory=self.sdk_path)

            socketserver.TCPServer.allow_reuse_address = True
            self.httpd = socketserver.TCPServer((self.host, self.port), handler)
            
            self.server_url = f"http://{self.host}:{self.port}"
            print(f"🚀 Starting Live2D server on {self.server_url}")
            
            # daemon=Trueにすることで、メインスレッドが終了すると自動的に終了する
            self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.server_thread.start()
            
            return self.server_url

        except Exception as e:
            print(f"❌ Live2D server startup failed: {e}")
            return None

    def stop_server(self):
        """HTTPサーバーを安全に停止する"""
        if self.httpd:
            print("🛑 Stopping Live2D server...")
            self.httpd.shutdown()
            self.httpd.server_close()
            print("✅ Live2D server stopped.")
            self.httpd = None

# グローバルなサーバーマネージャーのインスタンスを作成
live2d_manager = Live2DServerManager()

def main():
    print("TTS_Studio起動中...")
    
    # Live2Dサーバーを起動し、URLを取得
    live2d_url = live2d_manager.start_server()
    
    app = QApplication(sys.argv)
    
    app.setApplicationName("TTSスタジオ")
    app.setApplicationVersion("1.0.0")
    
    # MainWindowにlive2d_urlを渡す
    window = TTSStudioMainWindow(live2d_url=live2d_url)
    
    window.show()
    
    # アプリケーション終了時にサーバーを停止
    app.aboutToQuit.connect(live2d_manager.stop_server)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()