from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AppSettings:
    """用户偏好，持久化到 ~/.countdown_app/settings.json"""

    window_left: float | None = None
    window_top: float | None = None
    window_width: float | None = None
    window_height: float | None = None
    always_on_top: bool = False
    # 关闭窗口：若已记住则不再询问；is_tray=True 表示隐藏到托盘，False 表示退出
    close_behavior_remembered: bool = False
    close_behavior_is_tray: bool = False

    def has_saved_window_rect(self) -> bool:
        return all(
            v is not None
            for v in (
                self.window_left,
                self.window_top,
                self.window_width,
                self.window_height,
            )
        )


class SettingsStore:
    def __init__(self) -> None:
        self._path = Path.home() / ".countdown_app" / "settings.json"
        self.settings = AppSettings()
        self._load()

    def _load(self) -> None:
        try:
            if not self._path.is_file():
                return
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            # 兼容旧版 close_to_tray 复选框
            if "close_to_tray" in raw and "close_behavior_remembered" not in raw:
                if raw.get("close_to_tray"):
                    raw["close_behavior_remembered"] = True
                    raw["close_behavior_is_tray"] = True
            for k, v in asdict(self.settings).items():
                if k in raw:
                    setattr(self.settings, k, raw[k])
        except (OSError, ValueError, TypeError):
            pass

    def save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(asdict(self.settings), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

    def save_window_rect(self, left: float, top: float, width: float, height: float) -> None:
        self.settings.window_left = float(left)
        self.settings.window_top = float(top)
        self.settings.window_width = float(width)
        self.settings.window_height = float(height)
        self.save()
