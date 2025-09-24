import json
import time
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
from threading import Thread, Event
import traceback

try:
    import pyopenjtalk
    PYOPENJTALK_AVAILABLE = True
except ImportError:
    PYOPENJTALK_AVAILABLE = False
    print("⚠️ pyopenjtalk が利用できません。リップシンク機能は制限されます。")

@dataclass
class VowelFrame:
    """母音フレームデータ"""
    timestamp: float      # タイムスタンプ（秒）
    vowel: str           # 母音 ('a', 'i', 'u', 'e', 'o', 'n', 'sil')
    intensity: float     # 強度 (0.0-1.0)
    duration: float      # 持続時間（秒）

@dataclass
class LipSyncData:
    """リップシンクデータ"""
    text: str
    total_duration: float
    vowel_frames: List[VowelFrame]
    sample_rate: int = 22050

class LipSyncEngine:
    """メインリップシンクエンジン
    
    Style-Bert-VITS2の音素解析とLive2Dリップシンクを統合
    """
    
    def __init__(self):
        self.is_initialized = PYOPENJTALK_AVAILABLE
        self.phoneme_analyzer = None
        self.audio_processor = None
        
        # リップシンク設定
        self.settings = {
            'enabled': True,
            'sensitivity': 80,
            'response_speed': 70,
            'mouth_open_scale': 100,
            'auto_optimize': True,
            'delay_compensation': 0,
            'smoothing_factor': 70,
            'prediction_enabled': True,
            'consonant_detection': True,
            'volume_threshold': 5,
            'quality_mode': 'balanced'
        }
        
        # 母音マッピング設定（Live2Dパラメータ用）
        self.vowel_mapping = {
            'a': {'mouth_open': 100, 'mouth_form': 0},      # あ：大きく開く
            'i': {'mouth_open': 30, 'mouth_form': -100},    # い：横に広げる
            'u': {'mouth_open': 40, 'mouth_form': -70},     # う：すぼめる
            'e': {'mouth_open': 60, 'mouth_form': -30},     # え：中間
            'o': {'mouth_open': 80, 'mouth_form': 70},      # お：丸く開く
            'n': {'mouth_open': 10, 'mouth_form': 0},       # ん：閉じ気味
            'sil': {'mouth_open': 0, 'mouth_form': 0}       # 無音：閉じる
        }
        
        self._initialize_modules()
    
    def _initialize_modules(self):
        """関連モジュールの初期化"""
        try:
            if PYOPENJTALK_AVAILABLE:
                # pyopenjtalk の初期化確認
                test_result = pyopenjtalk.g2p("テスト")
                if test_result:
                    print("✅ pyopenjtalk初期化成功")
                else:
                    print("⚠️ pyopenjtalk初期化に問題があります")
                    self.is_initialized = False
            
            from .phoneme_analyzer import PhonemeAnalyzer
            from .audio_realtime_processor import AudioRealtimeProcessor
            
            self.phoneme_analyzer = PhonemeAnalyzer()
            self.audio_processor = AudioRealtimeProcessor()
            
            print("✅ LipSyncEngine初期化完了")
            
        except ImportError as e:
            print(f"⚠️ リップシンクモジュール読み込みエラー: {e}")
            self.is_initialized = False
        except Exception as e:
            print(f"❌ LipSyncEngine初期化エラー: {e}")
            self.is_initialized = False
    
    def is_available(self) -> bool:
        """リップシンク機能が利用可能かチェック"""
        return self.is_initialized and PYOPENJTALK_AVAILABLE
    
    def update_settings(self, settings: Dict[str, Any]):
        """リップシンク設定を更新"""
        try:
            if 'basic' in settings:
                basic_settings = settings['basic']
                self.settings.update({
                    'enabled': basic_settings.get('enabled', self.settings['enabled']),
                    'sensitivity': basic_settings.get('sensitivity', self.settings['sensitivity']),
                    'response_speed': basic_settings.get('response_speed', self.settings['response_speed']),
                    'mouth_open_scale': basic_settings.get('mouth_open_scale', self.settings['mouth_open_scale']),
                    'auto_optimize': basic_settings.get('auto_optimize', self.settings['auto_optimize'])
                })
            
            if 'phoneme' in settings:
                phoneme_settings = settings['phoneme']
                for vowel, params in phoneme_settings.items():
                    if vowel in self.vowel_mapping:
                        self.vowel_mapping[vowel].update(params)
            
            if 'advanced' in settings:
                advanced_settings = settings['advanced']
                self.settings.update({
                    'delay_compensation': advanced_settings.get('delay_compensation', self.settings['delay_compensation']),
                    'smoothing_factor': advanced_settings.get('smoothing_factor', self.settings['smoothing_factor']),
                    'prediction_enabled': advanced_settings.get('prediction_enabled', self.settings['prediction_enabled']),
                    'consonant_detection': advanced_settings.get('consonant_detection', self.settings['consonant_detection']),
                    'volume_threshold': advanced_settings.get('volume_threshold', self.settings['volume_threshold']),
                    'quality_mode': advanced_settings.get('quality_mode', self.settings['quality_mode'])
                })
            
            print(f"🔧 リップシンク設定更新完了")
            
        except Exception as e:
            print(f"❌ 設定更新エラー: {e}")
    
    def analyze_text_for_lipsync(self, text: str) -> Optional[LipSyncData]:
        """テキストをリップシンク用に解析
        
        Args:
            text: 解析するテキスト
            
        Returns:
            LipSyncData: リップシンクデータ（失敗時はNone）
        """
        if not self.is_available() or not self.settings['enabled']:
            return None
        
        try:
            print(f"🔍 リップシンク解析開始: '{text[:50]}...'")
            
            # pyopenjtalkで音素解析
            if not PYOPENJTALK_AVAILABLE:
                return self._fallback_analysis(text)
            
            # 音素とタイミング情報を取得
            phoneme_data = self._extract_phonemes_with_timing(text)
            if not phoneme_data:
                return self._fallback_analysis(text)
            
            # 母音フレームに変換
            vowel_frames = self._convert_to_vowel_frames(phoneme_data)
            
            # 設定に応じて調整
            vowel_frames = self._apply_settings_to_frames(vowel_frames)
            
            # 総再生時間を推定
            total_duration = self._estimate_duration(text, len(vowel_frames))
            
            lipsync_data = LipSyncData(
                text=text,
                total_duration=total_duration,
                vowel_frames=vowel_frames
            )
            
            print(f"✅ リップシンク解析完了: {len(vowel_frames)}フレーム, {total_duration:.2f}秒")
            return lipsync_data
            
        except Exception as e:
            print(f"❌ リップシンク解析エラー: {e}")
            print(traceback.format_exc())
            return self._fallback_analysis(text)
    
    def _extract_phonemes_with_timing(self, text: str) -> Optional[List[Dict]]:
        """pyopenjtalkで音素とタイミング情報を抽出"""
        try:
            # pyopenjtalkで詳細解析
            features = pyopenjtalk.run_frontend(text)
            
            phoneme_list = []
            current_time = 0.0
            
            for feature in features:
                # フィーチャーから音素情報を抽出
                if hasattr(feature, 'phoneme') or 'phoneme' in feature:
                    phoneme = feature.get('phoneme', '') if isinstance(feature, dict) else getattr(feature, 'phoneme', '')
                    
                    # 音素の推定再生時間（ヒューリスティック）
                    duration = self._estimate_phoneme_duration(phoneme)
                    
                    phoneme_list.append({
                        'phoneme': phoneme,
                        'start_time': current_time,
                        'duration': duration
                    })
                    
                    current_time += duration
            
            if not phoneme_list:
                # フォールバック: シンプルなg2p解析
                phonemes = pyopenjtalk.g2p(text, kana=False)
                phoneme_sequence = phonemes.split()
                
                avg_duration = 0.15  # 平均音素時間
                for i, phoneme in enumerate(phoneme_sequence):
                    phoneme_list.append({
                        'phoneme': phoneme,
                        'start_time': i * avg_duration,
                        'duration': avg_duration
                    })
            
            return phoneme_list
            
        except Exception as e:
            print(f"⚠️ 音素抽出エラー: {e}")
            return None
    
    def _estimate_phoneme_duration(self, phoneme: str) -> float:
        """音素の推定再生時間を計算"""
        # 母音は長め、子音は短め
        if phoneme in ['a', 'i', 'u', 'e', 'o']:
            return 0.2  # 母音：200ms
        elif phoneme in ['N', 'Q', 'pau']:
            return 0.1  # 特殊音素：100ms
        else:
            return 0.12  # 子音：120ms
    
    def _convert_to_vowel_frames(self, phoneme_data: List[Dict]) -> List[VowelFrame]:
        """音素データを母音フレームに変換"""
        vowel_frames = []
        
        for phoneme_info in phoneme_data:
            phoneme = phoneme_info['phoneme']
            start_time = phoneme_info['start_time']
            duration = phoneme_info['duration']
            
            # 音素を母音にマッピング
            vowel = self._map_phoneme_to_vowel(phoneme)
            
            # 強度を計算（母音は強く、子音は弱く）
            intensity = self._calculate_intensity(phoneme, vowel)
            
            vowel_frame = VowelFrame(
                timestamp=start_time,
                vowel=vowel,
                intensity=intensity,
                duration=duration
            )
            
            vowel_frames.append(vowel_frame)
        
        return vowel_frames
    
    def _map_phoneme_to_vowel(self, phoneme: str) -> str:
        """音素を母音にマッピング"""
        # 直接的な母音マッピング
        vowel_map = {
            'a': 'a', 'i': 'i', 'u': 'u', 'e': 'e', 'o': 'o',
            'A': 'a', 'I': 'i', 'U': 'u', 'E': 'e', 'O': 'o',
            'N': 'n',  # ん
            'Q': 'sil', 'pau': 'sil', 'sil': 'sil'  # 無音
        }
        
        if phoneme in vowel_map:
            return vowel_map[phoneme]
        
        # 子音の場合、後続する母音を推定
        # 簡易版：子音は直前の母音を継続または無音
        return 'sil'  # デフォルトは無音
    
    def _calculate_intensity(self, phoneme: str, vowel: str) -> float:
        """音素の強度を計算"""
        if vowel in ['a', 'e', 'o']:
            return 0.9  # 開口母音は強め
        elif vowel in ['i', 'u']:
            return 0.7  # 閉口母音は中程度
        elif vowel == 'n':
            return 0.3  # んは弱め
        else:
            return 0.1  # 子音・無音は最小
    
    def _apply_settings_to_frames(self, frames: List[VowelFrame]) -> List[VowelFrame]:
        """設定に基づいてフレームを調整"""
        adjusted_frames = []
        
        sensitivity = self.settings['sensitivity'] / 100.0
        mouth_scale = self.settings['mouth_open_scale'] / 100.0
        
        for frame in frames:
            # 強度調整
            adjusted_intensity = frame.intensity * sensitivity
            adjusted_intensity = max(0.0, min(1.0, adjusted_intensity))
            
            # 口の開きスケール調整
            if frame.vowel in self.vowel_mapping:
                original_open = self.vowel_mapping[frame.vowel]['mouth_open']
                scaled_open = original_open * mouth_scale
                self.vowel_mapping[frame.vowel]['mouth_open'] = max(0, min(100, scaled_open))
            
            adjusted_frame = VowelFrame(
                timestamp=frame.timestamp,
                vowel=frame.vowel,
                intensity=adjusted_intensity,
                duration=frame.duration
            )
            
            adjusted_frames.append(adjusted_frame)
        
        return adjusted_frames
    
    def _estimate_duration(self, text: str, frame_count: int) -> float:
        """総再生時間を推定"""
        # 文字数ベースの推定
        char_count = len(text)
        base_duration = char_count * 0.15  # 1文字150ms程度
        
        # フレーム数による補正
        if frame_count > 0:
            frame_duration = frame_count * 0.12
            estimated_duration = (base_duration + frame_duration) / 2
        else:
            estimated_duration = base_duration
        
        return max(0.5, estimated_duration)  # 最小0.5秒
    
    def _fallback_analysis(self, text: str) -> LipSyncData:
        """フォールバック解析（pyopenjtalkが使えない場合）"""
        print("⚠️ フォールバックモードでリップシンク解析")
        
        # 簡易的な母音推定
        char_count = len(text)
        duration_per_char = 0.2
        total_duration = char_count * duration_per_char
        
        # デフォルト母音フレーム生成
        vowel_frames = []
        default_vowels = ['a', 'i', 'u', 'e', 'o']
        
        for i in range(min(char_count, 10)):  # 最大10フレーム
            vowel = default_vowels[i % len(default_vowels)]
            frame = VowelFrame(
                timestamp=i * duration_per_char,
                vowel=vowel,
                intensity=0.7,
                duration=duration_per_char
            )
            vowel_frames.append(frame)
        
        return LipSyncData(
            text=text,
            total_duration=total_duration,
            vowel_frames=vowel_frames
        )
    
    def generate_lipsync_keyframes(self, lipsync_data: LipSyncData, fps: int = 30) -> Dict[str, Any]:
        """Live2D用のキーフレームデータを生成
        
        Args:
            lipsync_data: リップシンクデータ
            fps: フレームレート（デフォルト30fps）
            
        Returns:
            Dict: Live2D用のキーフレームデータ
        """
        try:
            if not lipsync_data or not lipsync_data.vowel_frames:
                return {}
            
            total_frames = int(lipsync_data.total_duration * fps)
            keyframes = {
                'total_duration': lipsync_data.total_duration,
                'fps': fps,
                'total_frames': total_frames,
                'vowel_keyframes': {},
                'mouth_params': {}
            }
            
            # 各母音用のキーフレーム生成
            for vowel in ['a', 'i', 'u', 'e', 'o', 'n']:
                keyframes['vowel_keyframes'][vowel] = []
            
            # 口の開閉パラメータ
            keyframes['mouth_params'] = {
                'mouth_open': [],
                'mouth_form': []
            }
            
            # フレームごとのデータ生成
            for frame_num in range(total_frames):
                current_time = frame_num / fps
                
                # 該当時間の母音フレームを探す
                active_frame = self._find_active_vowel_frame(lipsync_data.vowel_frames, current_time)
                
                if active_frame:
                    vowel = active_frame.vowel
                    intensity = active_frame.intensity
                    
                    # 母音キーフレーム
                    for v in keyframes['vowel_keyframes']:
                        value = intensity if v == vowel else 0.0
                        keyframes['vowel_keyframes'][v].append({
                            'frame': frame_num,
                            'value': value
                        })
                    
                    # 口パラメータキーフレーム
                    if vowel in self.vowel_mapping:
                        mapping = self.vowel_mapping[vowel]
                        mouth_open = (mapping['mouth_open'] / 100.0) * intensity
                        mouth_form = (mapping['mouth_form'] / 100.0) * intensity
                    else:
                        mouth_open = 0.0
                        mouth_form = 0.0
                    
                    keyframes['mouth_params']['mouth_open'].append({
                        'frame': frame_num,
                        'value': mouth_open
                    })
                    keyframes['mouth_params']['mouth_form'].append({
                        'frame': frame_num,
                        'value': mouth_form
                    })
                else:
                    # 無音フレーム
                    for v in keyframes['vowel_keyframes']:
                        keyframes['vowel_keyframes'][v].append({
                            'frame': frame_num,
                            'value': 0.0
                        })
                    
                    keyframes['mouth_params']['mouth_open'].append({
                        'frame': frame_num,
                        'value': 0.0
                    })
                    keyframes['mouth_params']['mouth_form'].append({
                        'frame': frame_num,
                        'value': 0.0
                    })
            
            print(f"✅ キーフレーム生成完了: {total_frames}フレーム")
            return keyframes
            
        except Exception as e:
            print(f"❌ キーフレーム生成エラー: {e}")
            return {}
    
    def _find_active_vowel_frame(self, vowel_frames: List[VowelFrame], current_time: float) -> Optional[VowelFrame]:
        """指定時間にアクティブな母音フレームを見つける"""
        for frame in vowel_frames:
            if frame.timestamp <= current_time < (frame.timestamp + frame.duration):
                return frame
        return None
    
    def export_lipsync_data(self, lipsync_data: LipSyncData, output_path: str) -> bool:
        """リップシンクデータをJSONファイルに出力"""
        try:
            # キーフレーム生成
            keyframes = self.generate_lipsync_keyframes(lipsync_data)
            
            export_data = {
                'metadata': {
                    'text': lipsync_data.text,
                    'total_duration': lipsync_data.total_duration,
                    'frame_count': len(lipsync_data.vowel_frames),
                    'generated_at': time.time(),
                    'engine_version': '1.0.0'
                },
                'settings': self.settings,
                'vowel_mapping': self.vowel_mapping,
                'keyframes': keyframes,
                'raw_vowel_frames': [
                    {
                        'timestamp': frame.timestamp,
                        'vowel': frame.vowel,
                        'intensity': frame.intensity,
                        'duration': frame.duration
                    }
                    for frame in lipsync_data.vowel_frames
                ]
            }
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ リップシンクデータ出力完了: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ データ出力エラー: {e}")
            return False
    
    def get_vowel_mapping(self) -> Dict[str, Dict[str, float]]:
        """現在の母音マッピング設定を取得"""
        return self.vowel_mapping.copy()
    
    def get_settings(self) -> Dict[str, Any]:
        """現在のリップシンク設定を取得"""
        return self.settings.copy()
    
    def debug_analysis(self, text: str) -> Dict[str, Any]:
        """デバッグ用：解析結果の詳細情報"""
        debug_info = {
            'input_text': text,
            'pyopenjtalk_available': PYOPENJTALK_AVAILABLE,
            'engine_initialized': self.is_initialized,
            'settings': self.settings,
            'vowel_mapping': self.vowel_mapping
        }
        
        if PYOPENJTALK_AVAILABLE:
            try:
                # pyopenjtalk解析結果
                g2p_result = pyopenjtalk.g2p(text, kana=False)
                debug_info['g2p_result'] = g2p_result
                
                # 詳細解析
                lipsync_data = self.analyze_text_for_lipsync(text)
                if lipsync_data:
                    debug_info['analysis_result'] = {
                        'total_duration': lipsync_data.total_duration,
                        'frame_count': len(lipsync_data.vowel_frames),
                        'vowel_sequence': [f.vowel for f in lipsync_data.vowel_frames]
                    }
                
            except Exception as e:
                debug_info['error'] = str(e)
        
        return debug_info