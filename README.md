tts_studio/
├── main.py                          # 変更なし
├── model_history.json              # 変更なし
├── ui/
│   ├── __init__.py                  # 変更なし
│   ├── main_window.py               # 🔄 修正必要（TabbedEmotionControl → TabbedAudioControl）
│   ├── tabbed_emotion_control.py    # 変更なし（そのまま使用）
│   ├── audio_cleaner_control.py     # 🆕 新規作成（上記アーティファクト）
│   ├── tabbed_audio_control.py      # 🆕 新規作成（上記アーティファクト）
│   ├── multi_text.py               # 変更なし
│   ├── keyboard_shortcuts.py       # 変更なし
│   ├── sliding_menu.py             # 変更なし
│   ├── help_dialog.py              # 変更なし
│   ├── model_history.py            # 変更なし
│   ├── model_loader.py             # 変更なし
│   └── operation_instructions.html # 変更なし
├── core/
│   ├── __init__.py                 # 変更なし
│   ├── tts_engine.py               # 🔄 後で修正（クリーナー統合時）
│   ├── model_manager.py            # 変更なし
│   └── audio_processor.py          # 🆕 新規作成（後で）
└── utils/
    ├── __init__.py                 # 変更なし
    └── file_utils.py               # 変更なし