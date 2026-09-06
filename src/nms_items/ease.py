"""How hard is it to actually get the inputs?

A recipe's ratio says nothing about whether you can reach its ingredients. This
module answers that in the terms the question is usually asked in: can I make it
from stuff lying on the ground, how many refining steps away is it, how many
different materials does it want, and how much of them.

Two sources feed it. The graph gives everything derivable from the recipe table:
reachability tier, chain depth, raw breadth and raw volume. The game files never
record where a loot item is found, so that part comes from data/acquisition.json,
hand-written from the guides -- and where the guides say nothing, this says
"unknown" rather than guessing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from . import graph
from .model import SOURCE_SETS, Book

TIER_ORDER = ["Tier 0 - any planet", "Tier 1 - + asteroids", "Tier 2 - + harvester"]

# Where a tier lands before the per-recipe penalties.
TIER_BASE = {0: 100.0, 1: 85.0, 2: 70.0}
# ...and where loot lands, by how much of a detour the guides make it sound.
EFFORT_BASE = {"easy": 60.0, "medium": 40.0, "hard": 20.0}
UNKNOWN_BASE = 25.0
# An item a refiner does make, but only once you have a material none of the
# source tiers contain -- Chromatic Metal, which needs a stellar metal to seed
# it. Not loot, and not free either: you find the seed once and then the
# `1 of it + 1 Chromatic Metal -> 2 of it` loop keeps you in it forever.
SEEDED_BASE = 55.0

BANDS = [(80, "easy"), (60, "ok"), (40, "work"), (0, "hard")]


@dataclass(frozen=True, slots=True)
class Ease:
    """Why an item is easy or hard to get, and a single number to sort on."""

    item_id: str
    tier: int | None          # source tier that reaches it; None = not reachable
    steps: int                # refining steps from that tier's raw materials
    raws: int                 # distinct raw materials consumed
    units: int                # total raw units per one unit of output
    effort: str | None        # curated loot effort, when it is loot
    where: str                # curated acquisition text, "" when unknown
    note: str
    score: float
    # Ingredients a recipe needs that no source tier reaches. Non-empty means
    # the item is makeable, just not from nothing.
    seeds: tuple[str, ...] = ()

    @property
    def band(self) -> str:
        for floor, name in BANDS:
            if self.score >= floor:
                return name
        return "hard"

    @property
    def label(self) -> str:
        if self.seeds:
            return "needs seed"
        if self.tier is None:
            return f"loot ({self.effort or 'unknown'})"
        if self.steps == 0:
            return f"T{self.tier} raw"
        return f"T{self.tier} +{self.steps}"

    def describe(self, book: Book) -> str:
        if self.seeds:
            names = " or ".join(book.name(s) for s in self.seeds)
            return f"refinable once you have {names}"
        if self.tier is None:
            return self.where or "no recipe makes it, and the guides do not say where it drops"
        return (
            f"{self.steps} step(s) from {self.raws} raw material(s), "
            f"{self.units} unit(s) in total"
        )


class EaseIndex:
    """Ease for every item, computed once per Book."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.acquisition = _load_acquisition(book)
        self._cache: dict[str, Ease] = {}
        # Cheapest recipe per item at each tier, widest tier last so that the
        # narrowest (cheapest to reach) tier wins.
        self._tiers: list[tuple[int, set[str], dict]] = []
        for index, name in enumerate(TIER_ORDER):
            sources = set(SOURCE_SETS[name])
            _, via = graph.cheapest_costs(book, sources)
            self._tiers.append((index, sources, via))

    def of(self, item_id: str) -> Ease:
        if item_id not in self._cache:
            self._cache[item_id] = self._compute(item_id)
        return self._cache[item_id]

    def _compute(self, item_id: str) -> Ease:
        entry = self.acquisition.get(item_id, {})
        where = entry.get("where", "")
        note = entry.get("note", "")
        effort = entry.get("effort")

        for tier, sources, via in self._tiers:
            if item_id in sources:
                return Ease(item_id, tier, 0, 1, 1, None, where, note, TIER_BASE[tier])
            if item_id in via:
                steps, raws, units = _walk(via, sources, item_id)
                score = TIER_BASE[tier]
                score -= 5 * max(0, steps - 1)
                score -= 3 * max(0, raws - 1)
                score -= min(15.0, units / 20)
                return Ease(
                    item_id, tier, steps, raws, units, None, where, note,
                    max(0.0, score),
                )

        # Makeable, but every recipe wants something outside the source tiers.
        # Report the recipe that needs the fewest such seeds.
        recipes = self.book.produced_by.get(item_id, [])
        if recipes:
            reachable = self._tiers[-1][1] | set(self._tiers[-1][2])
            best: tuple[int, tuple[str, ...]] | None = None
            for recipe in recipes:
                missing = tuple(
                    ing.id for ing in recipe.inputs if ing.id not in reachable
                )
                if best is None or len(missing) < best[0]:
                    best = (len(missing), missing)
            if best and best[1]:
                seeds = tuple(dict.fromkeys(best[1]))
                seeded = max(0.0, SEEDED_BASE - 3 * (len(seeds) - 1))
                looted = EFFORT_BASE.get(effort or "", 0.0)
                # Runaway Mould and Pugneum are both refinable-with-a-seed and
                # lying on the ground; whichever route the guides rate higher is
                # the one to report.
                if seeded >= looted:
                    return Ease(
                        item_id, None, 1, len(seeds), 1, effort, where, note,
                        seeded, seeds,
                    )

        base = EFFORT_BASE.get(effort or "", UNKNOWN_BASE)
        return Ease(item_id, None, 0, 1, 1, effort, where, note, base)

    def of_recipe(self, recipe) -> Ease:
        """The hardest ingredient is what gates a recipe."""
        return min((self.of(ing.id) for ing in recipe.inputs), key=lambda e: e.score)


def _walk(via: dict, sources: set[str], item_id: str) -> tuple[int, int, int]:
    """Depth, distinct raw materials and total raw units behind one unit."""
    steps = 0
    raws: dict[str, int] = {}

    def visit(current: str, need: int, depth: int) -> None:
        nonlocal steps
        if current in sources or current not in via or depth > 12:
            raws[current] = raws.get(current, 0) + need
            return
        steps += 1
        recipe = via[current]
        batches = max(1, -(-need // recipe.output.n))
        for ing in recipe.inputs:
            visit(ing.id, ing.n * batches, depth + 1)

    visit(item_id, 1, 0)
    return steps, len(raws), sum(raws.values())


@lru_cache(maxsize=1)
def _acquisition_file(path: str) -> dict:
    try:
        return json.loads(open(path).read()).get("items", {})
    except (OSError, ValueError):
        return {}


def _load_acquisition(book: Book) -> dict:
    from .model import DATA_DIR

    return _acquisition_file(str(DATA_DIR / "acquisition.json"))
