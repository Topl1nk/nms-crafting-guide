"""desktop/updater.py: which release is newer, which file of it is run, and what is never run."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "desktop"))

import updater  # noqa: E402

BASE = updater.DOWNLOADS + "v0.2.0/"


def test_versions_compare_as_numbers() -> None:
    assert updater.parse("0.10.0") > updater.parse("0.9.9")
    assert updater.parse("1.0") < updater.parse("1.0.1")
    # a build that is not a release is older than every release
    assert updater.parse("0.0.0-ab12cd3") < updater.parse("0.1.0")
    assert updater.parse("dev") == ()


def test_the_file_to_run_is_the_platforms_and_from_the_releases_only(monkeypatch) -> None:
    assets = [
        {"name": "nms-crafting-guide-0.2.0-x86_64.AppImage", "browser_download_url": BASE + "a.AppImage", "size": 3, "digest": "sha256:abc"},
        {"name": "nms-crafting-guide-Setup-0.2.0.exe", "browser_download_url": BASE + "s.exe", "size": 5, "digest": "sha256:def"},
    ]
    monkeypatch.setattr(updater.os, "name", "nt")
    assert updater.pick_asset(assets) == {"name": "nms-crafting-guide-Setup-0.2.0.exe", "url": BASE + "s.exe", "size": 5, "sha256": "def"}
    monkeypatch.setattr(updater.os, "name", "posix")
    assert updater.pick_asset(assets)["name"].endswith(".AppImage")
    # an address of another site is never taken, whatever the name says
    evil = [{"name": "nms-crafting-guide-Setup-9.exe", "browser_download_url": "https://example.com/s.exe", "size": 1}]
    monkeypatch.setattr(updater.os, "name", "nt")
    assert updater.pick_asset(evil) is None


def test_a_checkout_has_no_version_and_never_asks(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("NMS_CRAFTING_GUIDE_VERSION", raising=False)
    monkeypatch.setattr(updater.paths, "RES", tmp_path)
    assert updater.current_version() == ""
    assert updater.check() is False
    assert updater.status()["supported"] is False


def test_the_version_is_read_from_the_bundle(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("NMS_CRAFTING_GUIDE_VERSION", raising=False)
    monkeypatch.setattr(updater.paths, "RES", tmp_path)
    (tmp_path / "VERSION").write_text("0.1.5\n", encoding="utf-8")
    assert updater.current_version() == "0.1.5"
