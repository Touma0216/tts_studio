tts_studio/
├── main.py                           # アプリケーションエントリーポイント
├── model_history.json                # AIモデル履歴データ
├── user_settings.json                # ユーザー設定ファイル
├── image_history.json                # 画像履歴データ
├── live2d_history.json               # Live2Dモデル履歴データ
├── animations/                       # アニメーションJSONファイル
│   ├── preset_look_around.json       # サンプルアニメーション
│   └── (その他のアニメーションファイル)
├── assets/                           # 静的アセット
│   └── live2d_dist/                  # Live2D環境
│       ├── index.html                # Live2Dビューアー用HTML
│       ├── main.js                   # Live2D制御JavaScript
│       ├── animation_player.js       # アニメーション再生エンジン
│       ├── lip_sync/                 # リップシンク専用ディレクトリ
│       │   ├── phoneme_classifier.js # 音素分類・予測エンジン
│       │   ├── audio_analyzer.js     # リアルタイム音声解析
│       │   ├── lip_sync_controller.js# Live2D統合制御
│       │   └── models/               # 音素マッピングデータ
│       │       └── phoneme_model.json# 音素→Live2Dパラメータマッピング
│       ├── modeling/                 # モデリング制御ディレクトリ
│       │   ├── modeling_controller.js# メイン制御
│       │   ├── drag_controller.js    # ドラッグ操作
│       │   └── preset_manager.js     # モーション/表情管理
│       └── libs/
│           └── node_modules/
│               ├── pixi.js/
│               │   └── dist/
│               │       └── pixi.mjs  # PixiJS v7コアライブラリ
│               └── pixi-live2d-display-lipsyncpatch/
│                   └── dist/
│                       └── index.es.js # Live2D統合ライブラリ
├── core/                             # コア機能モジュール
│   ├── __init__.py                   # パッケージ初期化
│   ├── audio_analyzer.py             # 音声品質解析エンジン
│   ├── audio_processor.py            # 音声クリーニング・処理エンジン
│   ├── model_manager.py              # AIモデル管理システム
│   ├── audio_effects_processor.py    # 音声エフェクト処理エンジン
│   ├── tts_engine.py                 # Style-Bert-VITS2音声合成エンジン
│   ├── image_manager.py              # 画像履歴・UI設定管理システム
│   ├── live2d_manager.py             # Live2Dモデル管理システム
│   ├── animation_manager.py          # アニメーション管理システム
│   ├── lip_sync_engine.py            # メインリップシンクエンジン
│   ├── phoneme_analyzer.py           # 音素解析・最適化エンジン
│   ├── wav_player.py                 # WAV再生エンジン
│   ├── whisper_transcriber.py        # 文字起こしエンジン
│   └── audio_realtime_processor.py   # リアルタイム音声処理
└── ui/                               # ユーザーインターフェース
    ├── __init__.py                   # パッケージ初期化
    ├── audio_cleaner_control.py      # 音声クリーナー制御UI
    ├── audio_effects_control.py      # 音声エフェクト制御UI
    ├── character_display.py          # キャラクター表示・Live2D統合UI
    ├── help_dialog.py                # ヘルプ・操作説明ダイアログ
    ├── image_history.py              # 画像履歴選択・管理ダイアログ
    ├── live2d_history.py             # Live2D履歴選択・管理ダイアログ
    ├── keyboard_shortcuts.py         # キーボードショートカット管理
    ├── main_window.py                # メインウィンドウ・アプリケーション制御
    ├── model_history.py              # モデル履歴表示・管理UI
    ├── model_loader.py               # AIモデル読み込みダイアログ
    ├── multi_text.py                 # 複数テキスト入力・管理UI
    ├── operation_instructions.html   # 操作説明HTMLファイル
    ├── sliding_menu.py               # スライド式ファイルメニューUI
    ├── tabbed_audio_control.py       # タブ式音声制御統合UI
    ├── tabbed_emotion_control.py     # タブ式感情・パラメータ制御UI
    ├── tabbed_lip_sync_control.py    # タブ式リップシンク制御UI
    ├── tabbed_modeling_control.py    # タブ式モデリング制御UI
    ├── wav_playback_control.py       # タブ式wav再生制御UI
    └── tts_worker.py                 # TTS生成・リップシンク処理用バックグラウンドワーカー