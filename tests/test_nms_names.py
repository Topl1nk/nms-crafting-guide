"""The names the game makes up for systems and planets (desktop/nms_names.py), against the reference vectors of nms_namegen
(MIT, see THIRD_PARTY.md) and against names read out of a real save."""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "desktop"))

import nms_names  # noqa: E402


def test_the_reference_vectors_of_nms_namegen_all_come_out_the_same() -> None:
    cases = json.loads((ROOT / "tests" / "fixtures" / "namegen_golden.json").read_text(encoding="ascii"))
    assert len(cases) == 443
    wrong = []
    for rec in cases:
        code, galaxy = rec["code"], rec["galaxy"]
        found = nms_names.planet_seeds(code, galaxy)
        if nms_names.system_name(code, galaxy) != rec["system"]:
            wrong.append(("system", code, galaxy))
        if not str(rec["planet"]).startswith("ERR:") and nms_names.planet_name(nms_names.planet_seed(code, galaxy)) != rec["planet"]:
            wrong.append(("planet", code, galaxy))
        if (found["planet_seeds"], found["planet_count"], found["moon_count"], found["sizes"]) != (
                rec["seeds"], rec["planet_count"], rec["moon_count"], rec["sizes"]):
            wrong.append(("seeds", code, galaxy))
    assert not wrong, wrong[:10]


# Names the game showed for these addresses, as a player's save holds them (the discovery was uploaded under the name the game
# made up); the portal code is read as a number, the galaxy from 0.
@pytest.mark.parametrize("code, galaxy, name", [
    (0x011D024BCAD3, 0, "Shvald III"),
    (0x00F5024BCAD3, 0, "Orgiyevsk"),
    (0x0079FC6A7FEA, 0, "Ibosoniec"),
    (0x002D024BCAD3, 0, "Gobuzh"),
])
def test_system_names_read_back_from_a_real_save(code: int, galaxy: int, name: str) -> None:
    assert nms_names.system_name(code, galaxy) == name


def test_a_planet_name_from_its_seed_and_from_its_address_agree() -> None:
    # Ilus IX: the seed is what the save's discovery record holds, the address the portal code of the planet
    assert nms_names.planet_name(0x3E851C2217BAF847) == "Ilus IX"
    assert nms_names.planet_name(nms_names.planet_seed(0x200203F897FF, 7)) == "Ilus IX"


def test_the_letter_table_stays_small_and_needs_no_numpy() -> None:
    table = ROOT / "data" / "namegen.json.gz"
    assert table.stat().st_size < 500_000  # it ships in the program folder
    data = json.loads(gzip.decompress(table.read_bytes()))
    assert len(data["alphasets"]) == 8 and sorted(data["map"], key=int) == [str(n) for n in range(8)]
    assert "import numpy" not in Path(nms_names.__file__).read_text(encoding="utf-8")  # the build has none
