"""Entry point: `nms`, `mise run tui`, or `python -m nms_items`."""

from __future__ import annotations

import sys


def main() -> int:
    from .app import RecipeApp
    from .model import Book

    try:
        book = Book()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    RecipeApp(book).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
