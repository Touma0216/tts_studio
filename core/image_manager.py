import os
import json
from pathlib import Path
from typing import Dict, List, Optional

class ImageManager:
    """画像履歴とUI設定を管理するクラス（画面表示モード対応版）"""
    
    def __init__(self, config_file="image_history.json"):
        self.config_file = config_file
        self.images: List[Dict] = []
        self.load_history()

    # ---------- 内部ユーティリティ ----------
    def _pretty_default_name(self, image_path: str) -> str:
        """既定表示名：ファイル名（拡張子なし）"""
        return Path(image_path).stem or "image"

    def _generate_image_id(self, image_path: str) -> str:
        """画像パスからユニークIDを生成"""
        import hashlib
        return hashlib.md5(image_path.encode()).hexdigest()[:12]

    def _normalize_data(self) -> bool:
        """既存履歴のデータ構造を正規化。変更があれば True。"""
        changed = False
        for img in self.images:
            # nameフィールドの正規化
            current_name = (img.get("name") or "").strip()
            desired_name = self._pretty_default_name(img.get("image_path", ""))
            if not current_name and desired_name:
                img["name"] = desired_name
                changed = True
            
            # noteフィールドの追加
            if "note" not in img:
                img["note"] = ""
                changed = True
            
            # ui_settingsフィールドの追加
            if "ui_settings" not in img:
                img["ui_settings"] = {}  # デフォルトの空辞書
                changed = True
        return changed

    # ---------- I/O ----------
    def load_history(self):
        """履歴ファイルから読み込み"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.images = data.get('images', [])
            except Exception:
                self.images = []
        else:
            self.images = []

        # 起動時に一度だけデータ構造を正規化（必要時のみ保存）
        if self._normalize_data():
            self.save_history(quiet=True)

    def save_history(self, quiet: bool = True):
        """履歴ファイルに保存（quiet=True でログ抑制）"""
        try:
            data = {'images': self.images}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if not quiet:
                pass
        except Exception as e:
            print(f"画像履歴保存エラー: {e}")

    # ---------- CRUD ----------
    def add_image(self, image_path: str, custom_name: Optional[str] = None) -> str:
        """新しい画像を履歴に追加（既存なら先頭に移動のみ）"""
        image_path = str(Path(image_path).resolve())
        image_id = self._generate_image_id(image_path)
        existing = self.get_image_by_id(image_id)
        
        if existing:
            self.images.remove(existing)
            self.images.insert(0, existing)
            self.save_history(quiet=True)
            return image_id

        image_name = custom_name or self._pretty_default_name(image_path)
        entry = {
            'id': image_id,
            'name': image_name,
            'note': "",
            'image_path': image_path,
            'ui_settings': {},  # 新規追加時にUI設定を初期化
        }
        self.images.insert(0, entry)
        
        if len(self.images) > 20:
            self.images = self.images[:20]
        
        self.save_history(quiet=True)
        return image_id

    def get_image_by_id(self, image_id: str) -> Optional[Dict]:
        for img in self.images:
            if img.get('id') == image_id:
                return img
        return None

    def get_all_images(self) -> List[Dict]:
        return self.images.copy()

    def remove_image(self, image_id: str) -> bool:
        before = len(self.images)
        self.images = [img for img in self.images if img.get('id') != image_id]
        changed = len(self.images) != before
        if changed:
            self.save_history(quiet=True)
        return changed

    # ★★★ 新規追加：画像名更新機能 ★★★
    def update_image_name(self, image_id: str, new_name: str) -> bool:
        """指定された画像の名前を更新"""
        img = self.get_image_by_id(image_id)
        if not img:
            return False
        img['name'] = new_name
        self.save_history(quiet=True)
        return True

    def update_note(self, image_id: str, note: str) -> bool:
        """指定された画像のメモを更新"""
        img = self.get_image_by_id(image_id)
        if not img:
            return False
        img['note'] = note
        self.save_history(quiet=True)
        return True

    # ---------- UI設定関連（ここが追加・修正された箇所です！）----------
    def get_ui_settings(self, image_id: str) -> Dict:
        """指定された画像のUI設定を取得"""
        img = self.get_image_by_id(image_id)
        if img:
            # 必ず辞書を返すように .get() を使用
            return img.get('ui_settings', {})
        return {}

    def update_ui_settings(self, image_id: str, settings: Dict) -> bool:
        """指定された画像のUI設定を更新"""
        img = self.get_image_by_id(image_id)
        if not img:
            return False
        
        # 既存の設定と新しい設定をマージ（上書き）
        if 'ui_settings' not in img:
            img['ui_settings'] = {}
        img['ui_settings'].update(settings)
        
        self.save_history(quiet=True)
        return True

    # ---------- ユーティリティ ----------
    def cleanup_missing_images(self):
        """存在しない画像を履歴から削除"""
        original_count = len(self.images)
        self.images = [img for img in self.images if os.path.exists(img.get('image_path', ''))]
        
        removed_count = original_count - len(self.images)
        if removed_count > 0:
            self.save_history(quiet=True)
            print(f"存在しない画像を{removed_count}件削除しました")

    def get_last_image(self) -> Optional[Dict]:
        """最新の画像データを取得"""
        if self.images:
            return self.images[0].copy()
        return None


class DisplayModeManager:
    """画面表示モード管理クラス（新規追加）"""
    
    def __init__(self, settings_file="user_settings.json"):
        self.settings_file = Path(settings_file)
        self.settings = self.load_settings()
    
    def load_settings(self) -> dict:
        """設定ファイルを読み込み"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            print(f"⚠️ 設定読み込みエラー: {e}")
            return {}
    
    def save_settings(self):
        """設定ファイルに保存"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            print(f"💾 表示モード設定を保存: {self.settings_file}")
        except Exception as e:
            print(f"❌ 設定保存エラー: {e}")
    
    def get_display_mode(self) -> str:
        """現在の表示モードを取得（image or live2d）"""
        return self.settings.get('character_display', {}).get('mode', 'image')
    
    def set_display_mode(self, mode: str):
        """表示モードを設定（image or live2d）"""
        if mode not in ['image', 'live2d']:
            print(f"⚠️ 無効な表示モード: {mode}")
            return
        
        if 'character_display' not in self.settings:
            self.settings['character_display'] = {}
        
        self.settings['character_display']['mode'] = mode
        self.save_settings()
        print(f"🔧 表示モードを変更: {mode}")
    
    def get_last_image_id(self) -> Optional[str]:
        """最後に表示していた画像IDを取得"""
        return self.settings.get('character_display', {}).get('last_image_id')
    
    def set_last_image_id(self, image_id: str):
        """最後に表示していた画像IDを保存"""
        if 'character_display' not in self.settings:
            self.settings['character_display'] = {}
        
        self.settings['character_display']['last_image_id'] = image_id
        self.save_settings()
    
    def get_last_live2d_id(self) -> Optional[str]:
        """最後に表示していたLive2DモデルIDを取得"""
        return self.settings.get('character_display', {}).get('last_live2d_id')
    
    def set_last_live2d_id(self, model_id: str):
        """最後に表示していたLive2DモデルIDを保存"""
        if 'character_display' not in self.settings:
            self.settings['character_display'] = {}
        
        self.settings['character_display']['last_live2d_id'] = model_id
        self.save_settings()
    
    def is_image_mode(self) -> bool:
        """画像表示モードかどうか"""
        return self.get_display_mode() == 'image'
    
    def is_live2d_mode(self) -> bool:
        """Live2D表示モードかどうか"""
        return self.get_display_mode() == 'live2d'