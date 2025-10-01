import re
import json
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import traceback

try:
    import pyopenjtalk
    PYOPENJTALK_AVAILABLE = True
except ImportError:
    PYOPENJTALK_AVAILABLE = False
    print("⚠️ pyopenjtalk が利用できません。")

@dataclass
class PhonemeInfo:
    """音素情報データクラス"""
    phoneme: str        # 音素記号
    start_time: float   # 開始時間（秒）
    duration: float     # 持続時間（秒）
    vowel: str         # 対応する母音
    intensity: float   # 強度 (0.0-1.0)
    mora_position: int # モーラ内位置
    word_position: int # 単語内位置
    is_ending: bool = False  # 語尾音素フラグ

class PhonemeAnalyzer:
    """音素解析エンジン
    
    pyopenjtalkを使用してテキストを音素に分解し、
    Live2Dリップシンク用のデータに変換する（語尾保護機能付き）
    """
    
    def __init__(self):
        self.is_available = PYOPENJTALK_AVAILABLE
        
        # 語尾保護設定
        self.ending_protection_enabled = True
        self.min_ending_duration = 0.25  # 語尾音素の最小持続時間（秒）
        self.ending_intensity_boost = 1.2  # 語尾音素の強度ブースト
        
        # 日本語音素→母音マッピングテーブル
        self.phoneme_to_vowel_map = {
            # 母音
            'a': 'a', 'i': 'i', 'u': 'u', 'e': 'e', 'o': 'o',
            
            # 子音+母音（あ行）
            'ka': 'a', 'ga': 'a', 'sa': 'a', 'za': 'a', 'ta': 'a', 'da': 'a',
            'na': 'a', 'ha': 'a', 'ba': 'a', 'pa': 'a', 'ma': 'a', 'ya': 'a',
            'ra': 'a', 'wa': 'a',
            
            # 子音+母音（い行）
            'ki': 'i', 'gi': 'i', 'si': 'i', 'zi': 'i', 'ti': 'i', 'di': 'i',
            'ni': 'i', 'hi': 'i', 'bi': 'i', 'pi': 'i', 'mi': 'i', 'ri': 'i',
            'ji': 'i', 'chi': 'i',
            
            # 子音+母音（う行）
            'ku': 'u', 'gu': 'u', 'su': 'u', 'zu': 'u', 'tu': 'u', 'du': 'u',
            'nu': 'u', 'hu': 'u', 'bu': 'u', 'pu': 'u', 'mu': 'u', 'yu': 'u',
            'ru': 'u', 'tsu': 'u',
            
            # 子音+母音（え行）
            'ke': 'e', 'ge': 'e', 'se': 'e', 'ze': 'e', 'te': 'e', 'de': 'e',
            'ne': 'e', 'he': 'e', 'be': 'e', 'pe': 'e', 'me': 'e', 're': 'e',
            
            # 子音+母音（お行）
            'ko': 'o', 'go': 'o', 'so': 'o', 'zo': 'o', 'to': 'o', 'do': 'o',
            'no': 'o', 'ho': 'o', 'bo': 'o', 'po': 'o', 'mo': 'o', 'yo': 'o',
            'ro': 'o',
            
            # 特殊音素
            'N': 'n',           # ん
            'Q': 'sil',         # っ（無音）
            'pau': 'sil',       # ポーズ
            'sil': 'sil',       # 無音
            'sp': 'sil',        # ショートポーズ
            
            # 長音・拗音
            'ー': 'a',  # 長音記号（前の母音を継続）
            'kya': 'a', 'gya': 'a', 'sha': 'a', 'ja': 'a', 'cha': 'a',
            'nya': 'a', 'hya': 'a', 'bya': 'a', 'pya': 'a', 'mya': 'a', 'rya': 'a',
            'kyu': 'u', 'gyu': 'u', 'shu': 'u', 'ju': 'u', 'chu': 'u',
            'nyu': 'u', 'hyu': 'u', 'byu': 'u', 'pyu': 'u', 'myu': 'u', 'ryu': 'u',
            'kyo': 'o', 'gyo': 'o', 'sho': 'o', 'jo': 'o', 'cho': 'o',
            'nyo': 'o', 'hyo': 'o', 'byo': 'o', 'pyo': 'o', 'myo': 'o', 'ryo': 'o',
        }
        
        # 音素持続時間テーブル（語尾保護調整済み）
        self.phoneme_duration_map = {
            # 母音（語尾で重要）
            'a': 0.20, 'i': 0.18, 'u': 0.19, 'e': 0.19, 'o': 0.21,
            
            # 子音（語尾でよく使われるものを長めに）
            'k': 0.08, 'g': 0.09, 's': 0.18, 'z': 0.12, 't': 0.09, 'd': 0.10,
            'n': 0.15, 'h': 0.16, 'b': 0.10, 'p': 0.09, 'm': 0.12, 'r': 0.08,
            'w': 0.10, 'y': 0.08, 'j': 0.11, 'c': 0.10, 'f': 0.12, 'v': 0.11,
            
            # 特殊音素
            'N': 0.15,      # ん（語尾でよく使われる）
            'Q': 0.08,      # っ
            'pau': 0.20,    # ポーズ
            'sil': 0.05,    # 無音
            'sp': 0.03,     # ショートポーズ
        }
        
        print(f"✅ PhonemeAnalyzer初期化完了 (pyopenjtalk: {'有効' if self.is_available else '無効'})")
        print(f"🛡️ 語尾保護機能: {'有効' if self.ending_protection_enabled else '無効'}")
    
    def analyze_text(self, text: str) -> List[PhonemeInfo]:
        """テキストを音素解析してPhonemeInfoリストを返す
        
        Args:
            text: 解析対象のテキスト
            
        Returns:
            List[PhonemeInfo]: 音素情報のリスト（語尾保護機能付き）
        """
        if not self.is_available:
            return self._fallback_analysis(text)
        
        try:
            print(f"🔍 音素解析開始: '{text}'")
            
            # Method 1: run_frontendを使った詳細解析
            phoneme_info = self._detailed_analysis(text)
            if phoneme_info:
                print(f"✅ 詳細解析成功: {len(phoneme_info)}個の音素")
                # 語尾保護処理を適用
                phoneme_info = self._apply_ending_protection(phoneme_info)
                return phoneme_info
            
            # Method 2: g2pを使ったシンプル解析
            phoneme_info = self._simple_analysis(text)
            if phoneme_info:
                print(f"✅ シンプル解析成功: {len(phoneme_info)}個の音素")
                # 語尾保護処理を適用
                phoneme_info = self._apply_ending_protection(phoneme_info)
                return phoneme_info
            
            # Method 3: フォールバック解析
            print("⚠️ フォールバック解析を実行")
            fallback_result = self._fallback_analysis(text)
            return self._apply_ending_protection(fallback_result)
            
        except Exception as e:
            print(f"❌ 音素解析エラー: {e}")
            print(traceback.format_exc())
            fallback_result = self._fallback_analysis(text)
            return self._apply_ending_protection(fallback_result)
    
    def _is_ending_phoneme(self, phoneme_list: List[str], current_index: int) -> bool:
        """語尾音素かどうかを判定
        
        Args:
            phoneme_list: 音素リスト
            current_index: 現在の音素インデックス
            
        Returns:
            bool: 語尾音素の場合True
        """
        if current_index >= len(phoneme_list) - 1:
            return True
        
        # 後続が無音系のみの場合も語尾として扱う
        remaining = phoneme_list[current_index + 1:]
        if all(p in ['pau', 'sil', 'sp'] for p in remaining if p):
            return True
        
        # 語尾から3音素以内は語尾として扱う
        distance_from_end = len(phoneme_list) - current_index - 1
        if distance_from_end <= 2:
            # ただし無音系は除外
            current_phoneme = phoneme_list[current_index]
            if current_phoneme not in ['pau', 'sil', 'sp']:
                return True
        
        return False
    
    def _apply_ending_protection(self, phoneme_info_list: List[PhonemeInfo]) -> List[PhonemeInfo]:
        """語尾保護機能を適用
        
        Args:
            phoneme_info_list: 元の音素情報リスト
            
        Returns:
            List[PhonemeInfo]: 語尾保護が適用された音素情報リスト
        """
        if not self.ending_protection_enabled or not phoneme_info_list:
            return phoneme_info_list
        
        # 音素リストを作成
        phoneme_list = [info.phoneme for info in phoneme_info_list]
        
        protected_list = []
        total_time_adjustment = 0.0
        
        for i, info in enumerate(phoneme_info_list):
            is_ending = self._is_ending_phoneme(phoneme_list, i)
            
            # 語尾音素の場合は保護機能を適用
            if is_ending and info.vowel != 'sil':
                # 持続時間を最小値以上に調整
                original_duration = info.duration
                protected_duration = max(info.duration, self.min_ending_duration)
                
                # 強度をブースト
                protected_intensity = min(1.0, info.intensity * self.ending_intensity_boost)
                
                if protected_duration > original_duration:
                    adjustment = protected_duration - original_duration
                    total_time_adjustment += adjustment
                    print(f"🛡️ 語尾保護適用: {info.phoneme} "
                          f"({original_duration:.2f}s → {protected_duration:.2f}s, "
                          f"強度: {info.intensity:.2f} → {protected_intensity:.2f})")
                
                # 保護された音素情報を作成
                protected_info = PhonemeInfo(
                    phoneme=info.phoneme,
                    start_time=info.start_time + total_time_adjustment - adjustment,
                    duration=protected_duration,
                    vowel=info.vowel,
                    intensity=protected_intensity,
                    mora_position=info.mora_position,
                    word_position=info.word_position,
                    is_ending=True
                )
            else:
                # 通常音素はタイミング調整のみ
                protected_info = PhonemeInfo(
                    phoneme=info.phoneme,
                    start_time=info.start_time + total_time_adjustment,
                    duration=info.duration,
                    vowel=info.vowel,
                    intensity=info.intensity,
                    mora_position=info.mora_position,
                    word_position=info.word_position,
                    is_ending=False
                )
            
            protected_list.append(protected_info)
        
        if total_time_adjustment > 0:
            print(f"🛡️ 語尾保護による総時間延長: +{total_time_adjustment:.2f}秒")
        
        return protected_list
    
    def _detailed_analysis(self, text: str) -> Optional[List[PhonemeInfo]]:
        """run_frontendを使った詳細音素解析"""
        try:
            # フロントエンド解析実行
            features = pyopenjtalk.run_frontend(text)
            
            if not features:
                return None
            
            phoneme_list = []
            current_time = 0.0
            mora_position = 0
            word_position = 0
            
            for feature_idx, feature in enumerate(features):
                # フィーチャーデータの解析
                phoneme_data = self._extract_phoneme_from_feature(feature, feature_idx)
                
                if phoneme_data:
                    phoneme = phoneme_data['phoneme']
                    
                    # 持続時間計算（語尾判定は後で適用）
                    duration = self._estimate_phoneme_duration(phoneme, len(text))
                    
                    # 対応する母音を特定
                    vowel = self._map_phoneme_to_vowel(phoneme)
                    
                    # 強度計算
                    intensity = self._calculate_phoneme_intensity(phoneme, vowel)
                    
                    phoneme_info = PhonemeInfo(
                        phoneme=phoneme,
                        start_time=current_time,
                        duration=duration,
                        vowel=vowel,
                        intensity=intensity,
                        mora_position=mora_position,
                        word_position=word_position
                    )
                    
                    phoneme_list.append(phoneme_info)
                    current_time += duration
                    
                    # 位置カウンタ更新
                    if phoneme in ['pau', 'sp']:
                        word_position += 1
                        mora_position = 0
                    else:
                        mora_position += 1
            
            return phoneme_list if phoneme_list else None
            
        except Exception as e:
            print(f"⚠️ 詳細解析失敗: {e}")
            return None
    
    def _extract_phoneme_from_feature(self, feature, index: int) -> Optional[Dict[str, str]]:
        """フィーチャーデータから音素情報を抽出"""
        try:
            # フィーチャーがdict形式の場合
            if isinstance(feature, dict):
                phoneme = feature.get('phoneme', '')
                if phoneme:
                    return {'phoneme': phoneme}
            
            # フィーチャーがオブジェクト形式の場合
            if hasattr(feature, 'phoneme'):
                phoneme = getattr(feature, 'phoneme', '')
                if phoneme:
                    return {'phoneme': phoneme}
            
            # フィーチャーが文字列の場合
            if isinstance(feature, str) and feature.strip():
                return {'phoneme': feature.strip()}
            
            # フィーチャーがリスト形式の場合
            if isinstance(feature, (list, tuple)) and len(feature) > 0:
                phoneme = str(feature[0]) if feature[0] else ''
                if phoneme:
                    return {'phoneme': phoneme}
            
            return None
            
        except Exception as e:
            print(f"⚠️ フィーチャー解析エラー (index {index}): {e}")
            return None
    
    def _simple_analysis(self, text: str) -> Optional[List[PhonemeInfo]]:
        """g2pを使ったシンプル音素解析"""
        try:
            # g2pで音素列取得
            phoneme_sequence = pyopenjtalk.g2p(text, kana=False)
            
            if not phoneme_sequence or phoneme_sequence.strip() == '':
                return None
            
            # 音素を分割
            phonemes = phoneme_sequence.strip().split()
            
            if not phonemes:
                return None
            
            phoneme_list = []
            current_time = 0.0
            
            for i, phoneme in enumerate(phonemes):
                if not phoneme:
                    continue
                
                # 持続時間計算（語尾判定は後で適用）
                duration = self._estimate_phoneme_duration(phoneme, len(text))
                
                # 対応する母音を特定
                vowel = self._map_phoneme_to_vowel(phoneme)
                
                # 強度計算
                intensity = self._calculate_phoneme_intensity(phoneme, vowel)
                
                phoneme_info = PhonemeInfo(
                    phoneme=phoneme,
                    start_time=current_time,
                    duration=duration,
                    vowel=vowel,
                    intensity=intensity,
                    mora_position=i,
                    word_position=0
                )
                
                phoneme_list.append(phoneme_info)
                current_time += duration
            
            return phoneme_list
            
        except Exception as e:
            print(f"⚠️ シンプル解析失敗: {e}")
            return None
    
    def _fallback_analysis(self, text: str) -> List[PhonemeInfo]:
        """フォールバック音素解析（pyopenjtalk使用不可時）"""
        print("⚠️ フォールバックモードで音素解析実行")
        
        # 簡易的な文字→音素推定
        phoneme_list = []
        current_time = 0.0
        
        # ひらがな・カタカナの基本パターン
        kana_to_vowel = {
            'あ': 'a', 'い': 'i', 'う': 'u', 'え': 'e', 'お': 'o',
            'か': 'a', 'き': 'i', 'く': 'u', 'け': 'e', 'こ': 'o',
            'が': 'a', 'ぎ': 'i', 'ぐ': 'u', 'げ': 'e', 'ご': 'o',
            'さ': 'a', 'し': 'i', 'す': 'u', 'せ': 'e', 'そ': 'o',
            'ざ': 'a', 'じ': 'i', 'ず': 'u', 'ぜ': 'e', 'ぞ': 'o',
            'た': 'a', 'ち': 'i', 'つ': 'u', 'て': 'e', 'と': 'o',
            'だ': 'a', 'ぢ': 'i', 'づ': 'u', 'で': 'e', 'ど': 'o',
            'な': 'a', 'に': 'i', 'ぬ': 'u', 'ね': 'e', 'の': 'o',
            'は': 'a', 'ひ': 'i', 'ふ': 'u', 'へ': 'e', 'ほ': 'o',
            'ば': 'a', 'び': 'i', 'ぶ': 'u', 'べ': 'e', 'ぼ': 'o',
            'ぱ': 'a', 'ぴ': 'i', 'ぷ': 'u', 'ぺ': 'e', 'ぽ': 'o',
            'ま': 'a', 'み': 'i', 'む': 'u', 'め': 'e', 'も': 'o',
            'や': 'a', 'ゆ': 'u', 'よ': 'o',
            'ら': 'a', 'り': 'i', 'る': 'u', 'れ': 'e', 'ろ': 'o',
            'わ': 'a', 'ゐ': 'i', 'ゑ': 'e', 'を': 'o', 'ん': 'n',
            'ー': 'a'  # 長音（前の母音を継続）
        }
        
        for i, char in enumerate(text):
            if char in kana_to_vowel:
                vowel = kana_to_vowel[char]
                duration = 0.2  # デフォルト持続時間
                
                phoneme_info = PhonemeInfo(
                    phoneme=char,
                    start_time=current_time,
                    duration=duration,
                    vowel=vowel,
                    intensity=0.7,
                    mora_position=i,
                    word_position=0
                )
                
                phoneme_list.append(phoneme_info)
                current_time += duration
            
            elif char in '。、！？．，!?':
                # 句読点は無音として扱う
                phoneme_info = PhonemeInfo(
                    phoneme='pau',
                    start_time=current_time,
                    duration=0.3,
                    vowel='sil',
                    intensity=0.0,
                    mora_position=i,
                    word_position=0
                )
                
                phoneme_list.append(phoneme_info)
                current_time += 0.3
        
        # 最低限のデータを保証
        if not phoneme_list:
            default_vowels = ['a', 'i', 'u', 'e', 'o']
            for j, vowel in enumerate(default_vowels):
                phoneme_info = PhonemeInfo(
                    phoneme=vowel,
                    start_time=j * 0.2,
                    duration=0.2,
                    vowel=vowel,
                    intensity=0.5,
                    mora_position=j,
                    word_position=0
                )
                phoneme_list.append(phoneme_info)
        
        return phoneme_list
    
    def _estimate_phoneme_duration(self, phoneme: str, text_length: int) -> float:
        """音素の持続時間を推定"""
        # 基本持続時間
        base_duration = self.phoneme_duration_map.get(phoneme, 0.15)
        
        # テキスト長による補正
        length_factor = max(0.8, min(1.2, 10 / max(text_length, 1)))
        
        return base_duration * length_factor
    
    def _map_phoneme_to_vowel(self, phoneme: str) -> str:
        """音素を母音にマッピング"""
        # 直接マッピング
        if phoneme in self.phoneme_to_vowel_map:
            return self.phoneme_to_vowel_map[phoneme]
        
        # パターンマッチング
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
        
        # 子音のみの場合は無音
        return 'sil'
    
    def _calculate_phoneme_intensity(self, phoneme: str, vowel: str) -> float:
        """音素の強度を計算"""
        # 母音の強度
        vowel_intensity = {
            'a': 0.9,   # あ：開口母音、最大
            'e': 0.8,   # え：半開母音
            'o': 0.85,  # お：半開母音
            'i': 0.7,   # い：閉口母音
            'u': 0.65,  # う：閉口母音
            'n': 0.4,   # ん：鼻音
            'sil': 0.0  # 無音
        }
        
        base_intensity = vowel_intensity.get(vowel, 0.5)
        
        # 音素の種類による補正
        if phoneme in ['pau', 'sil', 'sp']:
            return 0.0
        elif phoneme == 'N':  # ん
            return 0.4
        elif phoneme == 'Q':  # っ
            return 0.1
        elif len(phoneme) > 1:  # 複合音素は少し弱める
            return base_intensity * 0.9
        
        return base_intensity
    
    def optimize_for_tts(self, phoneme_info_list: List[PhonemeInfo], 
                        audio_duration: float = None) -> List[PhonemeInfo]:
        """TTS音声の長さに合わせて音素タイミングを最適化
        
        Args:
            phoneme_info_list: 音素情報リスト
            audio_duration: 実際の音声長さ（秒）
            
        Returns:
            List[PhonemeInfo]: 最適化された音素情報リスト
        """
        if not phoneme_info_list:
            return phoneme_info_list
        
        try:
            # 総推定時間を計算
            estimated_duration = sum(p.duration for p in phoneme_info_list)
            
            if audio_duration and audio_duration > 0:
                # 実際の音声長さに合わせてスケール調整
                time_scale = audio_duration / estimated_duration
                print(f"🔧 タイミング最適化: {estimated_duration:.2f}秒 → {audio_duration:.2f}秒 (x{time_scale:.2f})")
                
                optimized_list = []
                current_time = 0.0
                
                for phoneme_info in phoneme_info_list:
                    # スケール適用（ただし語尾音素は最小時間を保証）
                    new_duration = phoneme_info.duration * time_scale
                    
                    # 語尾音素の場合は最小時間を保証
                    if phoneme_info.is_ending and self.ending_protection_enabled:
                        new_duration = max(new_duration, self.min_ending_duration * 0.8)  # 少し緩める
                    
                    optimized_phoneme = PhonemeInfo(
                        phoneme=phoneme_info.phoneme,
                        start_time=current_time,
                        duration=new_duration,
                        vowel=phoneme_info.vowel,
                        intensity=phoneme_info.intensity,
                        mora_position=phoneme_info.mora_position,
                        word_position=phoneme_info.word_position,
                        is_ending=phoneme_info.is_ending
                    )
                    
                    optimized_list.append(optimized_phoneme)
                    current_time += new_duration
                
                return optimized_list
            else:
                # 音声長さが不明な場合はそのまま返す
                return phoneme_info_list
                
        except Exception as e:
            print(f"⚠️ 最適化エラー: {e}")
            return phoneme_info_list
    
    def extract_vowel_sequence(self, phoneme_info_list: List[PhonemeInfo]) -> List[str]:
        """音素情報から母音シーケンスを抽出"""
        return [info.vowel for info in phoneme_info_list if info.vowel != 'sil']
    
    def get_analysis_stats(self, phoneme_info_list: List[PhonemeInfo]) -> Dict[str, Any]:
        """解析統計情報を取得"""
        if not phoneme_info_list:
            return {}
        
        # 母音の統計
        vowel_count = {}
        total_duration = 0.0
        ending_count = 0
        
        for info in phoneme_info_list:
            vowel = info.vowel
            duration = info.duration
            
            if vowel not in vowel_count:
                vowel_count[vowel] = {'count': 0, 'total_duration': 0.0}
            
            vowel_count[vowel]['count'] += 1
            vowel_count[vowel]['total_duration'] += duration
            total_duration += duration
            
            if info.is_ending:
                ending_count += 1
        
        stats = {
            'total_phonemes': len(phoneme_info_list),
            'total_duration': total_duration,
            'vowel_distribution': vowel_count,
            'average_phoneme_duration': total_duration / len(phoneme_info_list),
            'vowel_sequence': self.extract_vowel_sequence(phoneme_info_list),
            'unique_vowels': list(vowel_count.keys()),
            'ending_phonemes_count': ending_count,
            'ending_protection_applied': self.ending_protection_enabled
        }
        
        return stats
    
    def debug_phoneme_info(self, phoneme_info_list: List[PhonemeInfo]) -> str:
        """デバッグ用：音素情報の詳細表示"""
        if not phoneme_info_list:
            return "音素情報なし"
        
        debug_lines = [
            "=== 音素解析デバッグ情報（語尾保護機能付き） ===",
            f"総音素数: {len(phoneme_info_list)}",
            f"総時間: {sum(p.duration for p in phoneme_info_list):.2f}秒",
            f"語尾音素数: {sum(1 for p in phoneme_info_list if p.is_ending)}",
            "",
            "音素詳細:"
        ]
        
        for i, info in enumerate(phoneme_info_list):
            ending_mark = " 🛡️" if info.is_ending else ""
            line = (
                f"  {i:2d}: {info.phoneme:>4s} → {info.vowel} "
                f"({info.start_time:.2f}s-{info.start_time + info.duration:.2f}s, "
                f"強度:{info.intensity:.2f}){ending_mark}"
            )
            debug_lines.append(line)
        
        debug_lines.extend([
            "",
            f"母音シーケンス: {' '.join(self.extract_vowel_sequence(phoneme_info_list))}",
            f"語尾保護機能: {'有効' if self.ending_protection_enabled else '無効'}",
            "==============================================="
        ])
        
        return "\n".join(debug_lines)
    
    def set_ending_protection(self, enabled: bool, min_duration: float = 0.25, 
                             intensity_boost: float = 1.2):
        """語尾保護機能の設定を変更
        
        Args:
            enabled: 有効/無効
            min_duration: 語尾音素の最小持続時間（秒）
            intensity_boost: 語尾音素の強度ブースト倍率
        """
        self.ending_protection_enabled = enabled
        self.min_ending_duration = min_duration
        self.ending_intensity_boost = intensity_boost
        
        print(f"🛡️ 語尾保護設定更新: "
              f"有効={enabled}, 最小時間={min_duration}s, 強度ブースト={intensity_boost}x")