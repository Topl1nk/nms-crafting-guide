"""Turn the downloaded glyph PNGs into data/glyphs.json -- outlines and art.

One source, two shapes, because the two places a glyph has to appear want
opposite things:

  * the PDF wants **vectors**. A 256px raster set at 14pt would print at
    ~1300dpi, which is fine, but a raster cannot be recoloured, and the cheat
    sheet builds in two themes: white line art is invisible on Latte's paper.
    So the outlines are traced to SVG paths and the *fill is left to the
    caller*, which is how cheatsheet.typ tints them per theme.

  * the TUI wants **characters**. A terminal cannot show a PNG, so the same
    mask is knocked down to a dot grid and encoded as braille -- 2x4 dots per
    cell, which is four times the vertical resolution of half-blocks and the
    only way line this thin survives being shrunk to four rows.

Both fall out of the same alpha mask, so they cannot disagree about what a
glyph looks like.

The mask itself: the upstream art is a white stroke with a soft glow around it,
so a low threshold swallows the glyph into a blob (the waves of `sunset` merge
into a dome) and a high one keeps the drawing. 78% keeps it. The stroke is then
dilated by one pixel, because a 4px-of-256 hairline is 0.04mm at print size --
below what a laser printer resolves, and below what one braille dot can hold.

Needs `potrace` on PATH (`mise run setup`). PNG decoding is done here with
zlib rather than Pillow: these are the one image the project reads, they are
all 8-bit RGBA and non-interlaced, and that is 40 lines against a dependency.

Run via `mise run data:build-glyphs`, after `mise run data:fetch-glyphs`.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "glyphs"
OUT = ROOT / "data" / "glyphs.json"

sys.path.insert(0, str(ROOT / "src"))
from nms_items.portals import GLYPH_NAMES  # noqa: E402

SOURCE = "https://nmsportals.github.io/img/glyphs/"

# Where the white stroke ends and its glow begins, as a fraction of full alpha.
INK = 0.78
# Pixels to grow the stroke by, so it survives both print and a braille dot.
DILATE = 1

# Braille art sizes, in *cells*. A cell is 2 dots wide and 4 tall, and a
# terminal cell is about twice as tall as it is wide, so 8x4 cells (16x16
# dots) comes out square. Twelve of those is a 96-column row, so the smaller
# 6x3 is what a narrow terminal falls back to -- below about 12x12 dots the
# line art stops being one glyph rather than another.
SIZES = {"art": (8, 4), "art_small": (6, 3)}
# How much of a dot's area must be ink before the dot is lit. The braille is
# shrunk from the *undilated* stroke, cropped to the glyph: at 16 dots across,
# the upstream padding and the print dilation together cost so much room that
# neighbouring strokes merged -- atlas's three triangles came out one pyramid,
# sunset's waves a bowl. Cropped, a stroke crosses most of a dot it touches, so
# a dot can ask for more of itself before lighting and gaps stay open.
COVERAGE = 0.15

# Braille dot bit per (x, y) within a cell -- the numbering is historical and
# not row-major, which is the one thing to get right here.
DOTS = {
    (0, 0): 0x01, (0, 1): 0x02, (0, 2): 0x04, (0, 3): 0x40,
    (1, 0): 0x08, (1, 1): 0x10, (1, 2): 0x20, (1, 3): 0x80,
}


def read_alpha(path: Path) -> tuple[int, int, bytearray]:
    """Decode an 8-bit RGBA non-interlaced PNG down to its alpha channel."""
    raw = path.read_bytes()
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise SystemExit(f"{path}: not a PNG")

    width = height = 0
    idat = bytearray()
    pos = 8
    while pos < len(raw):
        length = int.from_bytes(raw[pos:pos + 4], "big")
        kind = raw[pos + 4:pos + 8]
        body = raw[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            width = int.from_bytes(body[0:4], "big")
            height = int.from_bytes(body[4:8], "big")
            depth, colour, _, _, interlace = body[8:13]
            if (depth, colour, interlace) != (8, 6, 0):
                raise SystemExit(
                    f"{path}: want 8-bit RGBA non-interlaced, got depth={depth} "
                    f"colour={colour} interlace={interlace}")
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break

    data = zlib.decompress(bytes(idat))
    stride = width * 4
    alpha = bytearray(width * height)
    prev = bytearray(stride)
    at = 0
    for y in range(height):
        filt = data[at]
        row = bytearray(data[at + 1:at + 1 + stride])
        at += 1 + stride
        # Undo the per-row filter. `a` is the pixel to the left, `b` above.
        if filt == 1:
            for i in range(4, stride):
                row[i] = (row[i] + row[i - 4]) & 0xFF
        elif filt == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 0xFF
        elif filt == 3:
            for i in range(stride):
                a = row[i - 4] if i >= 4 else 0
                row[i] = (row[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif filt == 4:
            for i in range(stride):
                a = row[i - 4] if i >= 4 else 0
                b = prev[i]
                c = prev[i - 4] if i >= 4 else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                row[i] = (row[i] + pred) & 0xFF
        elif filt != 0:
            raise SystemExit(f"{path}: unknown row filter {filt}")
        alpha[y * width:(y + 1) * width] = row[3::4]
        prev = row
    return width, height, alpha


def mask(width: int, height: int, alpha: bytearray,
         dilate: int = DILATE) -> bytearray:
    """Alpha -> 1-bit ink, thresholded and grown by `dilate` pixels."""
    cut = int(INK * 255)
    ink = bytearray(1 if a >= cut else 0 for a in alpha)
    if dilate <= 0:
        return ink
    # A disk kernel; at radius 1 that is a 3x3 square without its corners.
    offsets = [
        (dx, dy)
        for dy in range(-dilate, dilate + 1)
        for dx in range(-dilate, dilate + 1)
        if dx * dx + dy * dy <= dilate * dilate + 0.5
    ]
    grown = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            if not ink[y * width + x]:
                continue
            for dx, dy in offsets:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    grown[ny * width + nx] = 1
    return grown


def to_pbm(width: int, height: int, ink: bytearray) -> bytes:
    """Pack the mask as a binary PBM, which is what potrace reads. 1 = ink."""
    rows = bytearray()
    for y in range(height):
        bits = 0
        nbits = 0
        for x in range(width):
            bits = (bits << 1) | ink[y * width + x]
            nbits += 1
            if nbits == 8:
                rows.append(bits)
                bits = nbits = 0
        if nbits:
            rows.append(bits << (8 - nbits))
    return b"P4\n%d %d\n" % (width, height) + bytes(rows)


def trace(pbm: bytes) -> list[str]:
    """Run potrace and return the `d` of every path it emitted."""
    try:
        done = subprocess.run(
            ["potrace", "--svg", "--turdsize", "4", "--alphamax", "1.0",
             "--opttolerance", "0.2", "-o", "-", "-"],
            input=pbm, capture_output=True, check=True,
        )
    except FileNotFoundError:
        raise SystemExit(
            "potrace not found. Install it: mise run setup") from None
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"potrace failed: {exc.stderr.decode(errors='replace')}")
    svg = done.stdout.decode()
    paths = re.findall(r'<path d="(.*?)"', svg, re.S)
    if not paths:
        raise SystemExit("potrace produced no outline")
    # Collapse the newlines potrace wraps path data at; SVG does not care but a
    # JSON file full of them is unreadable.
    return [" ".join(d.split()) for d in paths]


def transform_of(width: int, height: int) -> str:
    """potrace's own flip: it works bottom-up, at ten times the scale."""
    return f"translate(0,{height}) scale(0.1,-0.1)"


