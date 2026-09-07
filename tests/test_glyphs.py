"""The glyph art has to stay in step with the dial, or an address is wrong.

data/glyphs.json is generated (`mise run glyphs`) and committed, so nothing at
runtime re-derives it -- which means these are the only checks that it still
lines up with portals.py. The one that matters is the mapping: glyph `A` is the
eleventh symbol, and if the file ever drifts by one position every address on
the cheat sheet points at a different star.
"""

from __future__ import annotations

import asyncio
import json
import re

from nms_items import glyphart, portals
from nms_items.app import RecipeApp
from nms_items.model import DATA_DIR, Book
from nms_items.screens import GLYPH_COLOURS, GLYPH_INDENT

CODE = "6046FFAE4450"


def plain(line: str) -> str:
    """Drop the Textual colour markup, leaving the columns it will occupy."""
    return re.sub(r"\[[^\]]*\]", "", line)


RAW = json.loads((DATA_DIR / "glyphs.json").read_text(encoding="utf-8"))


def test_sixteen_glyphs_in_dial_order():
    art = glyphart.load()
    assert len(art.glyphs) == 16
    for i, name in enumerate(portals.GLYPH_NAMES):
        g = art.glyphs[i]
        assert (g.position, g.hex, g.name) == (i + 1, f"{i:X}", name)


def test_lookup_is_by_position_on_the_dial():
    art = glyphart.load()
    assert art["A"].position == 11
    assert art["A"].name == portals.GLYPH_NAMES[10]
    assert art["0"] is art.glyphs[0]
    assert art["f"] is art["F"]


def test_every_glyph_has_an_outline():
    for g in RAW["glyphs"]:
        assert g["paths"], f"{g['name']} traced to nothing"
        assert all(d.startswith("M") for d in g["paths"])
        assert g["viewbox"] == "0 0 256 256"


def test_art_is_braille_of_the_declared_size():
    art = glyphart.load()
    for size in (glyphart.WIDE, glyphart.NARROW):
        cols, rows = art.cells[size]
        for g in art.glyphs:
            lines = g.rows(size)
            assert len(lines) == rows
            assert all(len(line) == cols for line in lines)
            # U+2800..U+28FF, and never a blank glyph.
            assert all(0x2800 <= ord(ch) <= 0x28FF for line in lines for ch in line)
            assert any(ch != "⠀" for line in lines for ch in line), g.name


def test_a_code_draws_as_one_strip():
    art = glyphart.load()
    code = portals.Address.from_portal_code("11AC008F4025").portal_code
    lines = art.strip(code)
    assert len(lines) == art.height()
    assert all(len(line) == art.columns() for line in lines)
    # The first two glyphs are the same symbol, so the strip repeats itself.
    width = art.width()
    assert lines[0][:width] == lines[0][width:2 * width]


def test_narrow_fits_where_wide_does_not():
    art = glyphart.load()
    assert art.columns(glyphart.NARROW) < art.columns(glyphart.WIDE)
    assert art.columns(glyphart.NARROW, gap=1) <= 96


def test_render_takes_the_biggest_layout_that_fits():
    art = glyphart.load()
    for width, (size, per_line) in (
        (200, (glyphart.WIDE, 12)),
        (107, (glyphart.WIDE, 12)),
        (106, (glyphart.NARROW, 12)),
        (83, (glyphart.NARROW, 12)),
        (82, (glyphart.WIDE, 6)),
        (53, (glyphart.WIDE, 6)),
        (52, (glyphart.NARROW, 6)),
        (41, (glyphart.NARROW, 6)),
    ):
        lines = art.render(CODE, width)
        blocks = 12 // per_line
        # One block per line of glyphs, plus a blank line between blocks.
        assert len(lines) == blocks * art.height(size) + blocks - 1, width
        assert max(len(l) for l in lines) == art.line_width(per_line, size, 1), width


def test_render_never_overruns_the_width_it_was_given():
    art = glyphart.load()
    for width in range(0, 130):
        for line in art.render(CODE, width, colours=GLYPH_COLOURS):
            assert len(plain(line)) <= width, width


def test_render_gives_up_rather_than_shrink_past_reading():
    art = glyphart.load()
    assert art.render(CODE, 40) == []
    # Refusing to stack costs the narrow widths entirely, which is the trade a
    # short pane makes.
    assert art.render(CODE, 82, stacked=False) == []
    assert art.render(CODE, 83, stacked=False) != []


def test_colours_wrap_each_glyph_in_its_field():
    art = glyphart.load()
    line = art.render(CODE, 200, colours=GLYPH_COLOURS)[0]
    assert line.count("[/]") == 12
    # Planet is one glyph, then three of system: the second colour repeats.
    assert line.startswith(f"[{GLYPH_COLOURS[0]}]")
    assert GLYPH_COLOURS[0] != GLYPH_COLOURS[1] == GLYPH_COLOURS[3]


def test_portal_panes_never_wrap_the_glyphs():
    """The width a pane reports and the width the art asks for must agree.

    Both panes are drawn once before the layout exists, so they work off
    arithmetic first and the measured width after; either being a column out
    wraps a strip and turns it into gibberish.
    """
    book = Book()

    async def scenario(width: int) -> None:
        app = RecipeApp(book)
        async with app.run_test(size=(width, 46)) as pilot:
            await pilot.press("P")
            await pilot.pause(0.3)
            screen = app.screen
            art = glyphart.load()
            for asked, pane, indent in (
                (screen._readout_width() - GLYPH_INDENT,
                 "#portal-readout", GLYPH_INDENT),
                (screen._detail_width(), "#loc-detail", 0),
            ):
                have = screen.query_one(pane).content_size.width
                for line in art.render(CODE, asked, colours=GLYPH_COLOURS):
                    assert len(plain(line)) + indent <= have, (width, pane)

    for width in (90, 100, 120, 150, 190):
        asyncio.run(scenario(width))
