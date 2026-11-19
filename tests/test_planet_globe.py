"""The colours and layers of a planet's globe against the game's own routine (the planet routine 0x16c44c0, run in an emulator over a running
game): the terrain colour (a gas giant's colour), the water setting and its colour, whether the planet has a sea and how thick its clouds
are; and which body of a system has rings (the orbit code 0x1683ec0).
tests/fixtures/planet_globe.json, planet_rings.json: for each planet / system what the game made."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "desktop"))
sys.path.insert(0, str(ROOT / "third_party" / "nms_namegen"))

import planet_gen  # noqa: E402
import planet_globe  # noqa: E402

PLANETS = json.loads((ROOT / "tests" / "fixtures" / "planet_globe.json").read_text(encoding="utf-8"))
RINGS = json.loads((ROOT / "tests" / "fixtures" / "planet_rings.json").read_text(encoding="utf-8"))
near = lambda a, b: all(abs(x - y) < 2e-6 for x, y in zip(a, b))


def test_globe_colours_match_the_game() -> None:
    assert len(PLANETS) > 300 and len({p["biome"] for p in PLANETS}) > 10
    for p in PLANETS:
        body = planet_gen.bodies(int(p["ua"], 16))[p["index"]]
        assert body.biome == p["biome"]
        if body.biome == 15:  # a gas giant: the colour of its atmosphere
            assert near(planet_globe.gas_colour(body.seed), p["terrain"]), (p["ua"], p["index"])
            continue
        assert near(planet_globe.terrain_colour(body), p["terrain"]), (p["ua"], p["index"])
        setting = planet_globe.water_setting(body.seed)
        assert setting == p["water_setting"], (p["ua"], p["index"])
        assert near(planet_globe.water_colour(setting), p["water_colour"]), (p["ua"], p["index"])
        spec = planet_globe.spec(body)
        assert (spec["water"] is not None) == (p["water"] > 0) and abs(spec["clouds"][1] - p["cloud"]) < 1e-6, (p["ua"], p["index"])


def test_ring_planet_matches_the_game() -> None:
    assert len(RINGS) > 100
    for s in RINGS:
        assert planet_gen.ring_body(int(s["ua"], 16)) == s["ring"], s["ua"]
