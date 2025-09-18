tts_studio-main/
├── main.py                           # アプリケーションエントリーポイント
├── model_history.json                # モデル履歴データ（自動生成）
├── user_settings.json                # ユーザー設定ファイル（自動生成）
├── image_history.json                # 画像履歴データ（自動生成）
├── core/                             # コア機能モジュール
│   ├── __init__.py                   # パッケージ初期化
│   ├── audio_analyzer.py             # 音声品質解析エンジン
│   ├── audio_processor.py            # 音声クリーニング・処理エンジン
│   ├── model_manager.py              # AIモデル管理システム
│   ├── audio_effects_processor.py    # 音声エフェクト処理エンジン
│   ├── tts_engine.py                 # Style-Bert-VITS2音声合成エンジン
│   └── image_manager.py              # 画像履歴・UI設定管理システム
└── ui/                               # ユーザーインターフェース
    ├── __init__.py                   # パッケージ初期化
    ├── audio_cleaner_control.py      # 音声クリーナー制御UI
    ├── audio_effects_control.py      # 音声エフェクト制御UI（ロボット音声・環境音等）
    ├── character_display.py          # キャラクター表示・画像管理UI
    ├── help_dialog.py                # ヘルプ・操作説明ダイアログ
    ├── image_history.py              # 画像履歴選択・管理ダイアログ
    ├── keyboard_shortcuts.py         # キーボードショートカット管理
    ├── main_window.py                # メインウィンドウ・アプリケーション制御
    ├── model_history.py              # モデル履歴表示・管理UI
    ├── model_loader.py               # AIモデル読み込みダイアログ
    ├── multi_text.py                 # 複数テキスト入力・管理UI
    ├── operation_instructions.html   # 操作説明HTMLファイル
    ├── sliding_menu.py               # スライド式ファイルメニューUI
    ├── tabbed_audio_control.py       # タブ式音声制御統合UI
    └── tabbed_emotion_control.py     # タブ式感情・パラメータ制御UI