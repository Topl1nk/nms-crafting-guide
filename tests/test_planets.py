"""The planets the save lists (desktop/nms_save.py planets): which are the player's, and how their addresses read."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("lz4")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "desktop"))

import nms_save  # noqa: E402

ME = "7656"


def _record(kind: str, ua: int, owner: str = ME, ts: int = 100, name: str = "") -> dict:
    return {"DD": {"UA": ua, "DT": kind, "VP": []}, "DM": {"CN": name} if name else {},
            "OWS": {"UID": owner, "LID": owner, "TS": ts}}


def _save(records: list[dict], bases: list[dict] | None = None) -> dict:
    return {"BaseContext": {"PlayerStateData": {"PersistentPlayerBases": bases or []}},
            "DiscoveryManagerData": {"DiscoveryData-v1": {"Store": {"Record": records}}}}


# planet 4 of system 0x15E, y 0, z 0xA24, x 0xEA9, in the first galaxy: the save's own current address
HOME = 0x415E0000A24EA9


def test_address_fields_read_back_as_the_portal_code() -> None:
    place = nms_save._place(HOME)
    assert place == {"galaxy": 1, "planet": 4, "system": 0x15E, "code": "415E00A24EA9"}
    assert nms_save._place(HOME | (5 << 32))["galaxy"] == 6  # the galaxy byte is 0-based


def test_only_the_players_own_finds_count_for_what_was_found_on_a_planet() -> None:
    records = [
        _record("Planet", HOME, ts=300, name="Home"),
        _record("Flora", HOME, ts=400),
        _record("Animal", HOME, ts=350),
        _record("Flora", HOME, owner="someone else"),  # a plant someone else found on it: not counted
        _record("Mineral", HOME + (1 << 52), ts=10),  # a mineral on the next planet makes that planet visited too
        _record("Planet", HOME + (2 << 52), owner="someone else"),  # a planet someone else found, in a system the player has a discovery of
        _record("SolarSystem", HOME & ~(0xF << 52), name="Sol"),
    ]
    found = nms_save.planets(_save(records), ME)
    assert [p["code"] for p in found] == ["415E00A24EA9", "515E00A24EA9", "615E00A24EA9"]  # latest activity first, the others' last
    home = found[0]
    assert (home["name"], home["system_name"], home["found"], home["seen"]) == ("Home", "Sol", 300, 400)
    assert (home["flora"], home["fauna"], home["minerals"]) == (1, 1, 0)
    assert found[1]["minerals"] == 1
    assert home["name_source"] == "save" and home["system_name_source"] == "save"


# Ilus IX, planet 2 of system 0x002 in the galaxy whose byte is 7 (the eighth); its seed is what the save's discovery record
# holds. The other is planet 1 of the system a real save names "Ibosoniec", in Euclid.
ILUS = (2 << 52) | (0x002 << 40) | (7 << 32) | (0x03 << 24) | (0xF89 << 12) | 0x7FF
IBOSON = (1 << 52) | (0x079 << 40) | (0xFC << 24) | (0x6A7 << 12) | 0xFEA


def test_a_planet_the_player_did_not_name_gets_the_name_the_game_made_up() -> None:
    pytest.importorskip("numpy")  # nms_namegen needs it
    planet = _record("Planet", ILUS)
    planet["DD"]["VP"] = ["0x3E851C2217BAF847", 0]
    flora = _record("Flora", IBOSON)  # no planet record: the seed is worked out from the address
    found = {p["code"]: p for p in nms_save.planets(_save([planet, flora]), ME)}
    ilus = found["200203F897FF"]
    assert (ilus["name"], ilus["name_source"]) == ("Ilus IX", "generated")
    other = found["1079FC6A7FEA"]
    assert (other["system_name"], other["system_name_source"]) == ("Ibosoniec", "generated")
    assert other["name_source"] == "generated" and other["name"]


def test_a_systems_name_is_not_given_to_other_systems_with_the_same_index() -> None:
    # the system index (here 0x15E) is shared by thousands of systems: only the one at the same voxel is the named system
    elsewhere = HOME + 0x10  # the same index, another x
    records = [_record("Planet", HOME), _record("Planet", elsewhere),
               _record("SolarSystem", HOME & ~(0xF << 52), name="Sol")]
    found = {p["code"]: p for p in nms_save.planets(_save(records), ME)}
    assert found["415E00A24EA9"]["system_name"] == "Sol"
    assert found["415E00A24EB9"]["system_name"] != "Sol"


def test_planets_others_found_are_listed_whoever_found_them_and_wherever() -> None:
    other = "7657"
    beside = _record("Planet", HOME + (1 << 52), owner=other)  # planet 5 of a system the player has no discovery of
    away = _record("Planet", HOME + (1 << 40), owner=other)    # a planet of another system
    found = nms_save.planets(_save([beside, away]), ME)
    assert sorted(p["code"] for p in found) == ["415F00A24EA9", "515E00A24EA9"]


def test_the_planet_the_player_stands_on_is_listed_even_if_nothing_was_scanned() -> None:
    here = {"RealityIndex": 0, "GalacticAddress": {"VoxelX": -343, "VoxelY": 0, "VoxelZ": -1500, "SolarSystemIndex": 350, "PlanetIndex": 4}}
    assert nms_save._pack(here) == HOME  # the same number as the save's own record of that planet
    save = _save([])
    save["BaseContext"]["PlayerStateData"].update({"UniverseAddress": here, "TimeStamp": 777})
    found = nms_save.planets(save, ME)
    assert [(p["code"], p["seen"]) for p in found] == [("415E00A24EA9", 777)]
    here["GalacticAddress"]["PlanetIndex"] = 0  # in a system's space, not on a planet
    assert nms_save.planets(save, ME) == []


def test_the_name_parts_put_together_give_the_name() -> None:
    pytest.importorskip("numpy")
    planet, _ = nms_save._namegen()
    seen = set()
    for n in range(1, 600):
        seed = n * 0x9E3779B97F4A7C15 & (2**64 - 1)
        parts = nms_save._planet_name_parts(planet, seed)
        template = planet.styles[10 if parts["style"] == 10 else parts["style"] - 1]  # nms_namegen keeps a placeholder at 9
        text = template.replace("%ADORNMENT%", planet.adornments[parts["adorn"] - 1])
        for key in ("PROCNORM", "PROCSHORT", "PROCLONG", "SHORTCODE", "NUMERAL", "LONGCODE"):
            text = text.replace(f"%{key}%", parts[key])
        assert text == planet.planetName(seed), (hex(seed), text)
        seen.add(parts["style"])
    assert {1, 2, 3, 4, 5, 6, 7, 8, 9, 10} - seen <= {10}  # every template turns up (the last is rare)


def test_the_name_is_the_one_the_game_shows_after_its_word_filter() -> None:
    pytest.importorskip("numpy")
    # Sobinsk IX 2, shown in the game as "Odale VI". One of the words made up for it ("eomititu") holds "tit", which the game's
    # filter changes, spending a random number the name's template is drawn after (desktop/word_filter.py).
    ua = (2 << 52) | (6 << 40) | 0x024BCAD3  # planet 2 of system 6, y 2, z 0x4BC, x 0xAD3
    found = nms_save.planets(_save([_typed(ua, [0x557B3D1B13177D2A, 5])]), ME)
    assert found[0]["name"] == "Odale VI"


def test_planet_zero_is_the_system_and_not_listed() -> None:
    base = {"Name": "", "Owner": {"UID": ME}, "GalacticAddress": IBOSON & ~(0xF << 52), "LastUpdateTimestamp": 5}
    found = nms_save.planets(_save([_record("Flora", IBOSON & ~(0xF << 52))], [base]), ME)  # a base can sit at planet 0
    assert found == []


def _typed(ua: int, vp: list, owner: str = ME) -> dict:
    record = _record("Planet", ua, owner=owner)
    record["DD"]["VP"] = vp
    return record


def test_the_planet_type_is_read_from_the_discovery_record() -> None:
    plain = HOME  # planet 4
    flagged = HOME + (1 << 52)  # planet 5: the bits above the low 16 are not part of the type
    swamp = HOME + (2 << 52)
    test_biome = HOME + (3 << 52)  # 11 is the game's test biome, not shown
    beyond = HOME + (4 << 52)  # a number the table of types does not have
    short = HOME + (5 << 52)  # a record with no second value
    none = HOME + (6 << 52)  # no record of the planet at all: only a plant found there
    other = HOME + (7 << 52)  # a planet only someone else found still tells its type
    records = [_typed(plain, ["0x1", 2]), _typed(flagged, ["0x1", 0x10001]), _typed(swamp, ["0x1", 12]), _typed(test_biome, ["0x1", 11]),
               _typed(beyond, ["0x1", 99]), _typed(short, ["0x1"]), _record("Flora", none), _typed(other, ["0x1", "0x4"], owner="x"),
               _record("Flora", other)]
    found = {p["planet"]: p["biome"] for p in nms_save.planets(_save(records), ME)}
    assert found == {4: "Scorched", 5: "Toxic", 6: "Swamp", 7: "", 8: "", 9: "", 10: "", 11: "Frozen"}


def test_a_name_in_the_save_is_kept_and_marked() -> None:
    found = nms_save.planets(_save([_record("Planet", ILUS, name="My Rock"), _record("SolarSystem", ILUS, name="My Sun")]), ME)
    assert (found[0]["name"], found[0]["name_source"], found[0]["system_name"], found[0]["system_name_source"]) == (
        "My Rock", "save", "My Sun", "save")


def test_a_base_makes_its_planet_visited() -> None:
    base = {"GalacticAddress": hex(HOME), "Name": "Camp", "Owner": {"UID": ME}, "LastUpdateTimestamp": 7}
    theirs = {"GalacticAddress": HOME + (1 << 52), "Name": "Theirs", "Owner": {"UID": "other"}}
    found = nms_save.planets(_save([], [base, theirs]), ME)
    assert [(p["code"], p["bases"]) for p in found] == [("415E00A24EA9", ["Camp"])]


def test_a_save_without_discoveries_has_no_planets() -> None:
    assert nms_save.planets({"BaseContext": {"PlayerStateData": {}}}, ME) == []
