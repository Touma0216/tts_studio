#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Style-Bert-VITS2 モデル解析ツール
学習モデルに適した音声出力パラメータを抽出
"""

import json
import numpy as np
import torch
from pathlib import Path
import traceback

class ModelAnalyzer:
    def __init__(self, model_history_path="model_history.json"):
        self.model_history_path = model_history_path
        self.models = []
        self.load_model_history()
    
    def load_model_history(self):
        """model_history.jsonを読み込み"""
        try:
            with open(self.model_history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.models = data.get('models', [])
            print(f"✅ モデル履歴読み込み完了: {len(self.models)}個のモデル")
        except Exception as e:
            print(f"❌ モデル履歴読み込みエラー: {e}")
            self.models = []
    
    def analyze_all_models(self):
        """全モデルを解析"""
        for i, model_data in enumerate(self.models, 1):
            print(f"\n{'='*60}")
            print(f"🔍 モデル解析 {i}/{len(self.models)}: {model_data['name']}")
            print(f"{'='*60}")
            
            try:
                self.analyze_single_model(model_data)
            except Exception as e:
                print(f"❌ 解析エラー: {e}")
                traceback.print_exc()
    
    def analyze_single_model(self, model_data):
        """単一モデルの詳細解析"""
        model_path = model_data['model_path']
        config_path = model_data['config_path']
        style_path = model_data['style_path']
        
        print(f"📁 モデルパス: {model_path}")
        print(f"📁 設定パス: {config_path}")
        print(f"📁 スタイルパス: {style_path}")
        
        # 1. config.json解析
        print(f"\n🔧 config.json解析:")
        config_data = self.analyze_config(config_path)
        
        # 2. style_vectors.npy解析
        print(f"\n🎭 style_vectors.npy解析:")
        style_data = self.analyze_style_vectors(style_path)
        
        # 3. モデルファイル解析
        print(f"\n🤖 モデルファイル解析:")
        model_file_data = self.analyze_model_file(model_path)
        
        # 4. 推奨設定生成
        print(f"\n⚙️ 推奨設定:")
        recommended_settings = self.generate_recommended_settings(
            config_data, style_data, model_file_data
        )
        
        return {
            'config': config_data,
            'style': style_data,
            'model_file': model_file_data,
            'recommended': recommended_settings
        }
    
    def analyze_config(self, config_path):
        """config.json詳細解析"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            print(f"  📊 全体構造: {list(config.keys())}")
            
            # データセクション
            if 'data' in config:
                data_section = config['data']
                print(f"  📈 データセクション:")
                print(f"    - sampling_rate: {data_section.get('sampling_rate', 'N/A')}")
                print(f"    - filter_length: {data_section.get('filter_length', 'N/A')}")
                print(f"    - hop_length: {data_section.get('hop_length', 'N/A')}")
                print(f"    - win_length: {data_section.get('win_length', 'N/A')}")
                print(f"    - n_mel_channels: {data_section.get('n_mel_channels', 'N/A')}")
                print(f"    - max_wav_value: {data_section.get('max_wav_value', 'N/A')}")
                print(f"    - num_styles: {data_section.get('num_styles', 'N/A')}")
                
                # スタイル情報
                if 'style2id' in data_section:
                    style2id = data_section['style2id']
                    print(f"    - style2id: {style2id}")
                else:
                    print(f"    - style2id: 未定義")
            
            # モデルセクション
            if 'model' in config:
                model_section = config['model']
                print(f"  🎛️ モデルセクション:")
                print(f"    - inter_channels: {model_section.get('inter_channels', 'N/A')}")
                print(f"    - hidden_channels: {model_section.get('hidden_channels', 'N/A')}")
                print(f"    - filter_channels: {model_section.get('filter_channels', 'N/A')}")
                print(f"    - n_heads: {model_section.get('n_heads', 'N/A')}")
                print(f"    - n_layers: {model_section.get('n_layers', 'N/A')}")
                print(f"    - kernel_size: {model_section.get('kernel_size', 'N/A')}")
                print(f"    - p_dropout: {model_section.get('p_dropout', 'N/A')}")
                print(f"    - gin_channels: {model_section.get('gin_channels', 'N/A')}")
            
            return config
            
        except Exception as e:
            print(f"    ❌ config.json読み込みエラー: {e}")
            return {}
    
    def analyze_style_vectors(self, style_path):
        """style_vectors.npy解析"""
        try:
            style_vectors = np.load(style_path, allow_pickle=True)
            
            print(f"  📊 shape: {style_vectors.shape}")
            print(f"  📊 dtype: {style_vectors.dtype}")
            print(f"  📊 size: {style_vectors.size}")
            print(f"  📊 ndim: {style_vectors.ndim}")
            
            if style_vectors.ndim >= 2:
                print(f"  📊 スタイル数: {style_vectors.shape[0]}")
                print(f"  📊 ベクトル次元: {style_vectors.shape[1] if style_vectors.shape[1:] else 'N/A'}")
                
                # 各スタイルベクトルの統計
                for i in range(min(style_vectors.shape[0], 10)):  # 最大10個まで
                    vec = style_vectors[i]
                    if vec.ndim >= 1:
                        print(f"    - スタイル{i}: min={np.min(vec):.4f}, max={np.max(vec):.4f}, mean={np.mean(vec):.4f}")
            
            return {
                'shape': style_vectors.shape,
                'dtype': str(style_vectors.dtype),
                'data': style_vectors
            }
            
        except Exception as e:
            print(f"    ❌ style_vectors.npy読み込みエラー: {e}")
            return {}
    
    def analyze_model_file(self, model_path):
        """モデルファイル（.safetensors）解析"""
        try:
            # safetensorsファイルの基本情報
            file_size = Path(model_path).stat().st_size
            print(f"  📊 ファイルサイズ: {file_size / (1024*1024):.1f} MB")
            
            # safetensorsの内容を解析（可能なら）
            try:
                # safetensorsライブラリがある場合
                from safetensors import safe_open
                
                tensors_info = {}
                with safe_open(model_path, framework="pt", device="cpu") as f:
                    keys = f.keys()
                    print(f"  📊 テンソル数: {len(list(keys))}")
                    
                    # 主要なテンソル情報を表示
                    key_list = list(f.keys())
                    for i, key in enumerate(key_list[:20]):  # 最初の20個
                        tensor = f.get_tensor(key)
                        tensors_info[key] = {
                            'shape': tensor.shape,
                            'dtype': str(tensor.dtype)
                        }
                        print(f"    - {key}: {tensor.shape} ({tensor.dtype})")
                    
                    if len(key_list) > 20:
                        print(f"    ... 他 {len(key_list) - 20} 個のテンソル")
                
                return {
                    'file_size_mb': file_size / (1024*1024),
                    'tensor_count': len(key_list),
                    'tensors': tensors_info
                }
                
            except ImportError:
                print(f"    ⚠️ safetensorsライブラリが見つかりません")
                return {'file_size_mb': file_size / (1024*1024)}
            
        except Exception as e:
            print(f"    ❌ モデルファイル解析エラー: {e}")
            return {}
    
    def generate_recommended_settings(self, config_data, style_data, model_file_data):
        """推奨設定を生成"""
        settings = {
            'audio_settings': {},
            'inference_settings': {},
            'style_settings': {}
        }
        
        # config.jsonから音声設定を抽出
        if config_data and 'data' in config_data:
            data_section = config_data['data']
            
            # 🔥 重要: max_wav_valueの確認
            max_wav_value = data_section.get('max_wav_value')
            if max_wav_value:
                print(f"  🎯 max_wav_value検出: {max_wav_value}")
                
                if max_wav_value == 32768.0 or max_wav_value == 32767.0:
                    settings['audio_settings']['format'] = 'int16'
                    settings['audio_settings']['normalization_factor'] = max_wav_value
                    settings['audio_settings']['recommended_action'] = 'int16正規化が必要'
                    print(f"  ✅ int16フォーマット確認 → 正規化係数: {max_wav_value}")
                    
                elif max_wav_value == 1.0:
                    settings['audio_settings']['format'] = 'float32'
                    settings['audio_settings']['normalization_factor'] = 1.0
                    settings['audio_settings']['recommended_action'] = '正規化不要'
                    print(f"  ✅ float32フォーマット確認")
                    
                else:
                    settings['audio_settings']['format'] = 'unknown'
                    settings['audio_settings']['normalization_factor'] = max_wav_value
                    settings['audio_settings']['recommended_action'] = f'カスタム正規化が必要 (/{max_wav_value})'
                    print(f"  ⚠️ 特殊フォーマット: {max_wav_value}")
            
            # サンプリング周波数
            sampling_rate = data_section.get('sampling_rate')
            if sampling_rate:
                settings['audio_settings']['sampling_rate'] = sampling_rate
                print(f"  🎵 サンプリング周波数: {sampling_rate} Hz")
            
            # スタイル数
            num_styles = data_section.get('num_styles', 1)
            settings['style_settings']['num_styles'] = num_styles
            print(f"  🎭 スタイル数: {num_styles}")
            
            # スタイルマッピング
            style2id = data_section.get('style2id', {})
            if style2id:
                settings['style_settings']['available_styles'] = list(style2id.keys())
                settings['style_settings']['style_mapping'] = style2id
                print(f"  🎨 利用可能スタイル: {list(style2id.keys())}")
        
        # style_vectorsから情報を抽出
        if style_data and 'shape' in style_data:
            shape = style_data['shape']
            if len(shape) >= 2:
                detected_styles = shape[0]
                settings['style_settings']['detected_style_count'] = detected_styles
                print(f"  🔍 検出されたスタイル数: {detected_styles}")
                
                # configとの整合性チェック
                config_styles = settings['style_settings'].get('num_styles', 1)
                if detected_styles != config_styles:
                    print(f"  ⚠️ スタイル数不整合: config={config_styles}, vectors={detected_styles}")
        
        # 推論設定の推奨値
        settings['inference_settings'] = {
            'style_weight': (0.5, 1.5),  # 推奨範囲
            'noise': (0.1, 0.6),
            'length_scale': (0.5, 1.5),
            'sdp_ratio': (0.0, 0.5)
        }
        
        return settings
    
    def print_summary(self, analysis_results):
        """解析結果のサマリーを表示"""
        print(f"\n{'='*60}")
        print(f"📋 解析結果サマリー")
        print(f"{'='*60}")
        
        for model_name, result in analysis_results.items():
            print(f"\n🔍 {model_name}:")
            
            recommended = result.get('recommended', {})
            audio_settings = recommended.get('audio_settings', {})
            
            if 'format' in audio_settings:
                print(f"  📊 音声フォーマット: {audio_settings['format']}")
                print(f"  🔧 推奨処理: {audio_settings['recommended_action']}")
                
                if 'normalization_factor' in audio_settings:
                    factor = audio_settings['normalization_factor']
                    print(f"  📐 正規化係数: {factor}")
                    print(f"  💻 コード例: audio.astype(np.float32) / {factor}")
            
            style_settings = recommended.get('style_settings', {})
            if 'available_styles' in style_settings:
                styles = style_settings['available_styles']
                print(f"  🎭 利用可能感情: {styles}")


def main():
    """メイン実行関数"""
    print("🚀 Style-Bert-VITS2 モデル解析ツール")
    print("="*60)
    
    analyzer = ModelAnalyzer()
    
    if not analyzer.models:
        print("❌ 解析対象のモデルが見つかりません")
        return
    
    # 全モデル解析実行
    analysis_results = {}
    
    for model_data in analyzer.models:
        model_name = model_data['name']
        try:
            result = analyzer.analyze_single_model(model_data)
            analysis_results[model_name] = result
        except Exception as e:
            print(f"❌ {model_name} の解析に失敗: {e}")
    
    # サマリー表示
    if analysis_results:
        analyzer.print_summary(analysis_results)
    
    print(f"\n✅ 解析完了!")


if __name__ == "__main__":
    main()