"""Real loops (lib/cycles.js) are rows of the Крафт table, found in the background; the old "1->6" recipes are not made a show of."""

from __future__ import annotations

from pathlib import Path

SRC = Path(__file__).parent.parent / "site" / "src"


def read(*parts: str) -> str:
    return SRC.joinpath(*parts).read_text(encoding="utf-8")


def test_the_search_runs_in_a_worker_and_rows_come_as_they_are_found() -> None:
    store = read("lib", "cycles.svelte.js")
    assert 'new Worker(new URL("./cycles.worker.js", import.meta.url), { type: "module" })' in store
    assert "cycles.rows = [...cycles.rows, rowOf(data.loop, cycles.rows.length)];" in store
    assert "index: -1 - k" in store, "loop rows are not in D.recipes"
    assert "onFound: (loop) => self.postMessage({ loop })" in read("lib", "cycles.worker.js")


def test_the_loops_are_rows_of_the_table_beside_the_recipes() -> None:
    page = read("views", "Recipes.svelte")
    assert "[...RECIPES, ...cycles.rows]" in page and "findLoopsInBackground();" in page
    assert "<RecipeCard r={cur} onpath={openPath} oncycle={openCycle} />" in page, "a loop has the card of a recipe"
    assert 'label={t("Loops")}' in page and "Самоумножение" not in page
    assert "Boolean(r.cycle)" in read("lib", "recipefacets.js")


def test_a_recipe_that_is_not_chosen_is_no_recipe_of_index_below_zero() -> None:
    """A loop's index is below zero, so «no recipe wanted» must not be -1 (the first loop was taken for the wanted one)."""
    page = read("views", "Recipes.svelte")
    assert 'let want = $state(params.has("r") ? Number(params.get("r")) : null);' in page


def test_the_old_loops_are_not_green_and_sort_as_plain_recipes() -> None:
    page = read("views", "Recipes.svelte")
    assert "const gain = (r) => (r.cycle ? 1e9 : r.loop > 1 ? 1 : r.ratio);" in page
    assert "class:loop" not in page and ".loop {" not in page


def test_the_card_of_a_loop_is_the_card_of_a_recipe_with_a_button_for_the_whole_cycle() -> None:
    card = read("components", "RecipeCard.svelte")
    assert 't("Full loop")' in card and "oncycle?.(r)" in card
    assert not (SRC / "components" / "CycleCard.svelte").exists(), "one card for every recipe"
    page = read("views", "Recipes.svelte")
    assert "cycle={cyc?.cycle ?? null}" in page and "oncycle={openCycle}" in page
    assert "<CycleSteps {cycle} mult={qty} />" in read("components", "ChainCanvas.svelte"), "every step from the start to the end of the turn, not a tree with stubs"


def test_my_things_can_be_searched() -> None:
    inv = read("views", "Inventory.svelte")
    assert 'placeholder={t("Search my items…")}' in inv and "bind:this={find}" in inv
    assert "get search() { return find; }" in inv
    assert "const shown = $derived(" in inv and "const rows = $derived(only ? shown.filter" in inv



def test_a_full_cycle_shows_its_books() -> None:
    """Before / after / difference in things and in units, and the stock after each run: the profit is read off, never guessed."""
    ledger = read("components", "CycleLedger.svelte")
    assert '<th>{t("Before")}</th><th>{t("After")}</th><th>{t("Difference")}</th><th>{t("Units")}</th>' in ledger
    assert "<CycleLedger {cycle} mult={qty}" in read("components", "ChainCanvas.svelte")
    assert "export function simulate(loop, get, turns = 1)" in read("lib", "cycles.js")



def test_the_steps_of_a_cycle_are_floors_of_stock_in_the_style_of_the_pyramids() -> None:
    steps = read("components", "CycleSteps.svelte")
    assert "Остаётся" not in steps and "class=\"wn\"" not in steps, "only what goes in and what comes out: no extra floors, counts or notes"
    assert "<Tile " in steps
    assert "из запаса" not in read("components", "Pyramid.svelte"), "no stub tiles"







