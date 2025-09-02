# core/audio_analyzer.py (TTS音声データ用)
import numpy as np
import scipy.signal
from typing import Dict, List, Tuple, Optional
import math

class AudioAnalyzer:
    """TTS生成音声データの解析＆自動クリーナープリセット生成"""
    
    def __init__(self):
        self.analysis_result = None
        self.recommended_preset = None
    
    def analyze_audio(self, audio: np.ndarray, sample_rate: int) -> Dict:
        """
        TTS生成音声を詳細解析してプリセット生成
        wav_health_check_jp.pyベースの解析ロジック（TTS用に改変）
        
        Args:
            audio: TTS生成音声データ (samples,) または (samples, channels)
            sample_rate: サンプリング周波数
        
        Returns:
            解析結果辞書
        """
        print(f"🔍 音声解析開始: shape={audio.shape}, sr={sample_rate}")
        
        # 入力データの正規化
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        
        result = {}
        
        # === 基本統計 ===
        abs_x = np.abs(audio)
        result['peak_per_ch'] = abs_x.max(axis=0)
        result['rms_per_ch'] = np.sqrt((audio**2).mean(axis=0))
        result['mean_per_ch'] = audio.mean(axis=0)  # DCオフセット
        
        peak_db = self.dbfs(result['peak_per_ch'].max())
        rms_db = self.dbfs(result['rms_per_ch'].mean())
        print(f"📊 ピーク: {peak_db:.2f}dBFS, RMS: {rms_db:.2f}dBFS")
        
        # === クリッピング検出 ===
        clip_threshold = 0.9995
        clip_mask = (abs_x >= clip_threshold)
        result['clip_ratio_per_ch'] = clip_mask.mean(axis=0)
        result['clip_runs_total'] = self._count_clip_runs(audio, clip_threshold)
        
        clip_percent = result['clip_ratio_per_ch'].max() * 100
        print(f"✂️ クリップ率: {clip_percent:.3f}%, 連続クリップ: {result['clip_runs_total']}箇所")
        
        # === 真ピーク推定 ===
        result['true_peak_est'] = self._true_peak_estimate(audio)
        true_peak_db = self.dbfs(result['true_peak_est'])
        print(f"🎯 真ピーク推定: {true_peak_db:.2f}dBFS")
        
        # === ノイズ床・SNR ===
        noise_db, snr_db = self._estimate_noise_floor_and_snr(audio, sample_rate)
        result['noise_floor_dbfs'] = noise_db
        result['snr_db'] = snr_db
        
        if snr_db is not None:
            print(f"📡 SNR: {snr_db:.1f}dB, ノイズ床: {noise_db:.1f}dBFS")
        
        # === ハム検出（最重要！） ===
        mono = audio.mean(axis=1)
        result['hum_detection'] = self._detect_hum(mono, sample_rate)
        
        for freq, strength in result['hum_detection'].items():
            if strength > 0.1:  # 10%以上なら表示
                print(f"⚡ {int(freq)}Hz系ハム: {strength*100:.1f}%")
        
        # === スペクトル分析 ===
        result['spectral_flatness'] = self._spectral_flatness(mono, sample_rate)
        
        # === 無音解析 ===
        silence_threshold = 10 ** (-60.0 / 20.0)  # -60dBFS
        if audio.shape[1] == 1:
            silence_mask = (abs_x[:, 0] < silence_threshold)
        else:
            silence_mask = (abs_x < silence_threshold).all(axis=1)
        
        result['silence_ratio'] = float(silence_mask.mean())
        result['leading_silence_sec'] = self._edge_silence_len(silence_mask, sample_rate, True)
        result['trailing_silence_sec'] = self._edge_silence_len(silence_mask, sample_rate, False)
        
        print(f"🔇 無音率: {result['silence_ratio']*100:.1f}%")
        
        # 解析結果を保存
        self.analysis_result = result
        
        # 自動プリセット生成
        self.recommended_preset = self._generate_cleaning_preset(result, sample_rate)
        
        print("✅ 解析完了")
        return result
    
    def _true_peak_estimate(self, audio: np.ndarray, upsample_factor: int = 4) -> float:
        """線形補間による真ピーク推定（TTS用に軽量化）"""
        if audio.shape[1] == 1:
            sig = audio[:, 0]
            # 線形補間でアップサンプリング
            idx = np.arange(len(sig))
            upsampled = np.interp(np.linspace(0, len(sig)-1, len(sig)*upsample_factor), idx, sig)
            return float(np.max(np.abs(upsampled)))
        else:
            peaks = []
            for c in range(audio.shape[1]):
                sig = audio[:, c]
                idx = np.arange(len(sig))
                upsampled = np.interp(np.linspace(0, len(sig)-1, len(sig)*upsample_factor), idx, sig)
                peaks.append(np.max(np.abs(upsampled)))
            return float(np.max(peaks))
    
    def _count_clip_runs(self, audio: np.ndarray, threshold: float = 0.9995, min_run: int = 3) -> int:
        """連続クリップ箇所数"""
        abs_x = np.abs(audio)
        total_runs = 0
        
        for c in range(audio.shape[1]):
            mask = (abs_x[:, c] >= threshold).astype(np.int8)
            if mask.sum() == 0:
                continue
            edges = np.diff(np.r_[0, mask, 0])
            starts = np.where(edges == 1)[0]
            ends = np.where(edges == -1)[0]
            run_lengths = (ends - starts)
            total_runs += int((run_lengths >= min_run).sum())
        
        return total_runs
    
    def _estimate_noise_floor_and_snr(self, audio: np.ndarray, sample_rate: int) -> Tuple[Optional[float], Optional[float]]:
        """ノイズ床とSNRを推定（TTS音声用）"""
        window_size = min(1024, len(audio) // 4)  # 短い音声に対応
        hop_size = window_size // 2
        mono = audio.mean(axis=1)
        
        if len(mono) < window_size:
            return None, None
        
        n_frames = (len(mono) - window_size) // hop_size + 1
        if n_frames <= 0:
            return None, None
        
        frame_rms = []
        for i in range(n_frames):
            segment = mono[i*hop_size:i*hop_size+window_size]
            rms = np.sqrt(np.mean(segment**2) + 1e-12)
            frame_rms.append(rms)
        
        frame_rms = np.array(frame_rms)
        
        # 下位20%をノイズ、中央値を信号とみなす
        noise_threshold = np.quantile(frame_rms, 0.2)
        noise_frames = frame_rms[frame_rms <= noise_threshold]
        noise_rms = np.median(noise_frames) if len(noise_frames) > 0 else np.median(frame_rms)
        signal_rms = np.median(frame_rms)
        
        noise_db = 20*np.log10(max(noise_rms, 1e-12))
        signal_db = 20*np.log10(max(signal_rms, 1e-12))
        snr_db = signal_db - noise_db
        
        return noise_db, snr_db
    
    def _detect_hum(self, mono: np.ndarray, sample_rate: int) -> Dict[float, float]:
        """ハム（50Hz/60Hz系）検出（TTS音声用）"""
        # FFTサイズを音声長に応じて調整
        N = min(16384, 2**int(np.log2(len(mono))))
        if N < 1024:
            N = 1024
        
        # 音声が短い場合はゼロパディング
        if len(mono) < N:
            padded = np.zeros(N, dtype=mono.dtype)
            padded[:len(mono)] = mono
            mono = padded
        
        # ハニング窓適用してFFT
        windowed = mono[:N] * np.hanning(N)
        spectrum = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(N, 1/sample_rate)
        
        def get_band_peak(center_freq: float, bandwidth: float = 2.0) -> float:
            """指定周波数帯域のピークを取得"""
            mask = (freqs >= center_freq - bandwidth) & (freqs <= center_freq + bandwidth)
            return float(spectrum[mask].max()) if np.any(mask) else 0.0
        
        # 50Hz/60Hz系ハムを検出（基本波+倍音）
        hum_peaks = {}
        for base_freq in [50.0, 60.0]:
            harmonics = []
            for k in range(1, 9):  # 8次まで
                harmonic_freq = base_freq * k
                if harmonic_freq < sample_rate / 2:  # ナイキスト周波数以下
                    peak = get_band_peak(harmonic_freq)
                    harmonics.append(peak)
            
            # 最大倍音強度を採用
            hum_peaks[base_freq] = max(harmonics) if harmonics else 0.0
        
        # スペクトル全体の最大値で正規化
        normalization = spectrum.max() + 1e-9
        return {freq: peak/normalization for freq, peak in hum_peaks.items()}
    
    def _spectral_flatness(self, mono: np.ndarray, sample_rate: int) -> float:
        """スペクトルフラットネス（0=トーン性, 1=ノイズ性）"""
        N = min(2048, 2**int(np.log2(len(mono))))
        if N < 512:
            N = 512
        
        hop = N // 2
        eps = 1e-12
        flatness_values = []
        
        for i in range(0, len(mono) - N, hop):
            segment = mono[i:i+N] * np.hanning(N)
            magnitude = np.abs(np.fft.rfft(segment)) + eps
            geometric_mean = np.exp(np.mean(np.log(magnitude)))
            arithmetic_mean = np.mean(magnitude)
            flatness_values.append(geometric_mean / arithmetic_mean)
        
        return float(np.median(flatness_values)) if flatness_values else 0.0
    
    def _edge_silence_len(self, silence_mask: np.ndarray, sample_rate: int, from_start: bool = True) -> float:
        """先頭または末尾の無音長を計算"""
        if silence_mask.size == 0:
            return 0.0
        
        if from_start:
            if not (~silence_mask).any():
                return len(silence_mask) / sample_rate
            idx = np.argmax(~silence_mask)
            return idx / sample_rate
        else:
            reversed_mask = silence_mask[::-1]
            if not (~reversed_mask).any():
                return len(silence_mask) / sample_rate
            idx = np.argmax(~reversed_mask)
            return idx / sample_rate
    
    def _generate_cleaning_preset(self, analysis: Dict, sample_rate: int) -> Dict:
        """解析結果から自動でクリーニングプリセットを生成（TTS特化）"""
        print("🤖 自動プリセット生成開始...")
        
        preset = {
            'enabled': True,
            'auto_generated': True,
            'highpass_freq': 80,  # デフォルト
            'hum_removal': False,
            'hum_frequencies': [],
            'hum_gains': [],
            'noise_reduction': False,
            'noise_floor': -28,
            'loudness_norm': True,
            'target_lufs': -20.0,
            'true_peak': -1.0,
            'lra': 11.0,
        }
        
        # === ハム除去の自動設定 ===
        hum_detection = analysis.get('hum_detection', {})
        significant_hums = []
        
        for base_freq, relative_strength in hum_detection.items():
            if relative_strength > 0.15:  # 15%以上の相対強度なら除去対象
                significant_hums.append((base_freq, relative_strength))
                print(f"🎯 {int(base_freq)}Hz系ハム検出: {relative_strength*100:.1f}% → 除去対象")
        
        if significant_hums:
            preset['hum_removal'] = True
            preset['hum_frequencies'] = []
            preset['hum_gains'] = []
            
            for base_freq, strength in significant_hums:
                # 基本周波数と倍音（最大8次まで）
                harmonics = []
                for k in range(1, 9):
                    harmonic_freq = base_freq * k
                    if harmonic_freq < sample_rate / 2:  # ナイキスト周波数以下
                        harmonics.append(harmonic_freq)
                
                gains = self._calculate_hum_gains(strength, len(harmonics))
                
                preset['hum_frequencies'].extend(harmonics)
                preset['hum_gains'].extend(gains)
            
            print(f"✅ ハム除去設定: {len(preset['hum_frequencies'])}個の周波数")
        
        # === ノイズ除去の自動設定 ===
        snr_db = analysis.get('snr_db')
        noise_floor_db = analysis.get('noise_floor_dbfs')
        
        if snr_db is not None and snr_db < 25:  # SNRが低い場合
            preset['noise_reduction'] = True
            if noise_floor_db is not None and noise_floor_db > -35:
                preset['noise_floor'] = max(-35, noise_floor_db - 3)  # ノイズ床より3dB下
                print(f"🔊 ノイズ除去有効: フロア {preset['noise_floor']}dBFS")
        
        # === ハイパスフィルター調整 ===
        max_hum_strength = max(hum_detection.values()) if hum_detection else 0
        if max_hum_strength > 0.3:
            preset['highpass_freq'] = 100  # ハムが強い場合は少し高めに
            print(f"🎚️ ハイパスフィルタ強化: {preset['highpass_freq']}Hz")
        
        # === ラウドネス正規化調整 ===
        true_peak = analysis.get('true_peak_est', 0)
        if true_peak > 0.9:  # ピークが高い場合
            preset['true_peak'] = -1.5  # より保守的に
            print(f"📈 真ピーク制限強化: {preset['true_peak']}dBFS")
        
        clip_ratio = analysis.get('clip_ratio_per_ch', [0])
        if np.any(np.array(clip_ratio) > 0.001):  # クリップがある場合
            preset['true_peak'] = -2.0  # さらに保守的に
            print(f"✂️ クリップ対策: 真ピーク制限 {preset['true_peak']}dBFS")
        
        print("🤖 自動プリセット生成完了")
        return preset
    
    def _calculate_hum_gains(self, strength: float, num_harmonics: int) -> List[float]:
        """ハム強度と倍音数に基づいて各倍音の減衰量を計算"""
        # 強度に応じて基本的な減衰量を決定
        if strength > 0.8:      # 非常に強い（80%以上）
            base_gain = -25
        elif strength > 0.5:    # 強い（50%以上）
            base_gain = -20
        elif strength > 0.3:    # 中程度（30%以上）
            base_gain = -15
        else:                   # 軽微（30%未満）
            base_gain = -10
        
        # 倍音ごとに減衰量を調整（高次倍音ほど軽く）
        gains = []
        for i in range(num_harmonics):
            if i < 2:  # 基本波と2次倍音
                gains.append(base_gain)
            elif i < 4:  # 3-4次倍音
                gains.append(base_gain + 5)  # 少し軽く
            elif i < 6:  # 5-6次倍音
                gains.append(base_gain + 8)  # さらに軽く
            else:  # 7次以上
                gains.append(base_gain + 10)  # 最も軽く
        
        return gains
    
    def get_analysis_summary(self) -> str:
        """解析結果の日本語サマリーを生成"""
        if not self.analysis_result:
            return "解析が実行されていません"
        
        analysis = self.analysis_result
        issues = []
        good_points = []
        
        # ハムチェック
        hum_detection = analysis.get('hum_detection', {})
        for freq, strength in hum_detection.items():
            if strength > 0.2:
                issues.append(f"{int(freq)}Hz系ハム成分が検出されました（強度 {strength*100:.1f}%）")
        
        # クリッピングチェック
        clip_ratio = analysis.get('clip_ratio_per_ch', [0])
        if np.any(np.array(clip_ratio) > 0.001):
            issues.append(f"音割れ（クリップ）が検出されました（{np.max(clip_ratio)*100:.3f}%）")
        else:
            good_points.append("音割れは検出されませんでした")
        
        # SNRチェック
        snr_db = analysis.get('snr_db')
        if snr_db is not None:
            if snr_db < 20:
                issues.append(f"SNRが低く、ノイズが多めです（{snr_db:.1f}dB）")
            else:
                good_points.append(f"SNRは良好です（{snr_db:.1f}dB）")
        
        # 真ピークチェック
        true_peak = analysis.get('true_peak_est', 0)
        peak_db = self.dbfs(true_peak)
        if true_peak > 0.9:
            issues.append(f"音量が大きすぎます（{peak_db:.1f}dBFS）")
        else:
            good_points.append(f"音量レベルは適切です（{peak_db:.1f}dBFS）")
        
        # 結果をまとめる
        summary = ""
        
        if good_points:
            summary += "✅ 良好な点:\n" + "\n".join(f"• {point}" for point in good_points) + "\n\n"
        
        if issues:
            summary += "⚠️ 検出された問題:\n" + "\n".join(f"• {issue}" for issue in issues)
        else:
            summary += "🎉 音質に大きな問題は検出されませんでした！"
        
        return summary
    
    def get_recommended_preset(self) -> Optional[Dict]:
        """推奨クリーニングプリセットを取得"""
        return self.recommended_preset
    
    def dbfs(self, value: float) -> float:
        """リニア値をdBFSに変換"""
        return 20.0 * math.log10(max(float(value), 1e-12))
    
    def _true_peak_estimate(self, audio: np.ndarray, upsample_factor: int = 8) -> float:
        """線形補間による真ピーク推定"""
        if audio.shape[1] == 1:
            sig = audio[:, 0]
            idx = np.arange(len(sig))
            upsampled = np.interp(np.linspace(0, len(sig)-1, len(sig)*upsample_factor), idx, sig)
            return float(np.max(np.abs(upsampled)))
        else:
            peaks = []
            for c in range(audio.shape[1]):
                sig = audio[:, c]
                idx = np.arange(len(sig))
                upsampled = np.interp(np.linspace(0, len(sig)-1, len(sig)*upsample_factor), idx, sig)
                peaks.append(np.max(np.abs(upsampled)))
            return float(np.max(peaks))
    
    def _count_clip_runs(self, audio: np.ndarray, threshold: float = 0.9995, min_run: int = 3) -> int:
        """連続クリップ箇所数"""
        abs_x = np.abs(audio)
        total_runs = 0
        
        for c in range(audio.shape[1]):
            mask = (abs_x[:, c] >= threshold).astype(np.int8)
            if mask.sum() == 0:
                continue
            edges = np.diff(np.r_[0, mask, 0])
            starts = np.where(edges == 1)[0]
            ends = np.where(edges == -1)[0]
            run_lengths = (ends - starts)
            total_runs += int((run_lengths >= min_run).sum())
        
        return total_runs
    
    def _estimate_noise_floor_and_snr(self, audio: np.ndarray, sample_rate: int) -> Tuple[Optional[float], Optional[float]]:
        """ノイズ床とSNRを推定"""
        window_size = 1024
        hop_size = 512
        mono = audio.mean(axis=1)
        
        if len(mono) < window_size + hop_size:
            return None, None
        
        n_frames = (len(mono) - window_size) // hop_size + 1
        if n_frames <= 0:
            return None, None
        
        frame_rms = np.empty(n_frames, dtype=np.float32)
        for i in range(n_frames):
            segment = mono[i*hop_size:i*hop_size+window_size]
            frame_rms[i] = np.sqrt(np.mean(segment**2) + 1e-12)
        
        # 下位20%をノイズ、中央値を信号とみなす
        noise_threshold = np.quantile(frame_rms, 0.2)
        noise_rms = np.median(frame_rms[frame_rms <= noise_threshold]) if np.any(frame_rms <= noise_threshold) else np.median(frame_rms)
        signal_rms = np.median(frame_rms)
        
        noise_db = 20*np.log10(max(noise_rms, 1e-12))
        signal_db = 20*np.log10(max(signal_rms, 1e-12))
        snr_db = signal_db - noise_db
        
        return noise_db, snr_db
    
    def _detect_hum(self, mono: np.ndarray, sample_rate: int) -> Dict[float, float]:
        """ハム（50Hz/60Hz系）検出"""
        N = 16384
        if len(mono) < N:
            padded = np.zeros(N, dtype=mono.dtype)
            padded[:len(mono)] = mono
            mono = padded
        
        # ハニング窓適用してFFT
        windowed = mono[:N] * np.hanning(N)
        spectrum = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(N, 1/sample_rate)
        
        def get_band_peak(center_freq: float, bandwidth: float = 1.0) -> float:
            mask = (freqs >= center_freq - bandwidth) & (freqs <= center_freq + bandwidth)
            return float(spectrum[mask].max()) if np.any(mask) else 0.0
        
        # 50Hz/60Hz系ハムを8次まで検出
        hum_peaks = {}
        for base_freq in [50.0, 60.0]:
            harmonics = [get_band_peak(base_freq * k) for k in range(1, 9)]
            hum_peaks[base_freq] = max(harmonics) if harmonics else 0.0
        
        # スペクトル全体の最大値で正規化
        normalization = spectrum.max() + 1e-9
        return {freq: peak/normalization for freq, peak in hum_peaks.items()}
    
    def _spectral_flatness(self, mono: np.ndarray, sample_rate: int) -> float:
        """スペクトルフラットネス（0=トーン性, 1=ノイズ性）"""
        N = 2048
        hop = 1024
        eps = 1e-12
        flatness_values = []
        
        for i in range(0, len(mono) - N, hop):
            segment = mono[i:i+N] * np.hanning(N)
            magnitude = np.abs(np.fft.rfft(segment)) + eps
            geometric_mean = np.exp(np.mean(np.log(magnitude)))
            arithmetic_mean = np.mean(magnitude)
            flatness_values.append(geometric_mean / arithmetic_mean)
        
        return float(np.median(flatness_values)) if flatness_values else 0.0
    
    def _edge_silence_len(self, silence_mask: np.ndarray, sample_rate: int, from_start: bool = True) -> float:
        """先頭または末尾の無音長を計算"""
        if silence_mask.size == 0:
            return 0.0
        
        if from_start:
            if not (~silence_mask).any():
                return len(silence_mask) / sample_rate
            idx = np.argmax(~silence_mask)
            return idx / sample_rate
        else:
            reversed_mask = silence_mask[::-1]
            if not (~reversed_mask).any():
                return len(silence_mask) / sample_rate
            idx = np.argmax(~reversed_mask)
            return idx / sample_rate
    
    def _generate_cleaning_preset(self, analysis: Dict, sample_rate: int) -> Dict:
        """解析結果から自動でクリーニングプリセットを生成"""
        preset = {
            'enabled': True,
            'auto_generated': True,
            'highpass_freq': 80,  # デフォルト
            'hum_removal': False,
            'hum_frequencies': [],
            'hum_gains': [],
            'noise_reduction': False,
            'noise_floor': -28,
            'loudness_norm': True,
            'target_lufs': -20.0,
            'true_peak': -1.0,
            'lra': 11.0,
        }
        
        # === ハム除去の自動設定 ===
        hum_detection = analysis.get('hum_detection', {})
        significant_hums = []
        
        for base_freq, relative_strength in hum_detection.items():
            if relative_strength > 0.15:  # 15%以上の相対強度なら除去対象
                significant_hums.append((base_freq, relative_strength))
        
        if significant_hums:
            preset['hum_removal'] = True
            preset['hum_frequencies'] = []
            preset['hum_gains'] = []
            
            for base_freq, strength in significant_hums:
                # 基本周波数と倍音を設定
                harmonics = [base_freq * k for k in range(1, 9)]  # 8次まで
                gains = self._calculate_hum_gains(strength)
                
                preset['hum_frequencies'].extend(harmonics)
                preset['hum_gains'].extend(gains)
        
        # === ノイズ除去の自動設定 ===
        snr_db = analysis.get('snr_db')
        noise_floor_db = analysis.get('noise_floor_dbfs')
        
        if snr_db is not None and snr_db < 25:  # SNRが低い場合
            preset['noise_reduction'] = True
            if noise_floor_db is not None and noise_floor_db > -35:
                preset['noise_floor'] = max(-35, noise_floor_db - 5)  # ノイズ床より5dB下
        
        # === ハイパスフィルター調整 ===
        if any(strength > 0.3 for strength in hum_detection.values()):
            preset['highpass_freq'] = 100  # ハムが強い場合は少し高めに
        
        # === ラウドネス正規化調整 ===
        true_peak = analysis.get('true_peak_est', 0)
        if true_peak > 0.9:  # ピークが高い場合
            preset['true_peak'] = -1.5  # より保守的に
        
        clip_ratio = analysis.get('clip_ratio_per_ch', [0])
        if np.any(np.array(clip_ratio) > 0.001):  # クリップがある場合
            preset['true_peak'] = -2.0  # さらに保守的に
        
        return preset
    
    def _calculate_hum_gains(self, strength: float) -> List[float]:
        """ハム強度に基づいて各倍音の減衰量を計算"""
        # 強度に応じて基本的な減衰量を決定
        if strength > 0.8:      # 非常に強い
            base_gains = [-25, -25, -18, -18, -15, -15, -12, -12]
        elif strength > 0.5:    # 強い
            base_gains = [-20, -20, -15, -15, -12, -12, -9, -9]
        elif strength > 0.3:    # 中程度
            base_gains = [-15, -15, -12, -12, -9, -9, -6, -6]
        else:                   # 軽微
            base_gains = [-10, -10, -8, -8, -6, -6, -3, -3]
        
        return base_gains
    
    def get_analysis_summary(self) -> str:
        """解析結果の日本語サマリーを生成"""
        if not self.analysis_result:
            return "解析が実行されていません"
        
        analysis = self.analysis_result
        issues = []
        
        # ハムチェック
        hum_detection = analysis.get('hum_detection', {})
        for freq, strength in hum_detection.items():
            if strength > 0.2:
                issues.append(f"{int(freq)}Hz系ハム成分が検出されました（強度 {strength*100:.1f}%）")
        
        # クリッピングチェック
        clip_ratio = analysis.get('clip_ratio_per_ch', [0])
        if np.any(np.array(clip_ratio) > 0.001):
            issues.append(f"音割れ（クリップ）が検出されました")
        
        # SNRチェック
        snr_db = analysis.get('snr_db')
        if snr_db is not None and snr_db < 20:
            issues.append(f"SNRが低く、ノイズが多めです（{snr_db:.1f}dB）")
        
        # 真ピークチェック
        true_peak = analysis.get('true_peak_est', 0)
        if true_peak > 0.9:
            peak_db = 20 * np.log10(true_peak)
            issues.append(f"音量が大きすぎます（{peak_db:.1f}dBFS）")
        
        if not issues:
            return "✅ 音質に大きな問題は検出されませんでした"
        else:
            return "⚠️ 検出された問題:\n" + "\n".join(f"• {issue}" for issue in issues)
    
    def get_recommended_preset(self) -> Optional[Dict]:
        """推奨クリーニングプリセットを取得"""
        return self.recommended_preset
    
    def dbfs(self, value: float) -> float:
        """リニア値をdBFSに変換"""
        return 20.0 * math.log10(max(float(value), 1e-12))