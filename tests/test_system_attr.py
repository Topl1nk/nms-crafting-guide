"""desktop/system_attr.py against the game's own routine (0x1354ac0, run in an emulator over a running game): 400 random systems."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "desktop"))
sys.path.insert(0, str(ROOT / "third_party" / "nms_namegen"))

import system_attr  # noqa: E402

SYSTEMS = json.loads((ROOT / "tests" / "fixtures" / "system_attr.json").read_text(encoding="utf-8"))


def test_system_attributes_match_the_game() -> None:
    assert len(SYSTEMS) == 400
    for s in SYSTEMS:
        want = {k: v for k, v in s.items() if k != "ua"}
        assert system_attr.attributes(int(s["ua"], 16)) == want, s["ua"]
