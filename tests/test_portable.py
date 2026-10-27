"""The portable layer on top of NMSii: reading a save, the local window's
server, Russian texts and colours from the extractor, and the wiki export.

tools/ sits beside app/ in the portable folder, so these skip in a plain
checkout of the upstream repository.
"""

from __future__ import annotations

import json
import os
import struct
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT.parent / "tools"
sys.path.insert(0, str(ROOT / "scripts"))

import build_web  # noqa: E402
import extract_game  # noqa: E402

needs_tools = pytest.mark.skipif(not (TOOLS / "nms_save.py").exists(), reason="portable tools/ not beside app/")
if TOOLS.exists():
    sys.path.insert(0, str(TOOLS))


# -- extract_game: colours and languages ---------------------------------------

def test_hex_colour() -> None:
    assert extract_game.hex_colour({"R": "1", "G": "0.5", "B": "0", "A": "1"}) == "#ff8000"
    assert extract_game.hex_colour({"R": 0, "G": 0, "B": 0}) == "#000000"
    # out-of-range floats are clamped, not wrapped
    assert extract_game.hex_colour({"R": "2", "G": "-1", "B": "0.2"}) == "#ff0033"


@pytest.mark.parametrize("bad", [None, {}, {"R": "x", "G": 0, "B": 0}, "red", {"R": 1}])
def test_hex_colour_gives_empty_for_anything_unusable(bad) -> None:
    assert extract_game.hex_colour(bad) == ""


def _tables(monkeypatch, tables: dict[str, list[dict]]) -> list[Path]:
    paths = [Path(f"nms_loc1_{lang}.MBIN") for lang in tables]
    by_name = dict(zip(paths, tables.values()))
    monkeypatch.setattr(extract_game, "parse_mxml", lambda p: (None, {"Table": by_name[p]}))
    return paths


def test_language_english_is_returned_as_is(monkeypatch) -> None:
    monkeypatch.setattr(extract_game, "LANG", "english")
    paths = _tables(monkeypatch, {"english": [{"Id": "A", "English": "Iron"}, {"Id": "B", "English": ""}]})
    assert extract_game.load_language(paths) == {"A": "Iron", "B": ""}


def test_language_translates_but_keeps_empty_english_empty(monkeypatch) -> None:
    # An id with no English text is not a real item (UI strings, hidden rows):
    # a translation for it must not bring it back.
    monkeypatch.setattr(extract_game, "LANG", "russian")
    paths = _tables(monkeypatch, {
        "english": [{"Id": "A", "English": "Iron"}, {"Id": "B", "English": ""}, {"Id": "C", "English": "Zinc"}],
        "russian": [{"Id": "A", "Russian": "Железо"}, {"Id": "B", "Russian": "Призрак"}, {"Id": "C", "Russian": ""}],
    })
    text = extract_game.load_language(paths)
    assert {k: v for k, v in text.items() if not k.startswith("en:")} == {"A": "Железо", "B": "", "C": "Zinc"}  # C falls back to English


def test_language_column_is_found_in_the_games_own_casing(monkeypatch) -> None:
    monkeypatch.setattr(extract_game, "LANG", "english")
    paths = _tables(monkeypatch, {
        "english": [{"Id": "A", "English": "Iron"}],
        "brazilianportuguese": [{"Id": "A", "BrazilianPortuguese": "Ferro"}],
    })
    assert extract_game.load_language(paths, "brazilianportuguese")["A"] == "Ferro"


def test_language_keeps_the_english_text_beside_it(monkeypatch) -> None:
    # The storage rules match English subtitles in every language.
    monkeypatch.setattr(extract_game, "LANG", "russian")
    paths = _tables(monkeypatch, {
        "english": [{"Id": "A", "English": "Iron"}],
        "russian": [{"Id": "A", "Russian": "Железо"}],
    })
    text = extract_game.load_language(paths)
    assert text["A"] == "Железо" and text["en:A"] == "Iron"
    assert extract_game._common({"Subtitle": "A"}, text)["Subtitle_Text_En"] == "Iron"


def test_languages_are_read_from_the_games_archives(monkeypatch) -> None:
    listing = [("a.pak", "language/nms_loc1_russian.mbin"), ("a.pak", "language/nms_loc4_russian.mbin"),
               ("b.pak", "language/nms_loc1_english.mbin"), ("b.pak", "language/nms_loc1_brazilianportuguese.mbin"),
               ("b.pak", "language/nms_loc10_french.mbin"), ("b.pak", "metadata/other.mbin"),
               ("b.pak", "language/readme.txt")]
    monkeypatch.setattr(extract_game, "pak_listing", lambda game: listing)
    # English first, then alphabetical; one entry per language however many tables it has
    assert extract_game.game_languages(Path(".")) == ["english", "brazilianportuguese", "french", "russian"]


