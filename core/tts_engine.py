import torch
import numpy as np
from pathlib import Path
import traceback
import inspect
import logging
import json

# Style-Bert-VITS2のログを無効化
logging.getLogger("style_bert_vits2").setLevel(logging.ERROR)
logging.getLogger("bert_models").setLevel(logging.ERROR)  
logging.getLogger("tts_model").setLevel(logging.ERROR)
logging.getLogger("infer").setLevel(logging.ERROR)

# 他の一般的なログも必要に応じて無効化
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)

class TTSEngine:
    def __init__(self):
        self.model = None
        self.is_loaded = False
        self.model_info = {}
        
        # デフォルトパラメータ
        self.default_params = {
            'style': 'Neutral',
            'style_weight': 1.0,
            'sdp_ratio': 0.25,
            'noise': 0.35,
            'length_scale': 0.85
        }
        
        # 感情名マッピング（大文字・小文字やamitaro/jvnvの違いに対応）
        self.emotion_mapping = {
            # 小文字 -> 大文字（JVNV用）
            'fear': 'Fear',
            'angry': 'Angry', 
            'disgust': 'Disgust',
            'happiness': 'Happy',
            'happy': 'Happy',
            'sadness': 'Sad',
            'sad': 'Sad',
            'surprise': 'Surprise',
            'neutral': 'Neutral',
            
            # 大文字もそのまま通す
            'Fear': 'Fear',
            'Angry': 'Angry',
            'Disgust': 'Disgust', 
            'Happy': 'Happy',
            'Sad': 'Sad',
            'Surprise': 'Surprise',
            'Neutral': 'Neutral',
        }
        
    def load_model(self, model_path, config_path, style_path):
        """モデルを読み込む（感情マッピング対応版）"""
        try:
            # ログ出力を完全に抑制
            import sys
            import os
            from io import StringIO
            
            # stdout/stderrを一時的にリダイレクト
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            
            try:
                # BERTモデルの読み込み
                from style_bert_vits2.nlp import bert_models
                from style_bert_vits2.constants import Languages
                from style_bert_vits2.tts_model import TTSModel
                
                bert_models.load_model(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")
                bert_models.load_tokenizer(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")
                
                # TTSモデル読み込み
                device = "cuda" if torch.cuda.is_available() else "cpu"
                
                self.model = TTSModel(
                    model_path=model_path,
                    config_path=config_path,
                    style_vec_path=style_path,
                    device=device,
                )
                
            finally:
                # stdout/stderrを復元
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            # モデル情報を保存
            self.model_info = {
                'model_path': model_path,
                'config_path': config_path,
                'style_path': style_path,
                'device': device
            }
            
            self.is_loaded = True
            
            # 利用可能な感情を取得してマッピングを更新
            self._update_emotion_mapping()
            
            print(f"✅ モデル読み込み完了: {Path(model_path).parent.name}")
            print(f"📱 利用可能な感情: {list(self.get_available_styles())}")
            
            return True
            
        except Exception as e:
            # エラー時もstdout/stderrを復元
            if 'old_stdout' in locals():
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            print(f"❌ モデル読み込みエラー: {e}")
            self.is_loaded = False
            return False
    
    def _update_emotion_mapping(self):
        """モデルから実際の感情リストを取得してマッピングを更新"""
        try:
            actual_styles = self._get_actual_styles_from_model()
            print(f"🔍 モデル内の実際の感情: {actual_styles}")
            
            # 実際の感情に基づいてマッピングを更新
            for actual_style in actual_styles:
                # そのまま登録
                self.emotion_mapping[actual_style] = actual_style
                
                # 小文字版も登録
                self.emotion_mapping[actual_style.lower()] = actual_style
                
                # 特別な変換ルール
                if actual_style.lower() == 'fear':
                    self.emotion_mapping['Fear'] = actual_style
                    self.emotion_mapping['FEAR'] = actual_style
                elif actual_style.lower() == 'happy':
                    self.emotion_mapping['happiness'] = actual_style
                    self.emotion_mapping['Happiness'] = actual_style
                elif actual_style.lower() == 'sad':
                    self.emotion_mapping['sadness'] = actual_style
                    self.emotion_mapping['Sadness'] = actual_style
            
            print(f"🔄 更新された感情マッピング: {self.emotion_mapping}")
            
        except Exception as e:
            print(f"⚠️ 感情マッピング更新エラー: {e}")
    
    def _get_actual_styles_from_model(self):
        """モデルから実際の利用可能な感情を取得（config.json優先版）"""
        try:
            # まず config.json から感情情報を取得
            config_path = self.model_info.get('config_path')
            if config_path and Path(config_path).exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                print(f"📄 config.json確認中...")
                
                # データセクションをチェック
                if 'data' in config:
                    data_section = config['data']
                    
                    # style2id から感情を取得（最優先）
                    if 'style2id' in data_section and data_section['style2id']:
                        style2id = data_section['style2id']
                        print(f"🎭 config.jsonからstyle2id発見: {style2id}")
                        
                        # キーから感情リストを作成
                        emotions = list(style2id.keys())
                        
                        # 各感情でテスト合成を試行
                        verified_emotions = []
                        for emotion in emotions:
                            try:
                                print(f"🧪 感情テスト: {emotion}")
                                
                                # ログ抑制
                                import sys
                                from io import StringIO
                                old_stdout = sys.stdout
                                old_stderr = sys.stderr
                                sys.stdout = StringIO()
                                sys.stderr = StringIO()
                                
                                try:
                                    sr, audio = self.model.infer(
                                        text="テスト",
                                        style=emotion,
                                        style_weight=1.0
                                    )
                                    
                                    if audio is not None and len(audio) > 0:
                                        verified_emotions.append(emotion)
                                        print(f"✅ {emotion}: 合成成功")
                                    else:
                                        print(f"❌ {emotion}: 空音声")
                                
                                finally:
                                    sys.stdout = old_stdout
                                    sys.stderr = old_stderr
                                    
                            except Exception as e:
                                print(f"❌ {emotion}: エラー - {str(e)[:50]}")
                                continue
                        
                        if verified_emotions:
                            print(f"🎯 検証済み感情: {verified_emotions}")
                            return verified_emotions
                    
                    # num_stylesから推測
                    num_styles = data_section.get('num_styles', 1)
                    print(f"📊 num_styles: {num_styles}")
                    
                    if num_styles > 1:
                        print("⚠️ num_stylesが1より大きいが、style2idが不完全です")
                        print("💡 推測: 感情学習が行われたが、config.jsonが正しく更新されていない可能性")
                        
                        # 一般的な感情名でテスト
                        common_emotions = ['Neutral', 'neutral', 'fear', 'Fear', 'happy', 'Happy', 'sad', 'Sad']
                        found_emotions = []
                        
                        for emotion in common_emotions:
                            try:
                                import sys
                                from io import StringIO
                                old_stdout = sys.stdout
                                old_stderr = sys.stderr
                                sys.stdout = StringIO()
                                sys.stderr = StringIO()
                                
                                try:
                                    sr, audio = self.model.infer(
                                        text="テスト",
                                        style=emotion,
                                        style_weight=1.0
                                    )
                                    
                                    if audio is not None and len(audio) > 0:
                                        found_emotions.append(emotion)
                                        print(f"🔍 発見: {emotion}")
                                
                                finally:
                                    sys.stdout = old_stdout
                                    sys.stderr = old_stderr
                                    
                            except:
                                continue
                        
                        if found_emotions:
                            print(f"🎭 推測で発見した感情: {found_emotions}")
                            return found_emotions
            
            # style_vectors.npy から推測
            style_path = self.model_info.get('style_path')
            if style_path and Path(style_path).exists():
                import numpy as np
                try:
                    style_vectors = np.load(style_path, allow_pickle=True)
                    print(f"📊 style_vectors shape: {getattr(style_vectors, 'shape', 'N/A')}")
                    
                    # 複数のベクトルがある場合は感情対応の可能性
                    if hasattr(style_vectors, 'shape') and len(style_vectors.shape) >= 2:
                        num_vectors = style_vectors.shape[0]
                        if num_vectors > 1:
                            print(f"🎯 {num_vectors}個のスタイルベクトル発見 - 感情対応の可能性")
                            
                            # ID順で感情名を推測
                            emotion_candidates = ['Neutral', 'fear', 'happy', 'sad', 'angry', 'disgust', 'surprise']
                            possible_emotions = emotion_candidates[:num_vectors]
                            
                            # 実際にテスト
                            verified = []
                            for i, emotion in enumerate(possible_emotions):
                                try:
                                    import sys
                                    from io import StringIO
                                    old_stdout = sys.stdout
                                    old_stderr = sys.stderr
                                    sys.stdout = StringIO()
                                    sys.stderr = StringIO()
                                    
                                    try:
                                        # インデックス指定でテスト
                                        sr, audio = self.model.infer(
                                            text="テスト",
                                            style=emotion,
                                            style_weight=1.0
                                        )
                                        
                                        if audio is not None and len(audio) > 0:
                                            verified.append(emotion)
                                            print(f"✅ インデックス{i}: {emotion}")
                                    
                                    finally:
                                        sys.stdout = old_stdout
                                        sys.stderr = old_stderr
                                        
                                except:
                                    continue
                            
                            if verified:
                                return verified
                except Exception as e:
                    print(f"style_vectors.npy読み込みエラー: {e}")
            
            # 最終的にNeutralのみ返す
            print("⚠️ 単一感情モデルと判断: Neutral のみ")
            return ["Neutral"]
            
        except Exception as e:
            print(f"❌ 感情取得エラー: {e}")
            import traceback
            traceback.print_exc()
            return ["Neutral"]
    
    def get_available_styles(self):
        """利用可能な感情スタイルを取得（マッピング対応版）"""
        if not self.is_loaded or not self.model:
            return ["Neutral"]
        
        try:
            # 実際のモデルから感情を取得
            actual_styles = self._get_actual_styles_from_model()
            
            if actual_styles:
                return actual_styles
            else:
                # フォールバック: 一般的な感情リスト
                print("⚠️ フォールバック: デフォルト感情リストを使用")
                return [
                    "Neutral",
                    "Happy", 
                    "Sad",
                    "Angry",
                    "fear",  # 小文字で試す
                    "Fear",  # 大文字も
                    "Disgust",
                    "Surprise"
                ]
                
        except Exception as e:
            print(f"❌ 利用可能スタイル取得エラー: {e}")
            return ["Neutral"]
    
    def normalize_emotion(self, emotion):
        """感情名を正規化（大文字・小文字やamitaro/jvnvの違いを吸収）"""
        if not emotion:
            return 'Neutral'
        
        # マッピングを確認
        normalized = self.emotion_mapping.get(emotion, emotion)
        
        if normalized != emotion:
            print(f"🔄 感情名を正規化: '{emotion}' -> '{normalized}'")
        
        return normalized
    
    def synthesize(self, text, **params):
        """音声合成を実行（感情名正規化対応版）"""
        if not self.is_loaded or self.model is None:
            raise RuntimeError("モデルが読み込まれていません")
        
        if not text.strip():
            raise ValueError("テキストが空です")
            
        try:
            # ログ出力を抑制
            import sys
            from io import StringIO
            
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            
            try:
                # パラメータを準備
                synth_params = self.default_params.copy()
                synth_params.update(params)
                
                # 感情名を正規化
                if 'style' in synth_params:
                    original_style = synth_params['style']
                    synth_params['style'] = self.normalize_emotion(original_style)
                    
                    if original_style != synth_params['style']:
                        print(f"✨ 感情正規化適用: {original_style} → {synth_params['style']}")
                            
                # モデルの infer メソッドのシグネチャを確認して安全に呼び出し
                kwargs = self._build_infer_kwargs(text, synth_params)
                
                # 音声合成実行
                sr, audio = self.model.infer(**kwargs)
                
            finally:
                # stdout/stderrを復元
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            # 結果チェック
            if audio is None or len(audio) == 0:
                raise RuntimeError("音声データが生成されませんでした")
                
            return sr, audio
            
        except Exception as e:
            print(f"❌ 音声合成エラー: {e}")
            # より詳細なエラー情報
            if 'style' in params:
                original_style = params['style']
                normalized_style = self.normalize_emotion(original_style)
                print(f"🎭 使用した感情: {original_style} -> {normalized_style}")
                
                # 利用可能な感情も表示
                available = self.get_available_styles()
                print(f"📋 利用可能感情: {available}")
                
                # 感情が利用可能かチェック
                if normalized_style not in available:
                    suggestion = available[0] if available else 'Neutral'
                    raise RuntimeError(f"感情 '{normalized_style}' は利用できません。利用可能: {available}. '{suggestion}'を試してください。")
            
            raise e
    
    def _build_infer_kwargs(self, text, params):
        """infer() メソッドに渡す引数を安全に構築（感情正規化済み前提）"""
        if not self.model:
            raise RuntimeError("モデルが読み込まれていません")
            
        # メソッドシグネチャを取得
        sig = inspect.signature(self.model.infer)
        method_params = sig.parameters
        
        # テキスト引数
        kwargs = {}
        if "text" in method_params:
            kwargs["text"] = text
        else:
            # 最初の位置引数にテキストを設定
            first_param = next(iter(method_params))
            kwargs[first_param] = text
        
        # スタイル系（既に正規化済み）
        if "style" in method_params:
            kwargs["style"] = params.get('style', 'Neutral')

        if "style_weight" in method_params:
            kwargs["style_weight"] = params.get('style_weight', 1.0)
        elif "emotion_weight" in method_params:
            kwargs["emotion_weight"] = params.get('style_weight', 1.0)

        # 長さ系（複数のパラメータ名をチェック）
        length_scale = params.get('length_scale', 0.85)
        
        if "length_scale" in method_params:
            kwargs["length_scale"] = length_scale
        elif "duration_scale" in method_params:
            kwargs["duration_scale"] = length_scale
        elif "speed" in method_params:
            # speedの場合は逆数になることが多い
            speed_value = 1.0 / length_scale
            kwargs["speed"] = speed_value
        elif "length" in method_params:
            kwargs["length"] = length_scale
        
        # SDP
        sdp_value = params.get('sdp_ratio', 0.25)
        
        if "sdp_ratio" in method_params:
            kwargs["sdp_ratio"] = sdp_value
        elif "sdp" in method_params:
            kwargs["sdp"] = sdp_value  
        
        # ノイズ系（優先順位: noise > noise_scale_w > noise_scale）
        noise_value = params.get('noise', 0.35)
        
        if "noise" in method_params:
            kwargs["noise"] = noise_value
        elif "noise_scale_w" in method_params:
            kwargs["noise_scale_w"] = noise_value
        elif "noise_scale" in method_params:
            kwargs["noise_scale"] = noise_value
        
        # ピッチとイントネーション
        if "pitch_scale" in method_params:
            pitch_value = params.get('pitch_scale', 1.0)
            kwargs["pitch_scale"] = pitch_value
        
        if "intonation_scale" in method_params:
            intonation_value = params.get('intonation_scale', 1.0)
            kwargs["intonation_scale"] = intonation_value
        
        print(f"🔧 推論パラメータ: {kwargs}")
        return kwargs
    
    def get_model_info(self):
        """モデル情報を取得"""
        return self.model_info.copy() if self.is_loaded else {}
    
    def unload_model(self):
        """モデルをアンロード"""
        if self.model:
            del self.model
            self.model = None
        self.is_loaded = False
        self.model_info = {}
        
        # GPU メモリをクリア
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    # 🆕 デバッグ用メソッド
    def debug_emotions(self):
        """感情マッピングのデバッグ情報を表示"""
        print("\n=== 感情マッピング デバッグ情報 ===")
        print(f"モデル読み込み状態: {'✅' if self.is_loaded else '❌'}")
        
        if self.is_loaded:
            print(f"モデルパス: {self.model_info.get('model_path', 'N/A')}")
            actual_styles = self._get_actual_styles_from_model()
            print(f"実際の利用可能感情: {actual_styles}")
        
        print(f"現在の感情マッピング:")
        for key, value in sorted(self.emotion_mapping.items()):
            status = "✅" if key == value else f"🔄 -> {value}"
            print(f"  '{key}' {status}")
        
        print("=== デバッグ情報終了 ===\n")
    
    def test_emotion(self, emotion, text="これはテストです"):
        """指定した感情での音声合成をテスト"""
        try:
            print(f"🧪 感情テスト: '{emotion}'")
            
            # 感情を正規化
            normalized = self.normalize_emotion(emotion)
            print(f"📝 正規化後: '{normalized}'")
            
            # 音声合成実行
            sr, audio = self.synthesize(text, style=emotion, style_weight=1.0)
            
            print(f"✅ テスト成功: {len(audio)} samples, {sr}Hz")
            return True, sr, audio
            
        except Exception as e:
            print(f"❌ テスト失敗: {e}")
            return False, None, None