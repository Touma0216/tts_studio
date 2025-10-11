import numpy as np
import sounddevice as sd
import soundfile as sf
from pathlib import Path
from typing import Optional, Callable
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
import threading

class WAVPlayer(QObject):
    """WAVファイル再生エンジン（リップシンク同期対応）"""
    
    playback_position_changed = pyqtSignal(float)  # 現在の再生位置（秒）
    playback_finished = pyqtSignal()
    playback_started = pyqtSignal()
    playback_paused = pyqtSignal()
    playback_stopped = pyqtSignal()
    
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
        self._playback_start_time = 0.0  # 🔥 追加
        self._playback_start_position = 0.0  # 🔥 追加
        self._playback_session_id = 0
        self._active_session_id = 0
        
        # 🔥 追加：再生完了時の処理
        self.playback_finished.connect(self._on_playback_finished)
        
    def load_wav_file(self, file_path: str) -> bool:
        """WAVファイルを読み込み"""
        try:
            path = Path(file_path)
            if not path.exists():
                print(f"❌ ファイルが見つかりません: {file_path}")
                return False
            
            # soundfileで読み込み
            audio, sr = sf.read(file_path, dtype='float32')
            
            # モノラル化（必要に応じて）
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)
            
            self.audio_data = audio
            self.sample_rate = sr
            self.duration = len(audio) / sr
            self.current_position = 0.0
            
            print(f"✅ WAV読み込み完了: {path.name}")
            print(f"   長さ: {self.duration:.2f}秒, サンプルレート: {sr}Hz")
            
            return True
            
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
            # 一時停止から再開
            self.is_paused = False
        else:
            # 新規または明示的な開始位置からの再生
            if start_position is not None:
                self.current_position = start_position
        
        self.is_playing = True

        # セッションIDを更新して古い再生完了イベントを無効化
        self._playback_session_id += 1
        session_id = self._playback_session_id
        self._active_session_id = session_id
        
        # 🔥 追加：再生開始時刻を記録
        import time
        self._playback_start_time = time.time()
        self._playback_start_position = self.current_position
        
        self._start_playback(session_id)
        self._position_timer.start(50)  # 50msごとに位置更新
        
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
            
            # 🔍 デバッグログ追加
            expected_duration = len(audio_segment) / self.sample_rate
            print(f"🔍 再生データ: {len(audio_segment)}サンプル, 予想時間: {expected_duration:.2f}秒")
            print(f"🔍 開始位置: {self.current_position:.2f}秒, 開始サンプル: {start_sample}")
            
            audio_segment = audio_segment * self.volume
            
            # 別スレッドで再生
            def play_audio(expected_session_id=session_id):
                try:
                    import time
                    play_start = time.time()
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
        except Exception as e:
            print(f"⚠️ 停止エラー: {e}")
    
    def _update_position(self):
        """内部：再生位置を更新"""
        if not self.is_playing:
            return
        
        # 🔥 修正：実際の経過時間から位置を計算
        import time
        elapsed = time.time() - self._playback_start_time
        self.current_position = self._playback_start_position + elapsed
        
        # タイマー停止はplayback_finishedで行う
        self.playback_position_changed.emit(self.current_position)
    
    def _on_playback_finished(self):
        """再生完了時の処理"""
        self._position_timer.stop()
        self.current_position = self.duration
        self.is_playing = False
        self.is_paused = False
        self._active_session_id = 0
        self.playback_position_changed.emit(self.current_position)
    
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