def braille(width: int, height: int, ink: bytearray, cells: tuple[int, int]) -> list[str]:
    """Shrink the mask to a dot grid and encode it as braille rows.

    The grid covers the glyph's own bounding box, squared up and centred, not
    the whole image -- every dot is spent on the drawing. Outside the image
    counts as blank.
    """
    cols, rows = cells
    dots_x, dots_y = cols * 2, rows * 4
    inked = [i for i, v in enumerate(ink) if v]
    xs = [i % width for i in inked]
    ys = [i // width for i in inked]
    side = max(max(xs) + 1 - min(xs), max(ys) + 1 - min(ys))
    left = (min(xs) + max(xs) + 1 - side) / 2
    top = (min(ys) + max(ys) + 1 - side) / 2
    bw, bh = side / dots_x, side / dots_y
    lit = [[False] * dots_x for _ in range(dots_y)]
    for dy in range(dots_y):
        y0 = int(top + dy * bh)
        y1 = max(y0 + 1, int(top + (dy + 1) * bh))
        for dx in range(dots_x):
            x0 = int(left + dx * bw)
            x1 = max(x0 + 1, int(left + (dx + 1) * bw))
            filled = sum(
                ink[y * width + x]
                for y in range(max(y0, 0), min(y1, height))
                for x in range(max(x0, 0), min(x1, width))
            )
            area = (y1 - y0) * (x1 - x0)
            lit[dy][dx] = filled >= COVERAGE * area
    out = []
    for row in range(rows):
        line = ""
        for col in range(cols):
            bits = 0
            for (dx, dy), bit in DOTS.items():
                if lit[row * 4 + dy][col * 2 + dx]:
                    bits |= bit
            line += chr(0x2800 + bits)
        out.append(line)
    return out


def main() -> int:
    if not CACHE.is_dir():
        raise SystemExit(f"{CACHE} missing. Run: mise run data:fetch-glyphs")

    glyphs = []
    for i, name in enumerate(GLYPH_NAMES):
        digit = f"{i:x}"
        src = CACHE / f"{digit}.png"
        if not src.is_file():
            raise SystemExit(f"{src} missing. Run: mise run data:fetch-glyphs")
        width, height, alpha = read_alpha(src)
        ink = mask(width, height, alpha)
        entry = {
            "position": i + 1,
            "hex": f"{i:X}",
            "name": name,
            "viewbox": f"0 0 {width} {height}",
            "transform": transform_of(width, height),
            "paths": trace(to_pbm(width, height, ink)),
        }
        # The dilation is for print; the braille wants the stroke as drawn.
        thin = mask(width, height, alpha, dilate=0)
        for key, cells in SIZES.items():
            entry[key] = braille(width, height, thin, cells)
        glyphs.append(entry)
        print(f"  {entry['hex']} {name:<10} {len(entry['paths'])} paths")

    OUT.write_text(json.dumps({
        "source": SOURCE,
        "note": (
            "Outlines traced from the nmsportals glyph art; fill is the "
            "caller's, so the same path prints on paper and on a dark screen. "
            "`art` is the same mask as braille, for the terminal. "
            "Rebuild with: mise run data:glyphs"
        ),
        "ink": INK,
        "dilate": DILATE,
        "cells": {key: list(value) for key, value in SIZES.items()},
        "glyphs": glyphs,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
