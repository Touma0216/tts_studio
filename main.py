import os
import sys

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

def main():
    print("TTS_Studio起動中...")
    """メイン関数"""
    app = QApplication(sys.argv)
    
    # アプリケーション情報
    app.setApplicationName("TTSスタジオ")
    app.setApplicationVersion("1.0.0")
    
    # メインウィンドウ作成・表示
    window = TTSStudioMainWindow()
    window.show()
    
    # イベントループ開始
    sys.exit(app.exec())

if __name__ == "__main__":
    main()