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
    assert found[1]["name"] == "" and found[1]["minerals"] == 1


def test_a_base_makes_its_planet_visited() -> None:
    base = {"GalacticAddress": hex(HOME), "Name": "Camp", "Owner": {"UID": ME}, "LastUpdateTimestamp": 7}
    theirs = {"GalacticAddress": HOME + (1 << 52), "Name": "Theirs", "Owner": {"UID": "other"}}
    found = nms_save.planets(_save([], [base, theirs]), ME)
    assert [(p["code"], p["bases"]) for p in found] == [("415E00A24EA9", ["Camp"])]


def test_a_save_without_discoveries_has_no_planets() -> None:
    assert nms_save.planets({"BaseContext": {"PlayerStateData": {}}}, ME) == []
