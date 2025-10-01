# core/video_recorder.py
import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QWidget


class VideoRecorder(QObject):
    """Live2D表示エリアの動画録画エンジン"""
    
    # シグナル
    recording_started = pyqtSignal()
    frame_captured = pyqtSignal(int, int)  # 現在フレーム, 総フレーム数
    recording_finished = pyqtSignal(str)  # 出力ファイルパス
    recording_error = pyqtSignal(str)  # エラーメッセージ
    encoding_started = pyqtSignal()
    encoding_progress = pyqtSignal(int)  # エンコード進行率（0-100）
    
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
        
        # 🆕 ffmpegパスを取得
        self.ffmpeg_path = self._get_ffmpeg_path()
        
        # キャプチャタイマー
        self.capture_timer = QTimer(self)
        self.capture_timer.timeout.connect(self._capture_frame)
        
        # 録画終了タイマー
        self.stop_timer = QTimer(self)
        self.stop_timer.setSingleShot(True)
        self.stop_timer.timeout.connect(self._finish_recording)
    
    def _get_ffmpeg_path(self) -> str:
        """
        ffmpegの実行ファイルパスを取得
        優先順位：
        1. assets/ffmpeg/bin/ffmpeg.exe (埋め込み版)
        2. システムPATH上のffmpeg
        """
        # 1. 埋め込み版ffmpegを探す
        if getattr(sys, 'frozen', False):
            # PyInstallerでパッケージ化されている場合
            base_path = Path(sys._MEIPASS)
        else:
            # 開発環境の場合
            base_path = Path(__file__).parent.parent
        
        embedded_ffmpeg = base_path / "assets" / "ffmpeg" / "bin" / "ffmpeg.exe"
        
        if embedded_ffmpeg.exists():
            print(f"✅ 埋め込みffmpeg使用: {embedded_ffmpeg}")
            return str(embedded_ffmpeg)
        
        # 2. システムPATH上のffmpegを探す
        print("⚠️ 埋め込みffmpegが見つかりません。システムPATHから探します...")
        return "ffmpeg"  # システムPATHから探す
    
    def start_recording(
        self,
        widget: QWidget,
        duration: float,
        fps: int = 60,
        output_format: str = "mov",
        output_path: str = ""
    ) -> bool:
        """
        録画を開始
        
        Args:
            widget: キャプチャ対象のウィジェット（QWebEngineView）
            duration: 録画時間（秒）
            fps: フレームレート（30 or 60）
            output_format: 出力形式（"mov", "mp4", "webm"）
            output_path: 出力先フォルダパス
        
        Returns:
            bool: 録画開始成功時True
        """
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
            # 初期化
            self.capture_widget = widget
            self.fps = fps
            self.output_format = output_format
            self.output_path = output_path
            self.frame_count = 0
            self.total_frames = int(duration * fps)
            
            # 一時ディレクトリ作成
            self.temp_dir = Path(tempfile.mkdtemp(prefix="tts_studio_capture_"))
            print(f"📁 一時フォルダ作成: {self.temp_dir}")
            
            # 録画開始
            self.is_recording = True
            self.recording_started.emit()
            
            # 🔥 フレームキャプチャ開始（1/fps秒間隔）
            interval_ms = int(1000 / fps)
            self.capture_timer.start(interval_ms)
            
            # 🔥 録画終了タイマー（duration + 0.1秒のバッファ）
            # バッファを追加することでタイマー誤差を吸収
            self.stop_timer.start(int((duration + 0.1) * 1000))
            
            print(f"🎬 録画開始: {duration}秒間, {fps}fps, {self.total_frames}フレーム, タイマー:{int((duration + 0.1) * 1000)}ms")
            return True
            
        except Exception as e:
            print(f"❌ 録画開始エラー: {e}")
            import traceback
            traceback.print_exc()
            self.recording_error.emit(f"録画開始に失敗しました: {str(e)}")
            self._cleanup()
            return False
    
    def _capture_frame(self):
        """1フレームをキャプチャ"""
        if not self.is_recording:
            print(f"⚠️ キャプチャスキップ: is_recording=False (フレーム{self.frame_count})")
            return
        
        if not self.capture_widget:
            print(f"⚠️ キャプチャスキップ: capture_widget=None")
            return
        
        try:
            # QWebEngineView用の正しいキャプチャ方法
            # grab()を使って画面をキャプチャ（render()よりも高速で正確）
            pixmap = self.capture_widget.grab()
            
            # QPixmap → QImage変換（透過対応）
            image = pixmap.toImage()
            
            # ARGB32フォーマットに変換（透過対応）
            if image.format() != QImage.Format.Format_ARGB32:
                image = image.convertToFormat(QImage.Format.Format_ARGB32)
            
            # PNG保存（透過対応）
            frame_path = self.temp_dir / f"frame_{self.frame_count:06d}.png"
            success = image.save(str(frame_path), "PNG")
            
            if not success:
                print(f"⚠️ フレーム保存失敗: {frame_path}")
                return
            
            self.frame_count += 1
            self.frame_captured.emit(self.frame_count, self.total_frames)
            
            # デバッグ出力（10フレームごと）
            if self.frame_count % 10 == 0:
                progress = int((self.frame_count / self.total_frames * 100))
                print(f"📸 キャプチャ: {self.frame_count}/{self.total_frames} ({progress}%) is_recording={self.is_recording}")
            
            # 🔥 予定フレーム数に達したら自動停止
            if self.frame_count >= self.total_frames:
                print(f"✅ 予定フレーム数に達しました: {self.frame_count}/{self.total_frames}")
                self._finish_recording()
            
        except Exception as e:
            print(f"❌ フレームキャプチャエラー: {e}")
            import traceback
            traceback.print_exc()
            self.stop_recording()
            self.recording_error.emit(f"フレームキャプチャに失敗しました: {str(e)}")
    
    def _finish_recording(self):
        """録画を終了してエンコード開始"""
        if not self.is_recording:
            print("⚠️ 既に録画停止済み")
            return
        
        # キャプチャタイマー停止
        self.capture_timer.stop()
        self.is_recording = False
        
        print(f"✅ キャプチャ完了: {self.frame_count}フレーム")
        print(f"⏱️ _finish_recording呼び出し時刻")
        
        # キャプチャしたフレーム数を確認
        if self.frame_count == 0:
            error_msg = "フレームが1枚もキャプチャされませんでした"
            print(f"❌ {error_msg}")
            self.recording_error.emit(error_msg)
            self._cleanup()
            return
        
        # 実際にキャプチャされたフレーム数でエンコード
        print(f"📊 実際のフレーム数: {self.frame_count}, 予定: {self.total_frames}")
        
        # エンコード開始
        self._encode_video()
    
    def stop_recording(self):
        """録画を強制停止"""
        if self.is_recording:
            import traceback
            print("⏹️ 録画を強制停止します")
            print("呼び出し元:")
            traceback.print_stack()
            
            self.capture_timer.stop()
            self.stop_timer.stop()
            self.is_recording = False
            self._cleanup()
            print("⏹️ 録画を停止しました")
    
    def _encode_video(self):
        """キャプチャしたフレームを動画にエンコード"""
        try:
            self.encoding_started.emit()
            print("🎞️ エンコード開始...")
            
            # 出力ファイル名生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.{self.output_format}"
            output_file = Path(self.output_path) / filename
            
            # ffmpegコマンド構築
            input_pattern = str(self.temp_dir / "frame_%06d.png")
            
            if self.output_format == "mov":
                # MOV (ProRes 4444) - 透過対応
                cmd = [
                    self.ffmpeg_path,  # 🆕 埋め込みパス使用
                    "-framerate", str(self.fps),
                    "-i", input_pattern,
                    "-c:v", "prores_ks",
                    "-profile:v", "4444",
                    "-pix_fmt", "yuva444p10le",
                    "-y",
                    str(output_file)
                ]
            elif self.output_format == "webm":
                # WebM (VP9) - 透過対応
                cmd = [
                    self.ffmpeg_path,  # 🆕 埋め込みパス使用
                    "-framerate", str(self.fps),
                    "-i", input_pattern,
                    "-c:v", "libvpx-vp9",
                    "-pix_fmt", "yuva420p",
                    "-b:v", "2M",
                    "-auto-alt-ref", "0",
                    "-y",
                    str(output_file)
                ]
            else:  # mp4
                # MP4 (H.264) - 透過（制限あり）
                cmd = [
                    self.ffmpeg_path,  # 🆕 埋め込みパス使用
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
            
            # ffmpeg実行
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # プロセス完了待ち
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                print(f"✅ エンコード完了: {output_file}")
                self.encoding_progress.emit(100)
                self.recording_finished.emit(str(output_file))
            else:
                error_msg = f"ffmpegエラー: {stderr}"
                print(f"❌ {error_msg}")
                self.recording_error.emit(error_msg)
            
            # クリーンアップ
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
        """一時ファイルとディレクトリを削除"""
        try:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                print(f"🗑️ 一時フォルダ削除: {self.temp_dir}")
                self.temp_dir = None
        except Exception as e:
            print(f"⚠️ クリーンアップエラー: {e}")
    
    def is_ffmpeg_available(self) -> bool:
        """ffmpegが利用可能かチェック"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],  # 🆕 埋め込みパス使用
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
        """録画状態を取得"""
        return {
            'is_recording': self.is_recording,
            'frame_count': self.frame_count,
            'total_frames': self.total_frames,
            'progress': int((self.frame_count / self.total_frames * 100) if self.total_frames > 0 else 0)
        }