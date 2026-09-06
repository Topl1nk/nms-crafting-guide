"""Write SVG screenshots of the TUI into docs/img/.

Textual can render a screen to SVG without a terminal, so the README images are
generated rather than captured -- no cropping, no stale screenshots after a
CSS change. Run via `mise run screenshot`.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
# Screenshots must not pick up (or write to) the real inventory.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()

from nms_items.app import RecipeApp  # noqa: E402
from nms_items.model import Book  # noqa: E402

OUT = ROOT / "docs" / "img"
SIZE = (150, 42)


async def shoot() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    app = RecipeApp(Book())

    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        main = app.screen

        # 1. The recipe list, searched.
        await pilot.press("slash")
        for char in "cobalt":
            await pilot.press(char)
        await pilot.pause(0.4)
        await pilot.pause(0.4)
        await pilot.press("enter")
        await pilot.pause(0.2)
        _save(app, "recipes.svg")

        # 2. A production chain.
        main.query_text = ""
        main.refresh_rows()
        await pilot.pause(0.2)
        await pilot.press("c")
        await pilot.pause(0.5)
        _save(app, "chain.svg")
        await pilot.press("escape")
        await pilot.pause(0.2)

        # 3. The nanite ladder.
        await pilot.press("n")
        await pilot.pause(0.5)
        _save(app, "nanites.svg")
        await pilot.press("escape")
        await pilot.pause(0.2)

        # 4. Cooking buffs.
        await pilot.press("e")
        await pilot.pause(0.5)
        _save(app, "food.svg")
        await pilot.press("escape")
        await pilot.pause(0.2)

        # 5. Inventory, with something in it.
        await pilot.press("i")
        await pilot.pause(0.3)
        for text in ("platinum 250", "oxygen 400", "ferrite dust 800"):
            for char in text:
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause(0.2)
        await pilot.pause(0.3)
        _save(app, "inventory.svg")


def _save(app: RecipeApp, name: str) -> None:
    path = OUT / name
    path.write_text(app.export_screenshot())
    print(f"wrote {path}")


if __name__ == "__main__":
    asyncio.run(shoot())
