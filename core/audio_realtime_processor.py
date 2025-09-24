import time
import numpy as np
from typing import List, Dict, Optional, Callable, Any, Tuple
from threading import Thread, Event, Lock
from queue import Queue, Empty
from dataclasses import dataclass
import traceback

try:
    from scipy import signal
    from scipy.fft import fft, fftfreq
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("⚠️ scipy が利用できません。音声解析機能が制限されます。")

@dataclass
class AudioFrame:
    """音声フレームデータ"""
    timestamp: float    # タイムスタンプ（秒）
    audio_data: np.ndarray  # 音声データ
    sample_rate: int    # サンプルレート
    frame_size: int     # フレームサイズ
    rms_level: float    # RMSレベル
    dominant_freq: float # 主要周波数

@dataclass
class VowelDetectionResult:
    """母音検出結果"""
    timestamp: float    # タイムスタンプ
    vowel: str         # 検出された母音
    confidence: float  # 信頼度 (0.0-1.0)
    formant_f1: float  # 第1フォルマント
    formant_f2: float  # 第2フォルマント
    intensity: float   # 強度

class AudioRealtimeProcessor:
    """リアルタイム音声処理エンジン
    
    音声データをリアルタイムで解析し、
    母音検出とリップシンク用データを生成する
    """
    
    def __init__(self, sample_rate: int = 22050, frame_size: int = 1024):
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.hop_size = frame_size // 2
        
        # 処理状態
        self.is_processing = False
        self.processing_thread = None
        self.stop_event = Event()
        
        # データキュー
        self.audio_queue = Queue(maxsize=100)
        self.result_queue = Queue(maxsize=50)
        
        # 同期用ロック
        self.process_lock = Lock()
        
        # 母音検出設定
        self.vowel_detection_settings = {
            'enabled': True,
            'confidence_threshold': 0.6,
            'smoothing_window': 3,
            'formant_analysis': SCIPY_AVAILABLE
        }
        
        # フォルマント周波数テーブル（日本語母音）
        self.vowel_formant_table = {
            'a': {'f1_range': (600, 900), 'f2_range': (1000, 1400)},   # あ
            'i': {'f1_range': (200, 400), 'f2_range': (2000, 2800)},   # い  
            'u': {'f1_range': (200, 400), 'f2_range': (600, 1200)},    # う
            'e': {'f1_range': (400, 600), 'f2_range': (1400, 2000)},   # え
            'o': {'f1_range': (400, 600), 'f2_range': (600, 1200)}     # お
        }
        
        # 音声解析バッファ
        self.analysis_buffer = np.array([])
        self.buffer_max_length = sample_rate * 2  # 2秒分のバッファ
        
        # 結果コールバック
        self.vowel_callback = None
        self.frame_callback = None
        
        print(f"✅ AudioRealtimeProcessor初期化完了")
        print(f"   サンプルレート: {sample_rate}Hz, フレームサイズ: {frame_size}")
        print(f"   scipy利用可能: {'Yes' if SCIPY_AVAILABLE else 'No'}")
    
    def set_vowel_callback(self, callback: Callable[[VowelDetectionResult], None]):
        """母音検出結果のコールバック設定"""
        self.vowel_callback = callback
    
    def set_frame_callback(self, callback: Callable[[AudioFrame], None]):
        """音声フレーム処理のコールバック設定"""
        self.frame_callback = callback
    
    def start_processing(self):
        """リアルタイム処理開始"""
        if self.is_processing:
            print("⚠️ 既に処理中です")
            return
        
        try:
            self.is_processing = True
            self.stop_event.clear()
            
            # 処理スレッド開始
            self.processing_thread = Thread(
                target=self._processing_loop,
                name="AudioRealtimeProcessor",
                daemon=True
            )
            self.processing_thread.start()
            
            print("🎵 リアルタイム音声処理を開始しました")
            
        except Exception as e:
            print(f"❌ 処理開始エラー: {e}")
            self.is_processing = False
    
    def stop_processing(self):
        """リアルタイム処理停止"""
        if not self.is_processing:
            return
        
        print("⏹️ リアルタイム音声処理を停止中...")
        
        self.stop_event.set()
        self.is_processing = False
        
        # スレッド終了を待機
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2.0)
        
        # キューをクリア
        self._clear_queues()
        
        print("✅ リアルタイム音声処理を停止しました")
    
    def add_audio_data(self, audio_data: np.ndarray, timestamp: float = None) -> bool:
        """音声データを処理キューに追加
        
        Args:
            audio_data: 音声データ（numpy配列）
            timestamp: タイムスタンプ（Noneの場合は現在時刻）
            
        Returns:
            bool: 追加成功時True
        """
        try:
            if timestamp is None:
                timestamp = time.time()
            
            # データ形式チェック
            if not isinstance(audio_data, np.ndarray):
                audio_data = np.array(audio_data, dtype=np.float32)
            
            # 正規化
            if audio_data.dtype != np.float32:
                if audio_data.dtype == np.int16:
                    audio_data = audio_data.astype(np.float32) / 32768.0
                elif audio_data.dtype == np.int32:
                    audio_data = audio_data.astype(np.float32) / 2147483648.0
                else:
                    audio_data = audio_data.astype(np.float32)
            
            # キューに追加
            frame_data = {
                'audio_data': audio_data,
                'timestamp': timestamp,
                'sample_rate': self.sample_rate
            }
            
            if not self.audio_queue.full():
                self.audio_queue.put(frame_data, timeout=0.1)
                return True
            else:
                print("⚠️ 音声キューが満杯です")
                return False
                
        except Exception as e:
            print(f"❌ 音声データ追加エラー: {e}")
            return False
    
    def get_latest_vowel_result(self) -> Optional[VowelDetectionResult]:
        """最新の母音検出結果を取得"""
        try:
            return self.result_queue.get(timeout=0.01)
        except Empty:
            return None
    
    def _processing_loop(self):
        """メイン処理ループ"""
        print("🔄 音声処理ループ開始")
        
        try:
            while not self.stop_event.is_set():
                try:
                    # 音声データを取得
                    frame_data = self.audio_queue.get(timeout=0.1)
                    
                    # フレーム処理
                    self._process_audio_frame(frame_data)
                    
                except Empty:
                    continue
                except Exception as e:
                    print(f"⚠️ フレーム処理エラー: {e}")
                    time.sleep(0.01)
                    
        except Exception as e:
            print(f"❌ 処理ループエラー: {e}")
            print(traceback.format_exc())
        finally:
            print("🔄 音声処理ループ終了")
    
    def _process_audio_frame(self, frame_data: Dict[str, Any]):
        """音声フレームを処理"""
        try:
            audio_data = frame_data['audio_data']
            timestamp = frame_data['timestamp']
            sample_rate = frame_data.get('sample_rate', self.sample_rate)
            
            # バッファに追加
            self._update_analysis_buffer(audio_data)
            
            # フレーム分析
            audio_frame = self._analyze_audio_frame(audio_data, timestamp, sample_rate)
            
            # フレームコールバック実行
            if self.frame_callback:
                self.frame_callback(audio_frame)
            
            # 母音検出（有効な場合のみ）
            if self.vowel_detection_settings['enabled'] and len(self.analysis_buffer) >= self.frame_size:
                vowel_result = self._detect_vowel(audio_frame)
                if vowel_result:
                    # 結果をキューに追加
                    if not self.result_queue.full():
                        self.result_queue.put(vowel_result)
                    
                    # コールバック実行
                    if self.vowel_callback:
                        self.vowel_callback(vowel_result)
            
        except Exception as e:
            print(f"⚠️ フレーム処理エラー: {e}")
    
    def _update_analysis_buffer(self, audio_data: np.ndarray):
        """解析用バッファを更新"""
        with self.process_lock:
            # バッファに追加
            self.analysis_buffer = np.concatenate([self.analysis_buffer, audio_data])
            
            # バッファサイズ制限
            if len(self.analysis_buffer) > self.buffer_max_length:
                excess = len(self.analysis_buffer) - self.buffer_max_length
                self.analysis_buffer = self.analysis_buffer[excess:]
    
    def _analyze_audio_frame(self, audio_data: np.ndarray, timestamp: float, sample_rate: int) -> AudioFrame:
        """音声フレームの基本分析"""
        try:
            # RMSレベル計算
            rms_level = np.sqrt(np.mean(audio_data ** 2))
            
            # 主要周波数計算（SCIPY使用可能時）
            dominant_freq = 0.0
            if SCIPY_AVAILABLE and len(audio_data) > 0:
                dominant_freq = self._calculate_dominant_frequency(audio_data, sample_rate)
            
            audio_frame = AudioFrame(
                timestamp=timestamp,
                audio_data=audio_data.copy(),
                sample_rate=sample_rate,
                frame_size=len(audio_data),
                rms_level=rms_level,
                dominant_freq=dominant_freq
            )
            
            return audio_frame
            
        except Exception as e:
            print(f"⚠️ フレーム分析エラー: {e}")
            return AudioFrame(
                timestamp=timestamp,
                audio_data=audio_data,
                sample_rate=sample_rate,
                frame_size=len(audio_data),
                rms_level=0.0,
                dominant_freq=0.0
            )
    
    def _calculate_dominant_frequency(self, audio_data: np.ndarray, sample_rate: int) -> float:
        """主要周波数を計算"""
        try:
            if len(audio_data) < 64:  # 最小サンプル数チェック
                return 0.0
            
            # FFT計算
            fft_data = fft(audio_data)
            freqs = fftfreq(len(audio_data), 1.0 / sample_rate)
            
            # パワースペクトル
            power_spectrum = np.abs(fft_data)
            
            # 正の周波数のみ
            positive_freqs = freqs[:len(freqs)//2]
            positive_power = power_spectrum[:len(power_spectrum)//2]
            
            # 主要周波数検出
            if len(positive_power) > 0:
                max_idx = np.argmax(positive_power)
                dominant_freq = positive_freqs[max_idx]
                return abs(dominant_freq)
            
            return 0.0
            
        except Exception as e:
            print(f"⚠️ 周波数計算エラー: {e}")
            return 0.0
    
    def _detect_vowel(self, audio_frame: AudioFrame) -> Optional[VowelDetectionResult]:
        """母音検出"""
        try:
            if not SCIPY_AVAILABLE:
                return self._simple_vowel_detection(audio_frame)
            
            # フォルマント解析による母音検出
            formants = self._extract_formants(audio_frame.audio_data, audio_frame.sample_rate)
            
            if not formants or len(formants) < 2:
                return self._simple_vowel_detection(audio_frame)
            
            f1, f2 = formants[0], formants[1]
            
            # フォルマントから母音を推定
            vowel, confidence = self._classify_vowel_by_formants(f1, f2)
            
            # 信頼度チェック
            if confidence < self.vowel_detection_settings['confidence_threshold']:
                return None
            
            # 強度計算
            intensity = min(1.0, audio_frame.rms_level * 5.0)
            
            vowel_result = VowelDetectionResult(
                timestamp=audio_frame.timestamp,
                vowel=vowel,
                confidence=confidence,
                formant_f1=f1,
                formant_f2=f2,
                intensity=intensity
            )
            
            return vowel_result
            
        except Exception as e:
            print(f"⚠️ 母音検出エラー: {e}")
            return self._simple_vowel_detection(audio_frame)
    
    def _extract_formants(self, audio_data: np.ndarray, sample_rate: int) -> List[float]:
        """フォルマント抽出"""
        try:
            if len(audio_data) < self.frame_size:
                return []
            
            # 窓関数適用
            windowed = audio_data * np.hanning(len(audio_data))
            
            # FFT
            fft_data = fft(windowed)
            freqs = fftfreq(len(windowed), 1.0 / sample_rate)
            power_spectrum = np.abs(fft_data)
            
            # 正の周波数のみ
            positive_freqs = freqs[:len(freqs)//2]
            positive_power = power_spectrum[:len(power_spectrum)//2]
            
            # ピーク検出（フォルマント候補）
            peaks = []
            
            # 200-3000Hz範囲でピーク検出
            freq_min, freq_max = 200, 3000
            start_idx = np.argmin(np.abs(positive_freqs - freq_min))
            end_idx = np.argmin(np.abs(positive_freqs - freq_max))
            
            if start_idx >= end_idx:
                return []
            
            # シンプルなピーク検出
            search_range = positive_power[start_idx:end_idx]
            search_freqs = positive_freqs[start_idx:end_idx]
            
            # ローカルマキシマ検出
            for i in range(1, len(search_range) - 1):
                if (search_range[i] > search_range[i-1] and 
                    search_range[i] > search_range[i+1] and
                    search_range[i] > np.max(search_range) * 0.1):  # 最大値の10%以上
                    
                    peaks.append((search_freqs[i], search_range[i]))
            
            # パワーでソート
            peaks.sort(key=lambda x: x[1], reverse=True)
            
            # 上位のピークをフォルマントとして返す
            formants = [peak[0] for peak in peaks[:4]]  # 最大4個のフォルマント
            
            return sorted(formants)  # 周波数順にソート
            
        except Exception as e:
            print(f"⚠️ フォルマント抽出エラー: {e}")
            return []
    
    def _classify_vowel_by_formants(self, f1: float, f2: float) -> Tuple[str, float]:
        """フォルマント値から母音を分類"""
        try:
            best_vowel = 'a'
            best_score = 0.0
            
            for vowel, formant_info in self.vowel_formant_table.items():
                f1_range = formant_info['f1_range']
                f2_range = formant_info['f2_range']
                
                # 各フォルマントの適合度計算
                f1_score = self._calculate_range_score(f1, f1_range)
                f2_score = self._calculate_range_score(f2, f2_range)
                
                # 総合スコア
                total_score = (f1_score + f2_score) / 2
                
                if total_score > best_score:
                    best_score = total_score
                    best_vowel = vowel
            
            return best_vowel, best_score
            
        except Exception as e:
            print(f"⚠️ 母音分類エラー: {e}")
            return 'a', 0.5
    
    def _calculate_range_score(self, value: float, range_tuple: Tuple[float, float]) -> float:
        """値が範囲にどれだけ適合するかスコア化"""
        min_val, max_val = range_tuple
        
        if min_val <= value <= max_val:
            # 範囲内の場合、中央に近いほど高スコア
            center = (min_val + max_val) / 2
            distance = abs(value - center)
            max_distance = (max_val - min_val) / 2
            return 1.0 - (distance / max_distance)
        else:
            # 範囲外の場合、距離に応じて減点
            if value < min_val:
                distance = min_val - value
            else:
                distance = value - max_val
            
            # 範囲幅の2倍まで許容（それ以上は0点）
            tolerance = (max_val - min_val) * 2
            return max(0.0, 1.0 - (distance / tolerance))
    
    def _simple_vowel_detection(self, audio_frame: AudioFrame) -> Optional[VowelDetectionResult]:
        """シンプル母音検出（フォールバック）"""
        try:
            # RMSレベルベースの簡易検出
            rms_level = audio_frame.rms_level
            
            # 音量が低すぎる場合は無音
            if rms_level < 0.01:
                return VowelDetectionResult(
                    timestamp=audio_frame.timestamp,
                    vowel='sil',
                    confidence=0.8,
                    formant_f1=0.0,
                    formant_f2=0.0,
                    intensity=0.0
                )
            
            # 主要周波数ベースの推定
            dominant_freq = audio_frame.dominant_freq
            
            # 簡易的な母音推定（周波数ベース）
            if dominant_freq < 500:
                vowel = 'u'  # 低い周波数：う
            elif dominant_freq < 1000:
                vowel = 'o'  # 中低域：お
            elif dominant_freq < 1500:
                vowel = 'a'  # 中域：あ
            elif dominant_freq < 2000:
                vowel = 'e'  # 中高域：え
            else:
                vowel = 'i'  # 高い周波数：い
            
            intensity = min(1.0, rms_level * 3.0)
            
            return VowelDetectionResult(
                timestamp=audio_frame.timestamp,
                vowel=vowel,
                confidence=0.6,
                formant_f1=dominant_freq * 0.3,
                formant_f2=dominant_freq,
                intensity=intensity
            )
            
        except Exception as e:
            print(f"⚠️ シンプル母音検出エラー: {e}")
            return None
    
    def _clear_queues(self):
        """キューをクリア"""
        try:
            while not self.audio_queue.empty():
                self.audio_queue.get_nowait()
        except Empty:
            pass
        
        try:
            while not self.result_queue.empty():
                self.result_queue.get_nowait()
        except Empty:
            pass
    
    def update_settings(self, settings: Dict[str, Any]):
        """処理設定を更新"""
        try:
            if 'vowel_detection' in settings:
                vowel_settings = settings['vowel_detection']
                self.vowel_detection_settings.update(vowel_settings)
                print(f"🔧 母音検出設定更新: {vowel_settings}")
            
            if 'frame_size' in settings:
                new_frame_size = settings['frame_size']
                if new_frame_size != self.frame_size:
                    self.frame_size = new_frame_size
                    self.hop_size = new_frame_size // 2
                    print(f"🔧 フレームサイズ更新: {new_frame_size}")
            
        except Exception as e:
            print(f"❌ 設定更新エラー: {e}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """処理統計情報を取得"""
        return {
            'is_processing': self.is_processing,
            'audio_queue_size': self.audio_queue.qsize(),
            'result_queue_size': self.result_queue.qsize(),
            'buffer_length': len(self.analysis_buffer),
            'sample_rate': self.sample_rate,
            'frame_size': self.frame_size,
            'scipy_available': SCIPY_AVAILABLE,
            'vowel_detection_enabled': self.vowel_detection_settings['enabled']
        }
    
    def __del__(self):
        """デストラクタ"""
        self.stop_processing()