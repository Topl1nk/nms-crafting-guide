"""Download the NMS-Handbook JSON tables into .cache/.

NMS-Handbook (https://github.com/ApexFatality93/NMS-Handbook) parses the game's
own NMS_REALITY_GCRECIPETABLE.MXML into JSON, so these files are the recipe
table as the game ships it -- not a wiki transcription. Only four of its tables
are needed; the repo as a whole is ~7,000 files.

Run via `mise run fetch`. The downloaded files stay in .cache/ (gitignored);
`build_data.py` turns them into the committed data/*.json.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

RAW = "https://raw.githubusercontent.com/ApexFatality93/NMS-Handbook/main/JSON_Files"
TABLES = [
    "Refining_Table.json",
    "Cooking_Table.json",
    "Substance_Table.json",
    "Product_Table.json",
]

CACHE = Path(__file__).resolve().parent.parent / ".cache"


def main() -> int:
    CACHE.mkdir(exist_ok=True)
    for name in TABLES:
        dest = CACHE / name
        url = f"{RAW}/{name}"
        print(f"fetching {name} ... ", end="", flush=True)
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                dest.write_bytes(resp.read())
        except Exception as exc:  # noqa: BLE001 - report and stop, whatever it is
            print(f"FAILED ({exc})")
            return 1
        print(f"{dest.stat().st_size / 1024:.0f} KiB")
    print(f"\nWrote to {CACHE}. Now run: mise run build-data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
