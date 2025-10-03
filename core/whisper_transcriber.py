import numpy as np
from pathlib import Path
from typing import Optional, Tuple
import traceback

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    print("⚠️ faster-whisper が利用できません。文字起こし機能は無効です。")
    print("   インストール: pip install faster-whisper")

class WhisperTranscriber:
    """faster-whisperを使った音声文字起こしエンジン
    
    WAVファイルから日本語テキストを自動抽出（精度改善版）
    """
    
    def __init__(self, model_size: str = "medium", device: str = "cuda"):
        """初期化
        
        Args:
            model_size: モデルサイズ (tiny/base/small/medium/large)
            device: デバイス (cuda/cpu)
        """
        self.is_available = FASTER_WHISPER_AVAILABLE
        self.model = None
        self.model_size = model_size
        self.device = device
        
        # 固有名詞・専門用語の修正辞書
        self.correction_dict = {
            '零音ほのか': 'れいねほのか',
            '零音': 'れいね',
        }
        
        if self.is_available:
            self._initialize_model()
        else:
            print("❌ WhisperTranscriber: faster-whisperがインストールされていません")
    
    def _initialize_model(self):
        """モデル初期化"""
        try:
            import torch
            
            # GPUが使えない場合はCPUに切り替え
            if self.device == "cuda" and not torch.cuda.is_available():
                print("⚠️ CUDA利用不可、CPUモードに切り替えます")
                self.device = "cpu"
                compute_type = "int8"
            else:
                compute_type = "float16" if self.device == "cuda" else "int8"
            
            print(f"🔄 Whisperモデル初期化中: {self.model_size} ({self.device}, {compute_type})")
            
            # faster-whisperモデル読み込み
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=compute_type,
                download_root=None  # デフォルトのキャッシュディレクトリを使用
            )
            
            print(f"✅ Whisperモデル初期化完了: {self.model_size}")
            
        except Exception as e:
            print(f"❌ Whisperモデル初期化エラー: {e}")
            traceback.print_exc()
            self.is_available = False
            self.model = None
    
    def transcribe_wav(self, wav_path: str, language: str = "ja", 
                      initial_prompt: str = None) -> Tuple[bool, str, list]:
        """WAVファイルから文字起こし（精度改善版）
        
        Args:
            wav_path: WAVファイルパス
            language: 言語コード (ja/en/auto)
            initial_prompt: 認識精度向上のためのヒント文（固有名詞など）
        
        Returns:
            (成功フラグ, 文字起こしテキスト, セグメントリスト)
        """
        if not self.is_available or self.model is None:
            return False, "❌ faster-whisperが利用できません", []
        
        try:
            path = Path(wav_path)
            if not path.exists():
                return False, f"❌ ファイルが見つかりません: {wav_path}", []
            
            print(f"🎤 文字起こし開始: {path.name}")
            print(f"   モデル: {self.model_size}, デバイス: {self.device}, 言語: {language}")
            
            if initial_prompt is None:
                initial_prompt = "零音ほのか, 修行"
            
            if initial_prompt:
                print(f"   ヒント: {initial_prompt}")
            else:
                print(f"   ヒント: なし")
            
            # faster-whisperで文字起こし実行（キャラ名ヒント付き）
            segments, info = self.model.transcribe(
                str(wav_path),
                language=language if language != "auto" else None,
                beam_size=5,
                initial_prompt=initial_prompt,  # キャラ名をヒントとして使用
                vad_filter=True,  # 無音部分を自動検出
                vad_parameters=dict(
                    min_silence_duration_ms=300,  # 無音判定を少し厳しく
                    speech_pad_ms=200,  # パディングを減らす
                    threshold=0.5  # 音声検出の閾値
                )
            )
            
            # 検出された言語情報
            detected_language = info.language
            language_probability = info.language_probability
            print(f"   検出言語: {detected_language} (確率: {language_probability:.2%})")
            
            # セグメントを結合してテキスト生成 + セグメントデータを保存
            full_text = ""
            segment_count = 0
            segment_list = []  # 🆕 タイムスタンプ付きセグメントリスト
            
            for segment in segments:
                full_text += segment.text
                segment_count += 1
                
                # 🆕 セグメント情報を保存
                segment_list.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text.strip()
                })
                
                # デバッグ出力（最初の3セグメントのみ）
                if segment_count <= 3:
                    print(f"   [{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")
            
            # 結果整形
            full_text = full_text.strip()
            
            if not full_text:
                return False, "⚠️ テキストを検出できませんでした", []
            
            # 🆕 後処理：固有名詞・専門用語の修正
            corrected_text = self._post_process_text(full_text)
            
            if corrected_text != full_text:
                print(f"   📝 修正前: {full_text}")
                print(f"   ✅ 修正後: {corrected_text}")
            
            print(f"✅ 文字起こし完了: {len(corrected_text)}文字, {segment_count}セグメント")
            
            # 🆕 セグメントリストも返す（タプルの3番目として）
            return True, corrected_text, segment_list
            
        except Exception as e:
            error_msg = f"❌ 文字起こしエラー: {e}"
            print(error_msg)
            traceback.print_exc()
            return False, error_msg, []
    
    def _post_process_text(self, text: str) -> str:
        """文字起こし結果の後処理（固有名詞・専門用語の修正）
        
        Args:
            text: 元のテキスト
            
        Returns:
            修正後のテキスト
        """
        corrected = text
        
        # 修正辞書を適用
        for wrong, correct in self.correction_dict.items():
            if wrong in corrected:
                print(f"      🔧 '{wrong}' → '{correct}'")
                corrected = corrected.replace(wrong, correct)
        
        return corrected
    
    def save_transcription_to_file(self, segments: list, output_path: str,
                                  include_timestamps: bool = True, 
                                  append_mode: bool = False,
                                  file_name: str = None) -> bool:
        """文字起こし結果をファイルに保存
        
        Args:
            segments: セグメントリスト
            output_path: 出力ファイルパス
            include_timestamps: タイムスタンプを含めるか
            append_mode: 追記モード（True）か上書きモード（False）
            file_name: 元ファイル名（追記モード時のヘッダー用）
            
        Returns:
            成功フラグ
        """
        try:
            mode = 'a' if append_mode else 'w'  # 🆕 追記 or 上書き
            
            with open(output_path, mode, encoding='utf-8') as f:
                # 🆕 追記モードの場合、ヘッダーを追加
                if append_mode and file_name:
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"\n{'='*60}\n")
                    f.write(f"=== {file_name} ({timestamp}) ===\n")
                    f.write(f"{'='*60}\n")
                
                if include_timestamps:
                    # タイムスタンプ付き形式
                    for segment in segments:
                        start_time = self._format_timestamp(segment['start'])
                        end_time = self._format_timestamp(segment['end'])
                        text = segment['text']
                        f.write(f"[{start_time} - {end_time}] {text}\n")
                else:
                    # テキストのみ
                    for segment in segments:
                        f.write(f"{segment['text']}\n")
                
                # 🆕 追記モードの場合、セクション終わりに空行
                if append_mode:
                    f.write("\n")
            
            print(f"✅ ファイル保存完了: {output_path} ({'追記' if append_mode else '新規'})")
            return True
            
        except Exception as e:
            print(f"❌ ファイル保存エラー: {e}")
            traceback.print_exc()
            return False
    
    def _format_timestamp(self, seconds: float) -> str:
        """秒数をタイムスタンプ形式に変換（HH:MM:SS.mmm）
        
        Args:
            seconds: 秒数
            
        Returns:
            タイムスタンプ文字列
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


    def add_correction(self, wrong: str, correct: str):
        """修正辞書に新しいエントリを追加
        
        Args:
            wrong: 誤認識される文字列
            correct: 正しい文字列
        """
        self.correction_dict[wrong] = correct
        print(f"✅ 修正辞書に追加: '{wrong}' → '{correct}'")
    
    def transcribe_audio_data(self, audio_data: np.ndarray, sample_rate: int, 
                             language: str = "ja", 
                             initial_prompt: str = None) -> Tuple[bool, str]:
        """音声データから直接文字起こし（numpy配列対応）
        
        Args:
            audio_data: 音声データ (float32, モノラル)
            sample_rate: サンプルレート
            language: 言語コード
            initial_prompt: 認識精度向上のためのヒント文
        
        Returns:
            (成功フラグ, 文字起こしテキスト)
        """
        if not self.is_available or self.model is None:
            return False, "❌ faster-whisperが利用できません"
        
        try:
            import tempfile
            import soundfile as sf
            
            # 一時WAVファイルに保存
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                
                # soundfileで保存
                sf.write(tmp_path, audio_data, sample_rate, format='WAV', subtype='PCM_16')
                
                # 文字起こし実行
                success, text = self.transcribe_wav(tmp_path, language, initial_prompt)
                
                # 一時ファイル削除
                Path(tmp_path).unlink(missing_ok=True)
                
                return success, text
            
        except Exception as e:
            error_msg = f"❌ 音声データ文字起こしエラー: {e}"
            print(error_msg)
            traceback.print_exc()
            return False, error_msg
    
    def is_ready(self) -> bool:
        """文字起こし機能が利用可能か"""
        return self.is_available and self.model is not None
    
    def get_model_info(self) -> dict:
        """モデル情報を取得"""
        return {
            'available': self.is_available,
            'model_size': self.model_size,
            'device': self.device,
            'model_loaded': self.model is not None,
            'correction_dict_size': len(self.correction_dict)
        }
    
    def change_model(self, model_size: str):
        """モデルサイズを変更
        
        Args:
            model_size: 新しいモデルサイズ (tiny/base/small/medium/large)
        """
        if not self.is_available:
            print("❌ faster-whisper が利用できません")
            return False
        
        try:
            print(f"🔄 モデル変更: {self.model_size} -> {model_size}")
            
            # 既存モデルを破棄
            if self.model:
                del self.model
                self.model = None
            
            self.model_size = model_size
            self._initialize_model()
            
            return self.model is not None
            
        except Exception as e:
            print(f"❌ モデル変更エラー: {e}")
            return False


# モジュールレベルでのテスト
if __name__ == "__main__":
    print("=== WhisperTranscriber テスト ===")
    
    transcriber = WhisperTranscriber(model_size="small", device="cuda")
    
    if transcriber.is_ready():
        print("✅ 初期化成功")
        print(f"モデル情報: {transcriber.get_model_info()}")
    else:
        print("❌ 初期化失敗")