"""The names the game makes up for systems and planets: third_party/nms_namegen (MIT, copied as it is) against its own reference
vectors, and against names read out of a real save."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("numpy")  # nms_namegen needs it; the desktop build installs it (desktop/requirements.txt)

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "third_party" / "nms_namegen"
sys.path.insert(0, str(PACKAGE))

sys.path.insert(0, str(ROOT / "desktop"))

import word_filter  # noqa: E402
from nms_namegen import planet as planet_module, region as region_module, system as system_module  # noqa: E402
from nms_namegen.planet import planetName, planetSeed  # noqa: E402
from nms_namegen.region import regionName  # noqa: E402
from nms_namegen.system import planetSeeds, systemName  # noqa: E402


def _u64(n: int) -> int:
    return n & 0xFFFFFFFFFFFFFFFF  # the vectors keep seeds as signed 64-bit numbers


@pytest.fixture
def as_published():
    """nms_namegen without the game's word filter that desktop/nms_save.py adds (desktop/word_filter.py): its reference vectors
    pin the library's own output, which has no filter."""
    modules = (planet_module, system_module, region_module)
    word_filter.unpatch(*modules)
    yield
    word_filter.patch(*modules)


def test_the_reference_vectors_of_nms_namegen_all_come_out_the_same(as_published) -> None:
    cases =json.loads((PACKAGE / "test" / "fixtures" / "golden_vectors.json").read_text(encoding="utf-8"))
    assert len(cases) == 443
    wrong = []
    for rec in cases:
        code, galaxy = rec["code"], rec["galaxy"]
        found = planetSeeds(code, galaxy)
        if regionName(code, galaxy) != rec["region"]:
            wrong.append(("region", code, galaxy))
        if systemName(code, galaxy) != rec["system"]:
            wrong.append(("system", code, galaxy))
        if not str(rec["planet"]).startswith("ERR:") and planetName(code, galaxy) != rec["planet"]:
            wrong.append(("planet", code, galaxy))
        if ([_u64(s) for s in found["planet_seeds"]], found["planet_count"], found["moon_count"]) != (
                [_u64(s) for s in rec["seeds"]], rec["planet_count"], rec["moon_count"]):
            wrong.append(("seeds", code, galaxy))
    assert not wrong, wrong[:10]


# Names a real save holds for these addresses (a discovery uploaded under the name the game made up); the portal code is read as
# a number, the galaxy counts from 0.
@pytest.mark.parametrize("code, galaxy, name", [
    (0x011D024BCAD3, 0, "Shvald III"),
    (0x00F5024BCAD3, 0, "Orgiyevsk"),
    (0x0079FC6A7FEA, 0, "Ibosoniec"),
    (0x002D024BCAD3, 0, "Gobuzh"),
])
def test_system_names_read_back_from_a_real_save(code: int, galaxy: int, name: str) -> None:
    assert systemName(code, galaxy) == name


def test_a_planet_name_from_its_seed_and_from_its_address_agree() -> None:
    # Ilus IX: the seed is what the save's discovery record holds (DD.VP[0]), the address the planet's portal code
    assert planetName(0x3E851C2217BAF847) == "Ilus IX"
    assert planetName(planetSeed(0x200203F897FF, 7)) == "Ilus IX"
    assert planetName(0x200203F897FF, 7) == "Ilus IX"


def test_the_letter_table_is_in_the_package_the_build_bundles() -> None:
    assert (PACKAGE / "nms_namegen" / "letter_map.json").is_file()
    spec = (ROOT / "desktop" / "nms-crafting-guide.spec").read_text(encoding="utf-8")
    assert "letter_map.json" in spec and "numpy" in (ROOT / "desktop" / "requirements.txt").read_text(encoding="utf-8")
