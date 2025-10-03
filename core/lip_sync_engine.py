import json
import time
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
from threading import Thread, Event
import traceback
import copy

try:
    import pyopenjtalk
    PYOPENJTALK_AVAILABLE = True
except ImportError:
    PYOPENJTALK_AVAILABLE = False
    print("⚠️ pyopenjtalk が利用できません。リップシンク機能は制限されます。")

@dataclass
class VowelFrame:
    """母音フレームデータ"""
    timestamp: float
    vowel: str
    intensity: float
    duration: float
    is_ending: bool = False

@dataclass
class LipSyncData:
    """リップシンクデータ"""
    text: str
    total_duration: float
    vowel_frames: List[VowelFrame]
    sample_rate: int = 22050

class LipSyncEngine:
    """メインリップシンクエンジン - 完全修正版
    
    音声データ対応 + 現実的な時間推定
    """
    
    def __init__(self):
        self.is_initialized = PYOPENJTALK_AVAILABLE
        self.phoneme_analyzer = None
        self.audio_processor = None
        
        self.ending_protection = {
            'enabled': True,
            'min_duration': 0.15,
            'intensity_boost': 1.05,
            'detection_range': 1
        }
        
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
            'quality_mode': 'balanced',
            'audio_sync_enabled': True,
            'char_duration': 0.08  # 🔥 1文字あたりの時間（秒）
        }
        
        self.base_vowel_mapping = {
            'a': {'mouth_open': 100, 'mouth_form': 0},
            'i': {'mouth_open': 30, 'mouth_form': -100},
            'u': {'mouth_open': 40, 'mouth_form': -70},
            'e': {'mouth_open': 60, 'mouth_form': -30},
            'o': {'mouth_open': 80, 'mouth_form': 70},
            'n': {'mouth_open': 10, 'mouth_form': 0},
            'sil': {'mouth_open': 0, 'mouth_form': 0}
        }
        
        self.vowel_mapping = copy.deepcopy(self.base_vowel_mapping)
        self.settings_change_callback = None
        
        self._initialize_modules()
    
    def _initialize_modules(self):
        """関連モジュールの初期化"""
        try:
            if PYOPENJTALK_AVAILABLE:
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
            
            print("✅ LipSyncEngine初期化完了 (完全修正版)")
            
        except ImportError as e:
            print(f"⚠️ リップシンクモジュール読み込みエラー: {e}")
            self.is_initialized = False
        except Exception as e:
            print(f"❌ LipSyncEngine初期化エラー: {e}")
            self.is_initialized = False
    
    def is_available(self) -> bool:
        """リップシンク機能が利用可能かチェック"""
        return self.is_initialized and PYOPENJTALK_AVAILABLE
    
    def set_settings_change_callback(self, callback):
        """設定変更通知コールバックを設定"""
        self.settings_change_callback = callback
    
    def update_settings(self, settings: Dict[str, Any]):
        """リップシンク設定を更新"""
        try:
            print(f"🔧 設定更新開始: {list(settings.keys())}")
            
            if 'basic' in settings:
                basic_settings = settings['basic']
                if isinstance(basic_settings, dict):
                    for key in ['enabled', 'sensitivity', 'response_speed', 'mouth_open_scale', 'auto_optimize', 'audio_sync_enabled', 'char_duration']:
                        if key in basic_settings:
                            if key in ['enabled', 'auto_optimize', 'audio_sync_enabled']:
                                self.settings[key] = bool(basic_settings[key])
                            elif key in ['sensitivity', 'response_speed', 'mouth_open_scale']:
                                self.settings[key] = max(0, min(500, int(basic_settings[key])))
                            elif key == 'char_duration':
                                self.settings[key] = max(0.05, min(0.3, float(basic_settings[key])))
                            else:
                                self.settings[key] = basic_settings[key]
            
            if 'ending_protection' in settings:
                protection_settings = settings['ending_protection']
                if isinstance(protection_settings, dict):
                    for key in ['enabled', 'min_duration', 'intensity_boost', 'detection_range']:
                        if key in protection_settings:
                            if key == 'enabled':
                                self.ending_protection[key] = bool(protection_settings[key])
                            elif key == 'min_duration':
                                self.ending_protection[key] = max(0.1, min(1.0, float(protection_settings[key])))
                            elif key == 'intensity_boost':
                                self.ending_protection[key] = max(1.0, min(3.0, float(protection_settings[key])))
                            elif key == 'detection_range':
                                self.ending_protection[key] = max(1, min(10, int(protection_settings[key])))
            
            if 'phoneme' in settings:
                phoneme_settings = settings['phoneme']
                if isinstance(phoneme_settings, dict):
                    for vowel, params in phoneme_settings.items():
                        if vowel in self.vowel_mapping and isinstance(params, dict):
                            if 'mouth_open' in params:
                                try:
                                    value = float(params['mouth_open'])
                                    self.vowel_mapping[vowel]['mouth_open'] = max(0, min(500, value))
                                except (ValueError, TypeError):
                                    pass
                            if 'mouth_form' in params:
                                try:
                                    value = float(params['mouth_form'])
                                    self.vowel_mapping[vowel]['mouth_form'] = max(-500, min(500, value))
                                except (ValueError, TypeError):
                                    pass
            
            if 'advanced' in settings:
                advanced_settings = settings['advanced']
                if isinstance(advanced_settings, dict):
                    for key in ['delay_compensation', 'smoothing_factor', 'prediction_enabled', 
                               'consonant_detection', 'volume_threshold', 'quality_mode']:
                        if key in advanced_settings:
                            value = advanced_settings[key]
                            if key == 'delay_compensation':
                                self.settings[key] = max(-1000, min(1000, int(value)))
                            elif key in ['smoothing_factor', 'volume_threshold']:
                                self.settings[key] = max(0, min(100, int(value)))
                            elif key in ['prediction_enabled', 'consonant_detection']:
                                self.settings[key] = bool(value)
                            else:
                                self.settings[key] = value
            
            if self.settings_change_callback:
                try:
                    self.settings_change_callback(self.get_current_live2d_params())
                except Exception as e:
                    print(f"  ⚠️ Live2D通知エラー: {e}")
            
            print(f"✅ リップシンク設定更新完了")
            
        except Exception as e:
            print(f"❌ 設定更新エラー: {e}")
            traceback.print_exc()
    
    def get_current_live2d_params(self) -> Dict[str, Any]:
        """Live2D用の現在のパラメータを取得"""
        return {
            'vowel_mapping': copy.deepcopy(self.vowel_mapping),
            'settings': copy.deepcopy(self.settings),
            'ending_protection': copy.deepcopy(self.ending_protection),
            'enabled': self.settings.get('enabled', True)
        }
        
    def analyze_text_for_lipsync(self, text: str, audio_data: np.ndarray = None, 
                                sample_rate: int = None) -> Optional[LipSyncData]:
        """テキストをリップシンク用に解析（音声対応統合版 + 無音検出）
        
        Args:
            text: 解析するテキスト
            audio_data: 実際の音声データ（オプション）
            sample_rate: サンプルレート
            
        Returns:
            LipSyncData: リップシンクデータ
        """
        if not self.is_available() or not self.settings['enabled']:
            print("⚠️ リップシンク無効またはエンジン利用不可")
            return None
        
        try:
            # 🔥 実際の音声長さを取得
            actual_duration = None
            if audio_data is not None and sample_rate is not None:
                actual_duration = len(audio_data) / sample_rate
                print(f"🎵 実際の音声長さ: {actual_duration:.3f}秒")
            
            print(f"🔍 リップシンク解析開始: '{text[:50]}...'")
            
            # pyopenjtalkで音素解析
            if not PYOPENJTALK_AVAILABLE:
                return self._fallback_analysis(text, actual_duration)
            
            # 音素とタイミング情報を取得
            phoneme_data = self._extract_phonemes_with_timing(text)
            if not phoneme_data:
                return self._fallback_analysis(text, actual_duration)
            
            # 語尾音素を検出・マーキング
            phoneme_data = self._mark_ending_phonemes(phoneme_data)
            
            # 母音フレームに変換
            vowel_frames = self._convert_to_vowel_frames(phoneme_data)
            
            # 🔥 実際の音声長さに合わせてスケール調整
            if actual_duration is not None:
                estimated_duration = sum(f.duration for f in vowel_frames)
                if estimated_duration > 0:
                    time_scale = actual_duration / estimated_duration
                    print(f"⏱️ タイムスケール調整: {estimated_duration:.3f}s → {actual_duration:.3f}s (x{time_scale:.3f})")
                    
                    scaled_frames = []
                    current_time = 0.0
                    for frame in vowel_frames:
                        new_duration = frame.duration * time_scale
                        scaled_frame = VowelFrame(
                            timestamp=current_time,
                            vowel=frame.vowel,
                            intensity=frame.intensity,
                            duration=new_duration,
                            is_ending=frame.is_ending
                        )
                        scaled_frames.append(scaled_frame)
                        current_time += new_duration
                    
                    vowel_frames = scaled_frames
                    total_duration = actual_duration
                else:
                    total_duration = actual_duration
            else:
                # 🔥 音声データがない場合は、テキスト長から推定
                total_duration = self._estimate_duration_from_text(text)
                estimated_duration = sum(f.duration for f in vowel_frames)
                
                if estimated_duration > 0:
                    time_scale = total_duration / estimated_duration
                    print(f"⏱️ テキストベース調整: {estimated_duration:.3f}s → {total_duration:.3f}s (x{time_scale:.3f})")
                    
                    scaled_frames = []
                    current_time = 0.0
                    for frame in vowel_frames:
                        new_duration = frame.duration * time_scale
                        scaled_frame = VowelFrame(
                            timestamp=current_time,
                            vowel=frame.vowel,
                            intensity=frame.intensity,
                            duration=new_duration,
                            is_ending=frame.is_ending
                        )
                        scaled_frames.append(scaled_frame)
                        current_time += new_duration
                    
                    vowel_frames = scaled_frames
            
            # 🆕 無音区間検出と適用（音声データがある場合のみ）
            if audio_data is not None and sample_rate is not None:
                silence_regions = self._detect_silence_regions(
                    audio_data, 
                    sample_rate,
                    min_silence_duration=0.2,  # 0.2秒以上の無音を検出
                    adaptive_threshold=True
                )
                
                if silence_regions:
                    vowel_frames = self._apply_silence_regions_to_frames(vowel_frames, silence_regions)
            
            # 語尾保護機能を適用
            vowel_frames = self._apply_ending_protection_to_frames(vowel_frames)
            
            # 設定に応じて調整
            vowel_frames = self._apply_settings_to_frames_safe(vowel_frames)
            
            lipsync_data = LipSyncData(
                text=text,
                total_duration=total_duration,
                vowel_frames=vowel_frames
            )
            
            print(f"✅ リップシンク解析完了: {len(vowel_frames)}フレーム, {total_duration:.3f}秒")
            
            ending_count = sum(1 for f in vowel_frames if f.is_ending)
            silence_count = sum(1 for f in vowel_frames if f.vowel == 'sil')
            if ending_count > 0:
                print(f"🛡️ 語尾保護適用: {ending_count}個の語尾音素")
            if silence_count > 0:
                print(f"🔇 無音フレーム: {silence_count}個")
            
            return lipsync_data
            
        except Exception as e:
            print(f"❌ リップシンク解析エラー: {e}")
            print(traceback.format_exc())
            return self._fallback_analysis(text, actual_duration)
    
    def _estimate_duration_from_text(self, text: str) -> float:
        """テキストから総時間を推定（現実的な値）"""
        # 日本語の平均的な読み上げ速度を考慮
        char_count = len(text)
        char_duration = self.settings.get('char_duration', 0.08)  # 1文字0.08秒
        
        # 句読点や記号は時間に含めない
        punctuation_count = sum(1 for c in text if c in '。、！？…～ー・')
        effective_chars = max(1, char_count - punctuation_count * 0.5)
        
        estimated = effective_chars * char_duration
        print(f"📏 推定時間: {char_count}文字 → {estimated:.3f}秒 ({char_duration}秒/文字)")
        
        return max(0.5, estimated)
    
    def _extract_phonemes_with_timing(self, text: str) -> Optional[List[Dict]]:
        """pyopenjtalkで音素とタイミング情報を抽出"""
        try:
            print(f"🔍 音素抽出開始: '{text}'")
            
            phonemes_result = pyopenjtalk.g2p(text, kana=False)
            print(f"  📝 g2p結果: '{phonemes_result}'")
            
            if phonemes_result and phonemes_result.strip():
                raw_phoneme_sequence = phonemes_result.strip().split()
                print(f"  🔗 生音素列: {raw_phoneme_sequence}")
                
                phoneme_sequence = self._merge_phonemes(raw_phoneme_sequence)
                print(f"  🔗 結合後音素列: {phoneme_sequence}")
                
                phoneme_list = []
                current_time = 0.0
                
                for i, phoneme in enumerate(phoneme_sequence):
                    if not phoneme or phoneme.isspace():
                        continue
                    
                    # 🔥 短い基本時間（後でスケール調整される）
                    duration = self._estimate_phoneme_duration_base(phoneme)
                    
                    phoneme_data = {
                        'phoneme': phoneme,
                        'start_time': current_time,
                        'duration': duration,
                        'is_ending': False,
                        'index': i
                    }
                    
                    phoneme_list.append(phoneme_data)
                    current_time += duration
                    print(f"    {i}: {phoneme} ({duration:.2f}s)")
                
                print(f"  ✅ 音素抽出成功: {len(phoneme_list)}個")
                return phoneme_list
            
            return None
            
        except Exception as e:
            print(f"❌ 音素抽出エラー: {e}")
            traceback.print_exc()
            return None
    
    def _merge_phonemes(self, raw_phonemes: List[str]) -> List[str]:
        """分解されすぎた音素を適切に結合する"""
        if not raw_phonemes:
            return []
        
        merged = []
        i = 0
        
        while i < len(raw_phonemes):
            current = raw_phonemes[i]
            
            if i + 1 < len(raw_phonemes):
                next_phoneme = raw_phonemes[i + 1]
                
                combined = self._try_combine_phonemes(current, next_phoneme)
                if combined:
                    print(f"    🔗 音素結合: {current} + {next_phoneme} → {combined}")
                    merged.append(combined)
                    i += 2
                    continue
            
            converted = self._convert_single_phoneme(current)
            merged.append(converted)
            if converted != current:
                print(f"    🔄 音素変換: {current} → {converted}")
            i += 1
        
        return merged
    
    def _try_combine_phonemes(self, first: str, second: str) -> Optional[str]:
        """2つの音素を結合できるかチェック"""
        combination_rules = {
            ('k', 'a'): 'ka', ('k', 'i'): 'ki', ('k', 'u'): 'ku', ('k', 'e'): 'ke', ('k', 'o'): 'ko',
            ('g', 'a'): 'ga', ('g', 'i'): 'gi', ('g', 'u'): 'gu', ('g', 'e'): 'ge', ('g', 'o'): 'go',
            ('s', 'a'): 'sa', ('s', 'i'): 'si', ('s', 'u'): 'su', ('s', 'e'): 'se', ('s', 'o'): 'so',
            ('z', 'a'): 'za', ('z', 'i'): 'zi', ('z', 'u'): 'zu', ('z', 'e'): 'ze', ('z', 'o'): 'zo',
            ('t', 'a'): 'ta', ('t', 'i'): 'ti', ('t', 'u'): 'tu', ('t', 'e'): 'te', ('t', 'o'): 'to',
            ('d', 'a'): 'da', ('d', 'i'): 'di', ('d', 'u'): 'du', ('d', 'e'): 'de', ('d', 'o'): 'do',
            ('n', 'a'): 'na', ('n', 'i'): 'ni', ('n', 'u'): 'nu', ('n', 'e'): 'ne', ('n', 'o'): 'no',
            ('h', 'a'): 'ha', ('h', 'i'): 'hi', ('h', 'u'): 'hu', ('h', 'e'): 'he', ('h', 'o'): 'ho',
            ('b', 'a'): 'ba', ('b', 'i'): 'bi', ('b', 'u'): 'bu', ('b', 'e'): 'be', ('b', 'o'): 'bo',
            ('p', 'a'): 'pa', ('p', 'i'): 'pi', ('p', 'u'): 'pu', ('p', 'e'): 'pe', ('p', 'o'): 'po',
            ('m', 'a'): 'ma', ('m', 'i'): 'mi', ('m', 'u'): 'mu', ('m', 'e'): 'me', ('m', 'o'): 'mo',
            ('y', 'a'): 'ya', ('y', 'u'): 'yu', ('y', 'o'): 'yo',
            ('r', 'a'): 'ra', ('r', 'i'): 'ri', ('r', 'u'): 'ru', ('r', 'e'): 're', ('r', 'o'): 'ro',
            ('w', 'a'): 'wa', ('w', 'i'): 'wi', ('w', 'u'): 'wu', ('w', 'e'): 'we', ('w', 'o'): 'wo',
            ('ch', 'i'): 'chi', ('ch', 'u'): 'chu', ('ch', 'o'): 'cho',
            ('sh', 'i'): 'shi', ('sh', 'u'): 'shu', ('sh', 'o'): 'sho',
            ('j', 'i'): 'ji', ('j', 'u'): 'ju', ('j', 'o'): 'jo',
            ('w', 'a'): 'ha',
        }
        
        key = (first, second)
        return combination_rules.get(key)
    
    def _convert_single_phoneme(self, phoneme: str) -> str:
        """単独音素の変換ルール"""
        single_conversions = {
            'w': 'wa',
            'n': 'N',
        }
        
        return single_conversions.get(phoneme, phoneme)
    
    def _mark_ending_phonemes(self, phoneme_data: List[Dict]) -> List[Dict]:
        """語尾音素をマーキング"""
        if not self.ending_protection['enabled'] or not phoneme_data:
            return phoneme_data
        
        meaningful_phonemes = []
        for i, data in enumerate(phoneme_data):
            phoneme = data['phoneme']
            if phoneme not in ['pau', 'sil', 'sp', 'Q', 'cl']:
                meaningful_phonemes.append((i, phoneme))
        
        if not meaningful_phonemes:
            return phoneme_data
        
        ending_count = 1
        
        print(f"🛡️ 語尾検出: 有意味音素{len(meaningful_phonemes)}個中、末尾{ending_count}個を語尾として設定")
        
        for j in range(ending_count):
            if j < len(meaningful_phonemes):
                idx, phoneme = meaningful_phonemes[-(j + 1)]
                phoneme_data[idx]['is_ending'] = True
                print(f"  🛡️ 語尾音素: {phoneme}")
        
        return phoneme_data
    
    def _estimate_phoneme_duration_base(self, phoneme: str) -> float:
        """音素の基本推定再生時間を計算（短縮版・後でスケール調整）"""
        # 🔥 全体的に短く設定（後で総時間に合わせてスケール）
        if phoneme in ['a', 'i', 'u', 'e', 'o']:
            return 1.0  # 相対値（母音）
        elif phoneme in ['N', 'Q', 'pau', 'cl']:
            return 0.3  # 相対値（無音系は短く）
        else:
            return 0.7  # 相対値（子音）
    
    def _convert_to_vowel_frames(self, phoneme_data: List[Dict]) -> List[VowelFrame]:
        """音素データを母音フレームに変換"""
        vowel_frames = []
        
        print(f"  🔗 音素→母音変換開始: {len(phoneme_data)}個の音素")
        
        for i, phoneme_info in enumerate(phoneme_data):
            phoneme = phoneme_info['phoneme']
            start_time = phoneme_info['start_time']
            duration = phoneme_info['duration']
            is_ending = phoneme_info.get('is_ending', False)
            
            vowel = self._map_phoneme_to_vowel_fixed(phoneme)
            intensity = self._calculate_intensity(phoneme, vowel)
            
            vowel_frame = VowelFrame(
                timestamp=start_time,
                vowel=vowel,
                intensity=intensity,
                duration=duration,
                is_ending=is_ending
            )
            
            vowel_frames.append(vowel_frame)
            
            ending_mark = "🛡️" if is_ending else ""
            print(f"    {i}: {phoneme} → {vowel} (強度:{intensity:.2f}, 時間:{duration:.2f}s) {ending_mark}")
        
        print(f"  ✅ 母音フレーム変換完了: {len(vowel_frames)}個")
        return vowel_frames
    
    def _map_phoneme_to_vowel_fixed(self, phoneme: str) -> str:
        """音素を母音にマッピング"""
        complete_vowel_map = {
            'a': 'a', 'i': 'i', 'u': 'u', 'e': 'e', 'o': 'o',
            'A': 'a', 'I': 'i', 'U': 'u', 'E': 'e', 'O': 'o',
            'ka': 'a', 'ga': 'a', 'sa': 'a', 'za': 'a', 'ta': 'a', 'da': 'a',
            'na': 'a', 'ha': 'a', 'ba': 'a', 'pa': 'a', 'ma': 'a', 'ya': 'a',
            'ra': 'a', 'wa': 'a', 'kya': 'a', 'gya': 'a', 'sha': 'a', 'ja': 'a',
            'cha': 'a', 'nya': 'a', 'hya': 'a', 'bya': 'a', 'pya': 'a', 'mya': 'a', 'rya': 'a',
            'ki': 'i', 'gi': 'i', 'si': 'i', 'zi': 'i', 'ti': 'i', 'di': 'i',
            'ni': 'i', 'hi': 'i', 'bi': 'i', 'pi': 'i', 'mi': 'i', 'ri': 'i',
            'chi': 'i', 'ji': 'i', 'shi': 'i',
            'ku': 'u', 'gu': 'u', 'su': 'u', 'zu': 'u', 'tu': 'u', 'du': 'u',
            'nu': 'u', 'hu': 'u', 'bu': 'u', 'pu': 'u', 'mu': 'u', 'yu': 'u',
            'ru': 'u', 'tsu': 'u', 'kyu': 'u', 'gyu': 'u', 'shu': 'u', 'ju': 'u',
            'chu': 'u', 'nyu': 'u', 'hyu': 'u', 'byu': 'u', 'pyu': 'u', 'myu': 'u', 'ryu': 'u',
            'ke': 'e', 'ge': 'e', 'se': 'e', 'ze': 'e', 'te': 'e', 'de': 'e',
            'ne': 'e', 'he': 'e', 'be': 'e', 'pe': 'e', 'me': 'e', 're': 'e',
            'ko': 'o', 'go': 'o', 'so': 'o', 'zo': 'o', 'to': 'o', 'do': 'o',
            'no': 'o', 'ho': 'o', 'bo': 'o', 'po': 'o', 'mo': 'o', 'yo': 'o',
            'ro': 'o', 'kyo': 'o', 'gyo': 'o', 'sho': 'o', 'jo': 'o', 'cho': 'o',
            'nyo': 'o', 'hyo': 'o', 'byo': 'o', 'pyo': 'o', 'myo': 'o', 'ryo': 'o',
            'N': 'n',
            'Q': 'sil',
            'pau': 'sil',
            'sil': 'sil',
            'sp': 'sil',
            'cl': 'sil',  # 🔥 clも無音として扱う
            'ー': 'a',
            'w': 'u',
            'v': 'u',
            'f': 'u',
            'sh': 'i',  # 🔥 shを追加
        }
        
        if phoneme in complete_vowel_map:
            mapped_vowel = complete_vowel_map[phoneme]
            if phoneme not in ['pau', 'sil', 'sp', 'Q', 'cl'] and len(phoneme) > 1:
                print(f"      🔗 {phoneme} → {mapped_vowel}")
            return mapped_vowel
        
        if phoneme.endswith('a'):
            return 'a'
        elif phoneme.endswith('i'):
            return 'i'
        elif phoneme.endswith('u'):
            return 'u'
        elif phoneme.endswith('e'):
            return 'e'
        elif phoneme.endswith('o'):
            return 'o'
        
        print(f"      ⚠️ 未知音素: {phoneme} → sil")
        return 'sil'  # 🔥 未知音素は無音にする
    
    def _apply_ending_protection_to_frames(self, vowel_frames: List[VowelFrame]) -> List[VowelFrame]:
        """語尾保護機能をフレームに適用"""
        if not self.ending_protection['enabled']:
            return vowel_frames
        
        protected_frames = []
        
        for frame in vowel_frames:
            if frame.is_ending and frame.vowel != 'sil':
                protected_intensity = min(1.0, frame.intensity * self.ending_protection['intensity_boost'])
                
                protected_frame = VowelFrame(
                    timestamp=frame.timestamp,
                    vowel=frame.vowel,
                    intensity=protected_intensity,
                    duration=frame.duration,
                    is_ending=True
                )
                
                if protected_intensity > frame.intensity:
                    print(f"  🛡️ 語尾保護: {frame.vowel} (強度:{frame.intensity:.2f}→{protected_intensity:.2f})")
            else:
                protected_frame = frame
            
            protected_frames.append(protected_frame)
        
        return protected_frames
    
    def _calculate_intensity(self, phoneme: str, vowel: str) -> float:
        """音素の強度を計算"""
        if vowel in ['a', 'e', 'o']:
            return 0.9
        elif vowel in ['i', 'u']:
            return 0.7
        elif vowel == 'n':
            return 0.3
        else:
            return 0.1
    
    def _apply_settings_to_frames_safe(self, frames: List[VowelFrame]) -> List[VowelFrame]:
        """設定に基づいてフレームを調整"""
        adjusted_frames = []
        sensitivity = self.settings['sensitivity'] / 100.0
        
        print(f"🔧 フレーム調整: 感度={sensitivity:.2f}, フレーム数={len(frames)}")
        
        for frame in frames:
            adjusted_intensity = frame.intensity * sensitivity
            adjusted_intensity = max(0.0, min(1.0, adjusted_intensity))
            
            adjusted_frame = VowelFrame(
                timestamp=frame.timestamp,
                vowel=frame.vowel,
                intensity=adjusted_intensity,
                duration=frame.duration,
                is_ending=frame.is_ending
            )
            
            adjusted_frames.append(adjusted_frame)
        
        return adjusted_frames
    
    def _fallback_analysis(self, text: str, actual_duration: float = None) -> LipSyncData:
        """フォールバック解析"""
        print("⚠️ フォールバックモードでリップシンク解析")
        
        if actual_duration is None:
            actual_duration = self._estimate_duration_from_text(text)
        
        char_count = len(text)
        duration_per_char = actual_duration / max(char_count, 1)
        
        vowel_frames = []
        default_vowels = ['a', 'i', 'u', 'e', 'o']
        
        for i in range(min(char_count, 10)):
            vowel = default_vowels[i % len(default_vowels)]
            is_ending = i >= char_count - 1
            
            frame = VowelFrame(
                timestamp=i * duration_per_char,
                vowel=vowel,
                intensity=0.8 if is_ending else 0.7,
                duration=duration_per_char,
                is_ending=is_ending
            )
            vowel_frames.append(frame)
        
        return LipSyncData(
            text=text,
            total_duration=actual_duration,
            vowel_frames=vowel_frames
        )
    
    def generate_lipsync_keyframes(self, lipsync_data: LipSyncData, fps: int = 30) -> Dict[str, Any]:
        """Live2D用のキーフレームデータを生成"""
        try:
            if not lipsync_data or not lipsync_data.vowel_frames:
                return {}
            
            total_frames = int(lipsync_data.total_duration * fps)
            keyframes = {
                'total_duration': lipsync_data.total_duration,
                'fps': fps,
                'total_frames': total_frames,
                'vowel_keyframes': {},
                'mouth_params': {},
                'ending_protection_applied': self.ending_protection['enabled']
            }
            
            for vowel in ['a', 'i', 'u', 'e', 'o', 'n']:
                keyframes['vowel_keyframes'][vowel] = []
            
            keyframes['mouth_params'] = {
                'mouth_open': [],
                'mouth_form': []
            }
            
            mouth_scale = self.settings.get('mouth_open_scale', 100) / 100.0
            
            for frame_num in range(total_frames):
                current_time = frame_num / fps
                
                active_frame = self._find_active_vowel_frame(lipsync_data.vowel_frames, current_time)
                
                if active_frame:
                    vowel = active_frame.vowel
                    intensity = active_frame.intensity
                    
                    for v in keyframes['vowel_keyframes']:
                        value = intensity if v == vowel else 0.0
                        keyframes['vowel_keyframes'][v].append({
                            'frame': frame_num,
                            'value': value,
                            'is_ending': active_frame.is_ending
                        })
                    
                    if vowel in self.vowel_mapping:
                        mapping = self.vowel_mapping[vowel]
                        
                        base_mouth_open = mapping['mouth_open']
                        scaled_mouth_open = base_mouth_open * mouth_scale
                        mouth_open = (scaled_mouth_open / 100.0) * intensity
                        
                        mouth_form = (mapping['mouth_form'] / 100.0) * intensity
                    else:
                        mouth_open = 0.0
                        mouth_form = 0.0
                    
                    keyframes['mouth_params']['mouth_open'].append({
                        'frame': frame_num,
                        'value': mouth_open,
                        'is_ending': active_frame.is_ending
                    })
                    keyframes['mouth_params']['mouth_form'].append({
                        'frame': frame_num,
                        'value': mouth_form,
                        'is_ending': active_frame.is_ending
                    })
                else:
                    for v in keyframes['vowel_keyframes']:
                        keyframes['vowel_keyframes'][v].append({
                            'frame': frame_num,
                            'value': 0.0,
                            'is_ending': False
                        })
                    
                    keyframes['mouth_params']['mouth_open'].append({
                        'frame': frame_num,
                        'value': 0.0,
                        'is_ending': False
                    })
                    keyframes['mouth_params']['mouth_form'].append({
                        'frame': frame_num,
                        'value': 0.0,
                        'is_ending': False
                    })
            
            ending_frame_count = sum(1 for frames in keyframes['vowel_keyframes'].values() 
                                   for frame in frames if frame.get('is_ending', False))
            
            print(f"✅ キーフレーム生成完了: {total_frames}フレーム（語尾フレーム: {ending_frame_count}）")
            return keyframes
            
        except Exception as e:
            print(f"❌ キーフレーム生成エラー: {e}")
            traceback.print_exc()
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
            keyframes = self.generate_lipsync_keyframes(lipsync_data)
            
            export_data = {
                'metadata': {
                    'text': lipsync_data.text,
                    'total_duration': lipsync_data.total_duration,
                    'frame_count': len(lipsync_data.vowel_frames),
                    'generated_at': time.time(),
                    'engine_version': '2.3.0',
                    'ending_protection_enabled': self.ending_protection['enabled']
                },
                'settings': self.settings,
                'ending_protection': self.ending_protection,
                'vowel_mapping': self.vowel_mapping,
                'keyframes': keyframes,
                'raw_vowel_frames': [
                    {
                        'timestamp': frame.timestamp,
                        'vowel': frame.vowel,
                        'intensity': frame.intensity,
                        'duration': frame.duration,
                        'is_ending': frame.is_ending
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
        return copy.deepcopy(self.vowel_mapping)
    
    def get_settings(self) -> Dict[str, Any]:
        """現在のリップシンク設定を取得"""
        return copy.deepcopy(self.settings)
    
    def get_ending_protection_settings(self) -> Dict[str, Any]:
        """語尾保護設定を取得"""
        return copy.deepcopy(self.ending_protection)
    
    def reset_vowel_mapping(self):
        """母音マッピングをデフォルトにリセット"""
        self.vowel_mapping = copy.deepcopy(self.base_vowel_mapping)
        print("✅ 母音マッピングをリセットしました")
    
    def debug_analysis(self, text: str) -> Dict[str, Any]:
        """デバッグ用：解析結果の詳細情報"""
        debug_info = {
            'input_text': text,
            'pyopenjtalk_available': PYOPENJTALK_AVAILABLE,
            'engine_initialized': self.is_initialized,
            'settings': self.settings,
            'ending_protection': self.ending_protection,
            'vowel_mapping': self.vowel_mapping,
            'base_vowel_mapping': self.base_vowel_mapping
        }
        
        if PYOPENJTALK_AVAILABLE:
            try:
                g2p_result = pyopenjtalk.g2p(text, kana=False)
                debug_info['g2p_result'] = g2p_result
                
                lipsync_data = self.analyze_text_for_lipsync(text)
                if lipsync_data:
                    ending_count = sum(1 for f in lipsync_data.vowel_frames if f.is_ending)
                    debug_info['analysis_result'] = {
                        'total_duration': lipsync_data.total_duration,
                        'frame_count': len(lipsync_data.vowel_frames),
                        'ending_frame_count': ending_count,
                        'vowel_sequence': [f.vowel for f in lipsync_data.vowel_frames],
                        'ending_frames': [f.vowel for f in lipsync_data.vowel_frames if f.is_ending]
                    }
                
            except Exception as e:
                debug_info['error'] = str(e)
        
        return debug_info
    
    def _detect_silence_regions(self, audio_data: np.ndarray, sample_rate: int, 
                            min_silence_duration: float = 0.2,
                            adaptive_threshold: bool = True) -> List[Tuple[float, float]]:
        """WAVデータから無音区間を検出（適応的閾値）
        
        Args:
            audio_data: 音声データ（モノラル、float32）
            sample_rate: サンプルレート
            min_silence_duration: 無音として扱う最小時間（秒）
            adaptive_threshold: 適応的閾値を使用するか
            
        Returns:
            無音区間のリスト [(開始時間, 終了時間), ...]
        """
        try:
            print(f"🔇 無音区間検出開始: {len(audio_data)/sample_rate:.2f}秒の音声")
            
            # 音声データの前処理
            if audio_data.ndim > 1:
                # ステレオの場合はモノラルに変換
                audio_data = np.mean(audio_data, axis=1)
            
            # フレーム長（50ms = 0.05秒）
            frame_length = int(sample_rate * 0.05)
            hop_length = frame_length // 2  # 50%オーバーラップ
            
            # RMS（二乗平均平方根）を計算
            num_frames = (len(audio_data) - frame_length) // hop_length + 1
            rms_values = np.zeros(num_frames)
            
            for i in range(num_frames):
                start_idx = i * hop_length
                end_idx = start_idx + frame_length
                frame = audio_data[start_idx:end_idx]
                rms_values[i] = np.sqrt(np.mean(frame ** 2))
            
            # 🔥 適応的閾値の計算
            if adaptive_threshold:
                # 音量分布を解析
                non_zero_rms = rms_values[rms_values > 1e-6]  # ほぼ0の値は除外
                
                if len(non_zero_rms) > 0:
                    avg_rms = np.mean(non_zero_rms)
                    std_rms = np.std(non_zero_rms)
                    percentile_5 = np.percentile(non_zero_rms, 5)  # 下位5%
                    
                    # 閾値 = 平均の15% と 5パーセンタイル の大きい方
                    threshold = max(avg_rms * 0.15, percentile_5)
                    
                    print(f"  📊 音量統計: 平均={avg_rms:.6f}, 標準偏差={std_rms:.6f}")
                    print(f"  📊 下位5%={percentile_5:.6f}")
                    print(f"  🎯 適応的閾値={threshold:.6f}")
                else:
                    # フォールバック
                    threshold = 0.01
                    print(f"  ⚠️ 音量データ不足、固定閾値使用={threshold}")
            else:
                # 固定閾値
                threshold = self.settings.get('silence_threshold', 0.01)
                print(f"  🎯 固定閾値={threshold}")
            
            # 無音フレームを検出（閾値以下）
            is_silence = rms_values < threshold
            
            # フレームインデックスを時間に変換
            frame_times = np.arange(num_frames) * hop_length / sample_rate
            
            # 連続する無音区間をグループ化
            silence_regions = []
            in_silence = False
            silence_start = 0.0
            
            for i in range(len(is_silence)):
                if is_silence[i] and not in_silence:
                    # 無音開始
                    in_silence = True
                    silence_start = frame_times[i]
                elif not is_silence[i] and in_silence:
                    # 無音終了
                    in_silence = False
                    silence_end = frame_times[i]
                    duration = silence_end - silence_start
                    
                    # 最小時間以上の無音のみ記録
                    if duration >= min_silence_duration:
                        silence_regions.append((silence_start, silence_end))
                        print(f"    🔇 無音区間: {silence_start:.2f}s - {silence_end:.2f}s ({duration:.2f}s)")
            
            # 最後まで無音だった場合
            if in_silence:
                silence_end = frame_times[-1]
                duration = silence_end - silence_start
                if duration >= min_silence_duration:
                    silence_regions.append((silence_start, silence_end))
                    print(f"    🔇 無音区間: {silence_start:.2f}s - {silence_end:.2f}s ({duration:.2f}s)")
            
            print(f"✅ 無音区間検出完了: {len(silence_regions)}個の無音区間")
            
            return silence_regions
            
        except Exception as e:
            print(f"❌ 無音検出エラー: {e}")
            traceback.print_exc()
            return []


    def _apply_silence_regions_to_frames(self, vowel_frames: List[VowelFrame], 
                                        silence_regions: List[Tuple[float, float]]) -> List[VowelFrame]:
        """無音区間を母音フレームに適用
        
        Args:
            vowel_frames: 元の母音フレームリスト
            silence_regions: 無音区間のリスト [(開始, 終了), ...]
            
        Returns:
            無音区間が適用された母音フレームリスト
        """
        if not silence_regions:
            return vowel_frames
        
        print(f"🔇 無音区間適用開始: {len(vowel_frames)}フレーム, {len(silence_regions)}無音区間")
        
        corrected_frames = []
        correction_count = 0
        
        for frame in vowel_frames:
            frame_start = frame.timestamp
            frame_end = frame.timestamp + frame.duration
            frame_mid = (frame_start + frame_end) / 2
            
            # このフレームが無音区間内にあるかチェック
            is_in_silence = False
            for silence_start, silence_end in silence_regions:
                # フレームの中心が無音区間内にあるか
                if silence_start <= frame_mid <= silence_end:
                    is_in_silence = True
                    break
            
            if is_in_silence and frame.vowel != 'sil':
                # 無音区間内 → 強制的にsilに変換
                corrected_frame = VowelFrame(
                    timestamp=frame.timestamp,
                    vowel='sil',
                    intensity=0.0,
                    duration=frame.duration,
                    is_ending=False  # 無音なので語尾フラグも解除
                )
                correction_count += 1
                print(f"  🔇 修正: [{frame_start:.2f}s] {frame.vowel} → sil")
            else:
                # 無音区間外 → そのまま
                corrected_frame = frame
            
            corrected_frames.append(corrected_frame)
        
        print(f"✅ 無音区間適用完了: {correction_count}フレームを修正")
        
        return corrected_frames

    def analyze_long_wav_for_lipsync(self, wav_path: str, text: str = None,
                                    min_segment_gap: float = 1.0) -> Optional[LipSyncData]:
        """長時間WAV用のリップシンク生成（セグメント分割方式）
        
        Args:
            wav_path: WAVファイルパス
            text: テキスト（Noneの場合はWhisperで自動文字起こし）
            min_segment_gap: セグメント分割の最小無音時間（秒）
            
        Returns:
            LipSyncData: 結合されたリップシンクデータ
        """
        try:
            import soundfile as sf
            from pathlib import Path
            
            print(f"🎬 長時間WAV解析開始: {Path(wav_path).name}")
            
            # WAVファイル読み込み
            audio_data, sample_rate = sf.read(wav_path, dtype='float32')
            total_duration = len(audio_data) / sample_rate
            print(f"📊 総時間: {total_duration:.2f}秒 ({total_duration/60:.1f}分)")
            
            # ステレオ→モノラル変換
            if audio_data.ndim > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            # ステップ1: Whisperで文字起こし + セグメント取得
            segments = self._get_whisper_segments(wav_path, text)
            if not segments:
                print("⚠️ Whisperセグメント取得失敗、フォールバック処理")
                return self._fallback_long_wav_analysis(audio_data, sample_rate, text)
            
            print(f"✅ Whisperセグメント取得: {len(segments)}個")
            
            # ステップ2: 無音区間でセグメントをグループ化
            segment_groups = self._group_segments_by_silence(segments, min_segment_gap)
            print(f"🔗 セグメントグループ化: {len(segment_groups)}グループ")
            
            # ステップ3: 各グループごとにリップシンク生成
            all_vowel_frames = []
            
            for group_idx, group in enumerate(segment_groups):
                group_start = group['start']
                group_end = group['end']
                group_text = group['text']
                group_duration = group_end - group_start
                
                print(f"\n--- グループ {group_idx + 1}/{len(segment_groups)} ---")
                print(f"⏱️  時間: {group_start:.2f}s - {group_end:.2f}s ({group_duration:.2f}s)")
                print(f"📝 テキスト: {group_text[:50]}...")
                
                # WAVデータを切り出し
                start_sample = int(group_start * sample_rate)
                end_sample = int(group_end * sample_rate)
                audio_segment = audio_data[start_sample:end_sample]
                
                # このセグメントのリップシンク生成
                segment_lipsync = self.analyze_text_for_lipsync(
                    text=group_text,
                    audio_data=audio_segment,
                    sample_rate=sample_rate
                )
                
                if segment_lipsync and segment_lipsync.vowel_frames:
                    # タイムスタンプをグローバル時間に変換
                    for frame in segment_lipsync.vowel_frames:
                        adjusted_frame = VowelFrame(
                            timestamp=frame.timestamp + group_start,  # グローバル時間に変換
                            vowel=frame.vowel,
                            intensity=frame.intensity,
                            duration=frame.duration,
                            is_ending=frame.is_ending
                        )
                        all_vowel_frames.append(adjusted_frame)
                    
                    print(f"✅ {len(segment_lipsync.vowel_frames)}フレーム生成")
                else:
                    print(f"⚠️ リップシンク生成失敗、スキップ")
            
            # ステップ4: 全体を結合
            if not all_vowel_frames:
                print("❌ 有効なフレームが1つもありません")
                return None
            
            # グループ間の無音を追加
            all_vowel_frames = self._fill_gaps_with_silence(all_vowel_frames, total_duration)
            
            # 最終的なLipSyncDataを生成
            combined_lipsync = LipSyncData(
                text=text if text else " ".join([g['text'] for g in segment_groups]),
                total_duration=total_duration,
                vowel_frames=all_vowel_frames
            )
            
            print(f"\n✅ 長時間リップシンク生成完了")
            print(f"   総フレーム数: {len(all_vowel_frames)}")
            print(f"   総時間: {total_duration:.2f}秒")
            print(f"   セグメント数: {len(segment_groups)}")
            
            silence_count = sum(1 for f in all_vowel_frames if f.vowel == 'sil')
            print(f"   無音フレーム: {silence_count}個 ({silence_count/len(all_vowel_frames)*100:.1f}%)")
            
            return combined_lipsync
            
        except Exception as e:
            print(f"❌ 長時間WAV解析エラー: {e}")
            traceback.print_exc()
            return None


    def _get_whisper_segments(self, wav_path: str, provided_text: str = None) -> List[Dict]:
        """Whisperでセグメント情報を取得
        
        Args:
            wav_path: WAVファイルパス
            provided_text: 提供されたテキスト（Noneの場合は自動文字起こし）
            
        Returns:
            セグメントリスト [{'start': float, 'end': float, 'text': str}, ...]
        """
        try:
            # WhisperTranscriberを使用
            if not self.phoneme_analyzer:
                print("⚠️ WhisperTranscriber利用不可")
                return []
            
            # whisper_transcriberがあるか確認
            if not hasattr(self, 'whisper_transcriber'):
                from .whisper_transcriber import WhisperTranscriber
                self.whisper_transcriber = WhisperTranscriber(model_size="medium", device="cuda")
            
            # 文字起こし実行
            success, transcribed_text, segments = self.whisper_transcriber.transcribe_wav(
                wav_path,
                language="ja"
            )
            
            if not success or not segments:
                print("⚠️ Whisper文字起こし失敗")
                return []
            
            print(f"📝 Whisper文字起こし結果: {len(transcribed_text)}文字")
            
            return segments
            
        except Exception as e:
            print(f"❌ Whisperセグメント取得エラー: {e}")
            traceback.print_exc()
            return []


    def _group_segments_by_silence(self, segments: List[Dict], 
                                min_gap: float) -> List[Dict]:
        """セグメントを無音区間でグループ化
        
        Args:
            segments: Whisperセグメントリスト
            min_gap: グループ分割の最小無音時間（秒）
            
        Returns:
            グループリスト [{'start': float, 'end': float, 'text': str, 'segments': [...]}, ...]
        """
        if not segments:
            return []
        
        groups = []
        current_group = {
            'start': segments[0]['start'],
            'end': segments[0]['end'],
            'text': segments[0]['text'],
            'segments': [segments[0]]
        }
        
        for i in range(1, len(segments)):
            prev_segment = segments[i - 1]
            curr_segment = segments[i]
            
            # 前のセグメントとの間隔
            gap = curr_segment['start'] - prev_segment['end']
            
            if gap >= min_gap:
                # 無音が長い → 新しいグループを開始
                groups.append(current_group)
                
                current_group = {
                    'start': curr_segment['start'],
                    'end': curr_segment['end'],
                    'text': curr_segment['text'],
                    'segments': [curr_segment]
                }
                
                print(f"  🔗 グループ分割: {gap:.2f}秒の無音を検出")
            else:
                # 同じグループに追加
                current_group['end'] = curr_segment['end']
                current_group['text'] += curr_segment['text']
                current_group['segments'].append(curr_segment)
        
        # 最後のグループを追加
        groups.append(current_group)
        
        return groups


    def _fill_gaps_with_silence(self, vowel_frames: List[VowelFrame], 
                                total_duration: float) -> List[VowelFrame]:
        """フレーム間のギャップを無音で埋める
        
        Args:
            vowel_frames: 元の母音フレームリスト（時系列順）
            total_duration: 総時間
            
        Returns:
            ギャップが埋められた母音フレームリスト
        """
        if not vowel_frames:
            return []
        
        filled_frames = []
        
        # 最初のフレームの前に無音がある場合
        if vowel_frames[0].timestamp > 0.1:
            silence_frame = VowelFrame(
                timestamp=0.0,
                vowel='sil',
                intensity=0.0,
                duration=vowel_frames[0].timestamp,
                is_ending=False
            )
            filled_frames.append(silence_frame)
            print(f"  🔇 先頭無音追加: 0.0s - {vowel_frames[0].timestamp:.2f}s")
        
        # フレーム間のギャップをチェック
        for i in range(len(vowel_frames)):
            filled_frames.append(vowel_frames[i])
            
            # 次のフレームとのギャップ
            if i < len(vowel_frames) - 1:
                current_end = vowel_frames[i].timestamp + vowel_frames[i].duration
                next_start = vowel_frames[i + 1].timestamp
                gap = next_start - current_end
                
                # 0.1秒以上のギャップがある場合、無音で埋める
                if gap > 0.1:
                    silence_frame = VowelFrame(
                        timestamp=current_end,
                        vowel='sil',
                        intensity=0.0,
                        duration=gap,
                        is_ending=False
                    )
                    filled_frames.append(silence_frame)
                    print(f"  🔇 無音追加: {current_end:.2f}s - {next_start:.2f}s ({gap:.2f}s)")
        
        # 最後のフレームの後に無音がある場合
        last_frame = vowel_frames[-1]
        last_end = last_frame.timestamp + last_frame.duration
        if last_end < total_duration - 0.1:
            silence_frame = VowelFrame(
                timestamp=last_end,
                vowel='sil',
                intensity=0.0,
                duration=total_duration - last_end,
                is_ending=False
            )
            filled_frames.append(silence_frame)
            print(f"  🔇 末尾無音追加: {last_end:.2f}s - {total_duration:.2f}s")
        
        return filled_frames


    def _fallback_long_wav_analysis(self, audio_data: np.ndarray, sample_rate: int,
                                    text: str = None) -> Optional[LipSyncData]:
        """Whisper失敗時のフォールバック処理
        
        Args:
            audio_data: 音声データ
            sample_rate: サンプルレート
            text: テキスト
            
        Returns:
            LipSyncData
        """
        print("⚠️ フォールバックモード: 単純分割処理")
        
        if text is None:
            text = "音声解析"
        
        # 全体を一度に処理（既存の方法）
        return self.analyze_text_for_lipsync(text, audio_data, sample_rate)