# -- build_web ------------------------------------------------------------------

def test_plain_strips_game_markup() -> None:
    assert build_web.plain("<STELLAR>Gold<> is <IMG>BUTTON<> () nice") == "Gold is nice"
    assert build_web.plain("Press <IMG>X<> (<IMG>Y<>)") == "Press"
    assert build_web.plain("no markup") == "no markup"
    assert build_web.plain("a < b") == "a < b"  # a bare "<" is not a tag


def test_wiki_export_is_consistent_with_items() -> None:
    wiki = json.loads((ROOT / "web" / "wiki.json").read_text(encoding="utf-8"))
    data = json.loads((ROOT / "web" / "data.json").read_text(encoding="utf-8"))
    assert set(data["items"]) <= set(wiki), "every item of the app is in the wiki"
    for key, row in wiki.items():
        assert len(row) == 8, key
        assert row[0].strip() and "%" not in row[0], key
        assert row[6] == "" or (len(row[6]) == 7 and row[6][0] == "#"), (key, row[6])
        assert "<" not in row[7] or ">" not in row[7], (key, row[7])
    for key, item in data["items"].items():
        assert item["color"] == wiki[key][6]
        assert item["type"] == wiki[key][2]
        assert item["rar"] == wiki[key][4]


def test_language_files_agree_with_the_data() -> None:
    web = ROOT / "web"
    if not (web / "languages.json").exists():
        pytest.skip("scripts/build_langs.py has not been run")
    listing = json.loads((web / "languages.json").read_text(encoding="utf-8"))
    codes = [x["code"] for x in listing["list"]]
    assert listing["base"] in codes and len(codes) == len(set(codes))
    data = json.loads((web / "data.json").read_text(encoding="utf-8"))
    wiki = json.loads((web / "wiki.json").read_text(encoding="utf-8"))
    ops = {r["op"] for r in data["recipes"]}
    stats = {i["effect_id"] for i in data["items"].values() if i.get("effect_id")}
    for code in codes:
        pack = json.loads((web / "lang" / f"{code}.json").read_text(encoding="utf-8"))
        assert set(pack) == {"items", "ops", "fx"}
        assert set(pack["items"]) == set(wiki), code
        assert all(len(v) == 4 and v[0] for v in pack["items"].values()), code
        assert stats <= {s for s, text in pack["fx"].items() if text}, code
        assert len(ops & set(pack["ops"])) >= 0.95 * len(ops), code
    # the language the data was built in reads back as the data itself
    base = json.loads((web / "lang" / f"{listing['base']}.json").read_text(encoding="utf-8"))
    assert all(base["items"][i][0] == item["name"] for i, item in data["items"].items())
    assert all(base["ops"].get(op, op) == op for op in ops)


# -- nms_save --------------------------------------------------------------------

def _mangle(obj, reverse: dict[str, str]):
    if isinstance(obj, dict):
        return {reverse.get(k, k): _mangle(v, reverse) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_mangle(v, reverse) for v in obj]
    return obj


def _slot(kind: str, item: str, amount: int) -> dict:
    return {"Type": {"InventoryType": kind}, "Id": item, "Amount": amount}


def _write_save(path: Path, state: dict, blocks: int = 2) -> None:
    import lz4.block

    import nms_save

    reverse = {v: k for k, v in nms_save.load_mapping().items()}
    raw = json.dumps(_mangle({"BaseContext": {"PlayerStateData": state}}, reverse), ensure_ascii=False).encode()
    raw += b"\0" * 5  # the game pads the last block
    size = -(-len(raw) // blocks)
    out = b""
    for i in range(0, len(raw), size):
        chunk = raw[i:i + size]
        packed = lz4.block.compress(chunk, store_size=False)
        out += struct.pack("<IIII", nms_save.MAGIC, len(packed), len(chunk), 0) + packed
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out)


STATE = {
    "Inventory": {"Slots": [
        _slot("Substance", "^FUEL1", 100),
        _slot("Substance", "^FUEL1", 50),  # same item in two slots: summed
        _slot("Product", "^TRA_SMALL#9f3a", 3),  # procedural id: the seed is dropped
        _slot("Technology", "^UT_JUMP", 1),  # installed tech is not stock
        _slot("Substance", "^GOLD", 0),  # empty slot
        _slot("Product", "^ПРЕДМЕТ", 5),  # not an id of the game
    ]},
    "FreighterInventory": {"Slots": [_slot("Substance", "^FUEL1", 7)]},
    "Chest2Inventory": {"Slots": [_slot("Product", "^TRA_SMALL", 2)]},
    "ShipOwnership": [{"Name": "Звезда ", "Inventory": {"Slots": [_slot("Substance", "^GOLD", 9)]}},
                      {"Name": "", "Inventory": {"Slots": [_slot("Substance", "^GOLD", 1)]}}],
    "VehicleOwnership": [{"Inventory": {"Slots": []}}],
}


