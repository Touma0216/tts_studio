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
    
    WAVファイルから日本語テキストを自動抽出
    """
    
    def __init__(self, model_size: str = "small", device: str = "cuda"):
        """初期化
        
        Args:
            model_size: モデルサイズ (tiny/base/small/medium/large)
            device: デバイス (cuda/cpu)
        """
        self.is_available = FASTER_WHISPER_AVAILABLE
        self.model = None
        self.model_size = model_size
        self.device = device
        
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
    
    def transcribe_wav(self, wav_path: str, language: str = "ja") -> Tuple[bool, str]:
        """WAVファイルから文字起こし
        
        Args:
            wav_path: WAVファイルパス
            language: 言語コード (ja/en/auto)
        
        Returns:
            (成功フラグ, 文字起こしテキスト)
        """
        if not self.is_available or self.model is None:
            return False, "❌ faster-whisperが利用できません"
        
        try:
            path = Path(wav_path)
            if not path.exists():
                return False, f"❌ ファイルが見つかりません: {wav_path}"
            
            print(f"🎤 文字起こし開始: {path.name}")
            print(f"   モデル: {self.model_size}, デバイス: {self.device}, 言語: {language}")
            
            # faster-whisperで文字起こし実行
            segments, info = self.model.transcribe(
                str(wav_path),
                language=language if language != "auto" else None,
                beam_size=5,
                vad_filter=True,  # 無音部分を自動検出
                vad_parameters=dict(
                    min_silence_duration_ms=500,  # 最小無音時間
                    speech_pad_ms=400  # 発話前後のパディング
                )
            )
            
            # 検出された言語情報
            detected_language = info.language
            language_probability = info.language_probability
            print(f"   検出言語: {detected_language} (確率: {language_probability:.2%})")
            
            # セグメントを結合してテキスト生成
            full_text = ""
            segment_count = 0
            
            for segment in segments:
                full_text += segment.text
                segment_count += 1
                
                # デバッグ出力（最初の3セグメントのみ）
                if segment_count <= 3:
                    print(f"   [{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")
            
            # 結果整形
            full_text = full_text.strip()
            
            if not full_text:
                return False, "⚠️ テキストを検出できませんでした"
            
            print(f"✅ 文字起こし完了: {len(full_text)}文字, {segment_count}セグメント")
            print(f"   テキスト: {full_text[:100]}{'...' if len(full_text) > 100 else ''}")
            
            return True, full_text
            
        except Exception as e:
            error_msg = f"❌ 文字起こしエラー: {e}"
            print(error_msg)
            traceback.print_exc()
            return False, error_msg
    
    def transcribe_audio_data(self, audio_data: np.ndarray, sample_rate: int, 
                             language: str = "ja") -> Tuple[bool, str]:
        """音声データから直接文字起こし（numpy配列対応）
        
        Args:
            audio_data: 音声データ (float32, モノラル)
            sample_rate: サンプルレート
            language: 言語コード
        
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
                success, text = self.transcribe_wav(tmp_path, language)
                
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
            'model_loaded': self.model is not None
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