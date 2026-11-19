"""The program listens on the same port every time: the browser keeps the page's settings per address, port included, so a new
port would forget the theme, the language and the typed items (desktop/nms_crafting_guide.py open_server)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

for module in ("lz4", "numpy", "PIL"):
    pytest.importorskip(module)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "desktop"))

import nms_crafting_guide as app  # noqa: E402


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(app.paths, "HOME", tmp_path)
    monkeypatch.setattr(app, "PORTS", range(47800, 47810))
    return tmp_path


def test_the_first_port_is_kept_and_found_again(home) -> None:
    first = app.open_server(None, None)
    port = first.server_address[1]
    assert port in app.PORTS and (home / "port.txt").read_text() == str(port)
    first.server_close()
    again = app.open_server(None, None)
    assert again.server_address[1] == port
    again.server_close()


def test_a_second_copy_takes_another_port_and_leaves_the_kept_one(home, monkeypatch) -> None:
    monkeypatch.setattr(app.time, "sleep", lambda s: None)  # the wait for the kept port to come free
    first = app.open_server(None, None)
    second = app.open_server(None, None)
    assert second.server_address[1] != first.server_address[1]
    assert (home / "port.txt").read_text() == str(first.server_address[1])
    first.server_close()
    second.server_close()
