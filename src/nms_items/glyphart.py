"""The portal glyphs, drawn in a terminal.

A terminal cannot show the game's symbols, and no font on a normal machine has
them, so the shapes have to arrive as characters. data/glyphs.json carries each
glyph twice over: as an outline for the PDF, and as braille -- 2x4 dots to the
cell, which is four times the vertical resolution of half-blocks and the only
thing fine enough to keep `sunset` from turning into a blob. Both come off one
mask (see scripts/build_glyphs.py), so the sheet and the screen cannot end up
drawing different symbols.

Two sizes, because a twelve-glyph address is a wide thing:

    WIDE   8 cells across, 4 down   ->  12 glyphs need 96 columns
    NARROW 6 cells across, 3 down   ->  12 glyphs need 72 columns

Below that the line art stops being one glyph rather than another, so there is
no third size: a terminal too narrow for NARROW gets the hex, which is what it
was always getting.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .model import DATA_DIR

WIDE = "art"
NARROW = "art_small"

# How a twelve-glyph code is laid out for the width there is: widest first, so
# the first that fits is the best that fits.
#
# Six per line is the only split worth making -- it falls on a field boundary,
# planet/system/Y above and Z/X below, where four per line would cut a
# coordinate in half. It buys narrowness with rows, which is why a caller with
# a short pane passes `stacked=False` and would rather show nothing.
LAYOUTS = ((WIDE, 12), (NARROW, 12), (WIDE, 6), (NARROW, 6))


@dataclass(frozen=True, slots=True)
class GlyphArt:
    """One symbol: its place on the dial, its name, and how to draw it."""

    position: int
    hex: str
    name: str
    wide: tuple[str, ...]
    narrow: tuple[str, ...]

    def rows(self, size: str = WIDE) -> tuple[str, ...]:
        return self.wide if size == WIDE else self.narrow


@dataclass(frozen=True, slots=True)
class GlyphSet:
    glyphs: tuple[GlyphArt, ...]
    source: str
    # Cells per glyph, {size: (columns, rows)}.
    cells: dict[str, tuple[int, int]]

    def __getitem__(self, digit: str) -> GlyphArt:
        """Look one up by its hex digit, which *is* its place on the dial."""
        return self.glyphs[int(digit, 16)]

    def width(self, size: str = WIDE) -> int:
        return self.cells[size][0]

    def height(self, size: str = WIDE) -> int:
        return self.cells[size][1]

    def strip(self, code: str, size: str = WIDE, gap: int = 0,
              colours: list[str] | None = None) -> list[str]:
        """A whole portal code as lines of braille, glyphs side by side.

        `gap` is columns of space between glyphs, and `colours` -- one entry
        per position -- wraps each glyph in Textual markup, which is what puts
        the five address fields in five colours the way the hex already is.
        """
        return self._block(code, size, len(code), gap, colours)

    def columns(self, size: str = WIDE, gap: int = 0) -> int:
        """How wide `strip` of a twelve-glyph code comes out."""
        return self.line_width(12, size, gap)

    def line_width(self, count: int, size: str = WIDE, gap: int = 0) -> int:
        return count * self.width(size) + max(0, count - 1) * gap

    def render(self, code: str, width: int, colours: list[str] | None = None,
               gap: int = 1, stacked: bool = True) -> list[str]:
        """The biggest layout of `code` that fits `width` columns, else [].

        Empty is a real answer: below about 40 columns the art stops telling
        one glyph from another, and the hex was always the fallback.
        """
        for size, per_line in LAYOUTS:
            if per_line < len(code) and not stacked:
                continue
            if self.line_width(per_line, size, gap) <= width:
                return self._block(code, size, per_line, gap, colours)
        return []

    def _block(self, code: str, size: str, per_line: int, gap: int,
               colours: list[str] | None) -> list[str]:
        pad = " " * gap
        out: list[str] = []
        for start in range(0, len(code), per_line):
            if out:
                out.append("")
            here = range(start, min(start + per_line, len(code)))
            for row in range(self.height(size)):
                out.append(pad.join(
                    self._cell(code[i], i, row, size, colours) for i in here))
        return out

    def _cell(self, digit: str, index: int, row: int, size: str,
              colours: list[str] | None) -> str:
        cells = self[digit].rows(size)[row]
        return cells if colours is None else f"[{colours[index]}]{cells}[/]"


@lru_cache(maxsize=1)
def load(data_dir: Path | None = None) -> GlyphSet:
    raw = json.loads(
        (Path(data_dir or DATA_DIR) / "glyphs.json").read_text(encoding="utf-8"))
    return GlyphSet(
        glyphs=tuple(
            GlyphArt(
                position=g["position"],
                hex=g["hex"],
                name=g["name"],
                wide=tuple(g[WIDE]),
                narrow=tuple(g[NARROW]),
            )
            for g in raw["glyphs"]
        ),
        source=raw["source"],
        cells={key: tuple(value) for key, value in raw["cells"].items()},
    )
