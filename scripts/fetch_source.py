"""Download the NMS-Handbook JSON tables into .cache/handbook/.

NMS-Handbook (https://github.com/ApexFatality93/NMS-Handbook) parses the game's
own NMS_REALITY_GCRECIPETABLE.MXML into JSON, so these files are the recipe
table as the game ships it -- not a wiki transcription. Only four of its tables
are needed; the repo as a whole is ~7,000 files.

Run via `mise run data:fetch`. The downloaded files stay in .cache/handbook/ (gitignored);
`build_data.py --source handbook` turns them into the committed data/*.json.

This is the fallback source now: `mise run extract:all` reads the same tables
straight out of the installed game, and NMS-Handbook lags behind patches.
"""

from __future__ import annotations

import datetime as dt
import json
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

CACHE = Path(__file__).resolve().parent.parent / ".cache" / "handbook"


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
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
    # Read by build_data.py into data/source.json, so the committed data says
    # where it came from. Upstream does not say which game version it parsed.
    today = dt.date.today().isoformat()
    (CACHE / "_source.json").write_text(json.dumps({
        "source": "handbook",
        "summary": f"NMS-Handbook JSON ({RAW}), fetched {today}; game version not recorded upstream",
        "fetched": today,
    }, indent=1))
    print(f"\nWrote to {CACHE}. Now run: mise run data:build-handbook")
    return 0


if __name__ == "__main__":
    sys.exit(main())
