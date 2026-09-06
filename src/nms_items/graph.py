"""Chain planning over the recipe graph.

The recipe table is an AND-OR graph: an item can be produced by any *one* of
several recipes (OR), but a recipe needs *all* of its inputs (AND). Plain
Dijkstra does not apply; the variant that does is Knuth's generalisation, which
is what `cheapest_costs` implements -- settle the cheapest item, then relax
every recipe whose inputs are now all settled.

Cost is measured in refiner-seconds per unit of output, so the plan you get is
the one that occupies a machine for the least time, not merely the one with the
fewest steps. Items in the source set cost nothing: they are things you pick up.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

from .model import Book, Recipe

INF = float("inf")


@dataclass(slots=True)
class Step:
    """One node of a production plan: `qty` of `item_id`, made by `recipe`."""

    item_id: str
    qty: int
    recipe: Recipe | None = None
    batches: int = 0
    children: list["Step"] = field(default_factory=list)
    # True when the item is in the source set, i.e. you go and pick it up.
    raw: bool = False


@dataclass(slots=True)
class Plan:
    target: str
    qty: int
    root: Step
    raw_totals: dict[str, int]
    total_seconds: float
    steps: int

    @property
    def ok(self) -> bool:
        return self.root.recipe is not None or self.root.raw


def cheapest_costs(
    book: Book,
    sources: set[str],
    domains: tuple[str, ...] = ("refine",),
) -> tuple[dict[str, float], dict[str, Recipe]]:
    """Seconds-per-unit for every item reachable from `sources`.

    Returns the cost map and, for each item, the recipe that achieved it.
    """
    recipes = [r for r in book.recipes if r.domain in domains]

    # Which recipes wait on which ingredient, so relaxation is O(edges).
    waiting: dict[str, list[Recipe]] = {}
    for recipe in recipes:
        for ing in recipe.inputs:
            waiting.setdefault(ing.id, []).append(recipe)

    cost: dict[str, float] = {item_id: 0.0 for item_id in sources}
    via: dict[str, Recipe] = {}
    settled: set[str] = set()
    queue: list[tuple[float, str]] = [(0.0, item_id) for item_id in sources]
    heapq.heapify(queue)

    while queue:
        item_cost, item_id = heapq.heappop(queue)
        if item_id in settled:
            continue
        settled.add(item_id)

        for recipe in waiting.get(item_id, []):
            if any(ing.id not in settled for ing in recipe.inputs):
                continue
            out_id = recipe.output.id
            if out_id in settled:
                continue
            total = recipe.time + sum(cost[ing.id] * ing.n for ing in recipe.inputs)
            candidate = total / recipe.output.n
            if candidate < cost.get(out_id, INF):
                cost[out_id] = candidate
                via[out_id] = recipe
                heapq.heappush(queue, (candidate, out_id))

    return cost, via


def plan(
    book: Book,
    target: str,
    sources: set[str],
    qty: int = 1,
    domains: tuple[str, ...] = ("refine",),
) -> Plan:
    """Build a production tree for `qty` of `target` out of `sources`."""
    cost, via = cheapest_costs(book, sources, domains)
    raw_totals: dict[str, int] = {}
    counter = [0]

    def build(item_id: str, need: int, depth: int = 0) -> Step:
        if item_id in sources or item_id not in via or depth > 12:
            raw_totals[item_id] = raw_totals.get(item_id, 0) + need
            return Step(item_id, need, raw=item_id in sources)

        recipe = via[item_id]
        batches = math.ceil(need / recipe.output.n)
        counter[0] += 1
        step = Step(item_id, need, recipe=recipe, batches=batches)
        for ing in recipe.inputs:
            step.children.append(build(ing.id, ing.n * batches, depth + 1))
        return step

    root = build(target, qty)
    total_seconds = _tree_seconds(root)
    return Plan(target, qty, root, raw_totals, total_seconds, counter[0])


def _tree_seconds(step: Step) -> float:
    total = step.recipe.time * step.batches if step.recipe else 0.0
    return total + sum(_tree_seconds(child) for child in step.children)


def reachable(
    book: Book,
    sources: set[str],
    domains: tuple[str, ...] = ("refine",),
) -> set[str]:
    """Everything makeable from `sources`, sources excluded."""
    cost, _ = cheapest_costs(book, sources, domains)
    return set(cost) - sources


def never_produced(book: Book) -> list[str]:
    """Items that appear as an ingredient but are the output of no recipe.

    These are the things the guides say you have to go and find.
    """
    return sorted(
        item_id for item_id in book.consumed_by
        if item_id not in book.produced_by
    )


def craftable_now(
    book: Book,
    have: dict[str, int],
    domains: tuple[str, ...] = ("refine", "cook"),
) -> list[tuple[Recipe, int]]:
    """Recipes every input of which is in `have`, with how many batches fit."""
    out: list[tuple[Recipe, int]] = []
    for recipe in book.recipes:
        if recipe.domain not in domains:
            continue
        batches = INF
        for ing in recipe.inputs:
            stock = have.get(ing.id, 0)
            if stock < ing.n:
                batches = 0
                break
            batches = min(batches, stock // ing.n)
        if batches:
            out.append((recipe, int(batches)))
    out.sort(key=lambda pair: (-pair[0].ratio, pair[0].time))
    return out


def one_hop_away(
    book: Book,
    have: dict[str, int],
    domains: tuple[str, ...] = ("refine", "cook"),
) -> list[tuple[Recipe, list[tuple[str, int]]]]:
    """Recipes blocked on exactly one missing ingredient, and what is missing."""
    out: list[tuple[Recipe, list[tuple[str, int]]]] = []
    for recipe in book.recipes:
        if recipe.domain not in domains:
            continue
        missing = [
            (ing.id, ing.n - have.get(ing.id, 0))
            for ing in recipe.inputs
            if have.get(ing.id, 0) < ing.n
        ]
        if len(missing) == 1:
            out.append((recipe, missing))
    out.sort(key=lambda pair: (pair[1][0][1], -pair[0].ratio))
    return out
