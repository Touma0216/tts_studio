# core/audio_processor.py (完全実装版)
import numpy as np
import scipy.signal
from typing import Dict, List, Optional, Tuple
import logging

class AudioProcessor:
    """実際の音声クリーニング処理エンジン"""
    
    def __init__(self):
        self.filters = {
            'declipping': True,
            'denoise': True, 
            'dehum': True,
            'normalize': True
        }
        self.logger = logging.getLogger(__name__)
    
    def process_audio(self, audio: np.ndarray, sample_rate: int, settings: Dict) -> np.ndarray:
        """
        音声に対してクリーニング処理チェーンを適用
        
        Args:
            audio: 入力音声 (samples, channels) または (samples,)
            sample_rate: サンプリング周波数
            settings: クリーナー設定辞書
        
        Returns:
            処理済み音声データ
        """
        if not settings.get('enabled', False):
            return audio
        
        # モノラル化（処理用）
        if audio.ndim == 1:
            mono_audio = audio.copy()
            is_mono = True
        else:
            mono_audio = np.mean(audio, axis=1)
            is_mono = False
        
        processed = mono_audio.copy()
        
        try:
            # 1. ハイパスフィルタ（低域カット）
            processed = self._apply_highpass(processed, sample_rate, settings)
            
            # 2. ハム除去（50Hz/60Hz系）
            if settings.get('hum_removal', False):
                processed = self._remove_hum(processed, sample_rate, settings)
            
            # 3. ノイズ除去
            if settings.get('noise_reduction', False):
                processed = self._reduce_noise(processed, sample_rate, settings)
            
            # 4. ラウドネス正規化
            if settings.get('loudness_norm', True):
                processed = self._normalize_loudness(processed, sample_rate, settings)
            
            # ステレオに戻す（必要な場合）
            if not is_mono:
                processed = np.column_stack([processed, processed])
            
            return processed
            
        except Exception as e:
            self.logger.error(f"音声処理中にエラー: {e}")
            return audio  # エラー時は元の音声を返す
    
    def _apply_highpass(self, audio: np.ndarray, sample_rate: int, settings: Dict) -> np.ndarray:
        """ハイパスフィルタを適用"""
        cutoff_freq = settings.get('highpass_freq', 80)
        
        if cutoff_freq <= 0:
            return audio
        
        # Butterworthフィルタ設計
        nyquist = sample_rate / 2
        normalized_cutoff = cutoff_freq / nyquist
        
        # カットオフ周波数が高すぎる場合の対策
        if normalized_cutoff >= 1.0:
            normalized_cutoff = 0.95
        
        b, a = scipy.signal.butter(4, normalized_cutoff, btype='high')
        
        # ゼロ位相フィルタで適用
        filtered = scipy.signal.filtfilt(b, a, audio)
        
        return filtered
    
    def _remove_hum(self, audio: np.ndarray, sample_rate: int, settings: Dict) -> np.ndarray:
        """ハム（50Hz/60Hz系）を除去"""
        frequencies = settings.get('hum_frequencies', [])
        gains_db = settings.get('hum_gains', [])
        
        if not frequencies or not gains_db:
            return audio
        
        processed = audio.copy()
        
        # 各周波数に対してノッチフィルタを適用
        for freq, gain_db in zip(frequencies, gains_db):
            if freq <= 0 or freq >= sample_rate / 2:
                continue
            
            processed = self._apply_notch_filter(processed, sample_rate, freq, gain_db)
        
        return processed
    
    def _apply_notch_filter(self, audio: np.ndarray, sample_rate: int, 
                           center_freq: float, gain_db: float) -> np.ndarray:
        """指定周波数にノッチフィルタを適用"""
        if gain_db >= -3:  # 効果が小さい場合はスキップ
            return audio
        
        nyquist = sample_rate / 2
        normalized_freq = center_freq / nyquist
        
        # Qファクターを周波数に応じて調整
        if center_freq <= 100:
            Q = 35  # 低域は鋭く
        elif center_freq <= 200:
            Q = 30
        elif center_freq <= 400:
            Q = 25
        else:
            Q = 20
        
        # ノッチフィルタ設計
        b, a = scipy.signal.iirnotch(center_freq, Q, sample_rate)
        
        # 適用
        filtered = scipy.signal.filtfilt(b, a, audio)
        
        # ゲインを適用（完全除去ではなく減衰）
        gain_linear = 10 ** (gain_db / 20)
        notched_component = filtered - audio
        result = audio + notched_component * gain_linear
        
        return result
    
    def _reduce_noise(self, audio: np.ndarray, sample_rate: int, settings: Dict) -> np.ndarray:
        """スペクトルサブトラクションベースのノイズ除去"""
        noise_floor_db = settings.get('noise_floor', -28)
        
        # FFTベースのノイズ除去
        # 実装はFFTdnに類似したアルゴリズム
        
        # パラメータ
        frame_size = 2048
        hop_size = 512
        overlap = frame_size - hop_size
        
        # ウィンドウ関数
        window = np.hanning(frame_size)
        
        # フレーム数計算
        num_frames = (len(audio) - overlap) // hop_size
        
        if num_frames <= 0:
            return audio
        
        # ノイズプロファイル推定（最初の10フレーム使用）
        noise_profile = self._estimate_noise_profile(audio, sample_rate, frame_size, hop_size, window)
        
        # 処理済み音声バッファ
        processed = np.zeros_like(audio)
        
        for i in range(num_frames):
            start = i * hop_size
            end = start + frame_size
            
            if end > len(audio):
                break
            
            # フレーム抽出
            frame = audio[start:end] * window
            
            # FFT
            spectrum = np.fft.rfft(frame)
            magnitude = np.abs(spectrum)
            phase = np.angle(spectrum)
            
            # スペクトルサブトラクション
            cleaned_magnitude = self._spectral_subtraction(magnitude, noise_profile, noise_floor_db)
            
            # 逆FFT
            cleaned_spectrum = cleaned_magnitude * np.exp(1j * phase)
            cleaned_frame = np.fft.irfft(cleaned_spectrum, n=frame_size)
            
            # オーバーラップアド
            processed[start:end] += cleaned_frame * window
        
        return processed
    
    def _estimate_noise_profile(self, audio: np.ndarray, sample_rate: int, 
                              frame_size: int, hop_size: int, window: np.ndarray) -> np.ndarray:
        """ノイズプロファイルを推定"""
        # 音声の最初の部分（通常は無音に近い）からノイズプロファイルを推定
        noise_frames = min(10, (len(audio) - frame_size) // hop_size)
        
        if noise_frames <= 0:
            # フォールバック: 全体の下位20%の平均
            spectrum = np.abs(np.fft.rfft(audio[:frame_size] * window))
            return spectrum * 0.1  # 控えめなノイズプロファイル
        
        noise_spectra = []
        
        for i in range(noise_frames):
            start = i * hop_size
            end = start + frame_size
            frame = audio[start:end] * window
            spectrum = np.abs(np.fft.rfft(frame))
            noise_spectra.append(spectrum)
        
        # ノイズプロファイル = 各周波数ビンの最小値の平均
        noise_profile = np.median(noise_spectra, axis=0)
        
        return noise_profile
    
    def _spectral_subtraction(self, magnitude: np.ndarray, noise_profile: np.ndarray, 
                            noise_floor_db: float) -> np.ndarray:
        """スペクトルサブトラクション実行"""
        noise_floor_linear = 10 ** (noise_floor_db / 20)
        
        # SNRベースの減衰計算
        snr = magnitude / (noise_profile + 1e-10)
        
        # 減衰係数計算（SNRが低いほど強く減衰）
        alpha = np.ones_like(snr)
        alpha[snr < 3.0] = 0.5  # SNR < 3 (約9.5dB)で50%減衰
        alpha[snr < 2.0] = 0.3  # SNR < 2 (約6dB)で70%減衰
        alpha[snr < 1.5] = 0.1  # SNR < 1.5 (約3.5dB)で90%減衰
        
        # 処理後のマグニチュード
        cleaned_magnitude = magnitude * alpha
        
        # 最小値制限
        min_magnitude = magnitude * noise_floor_linear
        cleaned_magnitude = np.maximum(cleaned_magnitude, min_magnitude)
        
        return cleaned_magnitude
    
    def _normalize_loudness(self, audio: np.ndarray, sample_rate: int, settings: Dict) -> np.ndarray:
        """ラウドネス正規化（簡易版EBU R128）"""
        target_lufs = settings.get('target_lufs', -20.0)
        true_peak_limit = settings.get('true_peak', -1.0)
        
        # 現在のラウドネス推定（RMSベース簡易版）
        # 実際のEBU R128は複雑なため、簡易実装
        
        # RMS計算（ゲート処理付き）
        current_rms = self._calculate_gated_rms(audio)
        current_lufs = self._rms_to_lufs(current_rms)
        
        # 必要なゲイン計算
        gain_db = target_lufs - current_lufs
        gain_linear = 10 ** (gain_db / 20)
        
        # ゲイン適用
        normalized = audio * gain_linear
        
        # 真ピーク制限
        peak = np.max(np.abs(normalized))
        true_peak_limit_linear = 10 ** (true_peak_limit / 20)
        
        if peak > true_peak_limit_linear:
            limiter_gain = true_peak_limit_linear / peak
            normalized *= limiter_gain
        
        return normalized
    
    def _calculate_gated_rms(self, audio: np.ndarray, gate_threshold_db: float = -70.0) -> float:
        """ゲート処理付きRMS計算"""
        # 400msブロックでゲート処理
        block_size = int(0.4 * 48000)  # 仮定: 48kHz基準
        gate_threshold_linear = 10 ** (gate_threshold_db / 20)
        
        valid_blocks = []
        
        for i in range(0, len(audio) - block_size, block_size // 4):  # 75%オーバーラップ
            block = audio[i:i + block_size]
            block_rms = np.sqrt(np.mean(block ** 2))
            
            if block_rms > gate_threshold_linear:
                valid_blocks.append(block_rms ** 2)
        
        if not valid_blocks:
            return np.sqrt(np.mean(audio ** 2))  # フォールバック
        
        return np.sqrt(np.mean(valid_blocks))
    
    def _rms_to_lufs(self, rms: float) -> float:
        """RMSをLUFS相当値に変換（簡易）"""
        # 実際のLUFSは複雑な重み付けが必要だが、ここでは簡易変換
        return 20 * np.log10(max(rms, 1e-10)) + 0.691  # EBU R128補正係数
    
    def fix_clipping(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """クリッピング修復（簡易デクリッパー）"""
        # クリップ検出
        clip_threshold = 0.99
        clipped_samples = np.abs(audio) >= clip_threshold
        
        if not np.any(clipped_samples):
            return audio
        
        # 簡易的な線形補間による修復
        fixed = audio.copy()
        
        # クリップ領域を検出
        clip_starts = np.where(np.diff(clipped_samples.astype(int)) == 1)[0] + 1
        clip_ends = np.where(np.diff(clipped_samples.astype(int)) == -1)[0] + 1
        
        # 開始点と終了点の数を合わせる
        if len(clip_starts) > len(clip_ends):
            clip_ends = np.append(clip_ends, len(audio) - 1)
        elif len(clip_ends) > len(clip_starts):
            clip_starts = np.insert(clip_starts, 0, 0)
        
        for start, end in zip(clip_starts, clip_ends):
            if end <= start or start < 1 or end >= len(audio) - 1:
                continue
            
            # 前後の非クリップ値で線形補間
            pre_value = fixed[start - 1]
            post_value = fixed[end + 1]
            
            # 補間値を計算
            interpolated = np.linspace(pre_value, post_value, end - start + 1)
            fixed[start:end + 1] = interpolated
        
        return fixed
    
    def remove_hum(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """ハム除去（レガシー互換メソッド）"""
        settings = {
            'hum_removal': True,
            'hum_frequencies': [50, 60, 100, 120, 150, 180, 200, 240],
            'hum_gains': [-20, -20, -12, -12, -9, -9, -6, -6]
        }
        return self._remove_hum(audio, sample_rate, settings)
    
    def reduce_noise(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """ノイズ除去（レガシー互換メソッド）"""
        settings = {
            'noise_reduction': True,
            'noise_floor': -28
        }
        return self._reduce_noise(audio, sample_rate, settings)
    
    def normalize_loudness(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """ラウドネス正規化（レガシー互換メソッド）"""
        settings = {
            'loudness_norm': True,
            'target_lufs': -20.0,
            'true_peak': -1.0
        }
        return self._normalize_loudness(audio, sample_rate, settings)
    
    def create_test_tone(self, frequency: float, duration: float, 
                        sample_rate: int = 44100, amplitude: float = 0.5) -> np.ndarray:
        """テスト用トーン生成"""
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = amplitude * np.sin(2 * np.pi * frequency * t)
        return tone
    
    def analyze_processing_effect(self, original: np.ndarray, processed: np.ndarray, 
                                sample_rate: int) -> Dict:
        """処理前後の比較分析"""
        def calculate_metrics(audio):
            return {
                'rms': np.sqrt(np.mean(audio ** 2)),
                'peak': np.max(np.abs(audio)),
                'dynamic_range': np.max(np.abs(audio)) / (np.sqrt(np.mean(audio ** 2)) + 1e-10)
            }
        
        original_metrics = calculate_metrics(original)
        processed_metrics = calculate_metrics(processed)
        
        return {
            'rms_change_db': 20 * np.log10(processed_metrics['rms'] / (original_metrics['rms'] + 1e-10)),
            'peak_change_db': 20 * np.log10(processed_metrics['peak'] / (original_metrics['peak'] + 1e-10)),
            'dynamic_range_change': processed_metrics['dynamic_range'] / (original_metrics['dynamic_range'] + 1e-10),
            'original_metrics': original_metrics,
            'processed_metrics': processed_metrics
        }