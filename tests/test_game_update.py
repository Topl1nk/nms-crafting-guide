"""game:update's comparison and exit codes, with no game installed (as in CI)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import game_update as gu  # noqa: E402

DATA = {"build": "180836", "label": "7.06_Cosmos_180836"}


@pytest.mark.parametrize("installed, status", [
    (None, gu.NO_GAME),
    ({"build": ""}, gu.NO_GAME),
    ({"build": "180836"}, gu.CURRENT),
    ({"build": "181002"}, gu.UPDATE),
    ({"build": "170000"}, gu.BEHIND),
    ({"build": "x9"}, gu.UPDATE),  # not numeric: different is enough
])
def test_compare(installed, status) -> None:
    assert gu.compare(installed, DATA) == status


def test_exit_codes() -> None:
    assert gu.EXIT == {gu.CURRENT: 0, gu.BEHIND: 0, gu.NO_GAME: 2,
                       gu.UPDATE: 10, gu.BLOCKED: 11}


def test_names() -> None:
    assert gu.branch_for("181002") == "data/game-181002"
    assert gu.label_of({"build": "181002"}) == "build 181002"
    assert gu.issue_title({"label": "7.07_Cosmos_181002", "build": "181002"}) == (
        "Game updated to 7.07_Cosmos_181002: waiting for MBINCompiler")
    items = [{"title": "Game updated to build 1810020: x"},
             {"title": "Game updated to 7.07_Cosmos_181002: waiting for MBINCompiler",
              "number": 7}]
    assert gu.find_numbered(items, "181002")["number"] == 7
    assert gu.find_numbered(items, "18100") is None


def test_failed_tests_and_body() -> None:
    out = "..F\nFAILED tests/test_data.py::test_recipe_counts - assert 1 == 2\n1 failed"
    failures = gu.failed_tests(out)
    assert failures == ["tests/test_data.py::test_recipe_counts"]
    body = gu.pr_body({"build": "181002"}, DATA, "line\n" * 100, False, failures, [], 7)
    assert "<details>" in body and "Closes #7" in body
    assert "`tests/test_data.py::test_recipe_counts`" in body
    assert "- [ ]" in body
    assert "<details>" not in gu.collapse("short", "x")


def _main(monkeypatch, tmp_path, build, readable=True) -> int:
    src = tmp_path / "source.json"
    src.write_text(json.dumps({"game": DATA}))
    monkeypatch.setenv("NMSII_SOURCE_JSON", str(src))
    monkeypatch.delenv("NMSII_FORCE_MBIN_MISMATCH", raising=False)
    game = None if build is None else tmp_path
    monkeypatch.setattr(gu.extract_game, "find_game", lambda arg=None: game)
    monkeypatch.setattr(gu.extract_game, "game_version",
                        lambda g: {"build": build, "label": ""})
    monkeypatch.setattr(gu.extract_game, "compiler_reads", lambda g: (readable, "why"))
    return gu.main(["--check"])


def test_check_exit_codes(monkeypatch, tmp_path, capsys) -> None:
    assert _main(monkeypatch, tmp_path, None) == 2
    assert _main(monkeypatch, tmp_path, "180836") == 0
    assert "data is current" in capsys.readouterr().out
    assert _main(monkeypatch, tmp_path, "181002") == 10
    assert _main(monkeypatch, tmp_path, "181002", readable=False) == 11
    assert _main(monkeypatch, tmp_path, "170000") == 0
