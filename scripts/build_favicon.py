"""Draw the site icon from the Atlas portal glyph, in every form browsers ask for.

The mark is plugii's icon frame -- a black square, a thin grey outline -- with
the `atlas` glyph from data/glyphs.json in the site's HUD gold, so the icon is the
same traced shape the portal pages draw, not a lookalike.

    web/favicon.svg           modern browsers, and the header logo
    web/favicon.ico           16 + 32 px, for browsers that skip SVG icons
    web/apple-touch-icon.png  180 px, for an iOS home screen
    web/icon-192.png          the installed app's icon (manifest.webmanifest)
    web/icon-512.png          ...and its splash screen
    web/icon-maskable-512.png the same mark full-bleed, for launchers that crop
                              it to a circle or a squircle: the glyph inside
                              the maskable safe zone, the middle 80% circle

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


def glyph_svg(x: float, size: float) -> str:
    glyphs = json.loads((ROOT / "data" / "glyphs.json").read_text(encoding="utf-8"))["glyphs"]
    glyph = next(g for g in glyphs if g["name"] == GLYPH)
    paths = "".join(f'<path d="{d}"/>' for d in glyph["paths"])
    return (
        f'<svg x="{x:g}" y="{x:g}" width="{size:g}" height="{size:g}" viewBox="{glyph["viewbox"]}">'
        f'<g transform="{glyph["transform"]}" fill="{INK}">{paths}</g></svg>'
    )


def svg() -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="2" fill="#000"/>'
        '<rect x=".5" y=".5" width="31" height="31" rx="1.5" fill="none" stroke="#474747"/>'
        f'{glyph_svg(3, 26)}</svg>\n'
    )


def maskable_svg() -> str:
    # No frame and no rounded corners: the launcher draws its own shape over a
    # full-bleed square. The safe zone is a circle of radius 40% (12.8 of 32).
    # The glyph's three triangles leave its box's corners empty, so a 22-unit
    # box keeps every drawn point within ~10.5 of the centre, inside it.
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" fill="#000"/>'
        f'{glyph_svg(5, 22)}</svg>\n'
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
        for size in (192, 512):
            out = WEB / f"icon-{size}.png"
            subprocess.run(["resvg", "-w", str(size), "-h", str(size), str(source), str(out)], check=True)
        maskable = Path(tmp) / "maskable.svg"
        maskable.write_text(maskable_svg(), encoding="utf-8")
        subprocess.run(["resvg", "-w", "512", "-h", "512", str(maskable),
                        str(WEB / "icon-maskable-512.png")], check=True)
    print("wrote web/favicon.ico, web/apple-touch-icon.png, web/icon-{192,512,maskable-512}.png")


if __name__ == "__main__":
    main()
