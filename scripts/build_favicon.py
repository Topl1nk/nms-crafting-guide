"""Draw the site icon from the Atlas portal glyph, in every form browsers ask for.

The mark is plugii's icon frame -- a black square, a thin grey outline -- with
the `atlas` glyph from data/glyphs.json in the site's HUD gold, so the icon is the
same traced shape the portal pages draw, not a lookalike.

    web/favicon.svg           modern browsers, and the header logo
    web/favicon.ico           16 + 32 px, for browsers that skip SVG icons
    web/apple-touch-icon.png  180 px, for an iOS home screen

Needs resvg and ImageMagick (pacman: resvg imagemagick). Run via
`mise run web:favicon`; the outputs are committed, since the glyph does not move.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
GLYPH = "atlas"
INK = "#ffc857"


def svg() -> str:
    glyphs = json.loads((ROOT / "data" / "glyphs.json").read_text(encoding="utf-8"))["glyphs"]
    glyph = next(g for g in glyphs if g["name"] == GLYPH)
    paths = "".join(f'<path d="{d}"/>' for d in glyph["paths"])
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="2" fill="#000"/>'
        '<rect x=".5" y=".5" width="31" height="31" rx="1.5" fill="none" stroke="#474747"/>'
        f'<svg x="3" y="3" width="26" height="26" viewBox="{glyph["viewbox"]}">'
        f'<g transform="{glyph["transform"]}" fill="{INK}">{paths}</g></svg></svg>\n'
    )


def main() -> None:
    source = WEB / "favicon.svg"
    source.write_text(svg(), encoding="utf-8")
    print(f"wrote {source.relative_to(ROOT)}")

    with tempfile.TemporaryDirectory() as tmp:
        sizes = {16: Path(tmp) / "16.png", 32: Path(tmp) / "32.png", 180: WEB / "apple-touch-icon.png"}
        for size, out in sizes.items():
            subprocess.run(["resvg", "-w", str(size), "-h", str(size), str(source), str(out)], check=True)
        subprocess.run(["magick", str(sizes[16]), str(sizes[32]), str(WEB / "favicon.ico")], check=True)
    print("wrote web/favicon.ico, web/apple-touch-icon.png")


if __name__ == "__main__":
    main()
