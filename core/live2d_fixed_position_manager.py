import json
from pathlib import Path
from typing import Any, Dict, Optional


class Live2DFixedPositionManager:
    """Live2Dモデルの定位置設定を管理する"""

    def __init__(self, config_file: str = "live2d_fixed_positions.json") -> None:
        self.config_path = Path(config_file)
        self._data: Dict[str, Any] = {"models": []}
        self._load()

    def _load(self) -> None:
        if not self.config_path.exists():
            self._data = {"models": []}
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    models = data.get("models", [])
                    if isinstance(models, list):
                        self._data = {**data, "models": models}
                        return
        except Exception as exc:  # pragma: no cover - ログのみ
            print(f"⚠️ 定位置設定の読み込みに失敗しました: {exc}")

        # フォーマット不正時は空データとして扱う
        self._data = {"models": []}

    def reload(self) -> None:
        """設定ファイルを再読み込み"""
        self._load()

    @staticmethod
    def _normalize_path(path: Optional[str]) -> Optional[str]:
        if path is None:
            return None
        return str(path).replace("\\", "/").strip().lower()

    def _match_entry(
        self,
        entry: Dict[str, Any],
        *,
        model_id: Optional[str],
        model_folder_path: Optional[str],
        model_name: Optional[str],
    ) -> bool:
        if not isinstance(entry, dict):
            return False

        entry_id = entry.get("id")
        if model_id and entry_id and str(entry_id) == str(model_id):
            return True

        entry_path = self._normalize_path(entry.get("model_folder_path"))
        target_path = self._normalize_path(model_folder_path)
        if target_path and entry_path and entry_path == target_path:
            return True

        entry_name = entry.get("name")
        if model_name and entry_name and str(entry_name) == str(model_name):
            return True

        return False

    def get_fixed_settings(
        self,
        *,
        model_id: Optional[str] = None,
        model_folder_path: Optional[str] = None,
        model_name: Optional[str] = None,
        reload: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """条件に一致する定位置設定を取得"""
        if reload:
            self.reload()

        models = self._data.get("models", [])
        if not isinstance(models, list):
            return None

        # 優先度: id -> パス -> 名前
        # 先にIDで一致するものを検索
        if model_id:
            for entry in models:
                if self._match_entry(entry, model_id=model_id, model_folder_path=None, model_name=None):
                    settings = entry.get("ui_settings")
                    return dict(settings) if isinstance(settings, dict) else None

        for entry in models:
            if self._match_entry(
                entry,
                model_id=None,
                model_folder_path=model_folder_path,
                model_name=None,
            ):
                settings = entry.get("ui_settings")
                return dict(settings) if isinstance(settings, dict) else None

        for entry in models:
            if self._match_entry(entry, model_id=None, model_folder_path=None, model_name=model_name):
                settings = entry.get("ui_settings")
                return dict(settings) if isinstance(settings, dict) else None

        return None

    def has_fixed_settings(
        self,
        *,
        model_id: Optional[str] = None,
        model_folder_path: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> bool:
        return self.get_fixed_settings(
            model_id=model_id,
            model_folder_path=model_folder_path,
            model_name=model_name,
            reload=True,
        ) is not None
