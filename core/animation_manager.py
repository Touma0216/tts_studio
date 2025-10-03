# core/animation_manager.py
# Live2Dアニメーション管理システム

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class AnimationManager:
    """Live2Dアニメーションの読み込み・管理・再生制御"""
    
    def __init__(self, animations_dir: str = "animations"):
        """
        初期化
        
        Args:
            animations_dir: アニメーションJSONファイルの保存ディレクトリ
        """
        self.animations_dir = Path(animations_dir)
        self.animations_dir.mkdir(exist_ok=True)
        
        self.current_animation: Optional[Dict[str, Any]] = None
        self.animation_list: List[Dict[str, Any]] = []
        
        self._load_animation_list()
    
    def _load_animation_list(self):
        """
        アニメーションディレクトリから全JSONファイルを読み込み
        """
        self.animation_list = []
        
        try:
            for json_file in self.animations_dir.glob("*.json"):
                try:
                    animation_data = self.load_animation_file(json_file)
                    if animation_data:
                        self.animation_list.append({
                            'file_path': str(json_file),
                            'file_name': json_file.name,
                            'name': animation_data.get('metadata', {}).get('name', json_file.stem),
                            'description': animation_data.get('metadata', {}).get('description', ''),
                            'duration': animation_data.get('metadata', {}).get('duration', 0),
                            'keyframe_count': len(animation_data.get('keyframes', []))
                        })
                except Exception as e:
                    print(f"⚠️ アニメーション読み込みエラー ({json_file.name}): {e}")
            
            print(f"✅ アニメーション読み込み完了: {len(self.animation_list)}件")
            
        except Exception as e:
            print(f"❌ アニメーションリスト読み込みエラー: {e}")
    
    def load_animation_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        JSONファイルからアニメーションデータを読み込み
        
        Args:
            file_path: JSONファイルパス
            
        Returns:
            アニメーションデータ、失敗時はNone
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 基本バリデーション
            if not self.validate_animation(data):
                print(f"❌ 無効なアニメーションデータ: {file_path.name}")
                return None
            
            return data
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析エラー ({file_path.name}): {e}")
            return None
        except Exception as e:
            print(f"❌ ファイル読み込みエラー ({file_path.name}): {e}")
            return None
    
    def validate_animation(self, data: Dict[str, Any]) -> bool:
        """
        アニメーションデータのバリデーション
        
        Args:
            data: アニメーションデータ
            
        Returns:
            有効ならTrue
        """
        # 必須フィールドチェック
        if 'keyframes' not in data:
            print("❌ keyframesフィールドが見つかりません")
            return False
        
        if not isinstance(data['keyframes'], list):
            print("❌ keyframesは配列である必要があります")
            return False
        
        if len(data['keyframes']) == 0:
            print("❌ keyframesが空です")
            return False
        
        # 各キーフレームのバリデーション
        for i, keyframe in enumerate(data['keyframes']):
            if 'time' not in keyframe:
                print(f"❌ キーフレーム{i}: timeフィールドがありません")
                return False
            
            if 'parameters' not in keyframe:
                print(f"❌ キーフレーム{i}: parametersフィールドがありません")
                return False
            
            if not isinstance(keyframe['parameters'], dict):
                print(f"❌ キーフレーム{i}: parametersは辞書型である必要があります")
                return False
        
        return True
    
    def get_animation_list(self) -> List[Dict[str, Any]]:
        """
        アニメーション一覧を取得
        
        Returns:
            アニメーション情報のリスト
        """
        return self.animation_list
    
    def load_animation_by_name(self, file_name: str) -> Optional[Dict[str, Any]]:
        """
        ファイル名でアニメーションを読み込み
        
        Args:
            file_name: JSONファイル名
            
        Returns:
            アニメーションデータ、失敗時はNone
        """
        file_path = self.animations_dir / file_name
        
        if not file_path.exists():
            print(f"❌ ファイルが見つかりません: {file_name}")
            return None
        
        animation_data = self.load_animation_file(file_path)
        
        if animation_data:
            self.current_animation = animation_data
            print(f"✅ アニメーション読み込み: {file_name}")
        
        return animation_data
    
    def get_current_animation(self) -> Optional[Dict[str, Any]]:
        """
        現在読み込まれているアニメーションを取得
        
        Returns:
            現在のアニメーションデータ、なければNone
        """
        return self.current_animation
    
    def save_animation(self, animation_data: Dict[str, Any], file_name: str) -> bool:
        """
        アニメーションデータをJSONファイルに保存
        
        Args:
            animation_data: アニメーションデータ
            file_name: 保存先ファイル名
            
        Returns:
            成功時True
        """
        try:
            # バリデーション
            if not self.validate_animation(animation_data):
                print("❌ 無効なアニメーションデータのため保存できません")
                return False
            
            # メタデータに保存日時を追加
            if 'metadata' not in animation_data:
                animation_data['metadata'] = {}
            
            animation_data['metadata']['saved_at'] = datetime.now().isoformat()
            
            # ファイル保存
            file_path = self.animations_dir / file_name
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(animation_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ アニメーション保存完了: {file_name}")
            
            # リスト更新
            self._load_animation_list()
            
            return True
            
        except Exception as e:
            print(f"❌ アニメーション保存エラー: {e}")
            return False
    
    def delete_animation(self, file_name: str) -> bool:
        """
        アニメーションファイルを削除
        
        Args:
            file_name: 削除するファイル名
            
        Returns:
            成功時True
        """
        try:
            file_path = self.animations_dir / file_name
            
            if not file_path.exists():
                print(f"❌ ファイルが見つかりません: {file_name}")
                return False
            
            file_path.unlink()
            print(f"✅ アニメーション削除完了: {file_name}")
            
            # リスト更新
            self._load_animation_list()
            
            # 現在のアニメーションが削除されたらクリア
            if self.current_animation and \
               self.current_animation.get('metadata', {}).get('name', '') == file_name:
                self.current_animation = None
            
            return True
            
        except Exception as e:
            print(f"❌ アニメーション削除エラー: {e}")
            return False
    
    def create_preset_from_parameters(
        self, 
        parameters: Dict[str, float], 
        name: str, 
        description: str = ""
    ) -> Dict[str, Any]:
        """
        現在のパラメータからプリセットアニメーションを作成
        
        Args:
            parameters: Live2Dパラメータ辞書
            name: プリセット名
            description: 説明
            
        Returns:
            プリセットアニメーションデータ
        """
        preset_data = {
            "version": "1.0",
            "type": "preset",
            "metadata": {
                "name": name,
                "description": description,
                "created_at": datetime.now().isoformat()
            },
            "parameters": parameters
        }
        
        return preset_data
    
    def refresh_list(self):
        """アニメーション一覧を再読み込み"""
        self._load_animation_list()
    
    def get_animation_info(self, file_name: str) -> Optional[Dict[str, Any]]:
        """
        指定されたアニメーションの情報を取得
        
        Args:
            file_name: ファイル名
            
        Returns:
            アニメーション情報、見つからない場合はNone
        """
        for anim_info in self.animation_list:
            if anim_info['file_name'] == file_name:
                return anim_info
        
        return None


# デバッグ用
if __name__ == "__main__":
    # テスト実行
    manager = AnimationManager("animations")
    
    print("=" * 50)
    print("アニメーション一覧:")
    for anim in manager.get_animation_list():
        print(f"  - {anim['name']} ({anim['file_name']})")
        print(f"    時間: {anim['duration']}秒, キーフレーム: {anim['keyframe_count']}個")
    
    print("=" * 50)
    
    # サンプルアニメーションを読み込み
    if manager.animation_list:
        first_anim = manager.animation_list[0]['file_name']
        data = manager.load_animation_by_name(first_anim)
        if data:
            print(f"読み込み成功: {first_anim}")
            print(f"キーフレーム数: {len(data['keyframes'])}")