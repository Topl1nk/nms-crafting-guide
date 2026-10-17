"""Export everything the TUI computes into web/data.json, for the static site.

The web page is a second front end over the same answers, not a second copy of
the logic. Anything the Python side decides -- how gettable an item is, which
container it goes in, the cheapest recipe per item for each source tier, the
nanite ladder, the dishes per buff -- is decided here, once, by the same
modules the TUI and the tests use, and shipped as data. The browser only
filters, sorts and draws.

What the page still does itself is what is cheap and has nowhere else to run:
search, the chain tree walk over the exported `via` maps, the inventory
matching, and the portal arithmetic (four lines of modular addition, pinned on
both sides by the galaxy-centre test).

The same bundle is also written out as markdown -- llms.txt, a page per section
and per item, a sitemap -- by build_markdown.py, for readers that do not run
JavaScript.

Run via `mise run web:data`; `mise run site` serves the result locally, and
.github/workflows/pages.yml publishes it to GitHub Pages on every push to main.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import build_markdown  # noqa: E402
from nms_items import food, graph, portals  # noqa: E402
from nms_items.ease import TIER_ORDER, EaseIndex  # noqa: E402
from nms_items.model import DATA_DIR, SOURCE_SETS, Book  # noqa: E402
from nms_items.storage import StorageGuide  # noqa: E402

WEB = ROOT / "web"
OUT = WEB / "data.json"

DOMAIN_SETS = {"refine": ("refine",), "all": ("refine", "cook")}


def source(data_dir: Path = DATA_DIR) -> dict | None:
    """Where the recipe data came from, from data/source.json, for the site to say.

    `from` is "game" (extracted from the game files) or "handbook" (the
    NMS-Handbook fallback, which records no game version). None when the file
    is missing, so the pages fall back to saying the version is unknown.
    """
    path = data_dir / "source.json"
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    game = raw.get("game") or {}
    build = str(game.get("build") or "")
    return {
        "from": raw.get("source", ""),
        "game": game.get("update", ""),
        "version": game.get("version", ""),
        "build": int(build) if build.isdigit() else None,
        "extracted": raw.get("extracted") or raw.get("fetched") or "",
        "summary": raw.get("summary", ""),
        "tools": raw.get("tools", {}),
    }


def build(book: Book) -> dict:
    ease = EaseIndex(book)
    guide = StorageGuide.load()

    # Storage: one entry per distinct (rule, action) outcome, and each item
    # points at its outcome -- 1,447 items share a few dozen answers.
    outcomes: list[dict] = []
    outcome_index: dict[tuple, int] = {}
    item_home: dict[str, int] = {}
    for item in book.items.values():
        placement = guide.place(item)
        key = (placement.home.key, placement.action, placement.why, placement.no_rocket)
        if key not in outcome_index:
            outcome_index[key] = len(outcomes)
            outcomes.append({
                "home": placement.home.key,
                "action": placement.action,
                "label": placement.label,
                "verdict": placement.verdict,
                "advice": placement.advice(),
                "why": placement.why,
            })
        item_home[item.id] = outcome_index[key]

    items = {}
    for item in book.items.values():
        row = {
            "name": item.name,
            "sub": item.subtitle,
            "cat": item.category,
            "value": item.value,
            "store": item_home[item.id],
        }
        if item.effect and item.potency > 0:
            row["effect"] = item.effect
            row["potency"] = round(item.potency, 3)
        items[item.id] = row

    # Ease for everything a recipe reads or writes: that is all the page asks
    # about, and the other ~750 items would only carry "loot (unknown)".
    touched = set(book.produced_by) | set(book.consumed_by)
    eases = {}
    for item_id in sorted(touched):
        e = ease.of(item_id)
        eases[item_id] = {
            "label": e.label,
            "band": e.band,
            "score": round(e.score, 2),
            "describe": e.describe(book),
            "where": e.where,
            "note": e.note,
        }

    recipes = [
        {
            "domain": r.domain,
            "op": r.operation,
            "out": [r.output.id, r.output.n],
            "in": [[ing.id, ing.n] for ing in r.inputs],
            "time": r.time,
            "machine": r.machine,
            "ratio": r.ratio,
            "loop": r.loop,
            "profit": r.profit,
            "rate": r.rate,
        }
        for r in book.recipes
    ]

    # The chain planner's search, done here: for each source tier and recipe
    # set, the recipe that makes each item cheapest. The page only walks it.
    tiers = []
    for name in TIER_ORDER:
        sources = set(SOURCE_SETS[name])
        via = {}
        for key, domains in DOMAIN_SETS.items():
            _, best = graph.cheapest_costs(book, sources, domains)
            via[key] = {item_id: recipe.index for item_id, recipe in best.items()}
        tiers.append({"name": name, "sources": SOURCE_SETS[name], "via": via})

    nanites = [
        {"recipe": row.recipe.index, "per_input": round(row.per_input, 4),
         "units_cost": row.units_cost}
        for row in graph.nanite_ladder(book)
    ]

    cooking = [
        {
            "effect": effect,
            "use": food.EFFECT_USE.get(effect, ""),
            "dishes": [
                {"item": d.item.id, "recipe": d.recipe.index, "ways": d.ways}
                for d in dishes
            ],
        }
        for effect, dishes in food.by_effect(book).items()
    ]

    homes = [
        {"key": h.key, "name": h.name, "label": h.label, "note": h.note,
         "container": h.is_container}
        for h in guide.homes.values()
    ]

    glyph_raw = json.loads((DATA_DIR / "glyphs.json").read_text(encoding="utf-8"))
    glyphs = [
        {"hex": g["hex"], "name": g["name"], "viewbox": g["viewbox"],
         "transform": g["transform"], "paths": g["paths"]}
        for g in glyph_raw["glyphs"]
    ]

    locations_raw = json.loads((DATA_DIR / "locations.json").read_text(encoding="utf-8"))

    return {
        "source": source(),
        "items": items,
        "ease": eases,
        "recipes": recipes,
        "tiers": tiers,
        "nanite": graph.NANITE_ID,
        "nanites": nanites,
        "cooking": cooking,
        "storage": {"homes": homes, "outcomes": outcomes},
        "multitools": json.loads((DATA_DIR / "multitools.json").read_text(encoding="utf-8")),
        "glyphs": glyphs,
        "portals": {
            "glyph_names": portals.GLYPH_NAMES,
            "galaxies": portals.GALAXY_NAMES,
            "kinds": portals.KINDS,
            "origins": portals.ORIGINS,
            "max_system": portals.MAX_SYSTEM_INDEX,
            "locations": locations_raw.get("locations", []),
        },
    }


def main() -> None:
    bundle = build(Book())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.0f} KiB)")
    # The same bundle as markdown, for whatever reads the site without running
    # its JavaScript: llms.txt, a page per section and per item, a sitemap.
    build_markdown.write(bundle, WEB, ROOT)
    # The cheat sheets and the README's TUI screenshots ride along, so the
    # site links and shows them without a second host.
    for src, dest, pattern in (("docs/pdf", "pdf", "*.pdf"), ("docs/img", "img", "*.svg")):
        (WEB / dest).mkdir(exist_ok=True)
        for path in sorted((ROOT / src).glob(pattern)):
            shutil.copy2(path, WEB / dest / path.name)
            print(f"copied {(WEB / dest / path.name).relative_to(ROOT)}")


if __name__ == "__main__":
    main()
