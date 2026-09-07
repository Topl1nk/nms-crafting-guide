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
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "src"))

from nms_items import food, glyphart, graph, multitools, portals  # noqa: E402
from nms_items.ease import EaseIndex  # noqa: E402
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


def best_per_output(recipes: list[Recipe], limit: int) -> list[Recipe]:
    """Keep the best row per distinct output.

    Without this the profit tables are eleven ways to make Bone Broth: the
    top-by-any-number lists are dominated by one output whose recipe differs
    only in which interchangeable ingredient it takes.
    """
    seen: set[str] = set()
    out: list[Recipe] = []
    for recipe in recipes:
        if recipe.output.id in seen:
            continue
        seen.add(recipe.output.id)
        out.append(recipe)
        if len(out) == limit:
            break
    return out


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


def portal_page() -> dict:
    """The portal reference plus every saved address, both forms precomputed.

    Typst cannot do the arithmetic, so the galactic address is worked out here.
    While we are in there, every committed address is round-tripped and the
    galaxy-centre invariant re-checked, so a typo in data/locations.json fails
    the build rather than printing a sheet you cannot dial.
    """
    centre = portals.Address.from_portal_code("000000000000")
    if centre.galactic != "07FF:007F:07FF:0000":
        raise SystemExit(f"portal conversion moved: centre is {centre.galactic}")

    # The sheet draws the symbols straight out of data/glyphs.json, which no
    # Python here writes -- so this is the only place that can catch it having
    # drifted from the dial. One position out and every address on the page
    # points at a different star, and it would look perfectly plausible.
    art = glyphart.load()
    for i, name in enumerate(portals.GLYPH_NAMES):
        g = art.glyphs[i]
        if (g.position, g.hex, g.name) != (i + 1, f"{i:X}", name):
            raise SystemExit(
                f"data/glyphs.json is off the dial at {i}: expected "
                f"{i + 1}/{i:X}/{name}, found {g.position}/{g.hex}/{g.name}. "
                f"Rebuild it: mise run glyphs")

    book = portals.LocationBook.load()
    rows = []
    for loc in book.locations:
        address = loc.address
        if address.portal_code != loc.code:
            raise SystemExit(f"{loc.name}: {loc.code} does not round-trip")
        if address.warnings:
            raise SystemExit(f"{loc.name}: {address.warnings[0]}")
        rows.append({
            "name": loc.name,
            "code": loc.code,
            "grouped": address.portal_grouped,
            "galactic": address.galactic,
            "kind": loc.kind,
            "origin": loc.origin,
            "galaxy": loc.galaxy_label,
            "detail": loc.detail,
            "where": loc.where,
            "source": loc.source,
            "added": loc.added,
        })

    example = portals.Address.from_portal_code("11AC008F4025")
    return {
        "source": book.source,
        "glyphs": [
            {"position": i + 1, "hex": f"{i:X}", "name": name}
            for i, name in enumerate(portals.GLYPH_NAMES)
        ],
        "galaxies": [
            {"number": i + 1, "name": name}
            for i, name in enumerate(portals.GALAXY_NAMES)
        ],
        "example": {
            "code": example.portal_code,
            "grouped": example.portal_grouped,
            "galactic": example.galactic,
            "planet": f"{example.planet:X}",
            "system": f"{example.system:03X}",
            "y": f"{example.y:02X}",
            "z": f"{example.z:03X}",
            "x": f"{example.x:03X}",
            "voxel": example.voxel_label.replace("   ", "  "),
        },
        "locations": rows,
        "counts": {
            "mine": book.count("mine"),
            "shared": book.count("shared"),
        },
    }


