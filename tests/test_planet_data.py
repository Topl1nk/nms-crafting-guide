"""desktop/planet_data.py against the game's own routines (stage A, the weather, the texts).

tests/fixtures/planet_data.json holds planets the game's routines were run on (scripts/check_planets_against_game.py --data emulates
NMS.exe over a running game in the ordinary game mode with the sentinel setting "Normal"): for each, what goes in (seed, biome, variant,
size, whether it is the start planet, star colour, galaxy, number in the system) and what the game made of it. Fauna is not part of
it: the game changes the level after stage A in a routine that is not ported.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "desktop"))

import planet_data  # noqa: E402
import planet_gen  # noqa: E402

PLANETS = json.loads((ROOT / "tests" / "fixtures" / "planet_data.json").read_text(encoding="utf-8"))


def _body(p: dict) -> planet_gen.Body:
    return planet_gen.Body(int(p["seed"], 16), p["size"], -1, p["biome"], p["subtype"], bool(p["start"]), star=p["star"], index=p["index"], galaxy=p["galaxy"])


def test_levels_match_the_game() -> None:
    for p in PLANETS:
        body = _body(p)
        got = planet_data.levels(body.seed, body, p["star"], p["galaxy"], p["index"])
        want = p["levels"]
        assert {k: got[k] for k in want} == want, p["seed"]


def test_texts_match_the_game() -> None:
    for p in PLANETS:
        body = _body(p)
        got = planet_data.describe(body, 2, 1)
        assert got is not None
        want = p["keys"]
        assert {k: got[k] for k in want} == want, p["seed"]


def test_odale_vi() -> None:
    # In the game: "Непрерывная засуха", "Требуют повиновения", flora "Необычная" (RARITY_LOW8)
    body = planet_gen.Body(0x557B3D1B13177D2A, 1, -1, 5, 21, False, star=0, index=1, galaxy=0)
    got = planet_data.describe(body, 2, 1)
    assert (got["weather"], got["sentinels"], got["flora"]) == ("WEATHER_BARREN10", "SENTINEL_DEFAULT5", "RARITY_LOW8")


def test_no_answer_where_the_rules_are_not_ported() -> None:
    body = planet_gen.Body(1, 1, -1, 5, 1, False)
    assert planet_data.describe(body, 2, 0) is None   # the game mode 0: extra rules
    assert planet_data.describe(body, 2, 6) is None
    assert planet_data.describe(body, None, 1) is None  # the sentinel setting is not known
