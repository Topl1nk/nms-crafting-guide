"""Game ids for the English names the guides use.

The tests quote items the way the written guides do ("Chromatic Metal"), but the
data may be in any of the game's languages, where that name is different. The
ids never change, so the tests go through this table (fixtures/english_ids.json,
read once from the English data) and compare ids.
"""

from __future__ import annotations

import json
from pathlib import Path

_IDS: dict[str, list[str]] = json.loads(
    (Path(__file__).parent / "fixtures" / "english_ids.json").read_text(encoding="utf-8"))


def ids(name: str) -> list[str]:
    """Every item the guides mean by this name (four grades of a module share one)."""
    return _IDS[name]


def one(name: str) -> str:
    """The item for a name that means exactly one."""
    found = _IDS[name]
    assert len(found) == 1, (name, found)
    return found[0]


def all_of(names: str) -> set[str]:
    """Ids for a comma-separated list of names."""
    return {i for n in names.split(", ") for i in ids(n.strip())}
