# core/audio_effects_processor.py
import numpy as np
import warnings

class AudioEffectsProcessor:
    """音声エフェクト処理クラス（音声エフェクト + 環境エフェクト）"""
    
    def __init__(self):
        self.sample_rate = None
        
    def process_effects(self, audio, sample_rate, effects_settings):
        """
        音声にエフェクトを適用
        
        Args:
            audio: 音声データ (numpy array)
            sample_rate: サンプリングレート
            effects_settings: エフェクト設定辞書
            
        Returns:
            processed_audio: エフェクト適用後の音声データ
        """
        self.sample_rate = sample_rate
        processed_audio = audio.copy().astype(np.float32)
        
        # 音声エフェクト（声質変更系）
        if effects_settings.get('robot_enabled', False):
            processed_audio = self.apply_robot_voice(
                processed_audio, 
                effects_settings.get('robot_intensity', 0.5)
            )
            
        if effects_settings.get('voice_change_enabled', False):
            processed_audio = self.apply_voice_change(
                processed_audio,
                effects_settings.get('voice_change_intensity', 0.0)
            )
            
        if effects_settings.get('distortion_enabled', False):
            processed_audio = self.apply_distortion(
                processed_audio,
                effects_settings.get('distortion_intensity', 0.4)
            )
            
        if effects_settings.get('echo_enabled', False):
            processed_audio = self.apply_echo(
                processed_audio,
                effects_settings.get('echo_intensity', 0.3)
            )
        
        # 環境エフェクト（空間・状況再現系）
        if effects_settings.get('phone_enabled', False):
            processed_audio = self.apply_phone_quality(
                processed_audio,
                effects_settings.get('phone_intensity', 0.5)
            )
            
        if effects_settings.get('through_wall_enabled', False):
            processed_audio = self.apply_through_wall(
                processed_audio,
                effects_settings.get('through_wall_intensity', 0.3)
            )
            
        if effects_settings.get('reverb_enabled', False):
            processed_audio = self.apply_reverb(
                processed_audio,
                effects_settings.get('reverb_intensity', 0.5)
            )
        
        # 最終的な音量調整
        processed_audio = self._normalize_audio(processed_audio)
        
        return processed_audio
    
    # ================================
    # 音声エフェクト（声質変更系）
    # ================================
    
    def apply_robot_voice(self, audio, intensity):
        """
        ロボット音声エフェクト - 安全版
        """
        try:
            # 入力チェック
            if not np.isfinite(audio).all():
                return audio
            
            # 1. 低い周波数のリングモジュレーション
            t = np.arange(len(audio)) / self.sample_rate
            base_freq = 30 + intensity * 70  # 30Hz-100Hz（超低域）
            carrier = np.sin(2 * np.pi * base_freq * t)
            
            # リングモジュレーション
            ring_modulated = audio * carrier
            
            # 2. 軽いディストーション
            drive = 1.0 + intensity * 2.0
            distorted = np.tanh(ring_modulated * drive)
            
            # 3. NaN/inf完全除去
            distorted = np.nan_to_num(distorted, nan=0.0, posinf=0.0, neginf=0.0)
            
            # 4. 音量制限
            max_val = np.abs(distorted).max()
            if max_val > 0.8:
                distorted = distorted / max_val * 0.8
            
            # 5. 控えめミックス
            mix_ratio = intensity * 0.5
            result = (1 - mix_ratio) * audio + mix_ratio * distorted
            
            # 6. 最終安全処理
            result = np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)
            
            return result.astype(np.float32)
            
        except Exception as e:
            print(f"ロボット音声エラー: {e}")
            return audio
    
    def apply_voice_change(self, audio, semitones):
        """
        ボイスチェンジ（ピッチシフト）
        ±12半音の範囲でピッチを変更
        """
        try:
            # librosa使用でピッチシフト
            import librosa
            
            # 半音を比率に変換
            if semitones == 0:
                return audio
                
            shift_ratio = 2 ** (semitones / 12.0)
            
            # ピッチシフト適用
            shifted_audio = librosa.effects.pitch_shift(
                audio, 
                sr=self.sample_rate, 
                n_steps=semitones
            )
            
            return shifted_audio.astype(np.float32)
            
        except ImportError:
            print("⚠️ librosaが利用できません。ボイスチェンジをスキップします。")
            return audio
        except Exception as e:
            print(f"ボイスチェンジエラー: {e}")
            return audio
    
    def apply_distortion(self, audio, intensity):
        """
        ディストーション（歪み）エフェクト - 強化版
        """
        try:
            # より強力なドライブ
            drive = 1.0 + intensity * 15.0  # 1.0 ~ 16.0（大幅強化）
            
            # ハードディストーション
            driven_audio = audio * drive
            distorted_audio = np.tanh(driven_audio)
            
            # 追加の歪み処理
            if intensity > 0.3:
                # ハードクリッピング追加
                clip_threshold = 0.7 - intensity * 0.4  # 0.7 → 0.3
                distorted_audio = np.clip(distorted_audio, -clip_threshold, clip_threshold)
            
            # 音量補正（歪み具合に応じて調整）
            distorted_audio *= (0.8 - intensity * 0.2)  # 強い歪みほど音量下げる
            
            # より強いミックス比率
            mix_ratio = intensity * 0.95  # 最大95%（大幅強化）
            result = (1 - mix_ratio) * audio + mix_ratio * distorted_audio
            
            return result
            
        except Exception as e:
            print(f"ディストーションエラー: {e}")
            return audio
    
    def apply_echo(self, audio, intensity):
        """
        やまびこ（エコー）エフェクト
        遅延時間と減衰をintensityで調整
        """
        try:
            # intensityに応じた遅延時間（0.1秒～1.0秒）
            delay_time = 0.1 + intensity * 0.9
            delay_samples = int(delay_time * self.sample_rate)
            
            if delay_samples >= len(audio):
                return audio
            
            # エコー生成
            echo_audio = np.zeros_like(audio)
            echo_decay = 0.3 + intensity * 0.4  # 0.3 ~ 0.7
            echo_audio[delay_samples:] = audio[:-delay_samples] * echo_decay
            
            # 複数エコー（山びこ感）
            if len(audio) > delay_samples * 2:
                echo_audio[delay_samples * 2:] += audio[:-delay_samples * 2] * echo_decay * 0.5
            
            return audio + echo_audio
            
        except Exception as e:
            print(f"エコーエラー: {e}")
            return audio
    
    # ================================
    # 環境エフェクト（空間・状況再現系）
    # ================================
    
    def apply_phone_quality(self, audio, intensity):
        """
        電話音質エフェクト
        帯域制限（300Hz-3400Hz）+ 圧縮感
        """
        try:
            # scipy.signalでバンドパスフィルター
            from scipy.signal import butter, filtfilt
            
            nyquist = 0.5 * self.sample_rate
            
            # 電話の周波数帯域（300Hz - 3400Hz）
            low_freq = 300.0
            high_freq = 3400.0
            
            # intensityに応じて帯域を調整
            # intensity 0: 通常音質
            # intensity 1: 完全に電話音質
            
            low_cut = low_freq * (1 + intensity * 0.5)  # 300Hz → 450Hz
            high_cut = high_freq * (1 - intensity * 0.3)  # 3400Hz → 2380Hz
            
            low_normalized = low_cut / nyquist
            high_normalized = high_cut / nyquist
            
            # 正規化周波数が範囲内かチェック
            if low_normalized >= 1.0 or high_normalized >= 1.0:
                return audio
            
            # バンドパスフィルター
            b, a = butter(4, [low_normalized, high_normalized], btype='band')
            filtered_audio = filtfilt(b, a, audio)
            
            # 軽い圧縮効果（電話の音質再現）
            compressed_audio = np.tanh(filtered_audio * 1.5) * 0.8
            
            # 原音とのミックス
            result = (1 - intensity) * audio + intensity * compressed_audio
            
            return result
            
        except ImportError:
            print("⚠️ scipy.signalが利用できません。電話音質エフェクトをスキップします。")
            return audio
        except Exception as e:
            print(f"電話音質エラー: {e}")
            return audio
    
    def apply_through_wall(self, audio, intensity):
        """
        壁越し音声エフェクト
        ローパスフィルター + 音量減衰 + わずかな反響
        """
        try:
            from scipy.signal import butter, filtfilt
            
            nyquist = 0.5 * self.sample_rate
            
            # intensityに応じたカットオフ周波数
            # intensity 0: 8000Hz（ほぼ通常）
            # intensity 1: 1000Hz（完全に壁越し）
            cutoff_freq = 8000 * (1 - intensity * 0.875)  # 8000Hz → 1000Hz
            cutoff_normalized = cutoff_freq / nyquist
            
            if cutoff_normalized >= 1.0:
                filtered_audio = audio
            else:
                # ローパスフィルター
                b, a = butter(6, cutoff_normalized, btype='low')
                filtered_audio = filtfilt(b, a, audio)
            
            # 音量減衰
            volume_reduction = 1.0 - intensity * 0.4  # 最大40%減衰
            filtered_audio *= volume_reduction
            
            # わずかな反響（壁の反射）
            if len(audio) > int(0.02 * self.sample_rate):  # 20ms以上の音声の場合
                reflection_delay = int(0.02 * self.sample_rate)  # 20ms
                reflection = np.zeros_like(audio)
                reflection[reflection_delay:] = filtered_audio[:-reflection_delay] * 0.1 * intensity
                filtered_audio += reflection
            
            return filtered_audio
            
        except ImportError:
            print("⚠️ scipy.signalが利用できません。壁越し音声エフェクトをスキップします。")
            return audio
        except Exception as e:
            print(f"壁越し音声エラー: {e}")
            return audio
    
    def apply_reverb(self, audio, intensity):
        """
        閉鎖空間（リバーブ）エフェクト
        複数の遅延による空間的な残響
        """
        try:
            # intensityに応じた部屋サイズ
            room_size = 0.3 + intensity * 0.7  # 0.3 ~ 1.0
            damping = 0.2 + intensity * 0.3    # 0.2 ~ 0.5
            
            # 複数の遅延時間（部屋の反射パターン）
            base_delays = [0.03, 0.05, 0.07, 0.09, 0.11, 0.13, 0.17, 0.19]
            reverb_audio = audio.copy()
            
            for i, base_delay in enumerate(base_delays):
                # 部屋サイズに応じて遅延時間を調整
                delay = base_delay * room_size
                delay_samples = int(delay * self.sample_rate)
                
                if delay_samples < len(audio):
                    # 減衰計算（距離と材質による）
                    decay_factor = (0.8 ** i) * (1 - damping) * intensity * 0.4
                    
                    # 遅延音声の作成
                    delayed_audio = np.zeros_like(audio)
                    delayed_audio[delay_samples:] = audio[:-delay_samples] * decay_factor
                    
                    # 左右の広がり（ステレオ効果のため）
                    if i % 2 == 1:
                        delayed_audio *= 0.8  # 若干音量を下げて広がり感
                    
                    reverb_audio += delayed_audio
            
            # 早期反射（壁からの直接反射）
            early_delay = int(0.01 * self.sample_rate)  # 10ms
            if early_delay < len(audio):
                early_reflection = np.zeros_like(audio)
                early_reflection[early_delay:] = audio[:-early_delay] * 0.2 * intensity
                reverb_audio += early_reflection
            
            return reverb_audio
            
        except Exception as e:
            print(f"リバーブエラー: {e}")
            return audio
    
    # ================================
    # ユーティリティメソッド
    # ================================
    
    def _normalize_audio(self, audio, target_level=0.8):
        """
        音声レベルを正規化（クリッピング防止）
        """
        try:
            max_val = np.abs(audio).max()
            if max_val > target_level:
                audio = audio * (target_level / max_val)
            
            return audio.astype(np.float32)
            
        except Exception:
            return audio.astype(np.float32)
    
    def get_effects_info(self, effects_settings):
        """
        適用されるエフェクトの情報を取得（デバッグ用）
        """
        active_effects = []
        
        # 音声エフェクト
        if effects_settings.get('robot_enabled'):
            active_effects.append(f"ロボット音声({effects_settings.get('robot_intensity', 0):.2f})")
        if effects_settings.get('voice_change_enabled'):
            semitones = effects_settings.get('voice_change_intensity', 0)
            active_effects.append(f"ボイスチェンジ({semitones:+.0f}半音)")
        if effects_settings.get('distortion_enabled'):
            active_effects.append(f"ディストーション({effects_settings.get('distortion_intensity', 0):.2f})")
        if effects_settings.get('echo_enabled'):
            active_effects.append(f"やまびこ({effects_settings.get('echo_intensity', 0):.2f})")
        
        # 環境エフェクト
        if effects_settings.get('phone_enabled'):
            active_effects.append(f"電話音質({effects_settings.get('phone_intensity', 0):.2f})")
        if effects_settings.get('through_wall_enabled'):
            active_effects.append(f"壁越し({effects_settings.get('through_wall_intensity', 0):.2f})")
        if effects_settings.get('reverb_enabled'):
            active_effects.append(f"閉鎖空間({effects_settings.get('reverb_intensity', 0):.2f})")
        
        return active_effects