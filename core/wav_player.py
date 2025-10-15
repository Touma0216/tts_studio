import numpy as np
import sounddevice as sd
import soundfile as sf
from pathlib import Path
from typing import Optional, Callable, List, Tuple
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
import threading
from collections import deque

class WAVPlayer(QObject):
    """WAVファイル再生エンジン（リップシンク同期対応 + キュー機能）"""
    
    playback_position_changed = pyqtSignal(float)  # 現在の再生位置（秒）
    playback_finished = pyqtSignal()
    playback_started = pyqtSignal()
    playback_paused = pyqtSignal()
    playback_stopped = pyqtSignal()
    queue_item_started = pyqtSignal(int)  # キューアイテム再生開始（インデックス）
    queue_item_finished = pyqtSignal(int)  # キューアイテム完了（インデックス）
    queue_finished = pyqtSignal()  # キュー全体完了
    
    def __init__(self):
        super().__init__()
        self.audio_data: Optional[np.ndarray] = None
        self.sample_rate: Optional[int] = None
        self.duration: float = 0.0
        self.current_position: float = 0.0
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.volume: float = 1.0
        
        self._stream = None
        self._position_timer = QTimer()
        self._position_timer.timeout.connect(self._update_position)
        self._playback_thread = None
        self._playback_start_time = 0.0
        self._playback_start_position = 0.0
        self._playback_session_id = 0
        self._active_session_id = 0
        
        # 🆕 キュー機能
        self._queue: deque = deque()  # [(audio_data, sample_rate, lipsync_data), ...]
        self._queue_enabled: bool = False
        self._current_queue_index: int = -1
        self._queue_playing: bool = False

        self._queue_stream = None
        self._queue_stream_sr: Optional[int] = None
        self._queue_stream_lock = threading.Lock()
        
        self.playback_finished.connect(self._on_playback_finished)
    
    # ========================================
    # 🆕 キュー機能
    # ========================================
    
    def enable_queue_mode(self, enabled: bool = True):
        """キューモードを有効化
        
        Args:
            enabled: True=キューモード、False=通常モード
        """
        self._queue_enabled = enabled
        if not enabled:
            self._queue.clear()
            self._current_queue_index = -1
            self._queue_playing = False
            self._close_queue_stream()
        print(f"🎵 キューモード: {'有効' if enabled else '無効'}")
    
    def add_to_queue(self, audio: np.ndarray, sample_rate: int, lipsync_data=None):
        """キューに音声を追加
        
        Args:
            audio: 音声データ
            sample_rate: サンプルレート
            lipsync_data: リップシンクデータ（オプション）
        """
        if not self._queue_enabled:
            print("⚠️ キューモードが無効です。enable_queue_mode(True)を呼び出してください")
            return
        
        self._queue.append((audio, sample_rate, lipsync_data))
        print(f"📥 キュー追加: {len(audio)/sample_rate:.2f}秒 (キューサイズ: {len(self._queue)})")
    
    def start_queue_playback(self):
        """キューの再生を開始"""
        if not self._queue_enabled:
            print("⚠️ キューモードが無効です")
            return
        
        if not self._queue:
            print("⚠️ キューが空です")
            return
        
        if self._queue_playing:
            print("⚠️ 既にキュー再生中です")
            return
        
        print(f"▶️ キュー再生開始: {len(self._queue)}個")
        self._queue_playing = True
        self._current_queue_index = -1
        self._play_next_in_queue()
    
    def _play_next_in_queue(self):
        """キューの次のアイテムを再生"""
        if not self._queue_enabled or not self._queue_playing:
            return
        
        if not self._queue:
            # キュー終了
            print("✅ キュー全体完了")
            self._queue_playing = False
            self._current_queue_index = -1
            self.queue_finished.emit()
            self._close_queue_stream()
            return
        
        # 次のアイテムを取り出す
        self._current_queue_index += 1
        audio, sample_rate, lipsync_data = self._queue.popleft()
        
        print(f"  🎵 [{self._current_queue_index + 1}] 再生開始: {len(audio)/sample_rate:.2f}秒")
        
        # 音声データをロード
        self.load_audio(audio, sample_rate)
        
        # リップシンクデータを保存（外部で使用）
        self._current_lipsync_data = lipsync_data
        
        # 再生開始
        self.play()
        self.queue_item_started.emit(self._current_queue_index)
    
    def stop_queue_playback(self):
        """キュー再生を停止"""
        print("⏹️ キュー再生停止")
        self._queue_playing = False
        self._queue.clear()
        self._current_queue_index = -1
        self.stop()
    
    def get_queue_size(self) -> int:
        """現在のキューサイズを取得"""
        return len(self._queue)
    
    def get_current_queue_index(self) -> int:
        """現在再生中のキューインデックスを取得"""
        return self._current_queue_index
    
    def get_current_lipsync_data(self):
        """現在のリップシンクデータを取得"""
        return getattr(self, '_current_lipsync_data', None)
    
    # ========================================
    # 既存の機能（修正版）
    # ========================================
    
    def load_audio(self, audio: np.ndarray, sample_rate: int):
        """音声データを直接ロード
        
        Args:
            audio: 音声データ（numpy配列）
            sample_rate: サンプルレート
        """
        try:
            # モノラル化
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)
            
            self.audio_data = audio.astype(np.float32)
            self.sample_rate = sample_rate
            self.duration = len(audio) / sample_rate
            self.current_position = 0.0
            
            print(f"✅ 音声ロード完了: {self.duration:.2f}秒")
            return True
            
        except Exception as e:
            print(f"❌ 音声ロードエラー: {e}")
            return False
    
    def load_wav_file(self, file_path: str) -> bool:
        """WAVファイルを読み込み"""
        try:
            path = Path(file_path)
            if not path.exists():
                print(f"❌ ファイルが見つかりません: {file_path}")
                return False
            
            audio, sr = sf.read(file_path, dtype='float32')
            return self.load_audio(audio, sr)
            
        except Exception as e:
            print(f"❌ WAV読み込みエラー: {e}")
            return False
    
    def play(self, start_position: float = None):
        """再生開始"""
        if self.audio_data is None:
            print("⚠️ 音声データが読み込まれていません")
            return
        
        if self.is_playing and not self.is_paused:
            print("⚠️ 既に再生中です")
            return
        
        if start_position is not None:
            self.current_position = max(0.0, min(start_position, self.duration))
        
        if self.is_paused:
            self.is_paused = False
        else:
            if start_position is not None:
                self.current_position = start_position
        
        self.is_playing = True
        self._playback_session_id += 1
        session_id = self._playback_session_id
        self._active_session_id = session_id
        
        import time
        self._playback_start_time = time.time()
        self._playback_start_position = self.current_position
        
        self._start_playback(session_id)
        self._position_timer.start(50)
        
        self.playback_started.emit()
        print(f"▶️ 再生開始: {self.current_position:.2f}秒から")
    
    def pause(self):
        """一時停止"""
        if not self.is_playing:
            return
        
        self.is_paused = True
        self.is_playing = False
        self._stop_playback()
        self._position_timer.stop()
        
        self.playback_paused.emit()
        print(f"⏸️ 一時停止: {self.current_position:.2f}秒")
    
    def stop(self):
        """停止"""
        if not self.is_playing and not self.is_paused:
            return
        
        self.is_playing = False
        self.is_paused = False
        self._stop_playback()
        self._position_timer.stop()
        self._active_session_id = 0
        
        self.playback_stopped.emit()
        print("⏹️ 停止")
    
    def seek(self, position: float):
        """再生位置を変更"""
        if self.audio_data is None:
            return
        
        was_playing = self.is_playing
        
        if was_playing:
            self.pause()
        
        self.current_position = max(0.0, min(position, self.duration))
        self.playback_position_changed.emit(self.current_position)
        
        if was_playing:
            self.play(self.current_position)
    
    def set_volume(self, volume: float):
        """音量設定（0.0〜2.0）"""
        self.volume = max(0.0, min(2.0, volume))
    
    def _start_playback(self, session_id: int):
        """内部：再生開始"""
        try:
            start_sample = int(self.current_position * self.sample_rate)
            audio_segment = self.audio_data[start_sample:]
            
            expected_duration = len(audio_segment) / self.sample_rate
            print(f"🔍 再生データ: {len(audio_segment)}サンプル, 予想時間: {expected_duration:.2f}秒")
            
            audio_segment = np.ascontiguousarray(audio_segment * self.volume, dtype=np.float32)
            
            def play_audio(expected_session_id=session_id):
                try:
                    import time
                    play_start = time.time()
                    if self._queue_enabled and self._queue_playing:
                        if self._ensure_queue_stream(self.sample_rate):
                            # OutputStreamは(サンプル, チャンネル)の配列を想定
                            stream_data = audio_segment
                            if stream_data.ndim == 1:
                                stream_data = stream_data.reshape(-1, 1)
                            with self._queue_stream_lock:
                                self._queue_stream.write(stream_data)
                        else:
                            sd.play(audio_segment, self.sample_rate, blocking=True)
                    else:
                        sd.play(audio_segment, self.sample_rate, blocking=True)
                    actual_duration = time.time() - play_start
                    print(f"🔍 実際の再生時間: {actual_duration:.2f}秒")
                    
                    if self._active_session_id == expected_session_id:
                        self.is_playing = False
                        self.playback_finished.emit()
                except Exception as e:
                    print(f"❌ 再生エラー: {e}")
            
            self._playback_thread = threading.Thread(target=play_audio, daemon=True)
            self._playback_thread.start()
            
        except Exception as e:
            print(f"❌ 再生開始エラー: {e}")
    
    def _stop_playback(self):
        """内部：再生停止"""
        try:
            sd.stop()
            if self._stream:
                self._stream.close()
                self._stream = None
            if not self._queue_playing:
                self._close_queue_stream()
        except Exception as e:
            print(f"⚠️ 停止エラー: {e}")
    
    def _update_position(self):
        """内部：再生位置を更新"""
        if not self.is_playing:
            return
        
        import time
        elapsed = time.time() - self._playback_start_time
        self.current_position = self._playback_start_position + elapsed
        
        self.playback_position_changed.emit(self.current_position)
        
    def _on_playback_finished(self):
        """再生完了時の処理"""
        self._position_timer.stop()
        self.current_position = self.duration
        self.is_playing = False
        self.is_paused = False
        self._active_session_id = 0
        self.playback_position_changed.emit(self.current_position)
        
        # 🆕 キューモードの場合は次を再生
        if self._queue_enabled and self._queue_playing:
            print(f"  ✅ [{self._current_queue_index + 1}] 完了")
            self.queue_item_finished.emit(self._current_queue_index)
            
            # 🔧 待機時間を500msに延長（語尾保護）
            QTimer.singleShot(500, self._play_next_in_queue)
    
    def get_audio_data(self) -> Optional[np.ndarray]:
        """音声データを取得"""
        return self.audio_data
    
    def get_sample_rate(self) -> Optional[int]:
        """サンプルレートを取得"""
        return self.sample_rate
    
    def get_duration(self) -> float:
        """総再生時間を取得"""
        return self.duration
    
    def get_current_position(self) -> float:
        """現在の再生位置を取得"""
        return self.current_position
    
    def is_loaded(self) -> bool:
        """WAVファイルが読み込まれているか"""
        return self.audio_data is not None
    
    def _ensure_queue_stream(self, sample_rate: int) -> bool:
        """キューモード用の連続再生ストリームを準備"""
        if self._queue_stream and self._queue_stream_sr == sample_rate:
            return True

        self._close_queue_stream()

        try:
            stream = sd.OutputStream(
                samplerate=sample_rate,
                channels=1,
                dtype='float32',
                blocksize=0,
            )
            stream.start()
            self._queue_stream = stream
            self._queue_stream_sr = sample_rate
            print("🔊 連続ストリーム初期化")
            return True
        except Exception as e:
            print(f"❌ 連続ストリーム初期化エラー: {e}")
            self._queue_stream = None
            self._queue_stream_sr = None
            return False

    def _close_queue_stream(self):
        """キューモード用のストリームをクローズ"""
        with self._queue_stream_lock:
            if self._queue_stream is None:
                return

            try:
                self._queue_stream.abort()
            except Exception:
                pass

            try:
                self._queue_stream.stop()
            except Exception:
                pass

            try:
                self._queue_stream.close()
            except Exception:
                pass

            self._queue_stream = None
            self._queue_stream_sr = None
            print("🔇 連続ストリーム終了")