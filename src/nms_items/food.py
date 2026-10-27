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
# else. Keyed by the game's stat id (Item.effect_id), which is the same in every
# language; the stat's display name is not.
EFFECT_USE = {
    "Suit_Protection_WaterDrain": "underwater exploration",
    "Suit_Energy": "long surface treks",
    "Suit_Protection": "extreme planets, storms",
    "Suit_Protection_HeatDrain": "scorched planets",
    "Suit_Protection_ColdDrain": "frozen planets",
    "Suit_Protection_ToxDrain": "toxic planets",
    "Suit_Protection_RadDrain": "irradiated planets",
    "Suit_Armour_Shield_Strength": "combat, sentinels",
    "Suit_Jetpack_Tank": "vertical caves, cliff bases",
    "Suit_Stamina_Strength": "crossing ground on foot",
    "Suit_Stamina_Recovery": "crossing ground on foot",
    "Weapon_Laser_Mining_Speed": "mining runs",
    "Weapon_Laser_MiningBonus": "mining runs - more per rock",
    "Weapon_Scan_Recharge_Time": "keeping tech topped up",
    "Suit_Energy_Regen": "exocraft and base power",
    "Suit_AutoTranslator": "learning alien languages fast",
    "Weapon_Scan_Discovery_Creature": "scanning creatures for units",
    "Weapon_Scan_Discovery_Flora": "scanning plants for units",
    "Weapon_Scan_Discovery_Mineral": "scanning minerals for units",
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
        return EFFECT_USE.get(self.item.effect_id, "")


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
