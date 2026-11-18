"""The resource list of a planet against the game's own routines (tests/fixtures/planet_resources.json: planets the game's whole planet
generator, 0x16c59b0, was run on in an emulator over a running game, with the ordinary game mode and the sentinel setting "Normal").

For each: the descriptor flags of the system (the planet is a prime planet or moon, the system has no race), the terrain stage (size class
of the terrain, water, hazards), the scrap flag, and the hints the lists of objects add (ancient bones, salvage, plants, bugs, swarm debris).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "desktop"))
sys.path.insert(0, str(ROOT / "third_party" / "nms_namegen"))

import planet_data  # noqa: E402
import planet_gen  # noqa: E402

PLANETS = json.loads((ROOT / "tests" / "fixtures" / "planet_resources.json").read_text(encoding="utf-8"))


def _body(p: dict) -> planet_gen.Body:
    return planet_gen.bodies(int(p["ua"], 16))[p["index"]]


def test_system_flags_match_the_game() -> None:
    assert len(PLANETS) > 100
    for p in PLANETS:
        body = _body(p)
        assert (int(body.extra), int(body.empty)) == (p["extra"], p["empty"]), p["ua"]


def test_terrain_matches_the_game() -> None:
    for p in PLANETS:
        body = _body(p)
        got = planet_data.terrain(body.seed, body, body.star)
        assert (got["size_index"], got["water"], int(got["hazard"])) == (p["size_index"], p["water"], p["hazard"]), (p["ua"], p["index"])


def test_hints_match_the_game() -> None:
    assert sum("UI_BONES_HINT" in p["hints"] for p in PLANETS) > 10
    for p in PLANETS:
        body = _body(p)
        got = planet_data.describe(body, 2, 1)
        assert got["hints"] == p["hints"], (p["ua"], p["index"])
        assert got["scrap"] == bool(p["scrap"]), (p["ua"], p["index"])
