"""Gives the whole site one colour: every colour in the source is set to a single hue at a single, low saturation, and only its
lightness is its own. So there is no mush of hues, only one tone seen in many lights (a bluish red, neither much blue nor much
red, and not saturated). Or, with --cap, only the loud colours are brought down to a saturation ceiling and the hues are left.

The colours are those written in the source (site/src: .css, .svelte, .js) as #rrggbb, #rrggbbaa, rgb(r g b / a), or as the
triplet of a custom property (`--v-ink: 14 9 9`). The data (data.json), the Python export and the pictures are not touched; an
item's glow takes the tone through --item-tone and a grey that is itself one of these colours.

The colours that MEAN something are not made one tone: the tags of an item's type and rarity, the branches of a pyramid, the accents to
choose from, and the signal colours of global.css (green, red, orange, purple, pink, yellow). They are only kept from being loud: their
saturation is brought to a ceiling (SEMANTIC_CAP, lively but not shouting) and their hues are left, so they stay colours but never shout.

Running it again changes nothing. Idempotent by construction: the colour is a function of its lightness alone.

    python scripts/tone_colors.py                      # the navy ramp: hue and saturation follow the lightness
    python scripts/tone_colors.py --hue 350 --sat 0.08 # one flat tone instead
    python scripts/tone_colors.py --cap 0.42           # only bring the loud ones down, keep the hues
    python scripts/tone_colors.py --check              # change nothing; exit 1 if anything is off (the tests run this)
"""

from __future__ import annotations

import argparse
import colorsys
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "site" / "src"
EXT = {".css", ".svelte", ".js"}
HEX = re.compile(r"(?<![\w&#])#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?(?![0-9a-zA-Z])")
RGB = re.compile(r"(rgba?\(\s*)(\d{1,3})([\s,]+)(\d{1,3})([\s,]+)(\d{1,3})")
TRIPLET = re.compile(r"(--[\w-]+:\s*)(\d{1,3}) (\d{1,3}) (\d{1,3})(\s*(?:;|/\*))")
# The navy the site is cut from: hue and saturation follow the lightness (lightness, hue in degrees, saturation), interpolated between
# the points, so the deepest shades are an ink blue, the panels a livelier blue-violet, the middle ones slate and steel, the lightest a cold white.
RAMP = [(0.00, 222, 0.55), (0.07, 222, 0.56), (0.13, 227, 0.52), (0.20, 230, 0.46), (0.32, 232, 0.36),
        (0.50, 221, 0.30), (0.72, 214, 0.32), (0.85, 220, 0.32), (0.96, 228, 0.46), (1.00, 228, 0.40)]
HUE, SAT = None, None
SEMANTIC_CAP = 0.85
SEMANTIC_FILES = {"lib/words.js", "components/Pyramid.svelte", "components/CycleSteps.svelte"}
SEMANTIC_LINE = {
    "global.css": re.compile(r"--p-(?:accent|secondary|tertiary|purple|red|orange|yellow|green|pink):"),
    "app.css": re.compile(r"--p-cyan:"),
    "lib/theme.js": re.compile(r'\["(?:gold|cyan|green|violet|orange)"'),
}


def ceiling(rel: str, line: str) -> float | None:
    """The ceiling a line's colours are brought to, or None when they are brought to the one tone."""
    if rel in SEMANTIC_FILES or (rel in SEMANTIC_LINE and SEMANTIC_LINE[rel].search(line)):
        return SEMANTIC_CAP
    return None


def tone_at(l: float) -> tuple[float, float]:
    """The hue and saturation the ramp gives a colour of this lightness."""
    for (l0, h0, s0), (l1, h1, s1) in zip(RAMP, RAMP[1:]):
        if l <= l1:
            k = (l - l0) / (l1 - l0)
            return h0 + (h1 - h0) * k, s0 + (s1 - s0) * k
    return RAMP[-1][1], RAMP[-1][2]


def recolour(rgb: tuple[int, int, int], hue: float, sat: float, cap: float | None) -> tuple[int, int, int] | None:
    """The colour in the site's tone, or None when it is already (within rounding of one step) what it should be."""
    h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in rgb))
    if cap is not None:
        if s <= cap + 0.004:
            return None
        new = colorsys.hls_to_rgb(h, l, cap - 0.015)
    else:
        if hue is None:
            hue, sat = tone_at(l)
        new = colorsys.hls_to_rgb(hue / 360, l, sat)
    out = tuple(round(v * 255) for v in new)
    return None if max(abs(a - b) for a, b in zip(out, rgb)) <= 1 else out


def convert_line(text: str, hue: float, sat: float, cap: float | None) -> tuple[str, list[tuple[str, str]]]:
    changes: list[tuple[str, str]] = []

    def hexed(m: re.Match) -> str:
        new = recolour(tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4)), hue, sat, cap)
        if new is None:
            return m.group(0)
        out = "#%02x%02x%02x%s" % (*new, m.group(2) or "")
        changes.append((m.group(0), out))
        return out

    def rgbed(m: re.Match) -> str:
        new = recolour((int(m.group(2)), int(m.group(4)), int(m.group(6))), hue, sat, cap)
        if new is None:
            return m.group(0)
        out = f"{m.group(1)}{new[0]}{m.group(3)}{new[1]}{m.group(5)}{new[2]}"
        changes.append((m.group(0), out))
        return out

    def triplet(m: re.Match) -> str:
        new = recolour((int(m.group(2)), int(m.group(3)), int(m.group(4))), hue, sat, cap)
        if new is None:
            return m.group(0)
        out = f"{m.group(1)}{new[0]} {new[1]} {new[2]}{m.group(5)}"
        changes.append((m.group(0), out))
        return out

    return TRIPLET.sub(triplet, RGB.sub(rgbed, HEX.sub(hexed, text))), changes


def convert(text: str, hue: float, sat: float, cap: float | None, rel: str) -> tuple[str, list[tuple[str, str]]]:
    """The whole text, line by line: a signal colour keeps its hue (under the ceiling), every other colour takes the one tone."""
    out: list[str] = []
    changes: list[tuple[str, str]] = []
    for line in text.split("\n"):
        mode = cap if cap is not None else ceiling(rel, line)
        new, found = convert_line(line, hue, sat, mode)
        out.append(new)
        changes += found
    return "\n".join(out), changes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hue", type=float, default=HUE, help="one hue for everything, in degrees, instead of the navy ramp")
    ap.add_argument("--sat", type=float, default=SAT, help="its saturation, 0 (grey) to 1, with --hue")
    ap.add_argument("--cap", type=float, default=None, help="keep the hues, bring only the saturation above this down to it")
    ap.add_argument("--check", action="store_true", help="change nothing; exit 1 if any colour is not in tone")
    args = ap.parse_args()
    total = 0
    for path in sorted(SRC.rglob("*")):
        if path.suffix not in EXT or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        new, changes = convert(text, args.hue, args.sat, args.cap, path.relative_to(SRC).as_posix())
        if not changes:
            continue
        total += len(changes)
        print(f"{path.relative_to(SRC)}: {len(changes)}")
        for a, b in changes[:6]:
            print(f"    {a} -> {b}")
        if not args.check:
            path.write_text(new, encoding="utf-8")
    print(f"{total} colours {'not in tone' if args.check else 'set to the tone'}")
    return 1 if (args.check and total) else 0


if __name__ == "__main__":
    sys.exit(main())


