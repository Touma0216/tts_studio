import torch
import numpy as np
from pathlib import Path
import traceback
import inspect
import logging
import json
from typing import List, Dict, Optional
from scipy.signal import butter, filtfilt, iirnotch
from scipy.ndimage import gaussian_filter1d
from scipy.fft import fft, ifft

# Style-Bert-VITS2のログを無効化
logging.getLogger("style_bert_vits2").setLevel(logging.ERROR)
logging.getLogger("bert_models").setLevel(logging.ERROR)  
logging.getLogger("tts_model").setLevel(logging.ERROR)
logging.getLogger("infer").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)

class TTSEngine:
    def __init__(self):
        self.model = None
        self.is_loaded = False
        self.model_info = {}
        self._use_autocast = torch.cuda.is_available()

        # core/tts_engine.py の default_params を修正
        self.default_params = {
            'style': 'Neutral',
            'style_weight': 1.0,
            'sdp_ratio': 0.5,    # 👈 0.02 → 0.25（元の値）
            'noise': 0.6,
            'noise_w': 0.8,        # 👈 0.02 → 0.25（元の値）
            'length_scale': 1.0
        }

        # 後処理を全部無効にする（問題切り分けのため）
        self.audio_processing = {
            'normalize': True,
            'target_peak_db': -9.0,        
            'remove_hum': True,           
            'remove_dc': True,
            'soft_limit': False,           # 👈 一時無効
            'limit_threshold': 0.95,
            'spectral_cleaning': False,    # 👈 一時無効
            'professional_gate': False,    # 👈 一時無効
            'frequency_cleanup': False,    
        }
        
        # 感情名マッピング
        self.emotion_mapping = {
            'fear': 'Fear', 'angry': 'Angry', 'disgust': 'Disgust',
            'happiness': 'Happy', 'happy': 'Happy', 'sadness': 'Sad',
            'sad': 'Sad', 'surprise': 'Surprise', 'neutral': 'Neutral',
            'Fear': 'Fear', 'Angry': 'Angry', 'Disgust': 'Disgust', 
            'Happy': 'Happy', 'Sad': 'Sad', 'Surprise': 'Surprise',
            'Neutral': 'Neutral',
        }
        self.long_processor = None
    
    def remove_dc_offset(self, audio):
        """DCオフセットを除去"""
        return audio - np.mean(audio)
    
    def professional_noise_gate(self, audio, sr):
        """プロ仕様ノイズゲート"""
        if len(audio) < 1024:
            return audio
            
        try:
            # RMSベースのより正確なゲート
            window_size = int(sr * 0.01)  # 10ms窓
            hop_size = window_size // 2
            
            # 全体のRMS計算
            total_rms = np.sqrt(np.mean(audio**2))
            
            # 厳しいゲート閾値（商用品質のため）
            gate_threshold = total_rms * 0.02  # 2%
            
            gated_audio = audio.copy()
            gate_applied = 0
            
            for i in range(0, len(audio) - window_size, hop_size):
                frame = audio[i:i+window_size]
                frame_rms = np.sqrt(np.mean(frame**2))
                
                if frame_rms < gate_threshold:
                    # 段階的減衰（完全ミュートではなく）
                    reduction = 0.005  # 0.5%まで減衰
                    gated_audio[i:i+window_size] *= reduction
                    gate_applied += 1
            
            gate_percentage = (gate_applied * hop_size / len(audio)) * 100
            print(f"🚪 プロ仕様ゲート: {gate_percentage:.1f}%処理, 閾値={gate_threshold:.6f}")
            
            return gated_audio
            
        except Exception as e:
            print(f"⚠️ ノイズゲートエラー: {e}")
            return audio
    
    def frequency_cleanup(self, audio, sr):
        """問題周波数の徹底清掃"""
        try:
            cleaned = audio.copy()
            nyquist = sr / 2
            
            # 1. 「じーー」音の原因となる持続性トーンを除去
            problem_frequencies = [
                # 低域の持続音
                50, 60, 100, 120, 150, 180, 200, 240, 300,
                # 中域の「じーー」音
                800, 1000, 1200, 1500, 1800, 2000, 2200, 2500,
                # 高域のデジタルノイズ
                3000, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000
            ]
            
            processed_count = 0
            for freq in problem_frequencies:
                if freq < nyquist * 0.95:
                    # 超狭帯域ノッチフィルタ
                    Q = 50  # 非常に鋭いフィルタ
                    b, a = iirnotch(freq, Q, sr)
                    cleaned = filtfilt(b, a, cleaned)
                    processed_count += 1
            
            print(f"🎯 周波数清掃: {processed_count}箇所処理")
            
            # 2. 6kHz以上の高周波カット（より積極的）
            cutoff = min(6000, nyquist * 0.8)
            cutoff_norm = cutoff / nyquist
            
            if cutoff_norm < 0.95:
                # 8次フィルタでより急峻に
                b, a = butter(8, cutoff_norm, btype='low')
                cleaned = filtfilt(b, a, cleaned)
                print(f"🔇 強力ローパス: {cutoff}Hz (8次)")
            
            return cleaned
            
        except Exception as e:
            print(f"⚠️ 周波数清掃エラー: {e}")
            return audio
    
    def spectral_cleaning(self, audio, sr):
        """高度スペクトラル清浄化（audio_processor.py風）"""
        try:
            if len(audio) < 2048:
                return audio
                
            # パラメータ
            frame_size = 2048
            hop_size = 512
            window = np.hanning(frame_size)
            
            # フレーム数計算
            num_frames = (len(audio) - frame_size) // hop_size + 1
            if num_frames <= 0:
                return audio
            
            # ノイズプロファイル推定（最初の5フレーム）
            noise_profile = self._estimate_noise_profile(audio, frame_size, hop_size, window)
            
            # 処理済み音声バッファ
            cleaned = np.zeros_like(audio)
            
            for i in range(num_frames):
                start = i * hop_size
                end = start + frame_size
                
                if end > len(audio):
                    break
                
                # フレーム抽出
                frame = audio[start:end] * window
                
                # FFT
                spectrum = fft(frame)
                magnitude = np.abs(spectrum)
                phase = np.angle(spectrum)
                
                # 積極的スペクトラルサブトラクション
                cleaned_magnitude = self._aggressive_spectral_subtraction(magnitude, noise_profile)
                
                # 逆FFT
                cleaned_spectrum = cleaned_magnitude * np.exp(1j * phase)
                cleaned_frame = np.real(ifft(cleaned_spectrum))
                
                # オーバーラップアド
                cleaned[start:end] += cleaned_frame * window
            
            print(f"🌊 スペクトラル清浄化: {num_frames}フレーム処理")
            return cleaned.astype(np.float32)
            
        except Exception as e:
            print(f"⚠️ スペクトラル清浄化エラー: {e}")
            return audio
    
    def _estimate_noise_profile(self, audio, frame_size, hop_size, window):
        """ノイズプロファイル推定"""
        noise_frames = min(5, (len(audio) - frame_size) // hop_size)
        
        if noise_frames <= 0:
            spectrum = np.abs(fft(audio[:frame_size] * window))
            return spectrum * 0.05  # 非常に控えめ
        
        noise_spectra = []
        for i in range(noise_frames):
            start = i * hop_size
            end = start + frame_size
            frame = audio[start:end] * window
            spectrum = np.abs(fft(frame))
            noise_spectra.append(spectrum)
        
        # より保守的なノイズプロファイル
        noise_profile = np.percentile(noise_spectra, 20, axis=0)  # 下位20%
        return noise_profile
    
    def _aggressive_spectral_subtraction(self, magnitude, noise_profile):
        """積極的スペクトラルサブトラクション"""
        # SNR計算
        snr = magnitude / (noise_profile + 1e-12)
        
        # 3段階の積極的サプレッション
        suppression = np.ones_like(snr)
        
        # 第1段階：中程度のノイズ
        mask1 = snr < 5.0
        suppression[mask1] = 0.3
        
        # 第2段階：強いノイズ
        mask2 = snr < 2.0
        suppression[mask2] = 0.1
        
        # 第3段階：極めて強いノイズ
        mask3 = snr < 1.2
        suppression[mask3] = 0.01
        
        # スムージング
        suppression = gaussian_filter1d(suppression, sigma=1.5)
        
        # 適用
        cleaned_magnitude = magnitude * suppression
        
        # 最小レベル制限
        min_magnitude = magnitude * 0.001  # 0.1%まで
        cleaned_magnitude = np.maximum(cleaned_magnitude, min_magnitude)
        
        return cleaned_magnitude
    
    def normalize_audio(self, audio, target_peak_db=-9.0):
        """音声正規化（保守的）"""
        audio = self.remove_dc_offset(audio)
        
        current_peak = np.max(np.abs(audio))
        if current_peak == 0:
            return audio
        
        target_peak_linear = 10 ** (target_peak_db / 20.0)
        scale_factor = target_peak_linear / current_peak
        normalized = audio * scale_factor
        
        print(f"🔊 音量正規化: {current_peak:.3f} -> {np.max(np.abs(normalized)):.3f}")
        return normalized
    
    def soft_limiter(self, audio, threshold=0.9):
        """ソフトリミッター（保守的）"""
        abs_audio = np.abs(audio)
        mask = abs_audio > threshold
        
        if np.any(mask):
            sign = np.sign(audio)
            limited = np.where(
                mask,
                sign * threshold * np.tanh(abs_audio / threshold),
                audio
            )
            
            clipped_samples = np.sum(mask)
            clip_rate = (clipped_samples / len(audio)) * 100
            print(f"🛡️ ソフトリミッター: {clip_rate:.2f}%処理")
            return limited
        
        return audio
    
    def process_audio(self, audio, sr):
        """総合音声処理（商用品質版）"""
        processed = audio.copy()
        
        # Float32変換
        if processed.dtype != np.float32:
            if processed.dtype == np.int16:
                processed = processed.astype(np.float32) / 32768.0
            elif processed.dtype == np.int32:
                processed = processed.astype(np.float32) / 2147483648.0
            else:
                processed = processed.astype(np.float32)
        
        original_peak = np.max(np.abs(processed))
        print(f"🎵 元音声ピーク: {original_peak:.6f}")
        
        # 1. DCオフセット除去
        if self.audio_processing['remove_dc']:
            processed = self.remove_dc_offset(processed)
        
        # 2. 周波数清掃（最優先）
        if self.audio_processing.get('frequency_cleanup', True):
            processed = self.frequency_cleanup(processed, sr)
        
        # 3. スペクトラル清浄化
        if self.audio_processing.get('spectral_cleaning', True):
            processed = self.spectral_cleaning(processed, sr)
        
        # 4. プロ仕様ノイズゲート
        if self.audio_processing.get('professional_gate', True):
            processed = self.professional_noise_gate(processed, sr)
        
        # 5. 音量正規化
        if self.audio_processing['normalize']:
            processed = self.normalize_audio(
                processed, 
                self.audio_processing['target_peak_db']
            )
        
        # 6. ソフトリミッター
        if self.audio_processing['soft_limit']:
            processed = self.soft_limiter(
                processed,
                self.audio_processing['limit_threshold']
            )
        
        final_peak = np.max(np.abs(processed))
        print(f"🎶 処理後ピーク: {final_peak:.6f}")
        
        return processed
    
    def load_model(self, model_path, config_path, style_path):
        """モデル読み込み"""
        try:
            import sys
            from io import StringIO
            
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            
            try:
                from style_bert_vits2.nlp import bert_models
                from style_bert_vits2.constants import Languages
                from style_bert_vits2.tts_model import TTSModel
                
                bert_models.load_model(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")
                bert_models.load_tokenizer(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")
                
                device = "cuda" if torch.cuda.is_available() else "cpu"
                
                self.model = TTSModel(
                    model_path=model_path,
                    config_path=config_path,
                    style_vec_path=style_path,
                    device=device,
                )
                
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

            self._inference_device = device
            self._use_autocast = device == "cuda"

            
            self.model_info = {
                'model_path': model_path,
                'config_path': config_path,
                'style_path': style_path,
                'device': device
            }
            
            self.is_loaded = True
            self._update_emotion_mapping()
            
            print(f"✅ モデル読み込み完了: {Path(model_path).parent.name}")
            print(f"📱 利用可能な感情: {list(self.get_available_styles())}")
            
            return True
            
        except Exception as e:
            if 'old_stdout' in locals():
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            print(f"❌ モデル読み込みエラー: {e}")
            self.is_loaded = False
            return False
    
    def _update_emotion_mapping(self):
        """感情マッピング更新"""
        try:
            actual_styles = self._get_actual_styles_from_model()
            print(f"🔍 モデル内の実際の感情: {actual_styles}")
            
            # 既存のマッピングをクリア
            self.emotion_mapping = {}
            
            # KMeansベースのスタイルマッピング
            if 'Style_0' in actual_styles:
                # Style_0 = Neutral (通常は最初のクラスタ)
                self.emotion_mapping['neutral'] = 'Style_0'
                self.emotion_mapping['Neutral'] = 'Style_0'
                
                # 他のスタイルを感情に割り当て
                if len(actual_styles) >= 2:
                    self.emotion_mapping['fear'] = 'Style_1'
                    self.emotion_mapping['Fear'] = 'Style_1'
                if len(actual_styles) >= 3:
                    self.emotion_mapping['sadness'] = 'Style_2'
                    self.emotion_mapping['Sad'] = 'Style_2'
                if len(actual_styles) >= 4:
                    self.emotion_mapping['surprise'] = 'Style_3'
                    self.emotion_mapping['Surprise'] = 'Style_3'
            else:
                # 従来の感情名の場合
                for actual_style in actual_styles:
                    self.emotion_mapping[actual_style] = actual_style
                    self.emotion_mapping[actual_style.lower()] = actual_style
            
            print(f"🔄 更新された感情マッピング: {self.emotion_mapping}")
            
        except Exception as e:
            print(f"⚠️ 感情マッピング更新エラー: {e}")
    
    def _get_actual_styles_from_model(self):
        """実際の利用可能感情を取得"""
        try:
            config_path = self.model_info.get('config_path')
            if config_path and Path(config_path).exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                if 'data' in config and 'style2id' in config['data']:
                    style2id = config['data']['style2id']
                    if style2id:
                        emotions = list(style2id.keys())
                        print(f"🎭 config.jsonから感情発見: {emotions}")
                        return emotions
            
            return ["Neutral"]
            
        except Exception as e:
            print(f"❌ 感情取得エラー: {e}")
            return ["Neutral"]
    
    def get_available_styles(self):
        """利用可能感情取得"""
        if not self.is_loaded:
            return ["Neutral"]
        return self._get_actual_styles_from_model()
    
    def normalize_emotion(self, emotion):
        """感情名正規化"""
        if not emotion:
            return 'Neutral'
        
        normalized = self.emotion_mapping.get(emotion, emotion)
        if normalized != emotion:
            print(f"🔄 感情正規化: '{emotion}' -> '{normalized}'")
        
        return normalized
    
    def synthesize(self, text, **params):
        """音声合成実行（根本解決版）"""
        if not self.is_loaded or self.model is None:
            raise RuntimeError("モデルが読み込まれていません")
        
        if not text.strip():
            raise ValueError("テキストが空です")
            
        try:
            import sys
            from io import StringIO
            
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            
            try:
                # 🔥 超低ノイズパラメータを強制適用
                synth_params = self.default_params.copy()
                synth_params.update(params)
                
                # 感情正規化
                if 'style' in synth_params:
                    original_style = synth_params['style']
                    synth_params['style'] = self.normalize_emotion(original_style)
                    
                    if original_style != synth_params['style']:
                        print(f"✨ 感情正規化: {original_style} → {synth_params['style']}")
                
                # 推論実行
                kwargs = self._build_infer_kwargs(text, synth_params)

                sr = raw_audio = None
                autocast_enabled = torch.cuda.is_available() and getattr(self, "_use_autocast", False)

                if autocast_enabled:
                    try:
                        with torch.cuda.amp.autocast():
                            sr, raw_audio = self.model.infer(**kwargs)
                    except (AssertionError, RuntimeError, FloatingPointError) as amp_error:
                        logging.getLogger(__name__).warning(
                            "AMP inference failed, retrying without autocast: %s", amp_error
                        )
                        self._use_autocast = False
                        sr, raw_audio = self.model.infer(**kwargs)
                else:
                    sr, raw_audio = self.model.infer(**kwargs)            
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            if isinstance(raw_audio, torch.Tensor):
                raw_audio = raw_audio.detach().cpu().float().numpy()
            
            if raw_audio is None or len(raw_audio) == 0:
                raise RuntimeError("音声データが生成されませんでした")
            
            # 商用品質後処理
            print(f"🎵 音声後処理開始...")
            processed_audio = self.process_audio(raw_audio, sr)
            print(f"✅ 音声後処理完了")
                
            return sr, processed_audio
            
        except Exception as e:
            print(f"❌ 音声合成エラー: {e}")
            raise e
    
    def _build_infer_kwargs(self, text, params):
        """推論引数構築"""
        if not self.model:
            raise RuntimeError("モデルが読み込まれていません")
            
        sig = inspect.signature(self.model.infer)
        method_params = sig.parameters
        
        kwargs = {}
        if "text" in method_params:
            kwargs["text"] = text
        else:
            first_param = next(iter(method_params))
            kwargs[first_param] = text
        
        # スタイル系
        if "style" in method_params:
            kwargs["style"] = params.get('style', 'Neutral')
        if "style_weight" in method_params:
            kwargs["style_weight"] = params.get('style_weight', 1.0)
        elif "emotion_weight" in method_params:
            kwargs["emotion_weight"] = params.get('style_weight', 1.0)

        # 長さ系
        length_scale = params.get('length_scale', 0.85)
        if "length_scale" in method_params:
            kwargs["length_scale"] = length_scale
        elif "duration_scale" in method_params:
            kwargs["duration_scale"] = length_scale
        elif "speed" in method_params:
            kwargs["speed"] = 1.0 / length_scale
        elif "length" in method_params:
            kwargs["length"] = length_scale
        
        # SDP
        sdp_value = params.get('sdp_ratio', 0.05)  # 🔥 デフォルト0.05
        if "sdp_ratio" in method_params:
            kwargs["sdp_ratio"] = sdp_value
        elif "sdp" in method_params:
            kwargs["sdp"] = sdp_value
        
        # ノイズ系
        noise_value = params.get('noise', 0.05)  # 🔥 デフォルト0.05
        if "noise" in method_params:
            kwargs["noise"] = noise_value
        elif "noise_scale_w" in method_params:
            kwargs["noise_scale_w"] = noise_value
        elif "noise_scale" in method_params:
            kwargs["noise_scale"] = noise_value
        
        # その他
        if "pitch_scale" in method_params:
            kwargs["pitch_scale"] = params.get('pitch_scale', 1.0)
        if "intonation_scale" in method_params:
            kwargs["intonation_scale"] = params.get('intonation_scale', 1.0)
        
        print(f"🔧 推論パラメータ: {kwargs}")
        return kwargs
    
    def set_audio_processing(self, **settings):
        """音声処理設定変更"""
        for key, value in settings.items():
            if key in self.audio_processing:
                old_value = self.audio_processing[key]
                self.audio_processing[key] = value
                print(f"🔧 設定変更: {key} = {old_value} -> {value}")
            else:
                print(f"⚠️ 未知の設定: {key}")
    
    def get_audio_processing_settings(self):
        """音声処理設定取得"""
        return self.audio_processing.copy()
    
    def get_model_info(self):
        """モデル情報取得"""
        return self.model_info.copy() if self.is_loaded else {}
    
    def unload_model(self):
        """モデルアンロード"""
        if self.model:
            del self.model
            self.model = None
        self.is_loaded = False
        self.model_info = {}
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    def debug_emotions(self):
        """感情デバッグ"""
        print("\n=== 感情マッピング デバッグ ===")
        print(f"モデル読み込み: {'✅' if self.is_loaded else '❌'}")
        
        if self.is_loaded:
            actual_styles = self._get_actual_styles_from_model()
            print(f"利用可能感情: {actual_styles}")
        
        print("感情マッピング:")
        for key, value in sorted(self.emotion_mapping.items()):
            status = "✅" if key == value else f"🔄 -> {value}"
            print(f"  '{key}' {status}")
        print("=== デバッグ終了 ===\n")
    
    def test_emotion(self, emotion, text="これはテストです"):
        """感情テスト"""
        try:
            print(f"🧪 感情テスト: '{emotion}'")
            normalized = self.normalize_emotion(emotion)
            print(f"📝 正規化後: '{normalized}'")
            
            sr, audio = self.synthesize(text, style=emotion, style_weight=1.0)
            print(f"✅ テスト成功: {len(audio)} samples, {sr}Hz")
            return True, sr, audio
            
        except Exception as e:
            print(f"❌ テスト失敗: {e}")
            return False, None, None
        
    def generate_continuous_wav(
        self, 
        texts_data: List[Dict],
        output_path: str,
        chunk_size: int = 100,
        resume: bool = True,
        progress_callback = None
    ) -> Dict:
        """
        複数テキストを連続TTS処理して1つのWAVに保存
        
        使い方:
            texts = ["リアクション1", "リアクション2", "リアクション3"]
            result = tts_engine.generate_continuous_wav(
                texts, 
                "outputs/reaction_part.wav",
                progress_callback=self.update_progress
            )
        
        Args:
            texts: 処理するテキストのリスト
            output_path: 出力WAVファイルパス
            chunk_size: メモリ管理用チャンクサイズ（デフォルト100）
            resume: 中断から再開するか
            progress_callback: 進捗コールバック
        """
        # 遅延初期化
        if self.long_processor is None:
            from core.tts_long_processor import LongTTSProcessor
            self.long_processor = LongTTSProcessor(self)
        
        return self.long_processor.process_texts_to_wav(
            texts_data, output_path, chunk_size, resume, progress_callback
        )