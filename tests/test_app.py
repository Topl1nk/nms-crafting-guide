"""A headless pass over the TUI: every binding that changes state."""

from __future__ import annotations

import asyncio
import json

import pytest

from nms_items.app import RecipeApp
from nms_items.inventory import Inventory
from nms_items.model import Book


@pytest.fixture(scope="module")
def book() -> Book:
    return Book()


def run(coro):
    return asyncio.run(coro)


def test_app_flows(book: Book, tmp_path_factory) -> None:
    inv_path = tmp_path_factory.mktemp("state") / "inventory.json"

    async def scenario() -> None:
        app = RecipeApp(book)
        app.inv = Inventory(inv_path)
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            main = app.screen
            table = main.query_one("#table")
            assert table.row_count == 357  # refining is the default domain

            # search debounces, so give the timer a chance
            await pilot.press("slash")
            for char in "platinum":
                await pilot.press(char)
            await pilot.pause(0.3)
            await pilot.pause(0.3)
            assert 0 < table.row_count < 357
            assert all("platinum" in r.search_key for r in main.rows)

            await pilot.press("enter")  # back to the table
            await pilot.press("s")      # sort
            await pilot.press("f")      # domain
            await pilot.pause()
            assert main.domain == "cook"
            await pilot.press("f")
            await pilot.press("f")
            await pilot.pause()
            assert main.domain == "refine"

            # reverse lookup and back
            await pilot.press("r")
            await pilot.pause()
            assert main.item_role == "input"
            await pilot.press("backspace")
            await pilot.pause()
            assert main.item_filter is None

            # chain screen
            await pilot.press("c")
            await pilot.pause(0.2)
            assert app.screen.__class__.__name__ == "ChainScreen"
            await pilot.press("t")
            await pilot.press("k")
            await pilot.pause(0.2)
            await pilot.press("escape")
            await pilot.pause(0.2)

            # inventory round trip, including persistence
            await pilot.press("i")
            await pilot.pause(0.2)
            assert app.screen.__class__.__name__ == "InventoryScreen"
            for char in "platinum 250":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause(0.3)
            assert app.inv.items == {"ASTEROID3": 250}
            assert app.screen.query_one("#can-table").row_count == 1
            await pilot.press("escape")
            await pilot.pause(0.2)

            await pilot.press("question_mark")
            await pilot.pause(0.2)
            assert app.screen.__class__.__name__ == "HelpScreen"
            await pilot.press("escape")
            await pilot.pause(0.2)

    run(scenario())
    assert json.loads(inv_path.read_text()) == {"ASTEROID3": 250}


def test_bindings_do_not_leak_between_screens(book: Book, tmp_path) -> None:
    """`s` sorts the recipe list, but only while the recipe list is on top."""

    async def scenario() -> None:
        app = RecipeApp(book)
        app.inv = Inventory(tmp_path / "inv.json")
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            main = app.screen
            before = main.sort_index

            await pilot.press("e")  # cooking effects
            await pilot.pause(0.3)
            assert app.screen is not main
            await pilot.press("s")
            await pilot.pause(0.2)
            assert main.sort_index == before

            await pilot.press("escape")
            await pilot.pause(0.2)
            await pilot.press("s")
            await pilot.pause(0.2)
            assert main.sort_index != before

    run(scenario())


def test_nanite_and_food_screens(book: Book, tmp_path) -> None:
    async def scenario() -> None:
        app = RecipeApp(book)
        app.inv = Inventory(tmp_path / "inv.json")
        async with app.run_test(size=(150, 40)) as pilot:
            await pilot.pause()

            await pilot.press("n")
            await pilot.pause(0.3)
            nanites = app.screen
            assert nanites.__class__.__name__ == "NaniteScreen"
            assert nanites.query_one("#nanite-table").row_count == 14
            await pilot.press("s")  # the screen's own sort, not the list's
            await pilot.pause(0.2)
            assert nanites.sort_index == 1
            await pilot.press("escape")
            await pilot.pause(0.2)

            await pilot.press("e")
            await pilot.pause(0.3)
            foods = app.screen
            assert foods.__class__.__name__ == "FoodScreen"
            assert foods.query_one("#effect-table").row_count == 19
            assert foods.query_one("#dish-table").row_count > 0
            await pilot.press("escape")
            await pilot.pause(0.2)

            await pilot.press("m")
            await pilot.pause(0.4)
            tools = app.screen
            assert tools.__class__.__name__ == "MultiToolScreen"
            assert tools.query_one("#type-table").row_count == 8
            assert tools.query_one("#weapon-table").row_count == 7
            tabs = tools.query_one("#mt-tabs")
            assert tabs.active == "tab-types"
            # Brackets must work even with a wide DataTable focused, which
            # would otherwise swallow the arrow keys for scrolling.
            tools.query_one("#type-table").focus()
            await pilot.pause(0.2)
            await pilot.press("]")
            await pilot.pause(0.3)
            assert tabs.active == "tab-weapons"
            await pilot.press("[")
            await pilot.pause(0.3)
            assert tabs.active == "tab-types"

    run(scenario())


