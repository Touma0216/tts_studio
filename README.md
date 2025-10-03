# TTS Studio

PyQt6 ベースのデスクトップアプリケーションで、Style-Bert-VITS2 を中心とした高度な音声合成ワークフローと、Live2D キャラクター連携を一体化させた制作スタジオです。テキスト入力から音声生成、クリーンアップ、エフェクト加工、モデル管理、Live2D での可視化・リップシンクまでを統合し、ストリーミング配信や動画制作の現場でそのまま使えるクオリティを目指しています。

## 主な機能

### 音声合成パイプライン
- **Style-Bert-VITS2 エンジン統合**: `core/tts_engine.py` を通じて GPU 最適化された Style-Bert-VITS2 モデルを読み込み、感情・話速・ノイズなどのパラメータを即時調整可能。
- **長文テキスト処理**: `core/tts_long_processor.py` によるチャンク分割とバッチ合成で長尺原稿でも破綻しないワークフローを提供。
- **マルチテキスト UI**: `ui/multi_text.py` で複数行の原稿を整理し、行単位のプレビュー再生や連続書き出しをサポート。

### 音声後処理と解析
- **プロ品質のクリーンアップ**: `core/audio_processor.py` と `core/audio_effects_processor.py` がノイズゲート、周波数除去、ローパス、リミッタなどを段階的に適用し、生成音声の歪みや「じー」ノイズを抑制。
- **音質解析フィードバック**: `core/audio_analyzer.py` がピーク/RMS レベルやスペクトルを解析し、処理結果を可視化するためのデータを生成。
- **リアルタイム処理**: `core/audio_realtime_processor.py` により生成音声と同期したエフェクト適用やメータリングを実現。

### Live2D & リップシンク統合
- **組み込み Live2D サーバー**: `main.py` で PyQt アプリ起動と同時にローカル HTTP サーバーを立ち上げ、`assets/live2d_dist` に含まれるビューアーを自動配信。
- **Live2D モデル管理**: `core/live2d_manager.py` と `ui/character_display.py` がモデル履歴、ドラッグ&ドロップ配置、ミニマップ操作、モーションプリセット、Live2D のズーム／ポジション制御を提供。
- **高度リップシンク**: `core/lip_sync_engine.py` と `assets/live2d_dist/lip_sync/` の Web コンポーネントが音素解析 (`core/phoneme_analyzer.py`) と連動し、Live2D パラメータへ高精度マッピング。
- **Live2D モデリング支援**: `ui/tabbed_modeling_control.py` と `assets/live2d_dist/modeling/` が表情プリセット、ドラッグ操作、物理演算の重み付けを GUI から制御。

### 作業効率化と管理
- **モデル・アセット履歴**: `model_history.json` / `image_history.json` / `live2d_history.json` を UI (`ui/model_history.py` など) から参照し、直近 20 件のアセットを素早く再読込。
- **音声書き出し管理**: `ui/tabbed_wav_export_control.py` と `core/wav_player.py` により、個別保存・連続保存・プレビュー再生をワンクリックで操作。
- **Whisper 文字起こし**: `core/whisper_transcriber.py` が OpenAI Whisper を使ったテキスト化を提供し、下書き原稿の準備を支援。
- **キーボードショートカット**: `ui/keyboard_shortcuts.py` が合成開始 (Ctrl+R) や一括保存 (Ctrl+Shift+S) などの操作を定義。
- **ヘルプ/チュートリアル**: `ui/help_dialog.py` と `ui/operation_instructions.html` がアプリ内で参照できる操作ガイドを提供。

## 技術スタック

| 分類 | 採用技術 |
| --- | --- |
| GUI | PyQt6 (Qt Widgets, QWebEngineView) |
| 音声合成 | PyTorch, Style-Bert-VITS2, NumPy, SciPy |
| 音声処理 | 自前アルゴリズム (ノイズゲート、スペクトラルクリーンアップ等)、リアルタイム分析 |
| 文字起こし | OpenAI Whisper (CUDA 最適化) |
| Live2D | PixiJS + pixi-live2d-display + カスタム lip-sync/modeling JS |
| サーバー | Python 標準ライブラリ (http.server, socketserver) によるローカル配信 |

## ディレクトリ構成 (抜粋)

```
tts_studio/
├── main.py                # アプリケーションエントリーポイント / Live2D サーバー
├── core/                  # 音声・モデル・Live2D のコアロジック
├── ui/                    # PyQt6 ベースの GUI コンポーネント
├── assets/live2d_dist/    # Live2D ビューアーとカスタム JS
├── animations/            # Live2D 用アニメーションプリセット
├── *_history.json         # 各種履歴データベース
└── user_settings.json     # 表示モードや Live2D 設定の永続化
```

## 動作環境

- Python 3.10 以上を推奨
- GPU (CUDA) 環境があると音声合成・Whisper が高速化
- 主要依存パッケージ
  - PyQt6 / PyQt6-WebEngine
  - torch / torchaudio
  - numpy / scipy
  - librosa, soundfile
  - openai-whisper
  - その他 `requirements.txt` (未同梱の場合は `pip install -r requirements.txt` を作成の上で利用)

## セットアップと起動

```bash
# 仮想環境の作成と依存関係インストール
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # もしくは各パッケージを個別インストール

# Style-Bert-VITS2 モデルと設定ファイルを用意し、アプリ内から読み込む

# アプリケーション起動
python main.py
```

初回起動時はメインウィンドウが最大化され、左側にテキスト・音声処理タブ、右側にキャラクター表示 (画像/Live2D) が表示されます。メニューまたはスライディングメニューからモデルや Live2D アセットを読み込んで制作を開始します。

## 推奨ワークフロー

1. **モデル読み込み**: `モデル読込` メニューから Style-Bert-VITS2 モデルファイルと設定を選択。
2. **テキスト入力**: Multi Text パネルにセリフやナレーションを複数行で入力し、行ごとのパラメータを調整。
3. **音声生成**: 行単位でプレビュー再生するか、Ctrl+R で連続再生。必要に応じてクリーンアップ・エフェクト・感情タブで微調整。
4. **Live2D 調整**: Live2D モデルを読み込み、モデリングタブでポーズやモーション、リップシンク重みを設定。
5. **書き出し**: WAV 書き出しタブから個別/連続保存。履歴から直近アセットに素早くアクセスして再利用。
6. **文字起こし** (任意): 既存音声を Whisper で取り込み、テキスト生成から TTS へのリライトに活用。

## ライセンスと注意事項

- 本リポジトリには Style-Bert-VITS2 や Live2D モデル本体は含まれていません。各ライセンスに従って別途取得してください。
- Live2D ビューアー (`assets/live2d_dist`) は PixiJS および pixi-live2d-display の配布条件に従います。
- OpenAI Whisper の利用には追加のモデルダウンロードが必要です。GPU メモリ使用量に注意してください。

## 貢献ガイドライン

1. Issues / Pull Request で変更点を議論してください。
2. コードスタイルは既存モジュールに倣い、日本語コメントで機能意図を明記します。
3. UI 変更時はスクリーンショットや簡単な操作説明を添付するとレビューが円滑です。

制作を楽しんでください！