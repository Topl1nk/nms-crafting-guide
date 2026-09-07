"""Download the 16 portal glyph images into .cache/glyphs/.

The glyph shapes are a game asset; nobody publishes them as vectors. The best
public raster of them is the set nmsportals.github.io draws its dial with --
256x256 RGBA PNGs, white line art on transparent, one per hex digit, named for
the digit. That naming is the useful part: `a.png` *is* glyph `A`, the eleventh
symbol on the dial, so the download needs no mapping table.

Run via `mise run glyphs`, which chains straight into build_glyphs.py. The PNGs
stay in .cache/ (gitignored); what gets committed is data/glyphs.json, the
traced outlines. Rerunning is only needed if that file is lost or the upstream
art changes, which it has not since 2018.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

# The same 16 files the site's CSS references, in dial order.
BASE = "https://nmsportals.github.io/img/glyphs"
DIGITS = "0123456789abcdef"

CACHE = Path(__file__).resolve().parent.parent / ".cache" / "glyphs"


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    total = 0
    for digit in DIGITS:
        dest = CACHE / f"{digit}.png"
        url = f"{BASE}/{digit}.png"
        print(f"fetching {digit}.png ... ", end="", flush=True)
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                data = resp.read()
        except Exception as exc:  # noqa: BLE001 - report and stop, whatever it is
            print(f"FAILED ({exc})")
            return 1
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            print("FAILED (not a PNG)")
            return 1
        dest.write_bytes(data)
        total += len(data)
        print(f"{len(data) / 1024:.0f} KiB")
    print(f"\nWrote {total / 1024:.0f} KiB to {CACHE}. "
          f"Now run: mise run build-glyphs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