def test_vim_motions(book: Book, tmp_path) -> None:
    """j/k/gg/G/ctrl+d move the cursor; the search box is insert mode."""

    async def scenario() -> None:
        app = RecipeApp(book)
        app.inv = Inventory(tmp_path / "inv.json")
        async with app.run_test(size=(150, 30)) as pilot:
            await pilot.pause()
            main = app.screen
            table = main.query_one("#table")

            for _ in range(3):
                await pilot.press("j")
            await pilot.pause(0.2)
            assert table.cursor_row == 3
            await pilot.press("k")
            await pilot.pause(0.2)
            assert table.cursor_row == 2

            await pilot.press("G")
            await pilot.pause(0.3)
            assert table.cursor_row == table.row_count - 1

            # A lone g does nothing; gg goes to the top.
            await pilot.press("g")
            await pilot.pause(0.1)
            assert table.cursor_row == table.row_count - 1
            await pilot.press("g")
            await pilot.pause(0.3)
            assert table.cursor_row == 0

            await pilot.press("ctrl+d")
            await pilot.pause(0.2)
            assert table.cursor_row > 0

            # Insert mode: letters are text, not commands.
            await pilot.press("slash")
            await pilot.pause(0.2)
            assert app.focused.id == "search"
            for char in "cobalt":
                await pilot.press(char)
            await pilot.pause(0.3)
            await pilot.pause(0.3)
            assert main.query_text == "cobalt"
            assert main.sort_index == 0  # the s in "cobalt" did not sort

            # Escape leaves insert mode and keeps the filter...
            await pilot.press("escape")
            await pilot.pause(0.3)
            assert app.focused.id == "table"
            assert main.query_text == "cobalt"

            # ...and a second Escape, in normal mode, clears it.
            await pilot.press("escape")
            await pilot.pause(0.3)
            assert main.query_text == ""
            assert table.row_count == 357

    run(scenario())


def test_help_scrolls_instead_of_closing(book: Book, tmp_path) -> None:
    async def scenario() -> None:
        app = RecipeApp(book)
        app.inv = Inventory(tmp_path / "inv.json")
        async with app.run_test(size=(150, 30)) as pilot:
            await pilot.pause()
            await pilot.press("question_mark")
            await pilot.pause(0.3)
            box = app.screen.query_one("#help-box")

            for _ in range(5):
                await pilot.press("j")
            await pilot.pause(0.3)
            assert app.screen.__class__.__name__ == "HelpScreen"
            assert box.scroll_offset.y > 0

            await pilot.press("q")
            await pilot.pause(0.3)
            assert app.screen.__class__.__name__ == "RecipeScreen"

    run(scenario())


def test_cooking_toggle_survives_vim_keys(book: Book, tmp_path) -> None:
    """k is cursor-up now, so the cooking toggle had to move to C."""

    async def scenario() -> None:
        app = RecipeApp(book)
        app.inv = Inventory(tmp_path / "inv.json")
        async with app.run_test(size=(150, 30)) as pilot:
            await pilot.pause()
            await pilot.press("i")
            await pilot.pause(0.3)
            inventory = app.screen
            assert inventory.with_cooking is True

            inventory.query_one("#inv-table").focus()
            await pilot.press("k")  # cursor-up, not a toggle
            await pilot.pause(0.2)
            assert inventory.with_cooking is True

            await pilot.press("C")
            await pilot.pause(0.3)
            assert inventory.with_cooking is False

    run(scenario())
