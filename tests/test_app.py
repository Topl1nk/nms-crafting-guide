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
            table = app.query_one("#table")
            assert table.row_count == 357  # refining is the default domain

            # search debounces, so give the timer a chance
            await pilot.press("slash")
            for char in "platinum":
                await pilot.press(char)
            await pilot.pause(0.3)
            await pilot.pause(0.3)
            assert 0 < table.row_count < 357
            assert all("platinum" in r.search_key for r in app.rows)

            await pilot.press("enter")  # back to the table
            await pilot.press("s")      # sort
            await pilot.press("f")      # domain
            await pilot.pause()
            assert app.domain == "cook"
            await pilot.press("f")
            await pilot.press("f")
            await pilot.pause()
            assert app.domain == "refine"

            # reverse lookup and back
            await pilot.press("r")
            await pilot.pause()
            assert app.item_role == "input"
            await pilot.press("backspace")
            await pilot.pause()
            assert app.item_filter is None

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

    run(scenario())
    assert json.loads(inv_path.read_text()) == {"ASTEROID3": 250}
