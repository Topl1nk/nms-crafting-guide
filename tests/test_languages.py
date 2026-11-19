"""desktop/languages.py: the names of an item in every built language, for a search that does not care which language the page is in."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "desktop"))

import languages  # noqa: E402


def _setup(tmp_path, monkeypatch, built: dict[str, dict]) -> None:
    dist, langs = tmp_path / "dist", tmp_path / "lang"
    dist.mkdir()
    langs.mkdir()
    listed = [{"code": c} for c in ("english", "usenglish", "russian", "french", "tencentchinese", "simplifiedchinese")]
    (dist / "languages.json").write_text(json.dumps({"base": "english", "list": listed}), encoding="utf-8")
    for code, items in built.items():
        (langs / f"{code}.json").write_text(json.dumps({"items": items}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(languages.paths, "DIST", dist)
    monkeypatch.setattr(languages.paths, "LANGS", langs)


def test_the_languages_worth_building_leave_out_the_base_and_the_two_copies(tmp_path, monkeypatch) -> None:
    _setup(tmp_path, monkeypatch, {})
    assert languages.codes() == ["russian", "french", "simplifiedchinese"]


def test_the_missing_languages_are_built_one_after_the_other_and_a_failure_does_not_stop_the_rest(tmp_path, monkeypatch) -> None:
    _setup(tmp_path, monkeypatch, {"russian": {}})
    built = []

    def fake_build(code: str) -> None:
        if code == "french":
            raise RuntimeError("no game")
        built.append(code)
    monkeypatch.setattr(languages, "_build", fake_build)
    assert languages.start_all() is True
    for _ in range(200):
        if languages.state["*"]["state"] == "done":
            break
        languages.time.sleep(0.01)
    assert built == ["simplifiedchinese"]  # russian was there already, french failed
    assert languages.state["*"]["done"] == 2 and "french" in languages.state["*"]["error"]


def test_names_gathers_an_items_names_over_the_built_languages(tmp_path, monkeypatch) -> None:
    _setup(tmp_path, monkeypatch, {
        "russian": {"AF_METAL": ["Испорченный металл", "Собранный утиль"], "X": ["", "no name"]},
        "french": {"AF_METAL": ["Métal corrompu", ""]},
    })
    got = languages.names()
    assert got["names"]["AF_METAL"] == ["Испорченный металл", "Métal corrompu"]
    assert "X" not in got["names"] or got["names"]["X"] == []
    assert (got["languages"], got["total"]) == (2, 3)  # two of the three are built
    assert languages.have() == 2
