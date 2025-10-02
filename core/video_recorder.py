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
            use_nvenc: True=ffvhuff録画、False=ProRes直接（名前はそのまま）
        """
        self.output_path = Path(output_path)
        self.width = width
        self.height = height
        self.fps = fps
        self.use_nvenc = use_nvenc
        
        # 録画用の一時ファイル（🔥 修正：.avi に変更）
        self.temp_file = self.output_path.with_suffix('.avi') if use_nvenc else None
        
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
            # 🔥 修正：FFmpegログファイルを作成
            stderr_log_path = self.output_path.with_suffix('.ffmpeg.log')
            self.stderr_file = open(stderr_log_path, 'w', encoding='utf-8')
            
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,  # 🔥 修正：破棄しない
                stderr=self.stderr_file,  # 🔥 修正：ログファイルに出力
                bufsize=10**8  # 100MBバッファ
            )
            
            self.start_time = time.time()
            print(f"✅ 録画開始: {self.output_path}")
            print(f"📝 FFmpegログ: {stderr_log_path}")
            
        except FileNotFoundError:
            print("❌ FFmpegが見つかりません。PATHに追加してください。")
            if hasattr(self, 'stderr_file'):
                self.stderr_file.close()
            raise
        except Exception as e:
            print(f"❌ 録画開始エラー: {e}")
            if hasattr(self, 'stderr_file'):
                self.stderr_file.close()
            raise
        
    def _build_nvenc_command(self) -> list:
        """非圧縮録画用コマンド生成（最速・透過対応）"""
        return [
            'ffmpeg',
            '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{self.width}x{self.height}',
            '-pix_fmt', 'rgba',
            '-r', str(self.fps),
            '-i', '-',
            '-c:v', 'rawvideo',     # 非圧縮
            '-pix_fmt', 'rgba',
            '-f', 'avi',            # 🔥 追加：AVIコンテナ指定
            str(self.temp_file.with_suffix('.avi'))  # 🔥 .aviに戻す
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
            dataURL: "data:image/png;base64,..."形式 または "data:image/jpeg;base64,..."形式
        """
        if self.process is None:
            raise RuntimeError("録画が開始されていません")
        
        if self.process.stdin is None or self.process.stdin.closed:
            print(f"⚠️ FFmpegのstdinが閉じられています（フレーム#{self.frame_count}）")
            return
        
        try:
            # Base64デコード
            if ',' not in dataURL:
                raise ValueError("無効なDataURL形式")
            
            # 🔥 追加：JPEG/PNG自動判定
            header, encoded = dataURL.split(',', 1)
            is_jpeg = 'jpeg' in header.lower()
            
            image_data = base64.b64decode(encoded)
            
            # 最初のフレームのみサイズ確認
            if self.frame_count == 0:
                print(f"🔍 最初のフレーム: {'JPEG' if is_jpeg else 'PNG'}, Base64サイズ={len(dataURL)} bytes, デコード後={len(image_data)} bytes")
            
            # PIL Imageに変換
            image = Image.open(BytesIO(image_data))
            
            # 🔥 JPEG→RGBA変換（透過を黒背景で補完）
            if image.mode == 'RGB':
                # RGBをRGBAに変換（アルファ=255で不透明）
                rgba_image = Image.new('RGBA', image.size, (0, 0, 0, 255))
                rgba_image.paste(image, (0, 0))
                image = rgba_image
            elif image.mode != 'RGBA':
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
            self.process.stdin.flush()
            
            # 🔥 追加：毎フレームログ（問題特定用）
            if self.frame_count % 10 == 0:  # 10フレームごと
                print(f"✅ フレーム#{self.frame_count}: {bytes_written} bytes書き込み")
            
            self.frame_count += 1
            
        except BrokenPipeError:
            print(f"💥 BrokenPipeError at frame #{self.frame_count}: FFmpegプロセスが予期せず終了")
            return
        except Exception as e:
            print(f"❌ フレーム書き込みエラー (frame #{self.frame_count}): {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def stop(self):
        """録画停止"""
        import traceback
        print("📹 stop()が呼ばれました")
        print("".join(traceback.format_stack()))
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
            finally:
                # 🔥 追加：ログファイルを閉じる
                if hasattr(self, 'stderr_file'):
                    self.stderr_file.close()
                    print("✅ FFmpegログファイルを閉じました")
                    
                    # 🔥 追加：ログの中身を表示
                    stderr_log_path = self.output_path.with_suffix('.ffmpeg.log')
                    if stderr_log_path.exists():
                        print("\n" + "="*50)
                        print("📋 FFmpegログの内容:")
                        print("="*50)
                        with open(stderr_log_path, 'r', encoding='utf-8') as f:
                            log_content = f.read()
                            print(log_content)
                        print("="*50 + "\n")
            
    def _convert_to_prores(self):
        """非圧縮録画をProRes 4444に変換"""
        output = self.output_path.with_suffix('.mov')
        
        command = [
            'ffmpeg',
            '-y',
            '-i', str(self.temp_file),  # 🔥 元に戻す
            '-c:v', 'prores_ks',
            '-profile:v', '4444',
            '-pix_fmt', 'yuva444p10le',
            '-alpha_bits', '16',
            '-vendor', 'ap10',
            str(output)
        ]
        
            
        print(f"🔄 変換コマンド: {' '.join(command)}")
        
        # 変換ログも保存
        convert_log_path = self.output_path.with_suffix('.convert.log')
        convert_log_file = open(convert_log_path, 'w', encoding='utf-8')
        
        try:
            process = subprocess.run(
                command, 
                stdout=subprocess.PIPE,
                stderr=convert_log_file,
                text=True, 
                timeout=300
            )
            
            convert_log_file.close()
            
            # 変換ログを表示
            if convert_log_path.exists():
                print("\n" + "="*50)
                print("📋 ProRes変換ログ:")
                print("="*50)
                with open(convert_log_path, 'r', encoding='utf-8') as f:
                    print(f.read())
                print("="*50 + "\n")
            
            if process.returncode == 0:
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
                
        except subprocess.TimeoutExpired:
            print("❌ 変換タイムアウト（5分経過）")
            convert_log_file.close()
        except Exception as e:
            print(f"❌ 変換エラー: {e}")
            convert_log_file.close()
            import traceback
            traceback.print_exc()