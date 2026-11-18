"""The number of creature roles of a planet against the game's own routine (0x16d6050, run in an emulator over a running game): the length
of the planet's creature list, which the Discoveries page counts its fauna out of. tests/fixtures/planet_roles.json: for each planet the
count the game made."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "desktop"))
sys.path.insert(0, str(ROOT / "third_party" / "nms_namegen"))

import planet_data  # noqa: E402
import planet_gen  # noqa: E402

PLANETS = json.loads((ROOT / "tests" / "fixtures" / "planet_roles.json").read_text(encoding="utf-8"))


def test_creature_total_matches_the_game() -> None:
    assert len(PLANETS) > 300 and len({p["total"] for p in PLANETS}) > 10
    for p in PLANETS:
        body = planet_gen.bodies(int(p["ua"], 16))[p["index"]]
        lv = planet_data.levels(body.seed, body, body.star, body.galaxy, body.index, 2)
        ground = planet_data.terrain(body.seed, body, body.star)
        assert planet_data.creature_total(body.seed, body, lv["fauna"], ground) == p["total"], (p["ua"], p["index"])
