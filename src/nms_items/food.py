"""Cooked food: what eating it does, and whether cooking beats selling.

Two questions this answers, both of which the recipe table alone cannot:

  * every cooked product grants a temporary buff -- the files name the stat and
    give it a 0-1 quality, which is the only strength figure they record, so
    that is what `potency` is here (a few ingredients rate above 1.0);
  * cooking multiplies base value enormously (Ambrosial Curse is 199,200 units
    out of three foraged ingredients), so the same dish is both the buff and
    the payday. `uplift` is what one batch adds over its inputs.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import Book, Item, Recipe

# Roughly, what each buff is for -- the files give the stat name and nothing
# else. Anything not listed falls back to the raw stat name.
EFFECT_USE = {
    "Breathing Efficiency": "underwater exploration",
    "Life Support Tanks": "long surface treks",
    "Hazard Protection Battery": "extreme planets, storms",
    "Heat Resistance": "scorched planets",
    "Cold Resistance": "frozen planets",
    "Toxic Resistance": "toxic planets",
    "Radiation Resistance": "irradiated planets",
    "Shield Strength": "combat, sentinels",
    "Jetpack Tanks": "vertical caves, cliff bases",
    "Sprint Distance": "crossing ground on foot",
    "Sprint Recovery Time": "crossing ground on foot",
    "Mining Speed": "mining runs",
    "Resources Mined": "mining runs - more per rock",
    "Recharge Time": "keeping tech topped up",
    "Solar Panel Power": "exocraft and base power",
    "Words Translated": "learning alien languages fast",
    "Fauna Analysis Rewards": "scanning creatures for units",
    "Flora Analysis Rewards": "scanning plants for units",
    "Mineral Analysis Rewards": "scanning minerals for units",
}


@dataclass(slots=True)
class Dish:
    item: Item
    recipe: Recipe        # the quickest way to cook it
    ways: int             # how many recipes produce it

    @property
    def effect(self) -> str:
        return self.item.effect

    @property
    def potency(self) -> float:
        return self.item.potency

    @property
    def value(self) -> int:
        return self.item.value

    @property
    def uplift(self) -> int:
        """Units gained over the ingredients, one batch."""
        return self.recipe.profit

    @property
    def use(self) -> str:
        return EFFECT_USE.get(self.effect, "")


def dishes(book: Book) -> list[Dish]:
    """Every product a Nutrient Processor makes, best recipe attached."""
    out: list[Dish] = []
    for item_id, recipes in book.produced_by.items():
        cooked = [r for r in recipes if r.domain == "cook"]
        item = book.items.get(item_id)
        # A couple of Nutrient Processor outputs are not food at all -- animal
        # feed and Carbon Nanotubes carry a stat name but no potency.
        if not cooked or item is None or not item.effect or item.potency <= 0:
            continue
        best = min(cooked, key=lambda r: (r.time, len(r.inputs)))
        out.append(Dish(item=item, recipe=best, ways=len(cooked)))
    return out


def by_effect(book: Book) -> dict[str, list[Dish]]:
    """Dishes grouped by the stat they boost, strongest first within each."""
    grouped: dict[str, list[Dish]] = {}
    for dish in dishes(book):
        grouped.setdefault(dish.effect, []).append(dish)
    for group in grouped.values():
        group.sort(key=lambda d: (-d.potency, -d.value))
    return dict(
        sorted(grouped.items(), key=lambda kv: (-max(d.potency for d in kv[1]), kv[0]))
    )
