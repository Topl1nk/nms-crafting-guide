"""The contribution bot: the issue form, what it reads back, what it accepts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import portal_issue as bot  # noqa: E402
from nms_items.portals import KINDS, LocationBook  # noqa: E402


def form_fields() -> dict[str, str]:
    """id -> label for every input in the issue form, read without a YAML parser."""
    text = bot.FORM.read_text()
    ids = re.findall(r"^\s+id: (\S+)$", text, flags=re.M)
    labels = re.findall(r"^\s+label: (.+)$", text, flags=re.M)
    return dict(zip(ids, labels))


def body(**fields: str) -> str:
    """An issue body the way GitHub renders a submitted form."""
    labels = {v: k for k, v in bot.FIELDS.items()}
    return "\n\n".join(f"### {labels[key]}\n\n{value or '_No response_'}" for key, value in fields.items())


GOOD = dict(name="Test Prime", code="0123 4567 89AB", galaxy="1", kind="starship",
            detail="S-class hauler", where="", source="visited myself")


def test_the_form_and_the_parser_agree() -> None:
    form = form_fields()
    assert {bot.FIELDS[label]: label for label in bot.FIELDS} == form


def test_the_form_offers_exactly_the_kinds() -> None:
    text = bot.FORM.read_text()
    block = text.split("id: kind", 1)[1].split("validations", 1)[0]
    assert re.findall(r"^\s+- (\S+)$", block, flags=re.M) == KINDS


def test_a_good_issue_passes_and_says_what_it_read() -> None:
    loc, errors, _ = bot.check(bot.parse_form(body(**GOOD)), LocationBook.load())
    assert not errors and loc is not None
    assert (loc.code, loc.kind, loc.origin, loc.galaxy) == ("0123456789AB", "starship", "shared", 1)
    assert loc.where == ""
    text = bot.reply(loc, errors, [])
    assert "✓" in text and "nmsii.dlu.one/#/portals?code=0123456789AB" in text


def test_a_galactic_address_converts_with_a_warning() -> None:
    fields = bot.parse_form(body(**{**GOOD, "code": "0BBB:007E:07E5:0123"}))
    loc, errors, warnings = bot.check(fields, LocationBook.load())
    assert not errors and loc.code.startswith("0")
    assert any("planet" in w for w in warnings)


@pytest.mark.parametrize("change, complaint", [
    ({"code": "not glyphs"}, "Portal address"),
    ({"code": ""}, "Portal address"),
    ({"name": ""}, "Name"),
    ({"galaxy": "999"}, "Galaxy"),
    ({"kind": "spaceship"}, "Kind"),
    ({"detail": "x" * 500}, "What is there"),
])
def test_a_bad_issue_is_told_what_to_fix(change, complaint) -> None:
    loc, errors, _ = bot.check(bot.parse_form(body(**{**GOOD, **change})), LocationBook.load())
    assert loc is None and any(complaint in e for e in errors)
    assert "✗" in bot.reply(loc, errors, [])


def test_a_listed_address_is_a_duplicate_only_for_the_same_kind() -> None:
    book = LocationBook.load()
    known = book.locations[0]
    same = body(**{**GOOD, "code": known.code, "galaxy": str(known.galaxy), "kind": known.kind})
    other = next(k for k in KINDS if k != known.kind)
    differs = body(**{**GOOD, "code": known.code, "galaxy": str(known.galaxy), "kind": other})
    assert bot.check(bot.parse_form(same), book)[0] is None
    loc, _, warnings = bot.check(bot.parse_form(differs), book)
    assert loc is not None and any("already listed" in w for w in warnings)


def test_galaxy_takes_a_number_or_a_name() -> None:
    assert [bot.galaxy_from(t) for t in ("1", "Euclid", "2. Hilbert Dimension", "0", "Andromeda?")] \
        == [1, 1, 2, None, None]


def test_the_committed_file_passes_the_pull_request_check() -> None:
    assert bot.validate(ROOT / "data" / "locations.json") == []


def test_the_pull_request_check_catches_what_the_loader_forgives(tmp_path) -> None:
    raw = json.loads((ROOT / "data" / "locations.json").read_text())
    raw["locations"] += [
        {**raw["locations"][0]},                                     # duplicate
        {**raw["locations"][0], "code": "0123456789ab", "kind": "boat"},
        {**raw["locations"][0], "code": "XYZ", "galaxy": 0, "colour": "red"},
    ]
    path = tmp_path / "locations.json"
    path.write_text(json.dumps(raw))
    problems = "\n".join(bot.validate(path))
    for expected in ("same address", "0123456789AB", "kind must be", "not dialable", "galaxy must", "unknown field"):
        assert expected in problems


def test_apply_appends_and_credits(tmp_path, monkeypatch) -> None:
    data = tmp_path / "locations.json"
    data.write_text((ROOT / "data" / "locations.json").read_text())
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"issue": {"number": 7, "user": {"login": "someone"}, "body": body(**GOOD)}}))
    monkeypatch.setattr(bot, "LOCATIONS", data)
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "out"))
    monkeypatch.setattr(sys, "argv", ["portal_issue.py", "apply", "--event", str(event), "--out", str(tmp_path / "r.md")])
    bot.main()
    added = json.loads(data.read_text())["locations"][-1]
    assert added["code"] == "0123456789AB" and added["source"] == "visited myself - @someone via #7"
    assert "valid=true" in (tmp_path / "out").read_text()
    assert bot.validate(data) == []