def main() -> int:
    book = Book()
    refine = [r for r in book.recipes if r.domain == "refine"]
    cook = [r for r in book.recipes if r.domain == "cook"]

    # 1. Self-multiplying loops: the stack grows every pass.
    loops = sorted(
        (r for r in refine if r.loop > 1),
        key=lambda r: (-r.loop, r.time),
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

    # 6. Essentials: the route the planner would actually take from asteroid
    #    tier, not merely the fastest recipe -- picking by time alone suggests
    #    seeding Pyrite with Lithium and Sodium Nitrate with Crystal Sulphide,
    #    both of which are rarer than the thing being made.
    _, via = graph.cheapest_costs(book, set(SOURCE_SETS["Tier 1 - + asteroids"]))
    ease = EaseIndex(book)
    essentials = []
    for item_id in ESSENTIALS:
        if item_id in via:
            essentials.append(row(book, via[item_id]))
            continue
        # Chromatic Metal and friends are not reachable from any source tier --
        # they need a stellar-metal seed you find once. Fall back to whichever
        # recipe has the most gettable ingredients.
        candidates = [r for r in book.produced_by.get(item_id, []) if r.domain == "refine"]
        if candidates:
            best = max(candidates, key=lambda r: (ease.of_recipe(r).score, r.ratio))
            how = ease.of_recipe(best)
            # Only annotate when the blocker really is a seed material; an item
            # that is itself a Tier 0 pickup just has no cheaper route to show.
            extra = {"seed": how.describe(book)} if how.tier is None else None
            essentials.append(row(book, best, extra))

    # 7. Cooking, ranked by value per processor-hour.
    cooking = sorted(
        (r for r in cook if r.profit > 0 and r.time),
        key=lambda r: -(r.profit * 3600 / r.time),
    )

    # 8. Nanites: the second currency, which the units columns say nothing
    #    about, with how gettable each source is.
    nanite_rows = []
    for entry in graph.nanite_ladder(book):
        how = ease.of_recipe(entry.recipe)
        nanite_rows.append(
            row(book, entry.recipe, {
                "nanites": entry.nanites,
                "per_hour": round(entry.per_hour),
                "per_input": round(entry.per_input, 2),
                "gettable": how.label,
                "band": how.band,
                "where": how.where or how.describe(book),
                "note": how.note,
            })
        )

    # 9. Cooking for buffs rather than for money: the strongest dish per stat.
    effects = []
    for effect, group in food.by_effect(book).items():
        effects.append({
            "effect": effect,
            "use": group[0].use,
            "count": len(group),
            "dishes": [
                {
                    "dish": dish.item.name,
                    "potency": dish.potency,
                    "value": dish.value,
                    "uplift": dish.uplift,
                    "from": dish.recipe.inputs_label,
                    "time": dish.recipe.time_label,
                }
                for dish in group[:3]
            ],
        })

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
        "nanites": nanite_rows,
        # Not deduped: the point of this section is that several different
        # alloys all break down into the same metal, so the repeats are the
        # information.
        "engine": [row(book, r) for r in engine[:12]],
        "profit": [row(book, r) for r in best_per_output(by_profit, 14)],
        "per_hour": [
            row(book, r, {"per_hour": round(r.profit * 3600 / r.time)})
            for r in best_per_output(by_hour, 14)
        ],
        "essentials": essentials,
        "cooking": [
            row(book, r, {"per_hour": round(r.profit * 3600 / r.time)})
            for r in best_per_output(cooking, 14)
        ],
        "effects": effects,
        # Straight passthrough: multi-tools are not in the recipe tables, so
        # data/multitools.json is the source for both the TUI and the sheet.
        "multitools": json.loads((DATA / "multitools.json").read_text()),
        # Same deal: portal addresses are not in the recipe tables either.
        "portals": portal_page(),
        "tier0": tier0,
        "tier1_extra": tier1_extra,
        "must_find": must_find,
        "sources": {
            "tier0": [book.name(i) for i in TIER0],
            "tier1": [book.name(i) for i in SOURCE_SETS["Tier 1 - + asteroids"]],
        },
    }

    out = DATA / "cheatsheet.json"
    out.write_text(json.dumps(sheet, indent=1))
    print(f"wrote {out}")
    for key in (
        "loops", "nanites", "engine", "profit", "per_hour", "essentials",
        "cooking", "effects",
    ):
        print(f"  {key:11} {len(sheet[key])} rows")
    tools = sheet["multitools"]
    print(f"  multitools  {len(tools['types'])} types, {len(tools['weapons'])} weapons, "
          f"{len(tools['rules'])} tips")
    ports = sheet["portals"]
    print(f"  portals     {len(ports['locations'])} addresses "
          f"({ports['counts']['mine']} mine, {ports['counts']['shared']} shared)")
    print(f"  tier0       {len(tier0)} materials")
    print(f"  must_find   {len(must_find)} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
