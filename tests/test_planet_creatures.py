"""The fauna level of a planet against the game's own routine (0x16d6050, run in an emulator over a running game): after the game has
chosen the creature kinds of the planet it may lower the level stage A drew. tests/fixtures/planet_creatures.json: for each planet the
level before, the level after and the fauna word the game made of it."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "desktop"))
sys.path.insert(0, str(ROOT / "third_party" / "nms_namegen"))

import planet_data  # noqa: E402
import planet_gen  # noqa: E402

PLANETS = json.loads((ROOT / "tests" / "fixtures" / "planet_creatures.json").read_text(encoding="utf-8"))


def test_fauna_level_matches_the_game() -> None:
    assert len(PLANETS) > 100 and sum(p["before"] != p["final"] for p in PLANETS) > 5
    for p in PLANETS:
        body = planet_gen.bodies(int(p["ua"], 16))[p["index"]]
        ground = planet_data.terrain(body.seed, body, body.star)
        assert planet_data.fauna_level(body.seed, body, p["before"], ground) == p["final"], (p["ua"], p["index"])


def test_fauna_word_matches_the_game() -> None:
    for p in PLANETS:
        body = planet_gen.bodies(int(p["ua"], 16))[p["index"]]
        got = planet_data.describe(body, 2, 1)
        assert got["fauna"] == p["word"], (p["ua"], p["index"])