@needs_tools
def test_save_roundtrip_through_several_lz4_blocks(tmp_path) -> None:
    import nms_save

    f = tmp_path / "save.hg"
    _write_save(f, STATE, blocks=3)
    rep = nms_save.report(f)
    assert rep["file"] == "save.hg"
    by_key = {c["key"]: c for c in rep["containers"]}
    assert by_key["suit"]["items"] == {"FUEL1": 150, "TRA_SMALL": 3}
    assert by_key["freighter"]["items"] == {"FUEL1": 7}
    assert by_key["chest1"]["items"] == {"TRA_SMALL": 2}  # Chest2Inventory is index 1
    assert by_key["ship0"]["label"] == "Ship: Звезда"
    assert by_key["ship1"]["label"] == "Ship 2"
    assert "vehicle0" not in by_key and "food" not in by_key  # empty containers are left out
    assert rep["totals"] == {"FUEL1": 157, "TRA_SMALL": 5, "GOLD": 10}


@needs_tools
def test_save_with_unknown_magic_is_refused(tmp_path) -> None:
    import nms_save

    f = tmp_path / "save.hg"
    f.write_bytes(struct.pack("<IIII", 0xDEADBEEF, 1, 1, 0) + b"x")
    with pytest.raises(ValueError, match="unknown save format"):
        nms_save.decode(f)


@needs_tools
def test_demangle_keeps_unknown_keys() -> None:
    import nms_save

    assert nms_save.demangle({"zzz": [{"zzz": 1}]}, {"a": "b"}) == {"zzz": [{"zzz": 1}]}
    assert nms_save.demangle({"a": {"a": 2}}, {"a": "b"}) == {"b": {"b": 2}}


@needs_tools
def test_a_save_with_a_slot_missing_fields_does_not_lose_the_rest(tmp_path) -> None:
    # The game adds fields over time; one odd slot must not blank the whole report.
    import nms_save

    state = {"Inventory": {"Slots": [{"Id": "^GOLD", "Amount": 2}, _slot("Substance", "^GOLD", 4)]}}
    f = tmp_path / "save.hg"
    _write_save(f, state, blocks=1)
    assert nms_save.report(f)["totals"] == {"GOLD": 4}


# -- the local server ---------------------------------------------------------------

@pytest.fixture
def server(tmp_path, monkeypatch):
    import functools

    import launch

    appdata = tmp_path / "appdata"
    _write_save(appdata / "HelloGames" / "NMS" / "st_123" / "save.hg", STATE)
    monkeypatch.setenv("APPDATA", str(appdata))
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<title>ok</title>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(launch.Quiet, directory=str(dist)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _get(url: str):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


@needs_tools
def test_server_serves_the_site_and_lists_saves(server) -> None:
    status, body = _get(server + "/")
    assert status == 200 and b"<title>ok</title>" in body
    status, body = _get(server + "/api/saves")
    saves = json.loads(body)
    assert status == 200 and [(s["account"], s["file"]) for s in saves] == [("st_123", "save.hg")]


@needs_tools
def test_server_reads_a_listed_save(server) -> None:
    status, body = _get(server + "/api/save?account=st_123&file=save.hg")
    assert status == 200
    assert json.loads(body)["totals"]["FUEL1"] == 157


@needs_tools
@pytest.mark.parametrize("query", [
    "account=st_123&file=nope.hg",
    "account=..&file=secret.txt",
    "account=st_123&file=../../../secret.txt",
    "account=st_123&file=..%2F..%2Fsecret.txt",
    "account=&file=",
    "",
])
def test_server_never_reads_a_file_the_listing_does_not_offer(server, query) -> None:
    status, body = _get(server + "/api/save?" + query)
    assert status == 404 and b"secret" not in body


@needs_tools
def test_server_reports_an_unreadable_save_instead_of_dying(server, tmp_path) -> None:
    (tmp_path / "appdata" / "HelloGames" / "NMS" / "st_123" / "save2.hg").write_bytes(b"not a save at all....")
    status, body = _get(server + "/api/save?account=st_123&file=save2.hg")
    assert status == 500 and "error" in json.loads(body)
    assert _get(server + "/api/saves")[0] == 200  # still alive


@needs_tools
def test_save_listing_is_empty_without_the_game(monkeypatch, tmp_path) -> None:
    import nms_save

    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert nms_save.listing() == []
    assert os.environ["APPDATA"] == str(tmp_path)
