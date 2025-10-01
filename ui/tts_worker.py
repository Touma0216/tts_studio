from __future__ import annotations

import traceback
from typing import Dict

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from core.lip_sync_engine import LipSyncEngine
from core.tts_engine import TTSEngine


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