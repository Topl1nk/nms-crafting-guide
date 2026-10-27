"""Ease scoring, the nanite ladder and the cooking-effect data."""

from __future__ import annotations

import pytest

from nms_items import food, graph
from nms_items.ease import EaseIndex
from nms_items.model import Book

from ids import one


@pytest.fixture(scope="module")
def book() -> Book:
    return Book()


@pytest.fixture(scope="module")
def ease(book: Book) -> EaseIndex:
    return EaseIndex(book)


def test_tier_sources_are_the_easiest_things(book: Book, ease: EaseIndex) -> None:
    assert ease.of(one("Oxygen")).label == "T0 raw"
    assert ease.of(one("Oxygen")).band == "easy"
    assert ease.of(one("Gold")).label == "T1 raw"


def test_refinable_items_report_their_depth(book: Book, ease: EaseIndex) -> None:
    mag = ease.of(one("Magnetised Ferrite"))
    assert mag.tier == 0
    assert mag.steps >= 1
    assert mag.band == "easy"


def test_seeded_items_are_not_called_loot(book: Book, ease: EaseIndex) -> None:
    """Chromatic Metal is makeable, just not from any source tier."""
    chromatic = ease.of(one("Chromatic Metal"))
    assert chromatic.seeds
    assert chromatic.label == "needs seed"


def test_loot_uses_the_curated_guide_data(book: Book, ease: EaseIndex) -> None:
    brain = ease.of(one("Hyaline Brain"))
    assert brain.tier is None
    assert brain.effort == "hard"
    assert brain.where  # where it drops, from data/acquisition.json (in the data's language)

    # An item with an easy loot source should not be reported as seeded even
    # though a refiner recipe for it exists.
    mould = ease.of(one("Runaway Mould"))
    assert mould.label == "loot (easy)"


def test_recipe_ease_is_the_hardest_ingredient(book: Book, ease: EaseIndex) -> None:
    for recipe in book.recipes[:200]:
        worst = ease.of_recipe(recipe)
        assert worst.score == min(ease.of(i.id).score for i in recipe.inputs)


def test_nanite_ladder_matches_the_guide(book: Book) -> None:
    """The nanite converters table in 20.refiner-recipes.md: 15 as of Cosmos
    7.06, which added 5 Corrupted Ichor -> 1 Nanite Cluster (14 before)."""
    ladder = graph.nanite_ladder(book)
    assert len(ladder) == 15

    def route(**by_name):
        wanted = {one(n.replace("_", " ")): amount for n, amount in by_name.items()}
        return next(r for r in ladder if {i.id: i.n for i in r.recipe.inputs} == wanted)

    ichor = route(Corrupted_Ichor=5)
    assert (ichor.nanites, ichor.per_hour) == (1, 40)  # 90 s a batch

    best = ladder[0]
    assert best.per_hour == 3000  # Larval / Hadal Core, 50 nanites in 60 s
    assert best.nanites == 50

    worst = ladder[-1]
    assert {i.id: i.n for i in worst.recipe.inputs} == {one("Runaway Mould"): 5}
    assert worst.per_hour == 24  # the guide's "slowest converter in the table"

    brain = route(Hyaline_Brain=1)
    assert brain.nanites == 230
    assert brain.per_hour < best.per_hour  # compact storage, not a fast tap


def test_every_cooked_dish_has_a_buff(book: Book) -> None:
    """Animal feed and Carbon Nanotubes come out of the same machine and are
    not food; they must not show up in the buff view."""
    dishes = food.dishes(book)
    made = {dish.item.id for dish in dishes}
    assert one("Creature Pellets") not in made
    assert one("Carbon Nanotubes") not in made
    assert len(dishes) == 331
    assert all(dish.effect for dish in dishes)
    assert all(dish.potency > 0 for dish in dishes)


def test_effects_group_cleanly(book: Book) -> None:
    grouped = food.by_effect(book)
    assert len(grouped) == 19
    # Breathing Efficiency, by the game's stat id (its display name is the language's)
    assert "Suit_Protection_WaterDrain" in {g[0].item.effect_id for g in grouped.values()}
    for effect, group in grouped.items():
        assert all(dish.effect == effect for dish in group)
        # Sorted strongest first.
        assert [d.potency for d in group] == sorted(
            (d.potency for d in group), reverse=True
        )


def test_cooking_pays_as_well_as_buffs(book: Book) -> None:
    """The premise of the cooking screen: the dish you eat is the one you sell."""
    top = max(food.dishes(book), key=lambda d: d.value)
    assert top.value > 100_000
    assert top.uplift > 0


def test_multitool_reference_loads() -> None:
    """The one file no game table backs -- guard its shape, not its prose."""
    from nms_items import multitools

    data = multitools.load()
    assert len(data.types) == 8
    assert all(t.type for t in data.types)

    # The guides' headline claim, which the type table has to keep agreeing with:
    # two types share the best damage bonus, and the plain pistol has none.
    assert len([t for t in data.types if t.damage.endswith("50%")]) == 2
    assert len([t for t in data.types if t.damage == "+0%"]) == 1

    assert len(data.weapons) == 7
    assert all(w.weapon for w in data.weapons)
    assert all(rule.title and rule.body for rule in data.rules)
    assert all(p.title and p.steps for p in data.procedures)
    assert data.upgrade_order
