import json
import os
import wave
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime

class LongTTSProcessor:
    """大量テキストの連続TTS処理（無音区間挿入対応版）"""
    
    def __init__(self, tts_engine, checkpoint_dir: str = "checkpoints"):
        self.tts_engine = tts_engine
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        
    def process_texts_to_wav(
        self, 
        texts_data: List[Dict],  # 🆕 テキスト+無音時間のデータ
        output_path: str,
        chunk_size: int = 100,
        resume: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict:
        """
        複数テキストを連続TTS処理して1つのWAVに保存（無音区間挿入対応）
        
        Args:
            texts_data: [{'text': str, 'silence_after': float}, ...] のリスト
            output_path: 最終的なWAVファイルパス
            chunk_size: 一度に処理するテキスト数（メモリ管理用）
            resume: 中断から再開するか
            progress_callback: 進捗通知用コールバック関数 (current, total)
            
        Returns:
            処理結果の辞書
        """
        session_id = self._get_session_id(output_path)
        checkpoint_path = self.checkpoint_dir / f"{session_id}.json"
        temp_dir = self.checkpoint_dir / session_id
        temp_dir.mkdir(exist_ok=True)
        
        # チェックポイントから復元
        if resume and checkpoint_path.exists():
            checkpoint = self._load_checkpoint(checkpoint_path)
            start_idx = checkpoint["completed_count"]
            print(f"🔄 チェックポイントから再開: {start_idx}個目から")
        else:
            checkpoint = {
                "session_id": session_id,
                "output_path": output_path,
                "total_texts": len(texts_data),
                "completed_count": 0,
                "temp_files": [],
                "created_at": datetime.now().isoformat()
            }
            start_idx = 0
        
        total_texts = len(texts_data)
        
        try:
            # サンプルレート取得（最初の音声生成で取得）
            if total_texts > 0:
                sr, _ = self.tts_engine.synthesize(texts_data[0]['text'])
                self.sample_rate = sr
            else:
                self.sample_rate = 44100
            
            # チャンクごとに処理（メモリ管理のため）
            for chunk_start in range(start_idx, total_texts, chunk_size):
                chunk_end = min(chunk_start + chunk_size, total_texts)
                chunk_data = texts_data[chunk_start:chunk_end]
                
                temp_wav_path = temp_dir / f"chunk_{chunk_start:06d}.wav"
                
                print(f"🎵 処理中: {chunk_start + 1}～{chunk_end}/{total_texts} ({len(chunk_data)}個)")
                
                # チャンク内のテキストを連続TTS処理（無音区間挿入）
                audio_data = self._generate_audio_with_silence(
                    chunk_data, 
                    chunk_start,
                    total_texts,
                    progress_callback
                )
                
                # 一時WAVファイルに保存
                self._save_wav(temp_wav_path, audio_data)
                
                # チェックポイント更新
                checkpoint["completed_count"] = chunk_end
                checkpoint["temp_files"].append(str(temp_wav_path))
                self._save_checkpoint(checkpoint_path, checkpoint)
                
                print(f"✓ {chunk_start + 1}～{chunk_end} 完了")
            
            # 全チャンク完了：WAVファイル結合
            print("🎉 全テキスト処理完了！WAVファイルを結合中...")
            self._merge_wav_files(checkpoint["temp_files"], output_path)
            
            # クリーンアップ
            self._cleanup(temp_dir, checkpoint_path)
            
            return {
                "success": True,
                "total_texts": total_texts,
                "output_path": output_path
            }
            
        except Exception as e:
            print(f"❌ エラー発生: {e}")
            print(f"💾 チェックポイント保存済み: {checkpoint_path}")
            return {
                "success": False,
                "error": str(e),
                "checkpoint": str(checkpoint_path),
                "completed": checkpoint["completed_count"],
                "total": total_texts
            }
    
    def _generate_audio_with_silence(
        self, 
        texts_data: List[Dict],
        start_idx: int,
        total_texts: int,
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> np.ndarray:
        """テキストを連続でTTS処理（無音区間挿入）"""
        audio_chunks = []
        
        for i, data in enumerate(texts_data):
            current_idx = start_idx + i
            text = data['text']
            silence_after = data.get('silence_after', 0.0)
            
            # 進捗通知
            if progress_callback:
                try:
                    progress_callback(current_idx + 1, total_texts)
                except Exception as e:
                    print(f"⚠️ 進捗コールバックエラー: {e}")
            
            # TTSで生成
            sr, audio = self.tts_engine.synthesize(text)
            audio_chunks.append(audio)
            
            print(f"  ✓ [{current_idx + 1}/{total_texts}] 生成完了: {text[:30]}...")
            
            # 🆕 無音区間を挿入
            if silence_after > 0:
                silence_samples = int(sr * silence_after)
                silence = np.zeros(silence_samples, dtype=np.float32)
                audio_chunks.append(silence)
                print(f"    🔇 無音挿入: {silence_after}秒 ({silence_samples} samples)")
        
        # 連結
        return np.concatenate(audio_chunks)
    
    def _save_wav(self, path: Path, audio_data: np.ndarray):
        """WAVファイルに保存"""
        with wave.open(str(path), 'wb') as wf:
            wf.setnchannels(1)  # モノラル
            wf.setsampwidth(2)  # 16bit
            wf.setframerate(self.sample_rate)
            
            # int16に変換
            audio_int16 = (audio_data * 32767).astype(np.int16)
            wf.writeframes(audio_int16.tobytes())
    
    def _merge_wav_files(self, wav_paths: List[str], output_path: str):
        """複数のWAVファイルを1つに結合"""
        audio_data_list = []
        sample_rate = None
        
        for wav_path in wav_paths:
            with wave.open(wav_path, 'rb') as wf:
                if sample_rate is None:
                    sample_rate = wf.getframerate()
                
                audio_bytes = wf.readframes(wf.getnframes())
                audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
                audio_float = audio_int16.astype(np.float32) / 32767.0
                audio_data_list.append(audio_float)
        
        # 連結
        merged_audio = np.concatenate(audio_data_list)
        
        # 保存
        self._save_wav(Path(output_path), merged_audio)
        
        # 長さを計算
        duration_sec = len(merged_audio) / sample_rate
        duration_min = duration_sec / 60
        print(f"✅ 最終WAVファイル保存完了: {output_path}")
        print(f"📊 総時間: {duration_min:.1f}分 ({duration_sec:.1f}秒)")
    
    def _get_session_id(self, output_path: str) -> str:
        """出力パスからセッションIDを生成"""
        from hashlib import md5
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_part = md5(output_path.encode()).hexdigest()[:8]
        return f"{timestamp}_{hash_part}"
    
    def _load_checkpoint(self, path: Path) -> Dict:
        """チェックポイント読み込み"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_checkpoint(self, path: Path, checkpoint: Dict):
        """チェックポイント保存"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False)
    
    def _cleanup(self, temp_dir: Path, checkpoint_path: Path):
        """一時ファイルとチェックポイントを削除"""
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        if checkpoint_path.exists():
            checkpoint_path.unlink()
        print("🧹 一時ファイルをクリーンアップ")