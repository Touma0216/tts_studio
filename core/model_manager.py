import os
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

class ModelManager:
    def __init__(self, config_file="model_history.json"):
        self.config_file = config_file
        self.models: List[Dict] = []
        self.load_history()

    # ---------- 内部ユーティリティ ----------
    def _pretty_default_name(self, model_path: str) -> str:
        """既定表示名：親フォルダ名。無ければファイル名から学習トークンを除去。"""
        parent = os.path.basename(os.path.dirname(model_path)) or ""
        if parent and parent not in (".", "/"):
            return parent
        stem = Path(model_path).stem
        # 末尾の e30_s300 / -e30-s300 / _e30 等を除去
        stem = re.sub(r'([_-]?e\d+([_-]?s\d+)?)$', "", stem, flags=re.IGNORECASE).strip("_- ")
        return stem or "model"

    def _generate_model_id(self, model_path: str) -> str:
        """モデルパスからユニークIDを生成"""
        import hashlib
        return hashlib.md5(model_path.encode()).hexdigest()[:12]

    def _normalize_names(self) -> bool:
        """既存履歴の名前や欠落フィールドを正規化。変更があれば True。"""
        changed = False
        for m in self.models:
            desired = self._pretty_default_name(m.get("model_path", ""))
            current = (m.get("name") or "").strip()
            # ファイル名に学習トークンが残ってたら除去
            cleaned = re.sub(r'([_-]?e\d+([_-]?s\d+)?)$', "", current, flags=re.IGNORECASE).strip("_- ")
            candidate = (os.path.basename(os.path.dirname(m.get("model_path",""))) or "").strip() or cleaned
            candidate = candidate or desired
            if candidate and candidate != current:
                m["name"] = candidate
                changed = True
            # note が無ければ初期化
            if "note" not in m:
                m["note"] = ""
                changed = True
        return changed

    # ---------- I/O ----------
    def load_history(self):
        """履歴ファイルから読み込み"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.models = data.get('models', [])
            except Exception:
                self.models = []
        else:
            self.models = []

        # 1回だけ正規化（必要時のみ保存）
        if self._normalize_names():
            self.save_history(quiet=True)

    def save_history(self, quiet: bool = True):
        """履歴ファイルに保存（quiet=True でログ抑制）"""
        try:
            data = {'models': self.models}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if not quiet:
                pass
        except Exception as e:
            print(f"履歴保存エラー: {e}")

    # ---------- CRUD ----------
    def add_model(self, model_path: str, config_path: str, style_path: str, custom_name: Optional[str] = None) -> str:
        """新しいモデルを履歴に追加（既存なら先頭に移動のみ）"""
        model_id = self._generate_model_id(model_path)
        existing = self.get_model_by_id(model_id)
        if existing:
            # 既存を先頭に持ってくるだけ
            self.models.remove(existing)
            self.models.insert(0, existing)
            self.save_history(quiet=True)
            return model_id

        model_name = custom_name or self._pretty_default_name(model_path)
        entry = {
            'id': model_id,
            'name': model_name,
            'note': "",
            'model_path': model_path,
            'config_path': config_path,
            'style_path': style_path,
        }
        # 最新を先頭に
        self.models.insert(0, entry)
        # 最大20件
        if len(self.models) > 20:
            self.models = self.models[:20]
        self.save_history(quiet=True)
        return model_id

    def get_model_by_id(self, model_id: str) -> Optional[Dict]:
        for m in self.models:
            if m['id'] == model_id:
                return m
        return None

    def get_all_models(self) -> List[Dict]:
        return self.models.copy()

    def update_model_name(self, model_id: str, new_name: str) -> bool:
        m = self.get_model_by_id(model_id)
        if not m:
            return False
        m['name'] = new_name
        self.save_history(quiet=True)
        return True

    def update_note(self, model_id: str, note: str) -> bool:
        m = self.get_model_by_id(model_id)
        if not m:
            return False
        m['note'] = note
        self.save_history(quiet=True)
        return True

    def remove_model(self, model_id: str) -> bool:
        before = len(self.models)
        self.models = [m for m in self.models if m['id'] != model_id]
        changed = len(self.models) != before
        if changed:
            self.save_history(quiet=True)
        return changed

    # ---------- ユーティリティ ----------
    def validate_model_files(self, model_entry: Dict) -> bool:
        paths = [model_entry['model_path'], model_entry['config_path'], model_entry['style_path']]
        return all(os.path.exists(p) for p in paths)
