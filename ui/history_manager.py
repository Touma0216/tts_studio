from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


class ParameterHistory:
    """状態辞書を保持する共通履歴管理クラス（最大20段・Undo/Redo対応）。"""

    def __init__(self, max_history: int = 20) -> None:
        self.history_stack: list[Dict[str, Any]] = []
        self.current_index: int = -1
        self.max_history = max_history
        self.is_undoing = False

    def save_current_state(self, parameters: Optional[Dict[str, Any]]) -> None:
        """現在の状態を履歴に保存する。"""
        if parameters is None or self.is_undoing:
            return

        snapshot = deepcopy(parameters)

        if self.current_index < len(self.history_stack) - 1:
            self.history_stack = self.history_stack[: self.current_index + 1]

        self.history_stack.append(snapshot)
        self.current_index = len(self.history_stack) - 1

        if len(self.history_stack) > self.max_history:
            self.history_stack.pop(0)
            self.current_index -= 1

    def get_previous_state(self) -> Optional[Dict[str, Any]]:
        if not self.has_undo_available():
            return None
        self.current_index -= 1
        return deepcopy(self.history_stack[self.current_index])

    def get_next_state(self) -> Optional[Dict[str, Any]]:
        if not self.has_redo_available():
            return None
        self.current_index += 1
        return deepcopy(self.history_stack[self.current_index])

    def has_undo_available(self) -> bool:
        return self.current_index > 0

    def has_redo_available(self) -> bool:
        return self.current_index < len(self.history_stack) - 1

    def clear_history(self) -> None:
        self.history_stack.clear()
        self.current_index = -1

    def set_undoing_flag(self, flag: bool) -> None:
        self.is_undoing = flag