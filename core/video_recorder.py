# core/video_recorder.py
import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime
import base64
import time

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QSize, pyqtSlot
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QWidget


class VideoRecorder(QObject):
    """Live2D表示エリアの動画録画エンジン"""
    
    # シグナル
    recording_started = pyqtSignal()
    frame_captured = pyqtSignal(int, int)
    recording_finished = pyqtSignal(str)
    recording_error = pyqtSignal(str)
    encoding_started = pyqtSignal()
    encoding_progress = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.is_recording = False
        self.capture_widget: Optional[QWidget] = None
        self.temp_dir: Optional[Path] = None
        self.frame_count = 0
        self.total_frames = 0
        self.fps = 60
        self.output_format = "mov"
        self.output_path = ""
        
        self.ffmpeg_path = self._get_ffmpeg_path()
        
        self.capture_timer = QTimer(self)
        self.capture_timer.timeout.connect(self._capture_frame)
        
        self.stop_timer = QTimer(self)
        self.stop_timer.setSingleShot(True)
        self.stop_timer.timeout.connect(self._finish_recording)
    
    def _get_ffmpeg_path(self) -> str:
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent
        
        embedded_ffmpeg = base_path / "assets" / "ffmpeg" / "bin" / "ffmpeg.exe"
        
        if embedded_ffmpeg.exists():
            print(f"✅ 埋め込みffmpeg使用: {embedded_ffmpeg}")
            return str(embedded_ffmpeg)
        
        print("⚠️ 埋め込みffmpegが見つかりません。システムPATHから探します...")
        return "ffmpeg"
    
    def start_recording(
        self,
        widget: QWidget,
        duration: float,
        fps: int = 60,
        output_format: str = "mov",
        output_path: str = ""
    ) -> bool:
        if self.is_recording:
            print("⚠️ すでに録画中です")
            return False
        
        if not widget:
            self.recording_error.emit("キャプチャ対象ウィジェットが指定されていません")
            return False
        
        if not output_path or not Path(output_path).exists():
            self.recording_error.emit("出力先フォルダが無効です")
            return False
        
        try:
            self.capture_widget = widget
            self.fps = fps
            self.output_format = output_format
            self.output_path = output_path
            self.frame_count = 0
            self.total_frames = int(duration * fps)
            
            self.temp_dir = Path(tempfile.mkdtemp(prefix="tts_studio_capture_"))
            print(f"📁 一時フォルダ作成: {self.temp_dir}")
            
            self.is_recording = True
            self.recording_started.emit()
            
            interval_ms = int(1000 / fps)
            self.capture_timer.start(interval_ms)
            
            self.stop_timer.start(int(duration * 1000))
            
            print(f"🎬 録画開始: {duration}秒間, {fps}fps, {self.total_frames}フレーム")
            return True
            
        except Exception as e:
            print(f"❌ 録画開始エラー: {e}")
            self.recording_error.emit(f"録画開始に失敗しました: {str(e)}")
            self._cleanup()
            return False
    
    def _capture_frame(self):
        if not self.is_recording or not self.capture_widget:
            return
        
        try:
            pixmap = self.capture_widget.grab()
            image = pixmap.toImage()
            
            if image.format() != QImage.Format.Format_ARGB32:
                image = image.convertToFormat(QImage.Format.Format_ARGB32)
            
            frame_path = self.temp_dir / f"frame_{self.frame_count:06d}.png"
            success = image.save(str(frame_path), "PNG")
            
            if not success:
                print(f"⚠️ フレーム保存失敗: {frame_path}")
                return
            
            self.frame_count += 1
            self.frame_captured.emit(self.frame_count, self.total_frames)
            
            if self.frame_count % 10 == 0:
                progress = int((self.frame_count / self.total_frames * 100))
                print(f"📸 キャプチャ: {self.frame_count}/{self.total_frames} ({progress}%)")
            
        except Exception as e:
            print(f"❌ フレームキャプチャエラー: {e}")
            import traceback
            traceback.print_exc()
            self.stop_recording()
            self.recording_error.emit(f"フレームキャプチャに失敗しました: {str(e)}")
    
    def _finish_recording(self):
        if not self.is_recording:
            return
        
        self.capture_timer.stop()
        self.is_recording = False
        
        print(f"✅ キャプチャ完了: {self.frame_count}フレーム")
        
        if self.frame_count == 0:
            error_msg = "フレームが1枚もキャプチャされませんでした"
            print(f"❌ {error_msg}")
            self.recording_error.emit(error_msg)
            self._cleanup()
            return
        
        print(f"📊 実際のフレーム数: {self.frame_count}, 予定: {self.total_frames}")
        
        self._encode_video()
    
    def stop_recording(self):
        if self.is_recording:
            self.capture_timer.stop()
            self.stop_timer.stop()
            self.is_recording = False
            self._cleanup()
            print("⏹️ 録画を停止しました")
    
    def _encode_video(self):
        try:
            self.encoding_started.emit()
            print("🎞️ エンコード開始...")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.{self.output_format}"
            output_file = Path(self.output_path) / filename
            
            input_pattern = str(self.temp_dir / "frame_%06d.png")
            
            if self.output_format == "mov":
                cmd = [
                    self.ffmpeg_path,
                    "-framerate", str(self.fps),
                    "-i", input_pattern,
                    "-c:v", "prores_ks",
                    "-profile:v", "4444",
                    "-pix_fmt", "yuva444p10le",
                    "-y",
                    str(output_file)
                ]
            elif self.output_format == "webm":
                cmd = [
                    self.ffmpeg_path,
                    "-framerate", str(self.fps),
                    "-i", input_pattern,
                    "-c:v", "libvpx-vp9",
                    "-pix_fmt", "yuva420p",
                    "-b:v", "2M",
                    "-auto-alt-ref", "0",
                    "-y",
                    str(output_file)
                ]
            else:
                cmd = [
                    self.ffmpeg_path,
                    "-framerate", str(self.fps),
                    "-i", input_pattern,
                    "-c:v", "libx264",
                    "-pix_fmt", "yuva420p",
                    "-crf", "18",
                    "-preset", "medium",
                    "-y",
                    str(output_file)
                ]
            
            print(f"🔧 ffmpegコマンド: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                print(f"✅ エンコード完了: {output_file}")
                self.encoding_progress.emit(100)
                self.recording_finished.emit(str(output_file))
            else:
                error_msg = f"ffmpegエラー: {stderr}"
                print(f"❌ {error_msg}")
                self.recording_error.emit(error_msg)
            
            self._cleanup()
            
        except FileNotFoundError:
            error_msg = "ffmpegが見つかりません。ffmpegをインストールしてPATHに追加してください。"
            print(f"❌ {error_msg}")
            self.recording_error.emit(error_msg)
            self._cleanup()
            
        except Exception as e:
            error_msg = f"エンコードエラー: {str(e)}"
            print(f"❌ {error_msg}")
            self.recording_error.emit(error_msg)
            self._cleanup()
    
    def _cleanup(self):
        try:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                print(f"🗑️ 一時フォルダ削除: {self.temp_dir}")
                self.temp_dir = None
        except Exception as e:
            print(f"⚠️ クリーンアップエラー: {e}")
    
    def is_ffmpeg_available(self) -> bool:
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            available = result.returncode == 0
            if available:
                print(f"✅ ffmpeg利用可能: {self.ffmpeg_path}")
            return available
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print(f"❌ ffmpeg利用不可: {self.ffmpeg_path}")
            return False
    
    def get_recording_status(self) -> dict:
        return {
            'is_recording': self.is_recording,
            'frame_count': self.frame_count,
            'total_frames': self.total_frames,
            'progress': int((self.frame_count / self.total_frames * 100) if self.total_frames > 0 else 0)
        }


class VideoBridge(QObject):
    """JavaScript MediaRecorder用ブリッジ"""
    
    video_ready = pyqtSignal(str)
    
    def __init__(self, ffmpeg_path, output_dir, parent=None):
        super().__init__(parent)
        self.ffmpeg_path = ffmpeg_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @pyqtSlot(str, 'QVariantMap')
    def receiveVideo(self, base64Data, metadata):
        """JavaScript側から録画データ受信"""
        try:
            print(f"📥 受信: {metadata.get('frameCount', 0)}フレーム, "
                  f"{metadata.get('size', 0) / 1024 / 1024:.2f}MB")
            
            videoBytes = base64.b64decode(base64Data)
            
            temp_dir = Path(tempfile.mkdtemp(prefix='yukkuri_'))
            temp_webm = temp_dir / 'recorded.webm'
            with open(temp_webm, 'wb') as f:
                f.write(videoBytes)
            
            print(f"💾 一時保存: {temp_webm}")
            
            output_file = self._convert_to_prores(temp_webm)
            
            print(f"✅ 変換完了: {output_file}")
            self.video_ready.emit(str(output_file))
            
        except Exception as e:
            print(f"❌ 動画処理エラー: {e}")
            import traceback
            traceback.print_exc()
    
    def _convert_to_prores(self, input_path):
        """WebM → 背景透過 → ProRes 4444"""
        timestamp = int(time.time())
        
        temp_alpha_webm = input_path.parent / 'alpha.webm'
        output_mov = self.output_dir / f"clip_{timestamp}.mov"
        
        print("🎨 Step 1/2: 背景透過処理中...")
        subprocess.run([
            self.ffmpeg_path, '-i', str(input_path),
            '-c:v', 'libvpx-vp9',
            '-vf', 'chromakey=0x00FF00:0.1:0.1,format=yuva420p',
            '-pix_fmt', 'yuva420p',
            '-b:v', '0', '-crf', '18',
            '-quality', 'good', '-speed', '2',
            '-threads', '12',
            '-c:a', 'copy',
            '-y',
            str(temp_alpha_webm)
        ], check=True, capture_output=True)
        
        print("🎞️ Step 2/2: ProRes変換中...")
        subprocess.run([
            self.ffmpeg_path, '-i', str(temp_alpha_webm),
            '-c:v', 'prores_ks',
            '-profile:v', '4',
            '-pix_fmt', 'yuva444p10le',
            '-alpha_bits', '16',
            '-vendor', 'apl0',
            '-c:a', 'pcm_s16le',
            '-y',
            str(output_mov)
        ], check=True, capture_output=True)
        
        size_mb = output_mov.stat().st_size / 1024 / 1024
        print(f"📦 出力: {output_mov.name} ({size_mb:.1f}MB)")
        
        return output_mov