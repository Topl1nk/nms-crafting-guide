"""Ease scoring, the nanite ladder and the cooking-effect data."""

from __future__ import annotations

import pytest

from nms_items import food, graph
from nms_items.ease import EaseIndex
from nms_items.model import Book


@pytest.fixture(scope="module")
def book() -> Book:
    return Book()


@pytest.fixture(scope="module")
def ease(book: Book) -> EaseIndex:
    return EaseIndex(book)


def test_tier_sources_are_the_easiest_things(book: Book, ease: EaseIndex) -> None:
    assert ease.of(book.by_name("Oxygen").id).label == "T0 raw"
    assert ease.of(book.by_name("Oxygen").id).band == "easy"
    assert ease.of(book.by_name("Gold").id).label == "T1 raw"


def test_refinable_items_report_their_depth(book: Book, ease: EaseIndex) -> None:
    mag = ease.of(book.by_name("Magnetised Ferrite").id)
    assert mag.tier == 0
    assert mag.steps >= 1
    assert mag.band == "easy"


def test_seeded_items_are_not_called_loot(book: Book, ease: EaseIndex) -> None:
    """Chromatic Metal is makeable, just not from any source tier."""
    chromatic = ease.of(book.by_name("Chromatic Metal").id)
    assert chromatic.seeds
    assert chromatic.label == "needs seed"


def test_loot_uses_the_curated_guide_data(book: Book, ease: EaseIndex) -> None:
    brain = ease.of(book.by_name("Hyaline Brain").id)
    assert brain.tier is None
    assert brain.effort == "hard"
    assert "Interceptor" in brain.where

    # An item with an easy loot source should not be reported as seeded even
    # though a refiner recipe for it exists.
    mould = ease.of(book.by_name("Runaway Mould").id)
    assert mould.label == "loot (easy)"


def test_recipe_ease_is_the_hardest_ingredient(book: Book, ease: EaseIndex) -> None:
    for recipe in book.recipes[:200]:
        worst = ease.of_recipe(recipe)
        assert worst.score == min(ease.of(i.id).score for i in recipe.inputs)


def test_nanite_ladder_matches_the_guide(book: Book) -> None:
    ladder = graph.nanite_ladder(book)
    assert len(ladder) == 14

    best = ladder[0]
    assert best.per_hour == 3000  # Larval / Hadal Core, 50 nanites in 60 s
    assert best.nanites == 50

    worst = ladder[-1]
    assert worst.recipe.inputs_label == "5 Runaway Mould"
    assert worst.per_hour == 24  # the guide's "slowest converter in the table"

    brain = next(r for r in ladder if r.recipe.inputs_label == "Hyaline Brain")
    assert brain.nanites == 230
    assert brain.per_hour < best.per_hour  # compact storage, not a fast tap


def test_every_cooked_dish_has_a_buff(book: Book) -> None:
    """Animal feed and Carbon Nanotubes come out of the same machine and are
    not food; they must not show up in the buff view."""
    dishes = food.dishes(book)
    names = {dish.item.name for dish in dishes}
    assert "Creature Pellets" not in names
    assert "Carbon Nanotubes" not in names
    assert len(dishes) == 331
    assert all(dish.effect for dish in dishes)
    assert all(dish.potency > 0 for dish in dishes)


def test_effects_group_cleanly(book: Book) -> None:
    grouped = food.by_effect(book)
    assert len(grouped) == 19
    assert "Breathing Efficiency" in grouped
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
