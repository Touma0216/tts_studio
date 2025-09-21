import os
import sys
import subprocess
import threading
import time
import socket

# ログを完全に無効化（importより前に設定）
os.environ["PYTHONPATH"] = os.pathsep.join([os.environ.get("PYTHONPATH", ""), "."])
os.environ["LOGURU_LEVEL"] = "CRITICAL"  # loguru使用時
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # TensorFlow用
os.environ["TRANSFORMERS_VERBOSITY"] = "error"  # Transformers用

import logging
import warnings
from PyQt6.QtWidgets import QApplication

# 標準ログも無効化
logging.disable(logging.CRITICAL)
logging.getLogger().disabled = True

# 警告も無効化
warnings.filterwarnings("ignore")

# コンソール出力も抑制（最終手段）
class NullStream:
    def write(self, data):
        pass
    def flush(self):
        pass

# 一時的にstdoutをリダイレクト
original_stdout = sys.stdout
original_stderr = sys.stderr

# 新しいモジュールのインポート
from ui.main_window import TTSStudioMainWindow

class Live2DServerManager:
    """Live2Dサーバー自動管理クラス"""
    
    def __init__(self):
        self.server_process = None
        self.is_running = False
        self.demo_path = "F:/CubismSdkForWeb-5-r.4/Samples/TypeScript/Demo"
    
    def check_server_running(self, port=5000):
        """サーバーが動作中かチェック"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                return result == 0
        except:
            return False
    
    def start_server(self):
        """Live2Dサーバーを起動"""
        if self.check_server_running():
            print("✅ Live2D server already running on localhost:5000")
            self.is_running = True
            return True
        
        if not os.path.exists(self.demo_path):
            print(f"❌ Live2D Demo path not found: {self.demo_path}")
            return False
        
        def run_server():
            try:
                print("🚀 Starting Live2D server...")
                # npm run serve を別プロセスで実行
                self.server_process = subprocess.Popen(
                    ["npm", "run", "serve"],
                    cwd=self.demo_path,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                # サーバー起動を待機
                for i in range(30):  # 30秒まで待機
                    time.sleep(1)
                    if self.check_server_running():
                        print("✅ Live2D server started successfully")
                        self.is_running = True
                        return
                
                print("⚠️ Live2D server startup timeout")
                
            except Exception as e:
                print(f"❌ Live2D server startup failed: {e}")
        
        # バックグラウンドでサーバー起動
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        return True
    
    def stop_server(self):
        """Live2Dサーバーを停止"""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                print("✅ Live2D server stopped")
            except:
                try:
                    self.server_process.kill()
                    print("⚠️ Live2D server force killed")
                except:
                    pass
            finally:
                self.server_process = None
                self.is_running = False

# グローバルなサーバーマネージャー
live2d_manager = Live2DServerManager()

def main():
    print("TTS_Studio起動中...")
    """メイン関数"""
    
    # Live2Dサーバーを起動
    live2d_manager.start_server()
    
    app = QApplication(sys.argv)
    
    # アプリケーション情報
    app.setApplicationName("TTSスタジオ")
    app.setApplicationVersion("1.0.0")
    
    # メインウィンドウ作成・表示
    window = TTSStudioMainWindow()
    
    # Live2Dサーバー情報をウィンドウに渡す
    if hasattr(window, 'set_live2d_manager'):
        window.set_live2d_manager(live2d_manager)
    
    window.show()
    
    # アプリケーション終了時の処理
    def cleanup():
        print("🔄 Cleaning up...")
        live2d_manager.stop_server()
    
    app.aboutToQuit.connect(cleanup)
    
    try:
        # イベントループ開始
        result = app.exec()
    finally:
        cleanup()
        
    sys.exit(result)

if __name__ == "__main__":
    main()