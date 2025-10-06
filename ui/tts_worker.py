from __future__ import annotations

import traceback
from typing import Dict, List

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from core.lip_sync_engine import LipSyncEngine
from core.lip_sync_engine import LipSyncData, VowelFrame
from core.tts_engine import TTSEngine
from core.audio_processor import AudioProcessor
from core.audio_effects_processor import AudioEffectsProcessor

class TTSWorker(QObject):
    """バックグラウンドでTTSとリップシンク解析を行うワーカー（音声同期対応版）"""

    synthesis_finished = pyqtSignal(object, object, object, object)

    def __init__(self, tts_engine: TTSEngine, lip_sync_engine: LipSyncEngine):
        super().__init__()
        self._tts_engine = tts_engine
        self._lip_sync_engine = lip_sync_engine

    @pyqtSlot(str, dict, bool)
    def synthesize(self, text: str, parameters: Dict, enable_lipsync: bool) -> None:
        """指定されたテキストを合成し、必要であればリップシンクデータも生成する（音声同期版）"""
        try:
            # 1. TTS音声生成
            sample_rate, audio = self._tts_engine.synthesize(text, **parameters)

            lipsync_data = None
            if enable_lipsync and self._lip_sync_engine and self._lip_sync_engine.is_available():
                # 🔥 修正：生成された音声データを使ってリップシンク解析
                print(f"🎭 音声同期リップシンク解析開始: {len(audio)} samples, {sample_rate}Hz")
                lipsync_data = self._lip_sync_engine.analyze_text_for_lipsync(
                    text=text,
                    audio_data=audio,
                    sample_rate=sample_rate
                )
                
                if lipsync_data:
                    print(f"✅ リップシンク解析完了: {len(lipsync_data.vowel_frames)}フレーム, {lipsync_data.total_duration:.3f}秒")
                else:
                    print("⚠️ リップシンク解析失敗")

            self.synthesis_finished.emit(sample_rate, audio, lipsync_data, None)
        except Exception:
            error_trace = traceback.format_exc()
            self.synthesis_finished.emit(None, None, None, error_trace)


class SequentialTTSWorker(QObject):
    """複数テキストをまとめて合成するバックグラウンドワーカー"""

    sequence_finished = pyqtSignal(object, object, object, object)

    def __init__(
        self,
        tts_engine: TTSEngine,
        lip_sync_engine: LipSyncEngine,
        audio_processor: AudioProcessor,
        audio_effects_processor: AudioEffectsProcessor,
    ):
        super().__init__()
        self._tts_engine = tts_engine
        self._lip_sync_engine = lip_sync_engine
        self._audio_processor = audio_processor
        self._audio_effects_processor = audio_effects_processor

    @pyqtSlot(object, object)
    def synthesize_sequence(self, texts_data: List[Dict], options: Dict) -> None:
        """複数テキストを連続再生用に合成"""

        try:
            if not texts_data:
                self.sequence_finished.emit(None, None, None, None)
                return

            enable_lipsync = bool(options.get('enable_lipsync', False))
            apply_cleaner = bool(options.get('apply_cleaner', False))
            cleaner_settings = options.get('cleaner_settings') or {}
            apply_effects = bool(options.get('apply_effects', False))
            effects_settings = options.get('effects_settings') or {}
            trim_threshold = float(options.get('trim_threshold', 0.0))

            all_audio = []
            combined_frames = []
            combined_texts = []
            audio_offset = 0.0
            sample_rate = None

            for entry in texts_data:
                text = (entry or {}).get('text', '').strip()
                if not text:
                    continue

                params = (entry or {}).get('parameters') or {}
                silence_after = float((entry or {}).get('silence_after', 0.0) or 0.0)

                sr, audio = self._tts_engine.synthesize(text, **params)
                if sample_rate is None:
                    sample_rate = sr

                processed_audio = audio.astype(np.float32)

                if apply_cleaner and self._audio_processor:
                    processed_audio = self._audio_processor.process_audio(processed_audio, sr, cleaner_settings)

                if apply_effects and self._audio_effects_processor:
                    processed_audio = self._audio_effects_processor.process_effects(processed_audio, sr, effects_settings)

                processed_audio = self._trim_silence(processed_audio, sr, trim_threshold)

                if processed_audio.size == 0:
                    continue

                processed_audio = processed_audio.astype(np.float32)
                segment_duration = len(processed_audio) / sr

                if enable_lipsync and self._lip_sync_engine and self._lip_sync_engine.is_available():
                    lipsync_data = self._lip_sync_engine.analyze_text_for_lipsync(
                        text=text,
                        audio_data=processed_audio,
                        sample_rate=sr,
                    )

                    if lipsync_data:
                        for frame in lipsync_data.vowel_frames:
                            combined_frames.append(
                                VowelFrame(
                                    timestamp=frame.timestamp + audio_offset,
                                    vowel=frame.vowel,
                                    intensity=frame.intensity,
                                    duration=frame.duration,
                                    is_ending=frame.is_ending,
                                )
                            )

                audio_offset += segment_duration
                combined_texts.append(text)
                all_audio.append(processed_audio)

                if silence_after > 0 and sr:
                    silence_samples = int(sr * silence_after)
                    if silence_samples > 0:
                        silence = np.zeros(silence_samples, dtype=np.float32)
                        all_audio.append(silence)

                        if enable_lipsync and self._lip_sync_engine and self._lip_sync_engine.is_available():
                            combined_frames.append(
                                VowelFrame(
                                    timestamp=audio_offset,
                                    vowel='sil',
                                    intensity=0.0,
                                    duration=silence_samples / sr,
                                    is_ending=True,
                                )
                            )

                        audio_offset += silence_samples / sr

            if not all_audio or sample_rate is None:
                self.sequence_finished.emit(None, None, None, None)
                return

            final_audio = np.concatenate(all_audio).astype(np.float32)
            max_val = float(np.abs(final_audio).max()) if final_audio.size else 0.0
            if max_val > 0.9:
                final_audio *= 0.9 / max_val

            combined_lipsync = None
            if enable_lipsync and combined_frames:
                combined_lipsync = LipSyncData(
                    text='\n'.join(combined_texts),
                    total_duration=audio_offset,
                    vowel_frames=combined_frames,
                    sample_rate=sample_rate,
                )

            self.sequence_finished.emit(sample_rate, final_audio, combined_lipsync, None)

        except Exception:
            error_trace = traceback.format_exc()
            self.sequence_finished.emit(None, None, None, error_trace)

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