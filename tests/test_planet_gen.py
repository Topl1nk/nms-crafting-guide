"""desktop/planet_gen.py against the game's own solar-system generator.

tests/fixtures/planet_systems.json holds systems the game's routine was run on (scripts/check_planets_against_game.py emulates
NMS.exe over a running game): for each, the seed, size class, biome, variant and start-planet flag of every body.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "desktop"))

import planet_gen  # noqa: E402

SYSTEMS = json.loads((ROOT / "tests" / "fixtures" / "planet_systems.json").read_text(encoding="utf-8"))


def test_bodies_match_what_the_game_made() -> None:
    for system in SYSTEMS:
        got = [[format(b.seed, "x"), b.size, b.biome, b.subtype, int(b.start)] for b in planet_gen.bodies(int(system["ua"], 16))]
        assert got == system["bodies"], system["ua"]


def test_the_fixture_covers_the_variants_and_sizes() -> None:
    bodies = [b for s in SYSTEMS for b in s["bodies"]]
    assert {1, 3, 24, 27} <= {b[3] for b in bodies}        # standard, structure, infested, worlds
    assert {0, 1, 2, 3} <= {b[1] for b in bodies}          # the sizes, moons included
    assert any(b[4] for b in bodies)                        # start planets


# Planets of a real save whose word the game shows (seed, address of the system, planet number, second value of the record's VP,
# the variant the game uses): the generator has to find the planet again and agree on its biome.
KNOWN = [
    (0x557B3D1B13177D2A, 0x600024BCAD3, 2, 5, 21),  # Odale VI, system Sobinsk IX: variant Variant_B
]


@pytest.mark.parametrize(("seed", "system", "number", "vp1", "variant"), KNOWN)
def test_a_planet_is_found_again(seed: int, system: int, number: int, vp1: int, variant: int) -> None:
    body = planet_gen.find(system | number << 52, seed, vp1)
    assert body is not None and body.subtype == variant


def test_a_record_that_disagrees_is_not_answered() -> None:
    address = 0x600024BCAD3 | 2 << 52
    assert planet_gen.find(address, 0x557B3D1B13177D2A, 6) is None   # the biome in the save is another
    assert planet_gen.find(address, 1234, 5) is None                  # the seed is another
    assert planet_gen.find(0x600024BCAD3, 0x557B3D1B13177D2A, 5) is None  # planet number 0 is no body
