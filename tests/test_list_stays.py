"""A list does not start over by itself. The save is read again every half minute (and when the window gets focus); what
is read and found the same must not rebuild the lists (their cursor and scroll went back to the top at random moments),
and rows made anew but the same ones must keep the cursor where it was."""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).parent.parent / "site" / "src"


def read(*parts: str) -> str:
    return SRC.joinpath(*parts).read_text(encoding="utf-8")


def test_a_save_read_again_and_found_the_same_is_left_as_it_was() -> None:
    save = read("lib", "gamesave.svelte.js")
    assert "const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);" in save
    assert "if (!same(read, report)) report = read;" in save and "if (!same(seen, slots)) slots = seen;" in save


def test_the_same_rows_again_keep_the_cursor() -> None:
    lst = read("components", "List.svelte")
    assert "keyOf = (row) => row" in lst
    assert re.search(r"const unchanged = sel >= 0 && keys\.length === was\.length && keys\.every", lst)
    assert "if (unchanged) return;" in lst


def test_a_list_that_makes_its_rows_anew_says_which_are_the_same() -> None:
    inv = read("views", "Inventory.svelte")
    assert "keyOf={([id, , c]) =>" in inv, "its rows are fresh arrays on every update"


def test_names_are_not_cut_short_while_there_is_room() -> None:
    """«Активированны…», «Термическ ий…», «Путь: Термический конде…»: names were cut at 16 or 24 characters, or in the middle
    of a word, with the whole line free beside them."""
    ings = read("components", "Ingredients.svelte")
    assert "max-width: 16ch" not in ings
    tile = read("components", "Tile.svelte")
    assert "word-break: break-word" not in tile and "hyphens: auto" in tile and "width: var(--tile); height: var(--tile)" in tile, "a name wraps inside the one square tile"
    css = (SRC / "app.css").read_text(encoding="utf-8")
    assert "max-width: 24ch" not in css



