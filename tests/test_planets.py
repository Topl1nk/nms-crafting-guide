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


def test_only_the_players_own_finds_count() -> None:
    records = [
        _record("Planet", HOME, ts=300, name="Home"),
        _record("Flora", HOME, ts=400),
        _record("Animal", HOME, ts=350),
        _record("Mineral", HOME + (1 << 52), ts=10),  # a mineral on the next planet makes that planet visited too
        _record("Planet", HOME + (2 << 52), owner="someone else"),  # a planet only someone else found
        _record("SolarSystem", HOME & ~(0xF << 52), name="Sol"),
    ]
    found = nms_save.planets(_save(records), ME)
    assert [p["code"] for p in found] == ["415E00A24EA9", "515E00A24EA9"]  # latest activity first
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


def test_planet_zero_is_no_body_and_gets_no_generated_name() -> None:
    pytest.importorskip("numpy")
    found = nms_save.planets(_save([_record("Flora", IBOSON & ~(0xF << 52))]), ME)  # a base can sit at planet 0
    assert (found[0]["name"], found[0]["name_source"]) == ("", "")
    assert found[0]["system_name_source"] == "generated"


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
