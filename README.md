tts_studio/
├── main.py              # メインエントリーポイント
├── model_history.json   # モデルの履歴
├── ui/
│   ├── __init__.py
│   ├── main_window.py   # メインウィンドウ
│   ├── sliding_menu.py   # スライドアニメ
│   ├── help_dialog.py   # 操作説明のメニュー
│   ├── tabbed_emotion_control.py # 感情コントロール
│   ├── keyboard_shortcuts.py # キーボードショートカット
│   ├── multi_text.py # 複数テキスト対応
│   ├── model_history.py # モデル履歴保持
│   ├── model_loader.py  # モデル選択・読み込みUI
│   └── operation_instructions.html  # 操作説明
├── core/
│   ├── __init__.py
│   ├── tts_engine.py    # TTS処理
│   └── model_manager.py # モデル管理
└── utils/
    ├── __init__.py
    └── file_utils.py    # ファイル関連ユーティリティ