import subprocess
import base64
from io import BytesIO
from PIL import Image
from pathlib import Path
from typing import Optional
import time

class VideoRecorder:
    """
    Live2Dフレームを受け取り、NVENC/ProRes動画に書き出すクラス
    """
    
    def __init__(self, output_path: str, width: int = 1920, height: int = 1080, 
                 fps: int = 60, use_nvenc: bool = True):
        """
        Args:
            output_path: 出力ファイルパス（拡張子なし）
            width: 動画幅
            height: 動画高さ
            fps: フレームレート
            use_nvenc: True=NVENC録画、False=ProRes直接
        """
        self.output_path = Path(output_path)
        self.width = width
        self.height = height
        self.fps = fps
        self.use_nvenc = use_nvenc
        
        # 録画用の一時ファイル
        self.temp_file = self.output_path.with_suffix('.mkv') if use_nvenc else None
        
        # FFmpegプロセス
        self.process: Optional[subprocess.Popen] = None
        self.frame_count = 0
        self.start_time = 0.0
        
    def start(self):
        """録画開始"""
        if self.use_nvenc:
            command = self._build_nvenc_command()
        else:
            command = self._build_prores_command()
        
        print(f"🎬 FFmpeg command: {' '.join(command)}")
        
        try:
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,  # ← 修正：stdout破棄
                stderr=subprocess.DEVNULL,  # ← 修正：stderr破棄（バッファ詰まり防止）
                bufsize=10**8  # 100MBバッファ
            )
            
            self.start_time = time.time()
            print(f"✅ 録画開始: {self.output_path}")
            
        except FileNotFoundError:
            print("❌ FFmpegが見つかりません。PATHに追加してください。")
            raise
        except Exception as e:
            print(f"❌ 録画開始エラー: {e}")
            raise
            raise
    
    def _build_nvenc_command(self) -> list:
        """NVENC録画用コマンド生成"""
        return [
            'ffmpeg',
            '-y',
            '-hwaccel', 'cuda',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{self.width}x{self.height}',
            '-pix_fmt', 'rgba',
            '-r', str(self.fps),
            '-i', '-',
            '-c:v', 'hevc_nvenc',
            '-pix_fmt', 'yuva420p',
            '-preset', 'p4',
            '-tune', 'hq',
            '-rc', 'vbr',
            '-cq', '23',
            '-b:v', '30M',
            str(self.temp_file)
        ]
    
    def _build_prores_command(self) -> list:
        """ProRes直接書き出し用コマンド生成"""
        output = self.output_path.with_suffix('.mov')
        return [
            'ffmpeg',
            '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{self.width}x{self.height}',
            '-pix_fmt', 'rgba',
            '-r', str(self.fps),
            '-i', '-',
            '-c:v', 'prores_ks',
            '-profile:v', '4444',
            '-pix_fmt', 'yuva444p10le',
            '-vendor', 'ap10',
            str(output)
        ]
    
    def write_frame_from_dataurl(self, dataURL: str):
        """
        DataURL形式のフレームを書き込み
        Args:
            dataURL: "data:image/png;base64,..."形式
        """
        if self.process is None:
            raise RuntimeError("録画が開始されていません")
        
        if self.process.stdin is None or self.process.stdin.closed:
            raise RuntimeError("FFmpegのstdinが閉じられています")
        
        try:
            # Base64デコード
            if ',' not in dataURL:
                raise ValueError("無効なDataURL形式")
            
            image_data = base64.b64decode(dataURL.split(',')[1])
            
            # 最初のフレームのみサイズ確認
            if self.frame_count == 0:
                print(f"🔍 最初のフレーム: Base64サイズ={len(dataURL)} bytes, デコード後={len(image_data)} bytes")
            
            # PIL Imageに変換
            image = Image.open(BytesIO(image_data))
            
            # RGBA形式確保
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            # サイズ確認・リサイズ
            if image.size != (self.width, self.height):
                if self.frame_count == 0:
                    print(f"🔍 画像リサイズ: {image.size} → ({self.width}, {self.height})")
                image = image.resize((self.width, self.height), Image.LANCZOS)
            
            # バイトデータ取得
            frame_bytes = image.tobytes()
            
            # 最初のフレームのみサイズ確認
            if self.frame_count == 0:
                expected_size = self.width * self.height * 4  # RGBA
                print(f"🔍 フレームバイト: {len(frame_bytes)} bytes (期待値: {expected_size} bytes)")
            
            # FFmpegに書き込み
            bytes_written = self.process.stdin.write(frame_bytes)
            self.process.stdin.flush()  # ← 追加：即座にフラッシュ
            
            if self.frame_count == 0:
                print(f"🔍 FFmpegへ書き込み完了: {bytes_written} bytes")
            
            self.frame_count += 1
            
            # 100フレームごとに進捗表示
            if self.frame_count % 100 == 0:
                elapsed_sec = self.frame_count / self.fps
                print(f"📹 録画中: {self.frame_count}フレーム ({elapsed_sec:.1f}秒)")
                
        except Exception as e:
            print(f"❌ フレーム書き込みエラー (frame #{self.frame_count}): {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def stop(self):
        """録画停止"""
        if self.process:
            try:
                print("📹 FFmpegパイプをクローズ中...")
                
                # stdinを閉じてFFmpegに終了を通知
                if self.process.stdin:
                    self.process.stdin.close()
                
                # FFmpegの処理完了を待つ（最大30秒）
                print("⏳ FFmpegの処理完了を待機中...")
                self.process.wait(timeout=30)
                
                elapsed_time = time.time() - self.start_time
                print(f"⏹️ 録画停止: {self.frame_count}フレーム, {elapsed_time:.1f}秒")
                
                # NVENC録画の場合、ファイルサイズ確認
                if self.use_nvenc and self.temp_file.exists():
                    temp_size = self.temp_file.stat().st_size
                    print(f"📦 一時ファイルサイズ: {temp_size / (1024**2):.2f}MB")
                    
                    if temp_size == 0:
                        print("❌ 一時ファイルが空です。録画に失敗した可能性があります。")
                        return
                    
                    print("🔄 ProRes 4444変換中...")
                    self._convert_to_prores()
                
            except subprocess.TimeoutExpired:
                print("⚠️ FFmpegプロセスが30秒以内に終了しませんでした。強制終了します。")
                self.process.kill()
                self.process.wait()
            except Exception as e:
                print(f"❌ 録画停止エラー: {e}")
                import traceback
                traceback.print_exc()
    
    def _convert_to_prores(self):
        """NVENC録画をProRes 4444に変換"""
        output = self.output_path.with_suffix('.mov')
        
        command = [
            'ffmpeg',
            '-y',
            '-hwaccel', 'cuda',
            '-i', str(self.temp_file),
            '-c:v', 'prores_ks',
            '-profile:v', '4444',
            '-pix_fmt', 'yuva444p10le',
            '-vendor', 'ap10',
            str(output)
        ]
        
        print(f"🔄 変換コマンド: {' '.join(command)}")
        
        try:
            # 変換実行（最大5分）
            process = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=300
            )
            
            if process.returncode == 0:
                # 変換成功：ファイルサイズ確認
                if output.exists():
                    output_size = output.stat().st_size
                    print(f"✅ ProRes変換完了: {output}")
                    print(f"📦 最終ファイルサイズ: {output_size / (1024**3):.2f}GB")
                    
                    # 一時ファイル削除
                    self.temp_file.unlink()
                else:
                    print(f"❌ 変換後のファイルが見つかりません: {output}")
            else:
                print(f"❌ 変換失敗（終了コード: {process.returncode}）")
                print(f"stderr: {process.stderr}")
                
        except subprocess.TimeoutExpired:
            print("❌ 変換タイムアウト（5分経過）")
        except Exception as e:
            print(f"❌ 変換エラー: {e}")
            import traceback
            traceback.print_exc()