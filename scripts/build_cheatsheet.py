"""Select the cheat-sheet recipes and write them to data/cheatsheet.json.

The point of the sheet is not to reprint 1,680 recipes -- it is the handful
worth memorising. Everything here is computed from the game's own recipe table
(see build_data.py), so when the game patches a ratio the sheet follows.

Selection is deliberate, not "top N by one number":
  * self-loops       the x6 multipliers, the only recipes that grow a stack
  * nanites          every converter, ranked by nanites/hour/refiner
  * precious metals  the alloy engine, which is where the money actually is
  * profit           best units per batch, and best units per machine-hour
  * essentials       fuels and the things you stop mining once you can refine
  * cooking          the edible products worth the processor time
Plus two lists that only fall out of a graph walk: what Tier 0 reaches, and
what no recipe produces at all.

Run via `mise run cheatsheet-data` (or just `mise run pdf`, which chains it).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from nms_items import graph  # noqa: E402
from nms_items.model import SOURCE_SETS, TIER0, Book, Recipe  # noqa: E402

NANITES = "TECHFRAG"

# Things you should stop going out of your way to mine once a refiner is up.
ESSENTIALS = [
    "STELLAR2",    # Chromatic Metal
    "FUEL2",       # Condensed Carbon
    "CATALYST2",   # Sodium Nitrate
    "LAND3",       # Magnetised Ferrite
    "LAND2",       # Pure Ferrite
    "CAVE2",       # Ionised Cobalt
    "LAUNCHSUB2",  # Deuterium (pulse drive)
    "LAUNCHFUEL",  # Starship Launch Fuel
    "DUSTY1",      # Pyrite
    "WATER1",      # Salt
    "FARMPROD3",   # Glass
    "OXYGEN",      # Oxygen
]


def row(book: Book, recipe: Recipe, extra: dict | None = None) -> dict:
    data = {
        "make": recipe.output_label,
        "from": recipe.inputs_label,
        "mult": recipe.multiplier_label,
        "time": recipe.time_label,
        "machine": recipe.machine_short,
        "rate": round(recipe.rate),
        "profit": recipe.profit,
        "operation": recipe.operation,
    }
    if extra:
        data.update(extra)
    return data


def main() -> int:
    book = Book()
    refine = [r for r in book.recipes if r.domain == "refine"]
    cook = [r for r in book.recipes if r.domain == "cook"]

    # 1. Self-multiplying loops: the stack grows every pass.
    loops = sorted(
        (r for r in refine if r.loop > 1),
        key=lambda r: (-r.loop, r.time),
    )

    # 2. Nanite converters, ranked by throughput per refiner rather than by the
    #    headline number -- a 230-nanite recipe that takes 53 minutes loses to a
    #    50-nanite one that takes a minute.
    nanites = sorted(
        (r for r in refine if r.output.id == NANITES),
        key=lambda r: -r.rate,
    )

    # 3. The precious-metal engine: anything that outputs Gold, Silver, Platinum
    #    or Chromatic Metal at a gain, plus the alloys that feed it.
    metals = {"ASTEROID1", "ASTEROID2", "ASTEROID3", "STELLAR2"}
    engine = sorted(
        (r for r in refine if r.output.id in metals and r.profit > 0),
        key=lambda r: -r.profit,
    )

    # 4/5. Money: per batch, and per hour of machine time.
    by_profit = sorted((r for r in refine if r.profit > 0), key=lambda r: -r.profit)
    by_hour = sorted(
        (r for r in refine if r.profit > 0 and r.time),
        key=lambda r: -(r.profit * 3600 / r.time),
    )

    # 6. Essentials: the cheapest way to make each, by machine time.
    essentials = []
    for item_id in ESSENTIALS:
        candidates = [r for r in book.produced_by.get(item_id, []) if r.domain == "refine"]
        if not candidates:
            continue
        best = min(candidates, key=lambda r: (r.time / r.output.n, -r.ratio))
        essentials.append(row(book, best))

    # 7. Cooking, ranked by value per processor-hour.
    cooking = sorted(
        (r for r in cook if r.profit > 0 and r.time),
        key=lambda r: -(r.profit * 3600 / r.time),
    )

    tier0 = sorted(book.name(i) for i in graph.reachable(book, set(TIER0)))
    tier1_extra = sorted(
        book.name(i)
        for i in graph.reachable(book, set(SOURCE_SETS["Tier 1 - + asteroids"]))
        - graph.reachable(book, set(TIER0))
        - set(TIER0)
    )
    # Restricted to the refiner: the cooking table pulls in every fish, egg and
    # flora, none of which anyone expects to refine into existence.
    refine_inputs = {
        ing.id for r in refine for ing in r.inputs
    }
    refine_outputs = {r.output.id for r in refine}
    must_find = sorted(
        book.name(i) for i in refine_inputs - refine_outputs
    )

    sheet = {
        "counts": {
            "refine": len(refine),
            "cook": len(cook),
            "items": len(book.items),
        },
        "loops": [row(book, r) for r in loops],
        "nanites": [row(book, r) for r in nanites],
        "engine": [row(book, r) for r in engine[:12]],
        "profit": [row(book, r) for r in by_profit[:14]],
        "per_hour": [
            row(book, r, {"per_hour": round(r.profit * 3600 / r.time)})
            for r in by_hour[:14]
        ],
        "essentials": essentials,
        "cooking": [
            row(book, r, {"per_hour": round(r.profit * 3600 / r.time)})
            for r in cooking[:14]
        ],
        "tier0": tier0,
        "tier1_extra": tier1_extra,
        "must_find": must_find,
        "sources": {
            "tier0": [book.name(i) for i in TIER0],
            "tier1": [book.name(i) for i in SOURCE_SETS["Tier 1 - + asteroids"]],
        },
    }

    out = ROOT / "data" / "cheatsheet.json"
    out.write_text(json.dumps(sheet, indent=1))
    print(f"wrote {out}")
    for key in ("loops", "nanites", "engine", "profit", "per_hour", "essentials", "cooking"):
        print(f"  {key:11} {len(sheet[key])} rows")
    print(f"  tier0       {len(tier0)} materials")
    print(f"  must_find   {len(must_find)} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
