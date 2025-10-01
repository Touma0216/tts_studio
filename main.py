import os
os.environ['QTWEBENGINE_REMOTE_DEBUGGING'] = '8080'
import os
import sys
import threading
import http.server
import socketserver
import urllib.parse
from functools import partial
import logging
import warnings
from PyQt6.QtWidgets import QApplication
from ui.main_window import TTSStudioMainWindow

# ログ・警告の無効化
logging.disable(logging.CRITICAL)
logging.getLogger().disabled = True
warnings.filterwarnings("ignore")
os.environ["PYTHONPATH"] = os.pathsep.join([os.environ.get("PYTHONPATH", ""), "."])
os.environ["LOGURU_LEVEL"] = "CRITICAL"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

class Live2DServerManager:
    """Live2D配信用ローカルHTTPサーバーを管理するクラス（Python内蔵版）"""
    def __init__(self):
        self.httpd = None
        self.server_thread = None
        self.host = "127.0.0.1"
        self.port = 0
        self.server_url = None
        self.served_directories = {}
        
        sdk_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "live2d_dist")
        if os.path.exists(sdk_path):
            self.add_directory("/", sdk_path)

    def _get_free_port(self):
        with socketserver.TCPServer((self.host, 0), http.server.SimpleHTTPRequestHandler) as s:
            return s.server_address[1]

    def add_directory(self, prefix, path):
        if not prefix.endswith('/'):
            prefix += '/'
        self.served_directories[prefix] = path
        print(f"✅ Serving '{path}' at URL prefix '{prefix}'")

    def _create_handler(self):
        class MultiDirectoryHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, served_directories=None, **kwargs):
                self.served_directories = served_directories
                super().__init__(*args, **kwargs)

            def do_GET(handler_self):
                path = urllib.parse.unquote(handler_self.path)
                
                # ルートパスへのアクセスをindex.htmlに変換
                if path == '/':
                    path = '/index.html'

                for prefix, directory in handler_self.served_directories.items():
                    if path.startswith(prefix):
                        local_path = path[len(prefix):]
                        # Windowsの絶対パスを正しく処理
                        file_path = os.path.join(directory, local_path.lstrip('/'))
                        
                        if os.path.exists(file_path):
                            if os.path.isfile(file_path):
                                handler_self.serve_file(file_path)
                                return
                            elif os.path.isdir(file_path):
                                handler_self.serve_directory(file_path, path)
                                return
                
                handler_self.send_response(404)
                handler_self.end_headers()
                handler_self.wfile.write(b'File not found')
                
            def serve_file(self, file_path):
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-type', self.guess_type(file_path))
                    self.send_header('Content-Length', len(content))
                    self.end_headers()
                    self.wfile.write(content)
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(f'Error: {e}'.encode())
            
            def serve_directory(self, dir_path, url_path):
                try:
                    files = os.listdir(dir_path)
                    html = f'<h1>Directory: {url_path}</h1><ul>'
                    for file in files:
                        html += f'<li><a href="{url_path.rstrip("/")}/{file}">{file}</a></li>'
                    html += '</ul>'
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(html.encode())
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(f'Error: {e}'.encode())
                    
        return partial(MultiDirectoryHandler, served_directories=self.served_directories)

    def start_server(self):
        if not self.served_directories:
            print("❌ No directories to serve.")
            return None
        try:
            self.port = self._get_free_port()
            handler = self._create_handler()
            socketserver.TCPServer.allow_reuse_address = True
            self.httpd = socketserver.TCPServer((self.host, self.port), handler)
            self.server_url = f"http://{self.host}:{self.port}/"
            print(f"🚀 Starting Live2D server on {self.server_url}")
            self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.server_thread.start()
            return self.server_url
        except Exception as e:
            print(f"❌ Live2D server startup failed: {e}")
            return None

    def stop_server(self):
        if self.httpd:
            print("🛑 Stopping Live2D server...")
            self.httpd.shutdown()
            self.httpd.server_close()
            print("✅ Live2D server stopped.")
            self.httpd = None

live2d_manager = Live2DServerManager()

def main():
    print("TTS_Studio起動中...")
    live2d_url = live2d_manager.start_server()
    app = QApplication(sys.argv)
    app.setApplicationName("TTSスタジオ")
    app.setApplicationVersion("1.0.0")
    window = TTSStudioMainWindow(live2d_url=live2d_url, live2d_server_manager=live2d_manager)
    
    # 🆕 起動時に最大化（ウィンドウ枠あり）
    window.showMaximized()
    
    # 👈 真のフルスクリーン（ウィンドウ枠なし）にしたい場合は下のコメントアウトを外す
    # window.showFullScreen()
    
    app.aboutToQuit.connect(live2d_manager.stop_server)
    sys.exit(app.exec())
    

if __name__ == "__main__":
    main()