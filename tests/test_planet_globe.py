"""The colours of a planet's globe against the game's own routine (the planet routine 0x16c44c0, run in an emulator over a running game):
the terrain colour, the water setting and its colour, whether the planet has a sea and how thick its clouds are.
tests/fixtures/planet_globe.json: for each planet what the game made."""

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


def test_globe_colours_match_the_game() -> None:
    assert len(PLANETS) > 300 and len({p["biome"] for p in PLANETS}) > 8
    for p in PLANETS:
        body = planet_gen.bodies(int(p["ua"], 16))[p["index"]]
        assert (body.biome,) == (p["biome"],)
        near = lambda a, b: all(abs(x - y) < 2e-6 for x, y in zip(a, b))
        assert near(planet_globe.terrain_colour(body), p["terrain"]), (p["ua"], p["index"])
        setting = planet_globe.water_setting(body.seed)
        assert setting == p["water_setting"], (p["ua"], p["index"])
        assert near(planet_globe.water_colour(setting), p["water_colour"]), (p["ua"], p["index"])
        spec = planet_globe.spec(body)
        assert (spec["water"] is not None) == (p["water"] > 0) and abs(spec["clouds"][1] - p["cloud"]) < 1e-6, (p["ua"], p["index"])
