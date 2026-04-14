from __future__ import annotations

import json
from pathlib import Path

from countdown_app.timer_engine import MAX_TOTAL_SECONDS

MAX_RECENTS = 30


def _hms_total(h: int, m: int, s: int) -> int:
    return h * 3600 + m * 60 + s


class RecentsStore:
    """将成功开始过的时长（时/分/秒）持久化到用户目录，供「最近」一键填入。"""

    def __init__(self) -> None:
        self._path = Path.home() / ".countdown_app" / "recents.json"
        self._items: list[tuple[int, int, int]] = []
        self._load()

    def _load(self) -> None:
        try:
            if self._path.is_file():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                raw = data.get("recents", [])
                out: list[tuple[int, int, int]] = []
                for x in raw:
                    if isinstance(x, (list, tuple)) and len(x) == 3:
                        h, m, s = (int(x[0]), int(x[1]), int(x[2]))
                        out.append((h, m, s))
                self._items = out
        except (OSError, ValueError, TypeError):
            self._items = []

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"recents": [list(t) for t in self._items]}
            self._path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def remember(self, h: int, m: int, s: int) -> None:
        total = _hms_total(h, m, s)
        if total <= 0 or total > MAX_TOTAL_SECONDS:
            return
        tup = (h, m, s)
        self._items = [x for x in self._items if _hms_total(*x) != total]
        self._items.insert(0, tup)
        self._items = self._items[:MAX_RECENTS]
        self._save()

    def remember_from_total_seconds(self, total: int) -> None:
        total = max(0, int(total))
        if total <= 0:
            return
        h, r = divmod(total, 3600)
        m, s = divmod(r, 60)
        self.remember(h, m, s)

    def most_recent(self) -> tuple[int, int, int] | None:
        return self._items[0] if self._items else None
