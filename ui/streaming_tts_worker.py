"""
ストリーミングTTSワーカー - チャンク単位で処理・配信
"""

import traceback
from typing import Dict, List, Optional
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread

from core.tts_engine import TTSEngine
from core.lip_sync_engine import LipSyncEngine
from core.audio_processor import AudioProcessor
from core.audio_effects_processor import AudioEffectsProcessor


class StreamingTTSWorker(QObject):
    """チャンク単位でストリーミング処理するワーカー
    
    特徴:
    - 先行バッファリング（3チャンク先まで生成）
    - 1チャンク完成ごとに即座に配信
    - メモリ効率的（全部溜め込まない）
    - キャンセル可能
    """
    
    # シグナル定義
    chunk_ready = pyqtSignal(int, int, object, object)  # (index, sr, audio, lipsync)
    progress_updated = pyqtSignal(int, int)  # (current, total)
    all_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    processing_started = pyqtSignal(int)  # (total_count)
    
    def __init__(
        self,
        tts_engine: TTSEngine,
        lip_sync_engine: LipSyncEngine,
        audio_processor: AudioProcessor,
        audio_effects_processor: AudioEffectsProcessor
    ):
        super().__init__()
        self.tts_engine = tts_engine
        self.lip_sync_engine = lip_sync_engine
        self.audio_processor = audio_processor
        self.audio_effects_processor = audio_effects_processor
        
        # 設定
        self.buffer_size = 3  # 先行バッファ数（調整可能）
        self.is_cancelled = False
        
        print("✅ StreamingTTSWorker初期化完了")
    
    @pyqtSlot(object, object)
    def synthesize_streaming(self, texts_data: List[Dict], options: Dict):
        """ストリーミング方式で処理
        
        Args:
            texts_data: テキストデータリスト
            options: 処理オプション（cleaner, effects等）
        """
        try:
            self.is_cancelled = False
            total = len(texts_data)
            
            if total == 0:
                print("⚠️ 処理するテキストがありません")
                self.all_finished.emit()
                return
            
            print(f"🎬 ストリーミング処理開始: {total}個のテキスト")
            self.processing_started.emit(total)
            
            # バッファ管理
            ready_buffer = {}  # {index: (sr, audio, lipsync)}
            processing_indices = set()  # 処理中のインデックス
            
            # 最初のbuffer_size個を先行生成開始
            for i in range(min(self.buffer_size, total)):
                self._start_chunk_processing_async(i, texts_data[i], options, ready_buffer, processing_indices)
            
            # 順次配信ループ
            for current_index in range(total):
                if self.is_cancelled:
                    print("🛑 キャンセルされました")
                    break
                
                # このチャンクが準備完了するまで待機
                while current_index not in ready_buffer:
                    if self.is_cancelled:
                        break
                    QThread.msleep(50)  # 50ms待機
                
                if self.is_cancelled:
                    break
                
                # 準備完了したチャンクを配信
                result = ready_buffer.pop(current_index)
                processing_indices.discard(current_index)
                
                if result is not None:
                    sr, audio, lipsync = result
                    
                    if sr is not None and audio is not None:
                        self.chunk_ready.emit(current_index, sr, audio, lipsync)
                        print(f"  ✅ [{current_index + 1}/{total}] チャンク配信完了")
                
                self.progress_updated.emit(current_index + 1, total)
                
                # 次のチャンクを生成開始
                next_index = current_index + self.buffer_size
                if next_index < total:
                    self._start_chunk_processing_async(
                        next_index, 
                        texts_data[next_index], 
                        options, 
                        ready_buffer,
                        processing_indices
                    )
            
            if not self.is_cancelled:
                print("✅ ストリーミング処理完了")
                self.all_finished.emit()
            
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"❌ ストリーミング処理エラー:\n{error_trace}")
            self.error_occurred.emit(error_trace)
    
    def _start_chunk_processing_async(
        self, 
        index: int, 
        entry: Dict, 
        options: Dict,
        result_buffer: Dict,
        processing_indices: set
    ):
        """1チャンクを非同期で処理開始してバッファに格納
        
        Args:
            index: チャンクインデックス
            entry: テキストデータ
            options: 処理オプション
            result_buffer: 結果格納用バッファ
            processing_indices: 処理中インデックスのセット
        """
        try:
            text = entry.get('text', '').strip()
            if not text:
                result_buffer[index] = None
                return
            
            processing_indices.add(index)
            
            # 別スレッドで処理（実際にはこのワーカー自体が別スレッドなので直接実行）
            result = self._process_single_chunk(index, entry, options)
            result_buffer[index] = result
            
        except Exception as e:
            print(f"❌ チャンク{index}処理エラー: {e}")
            result_buffer[index] = None
    
    def _process_single_chunk(self, index: int, entry: Dict, options: Dict) -> Optional[tuple]:
        """1チャンクを処理
        
        Returns:
            (sample_rate, audio, lipsync_data) or None
        """
        try:
            text = entry.get('text', '').strip()
            if not text:
                return None
            
            params = entry.get('parameters', {})
            
            print(f"  🔄 [{index + 1}] 処理開始: '{text[:30]}...'")
            
            # 1. TTS生成
            sr, audio = self.tts_engine.synthesize(text, **params)
            
            if audio is None or sr is None:
                print(f"  ⚠️ [{index + 1}] TTS生成失敗")
                return None
            
            # 2. 音声処理（クリーナー）
            if options.get('apply_cleaner') and self.audio_processor:
                cleaner_settings = options.get('cleaner_settings', {})
                audio = self.audio_processor.process_audio(audio, sr, cleaner_settings)
            
            # 3. 音声エフェクト
            if options.get('apply_effects') and self.audio_effects_processor:
                effects_settings = options.get('effects_settings', {})
                audio = self.audio_effects_processor.process_effects(audio, sr, effects_settings)
            
            # 4. 無音トリミング
            trim_threshold = float(options.get('trim_threshold', 0.0))
            if trim_threshold > 0:
                audio = self._trim_silence(audio, sr, trim_threshold)
            
            # 5. リップシンク生成
            lipsync = None
            if options.get('enable_lipsync') and self.lip_sync_engine.is_available():
                lipsync = self.lip_sync_engine.analyze_text_for_lipsync(
                    text=text,
                    audio_data=audio,  # 👈 無音追加前の音声で解析してる
                    sample_rate=sr
                )

            # 6. silence_after を反映
            silence_after = float(entry.get('silence_after', 0.0) or 0.0)
            if silence_after > 0:
                silence_samples = int(sr * silence_after)
                silence_padding = np.zeros(silence_samples, dtype=np.float32)
                audio = np.concatenate([audio, silence_padding])  # 👈 音声に無音追加
                
                # 🆕 リップシンクにも無音フレーム追加
                if lipsync:
                    from core.lip_sync_engine import VowelFrame
                    lipsync.vowel_frames.append(
                        VowelFrame(
                            timestamp=lipsync.total_duration,
                            vowel='sil',
                            intensity=0.0,
                            duration=silence_after,
                            is_ending=True
                        )
                    )
                    lipsync.total_duration += silence_after
            print(f"  ✅ [{index + 1}] 処理完了: {len(audio)/sr:.2f}秒")
            
            return (sr, audio, lipsync)
            
        except Exception as e:
            print(f"❌ チャンク{index}処理中エラー: {e}")
            import traceback
            traceback.print_exc()
            return None

    
    @staticmethod
    def _trim_silence(audio: np.ndarray, sample_rate: int, threshold: float) -> np.ndarray:
        """末尾の無音をトリミング"""
        if audio.size == 0 or threshold <= 0:
            return audio
        
        indices = np.where(np.abs(audio) > threshold)[0]
        if indices.size == 0:
            return audio
        
        end_index = indices[-1] + int(sample_rate * 0.1)
        end_index = min(end_index, audio.size)
        return audio[:end_index]
    
    def cancel(self):
        """処理をキャンセル"""
        print("🛑 ストリーミング処理をキャンセル")
        self.is_cancelled = True