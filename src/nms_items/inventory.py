"""Persistent inventory: what you are actually carrying.

Stored as {item_id: count} in the XDG state dir, so it survives between runs and
stays out of the repo.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def state_path() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")
    return Path(base) / "nms-items" / "inventory.json"


class Inventory:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or state_path()
        self.items: dict[str, int] = {}
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return
        if isinstance(raw, dict):
            self.items = {str(k): int(v) for k, v in raw.items() if int(v) > 0}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.items, indent=1, sort_keys=True))

    def set(self, item_id: str, count: int) -> None:
        if count > 0:
            self.items[item_id] = count
        else:
            self.items.pop(item_id, None)
        self.save()

    def add(self, item_id: str, count: int) -> int:
        total = max(0, self.items.get(item_id, 0) + count)
        self.set(item_id, total)
        return total

    def clear(self) -> None:
        self.items = {}
        self.save()

    def __contains__(self, item_id: object) -> bool:
        return item_id in self.items

    def __len__(self) -> int:
        return len(self.items)
