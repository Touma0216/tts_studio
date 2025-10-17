import json
import os
import uuid
import glob
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

class Live2DManager:
    """Live2Dモデル管理システム - モデルフォルダのパス管理と履歴機能"""
    
    def __init__(self, history_file: str = "live2d_history.json"):
        self.history_file = Path(history_file)
        # ★追加: Live2Dモデルのベースディレクトリを定義
        # main_window.pyからlive2d_urlを渡されることを想定
        self.base_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent / 'assets' / 'live2d_dist'
        self.models_data: List[Dict[str, Any]] = []
        self.load_history()

    def get_relative_path(self, absolute_path: str) -> Optional[str]:
        try:
            return str(Path(absolute_path).relative_to(self.base_dir).as_posix())
        except ValueError:
            return None
    
    def load_history(self) -> None:
        """履歴ファイルを読み込み"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.models_data = data.get('models', [])
                    for model in self.models_data:
                        ui_settings = model.setdefault('ui_settings', {})
                        ui_settings.setdefault('zoom_percent', 100)
                        ui_settings.setdefault('h_position', 50)
                        ui_settings.setdefault('v_position', 50)
                        ui_settings.setdefault('minimap_visible', False)
                        ui_settings.setdefault('background_settings', {
                            'mode': 'default',
                            'color': '#000000',
                            'alpha': 1.0,
                            'previewAlpha': 1.0
                        })
                    # 存在しないモデルフォルダを自動削除
                    self.cleanup_missing_models()
        except Exception as e:
            print(f"Live2D履歴読み込みエラー: {e}")
            self.models_data = []
    
    def save_history(self) -> None:
        """履歴ファイルに保存"""
        try:
            data = {
                'models': self.models_data,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Live2D履歴保存エラー: {e}")
    
    def add_model(self, model_folder_path: str, model_name: str = "") -> str:
        """新しいLive2Dモデルを追加"""
        model_folder_path = str(Path(model_folder_path).resolve())
        model_name = model_name or Path(model_folder_path).name
        
        # 既存チェック
        for model in self.models_data:
            if model['model_folder_path'] == model_folder_path:
                # 既存の場合、最新に移動
                self.models_data.remove(model)
                self.models_data.insert(0, model)
                model['last_used'] = datetime.now().isoformat()
                self.save_history()
                return model['id']
        
        # 新規追加
        model_id = str(uuid.uuid4())
        model_data = {
            'id': model_id,
            'model_folder_path': model_folder_path,
            'name': model_name,
            'created_at': datetime.now().isoformat(),
            'last_used': datetime.now().isoformat(),
            'ui_settings': {
                'scale': 1.0,
                'position_x': 0.0,
                'position_y': 0.0,
                'auto_breath': True,
                'auto_eye_blink': True,
                'lip_sync_gain': 1.0,
                'background_visible': True,
                'zoom_percent': 100,
                'h_position': 50,
                'v_position': 50,
                'minimap_visible': False,
                'background_settings': {
                    'mode': 'default',
                    'color': '#000000',
                    'alpha': 1.0,
                    'previewAlpha': 1.0
                }
            }
        }
        
        self.models_data.insert(0, model_data)
        self.save_history()
        return model_id
    
    def get_all_models(self) -> List[Dict[str, Any]]:
        """全てのモデル履歴を取得"""
        return self.models_data.copy()
    
    def get_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """IDでモデルデータを取得"""
        for model in self.models_data:
            if model['id'] == model_id:
                return model.copy()
        return None
    
    def get_last_model(self) -> Optional[Dict[str, Any]]:
        """最後に使用したモデルを取得"""
        if self.models_data:
            return self.models_data[0].copy()
        return None
    
    def remove_model(self, model_id: str) -> bool:
        """モデルを履歴から削除"""
        for i, model in enumerate(self.models_data):
            if model['id'] == model_id:
                del self.models_data[i]
                self.save_history()
                return True
        return False
    
    def update_ui_settings(self, model_id: str, ui_settings: Dict[str, Any]) -> bool:
        """モデルのUI設定を更新"""
        for model in self.models_data:
            if model['id'] == model_id:
                model['ui_settings'].update(ui_settings)
                model['last_used'] = datetime.now().isoformat()
                self.save_history()
                return True
        return False
    
    def get_ui_settings(self, model_id: str) -> Dict[str, Any]:
        """モデルのUI設定を取得"""
        for model in self.models_data:
            if model['id'] == model_id:
                return model['ui_settings'].copy()
        
        # デフォルト設定を返す
        return {
            'scale': 1.0,
            'position_x': 0.0,
            'position_y': 0.0,
            'auto_breath': True,
            'auto_eye_blink': True,
            'lip_sync_gain': 1.0,
            'background_visible': True,
            'zoom_percent': 100,
            'h_position': 50,
            'v_position': 50,
            'minimap_visible': False,
            'idle_motion_enabled': True,
            'background_settings': {
                'mode': 'default',
                'color': '#000000',
                'alpha': 1.0,
                'previewAlpha': 1.0
            }
        }
    
    # ★追加: find_model3_json メソッドを追加
    def find_model3_json(self, folder_path: str) -> Optional[str]:
        """
        指定されたフォルダ内から.model3.jsonファイルを探索する。
        見つかった場合、そのファイルの絶対パスを返す。
        """
        model_json_files = glob.glob(os.path.join(folder_path, '*.model3.json'))
        if model_json_files:
            return model_json_files[0]
        
        # サブディレクトリも探索する
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.model3.json'):
                    return os.path.join(root, file)
                    
        return None
    
    def validate_model_folder(self, folder_path: str) -> Dict[str, Any]:
        """Live2Dモデルフォルダの検証"""
        folder_path = Path(folder_path)
        result = {
            'is_valid': False,
            'model3_json': None,
            'moc3_file': None,
            'physics3_json': None,
            'missing_files': [],
            'found_files': {}
        }
        
        if not folder_path.exists() or not folder_path.is_dir():
            result['missing_files'].append('フォルダが存在しません')
            return result
        
        # 必須ファイルを検索
        required_patterns = {
            'model3_json': '*.model3.json',
            'moc3_file': '*.moc3'
        }
        
        optional_patterns = {
            'physics3_json': '*.physics3.json',
            'exp3_files': '*.exp3.json',
            'motion3_files': '*.motion3.json',
            'texture_files': '*.png'
        }
        
        # 必須ファイルチェック
        for key, pattern in required_patterns.items():
            files = list(folder_path.glob(pattern))
            if files:
                result['found_files'][key] = str(files[0])
            else:
                result['missing_files'].append(f'{pattern} ファイルが見つかりません')
        
        # オプションファイルチェック
        for key, pattern in optional_patterns.items():
            files = list(folder_path.glob(pattern))
            if files:
                result['found_files'][key] = [str(f) for f in files]
        
        # 検証結果
        if not result['missing_files']:
            result['is_valid'] = True
            result['model3_json'] = result['found_files']['model3_json']
            result['moc3_file'] = result['found_files']['moc3_file']
            result['physics3_json'] = result['found_files'].get('physics3_json')
        
        return result
    
    def cleanup_missing_models(self) -> None:
        """存在しないモデルフォルダを履歴から削除"""
        valid_models = []
        for model in self.models_data:
            if Path(model['model_folder_path']).exists():
                valid_models.append(model)
        
        if len(valid_models) != len(self.models_data):
            self.models_data = valid_models
            self.save_history()
    
    def get_model_info(self, model_folder_path: str) -> Dict[str, Any]:
        """モデルフォルダの詳細情報を取得"""
        validation = self.validate_model_folder(model_folder_path)
        folder_path = Path(model_folder_path)
        
        info = {
            'folder_name': folder_path.name,
            'folder_size': self._get_folder_size(folder_path),
            'file_count': len(list(folder_path.glob('*'))),
            'validation': validation
        }
        
        return info
    
    def _get_folder_size(self, folder_path: Path) -> int:
        """フォルダサイズを取得（バイト単位）"""
        try:
            total_size = 0
            for file_path in folder_path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except Exception:
            return 0