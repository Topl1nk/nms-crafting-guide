"""The short path of an item opens in Крафт, in the place of the table, as a pyramid like a chain of the Tree, and a large
«Закрыть» (or Esc) gives the table back. There is no page of its own for it any more (#/chain/ITEM is an old link that
opens there). lib/tree.js `pyramidOf` draws the path; tests/js/tree.real.test.mjs checks it step for step."""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).parent.parent / "site" / "src"


def read(*parts: str) -> str:
    return SRC.joinpath(*parts).read_text(encoding="utf-8")


def test_the_path_is_no_page_of_its_own() -> None:
    assert not (SRC / "views" / "Chain.svelte").exists()
    views = re.search(r"const VIEWS = \{(.*?)\};", read("App.svelte"), re.S).group(1)
    assert "chain" not in views
    assert 'section === "chain"' in read("lib", "router.svelte.js"), "old links open in Крафт"


def test_the_path_takes_the_tables_place_in_craft() -> None:
    rec = read("views", "Recipes.svelte")
    assert "<ChainCanvas " in rec and "<ChainBar " in rec
    assert re.search(r"\{#if open\}\s*<ChainCanvas [^>]*/>\s*\{:else\}\s*<List ", rec), "the canvas is the table's alternative"
    assert "onpath={openPath}" in rec, "the button of the card opens it in place"
    assert 'params.get("path")' in rec


def test_the_way_back_is_large_and_in_reach() -> None:
    bar = read("components", "ChainBar.svelte")
    assert '{t("Close")}</button>' in bar and "onclick={onclose}" in bar
    assert re.search(r"\.close \{[^}]*--p-red", bar, re.S) and re.search(r"\.zoomwrap \{[^}]*margin-left: auto", bar), "red, at the far end of the bar"
    assert "if (open) { closePath(); return; }" in read("views", "Recipes.svelte"), "Esc closes it too"


def test_the_short_path_is_a_pyramid() -> None:
    canvas = read("components", "ChainCanvas.svelte")
    assert "<Pyramid " in canvas and "pyramidOf(" in canvas, "the path is drawn by the Tree's component"
    assert 'title={t("Short path")}' in canvas


def test_no_flat_list_is_left() -> None:
    canvas = read("components", "ChainCanvas.svelte")
    for flat in ("Это делают так", 'class="tree"', "snippet node(", "Нужно собрать"):
        assert flat not in canvas, flat


def test_when_nothing_can_be_made_the_smallest_chains_are_drawn_without_a_warning_card() -> None:
    """«Из этого набора сырья не получится» + two buttons over every such page was noise: the chains are the answer. The
    card stays only where there is nothing to draw (an item that can only be found)."""
    canvas = read("components", "ChainCanvas.svelte")
    assert "pyramids(target" in canvas and "{#each shortest as pyr" in canvas
    assert canvas.index("{#each shortest as pyr") < canvas.index('t("It cannot be made from this set of raws")')
    assert "Вот самые короткие цепочки" not in canvas


def test_nothing_links_to_the_old_page() -> None:
    for path in sorted(SRC.rglob("*")):
        if path.suffix in {".svelte", ".js"} and path.name != "router.svelte.js":
            assert "#/chain" not in path.read_text(encoding="utf-8"), f"{path.name} links to #/chain, use #/recipes?path="

def test_the_canvas_and_the_card_stay_where_the_table_and_the_card_were() -> None:
    """The row «Рецептов: N …» under the bar stays while the path is open, so nothing moves up: the canvas takes exactly
    the table's place and the card its own (measured: both at top 138, the same width and height)."""
    rec = read("views", "Recipes.svelte")
    # while the path is open the row is empty (no text for its own sake) and only keeps its height
    assert re.search(r"\{#if open\}\s*<!--[^>]*-->\s*<div class=\"count\" aria-hidden=\"true\">&nbsp;</div>\s*\{:else\}\s*<div class=\"count\">", rec)
    assert re.search(r"</div>\s*\{/if\}\s*<div class=\"split split-craft\">", rec)
    assert '{" "}{t("of {n}", { n: base.length })}' in rec, "«361 of 1684», not «361of 1684»"


def test_the_card_beside_the_path_is_the_recipe_of_the_path() -> None:
    """Not the recipe the table had selected (it could be another way altogether, even a loop): the one at the top of
    the pyramid on the canvas."""
    rec = read("views", "Recipes.svelte")
    assert "bind:rootRecipe" in rec and "r={cyc ?? rootRecipe ?? cur}" in rec
    assert "rootRecipe = " in read("components", "ChainCanvas.svelte")


def test_a_name_is_not_shortened_while_there_is_room() -> None:
    css = (SRC / "app.css").read_text(encoding="utf-8")
    assert re.search(r"\.list td\.strong \{[^}]*min-width: min\(max-content, 360px\)", css)


