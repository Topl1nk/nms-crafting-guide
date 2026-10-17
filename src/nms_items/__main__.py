"""Entry point: `nms`, `mise run tui`, or `python -m nms_items`.

`nms mcp` serves the same answers to AI assistants over MCP on stdio instead;
see mcp_server.py.
"""

from __future__ import annotations

import sys

USAGE = """usage: nms [mcp]

  nms        open the recipe browser (the TUI)
  nms mcp    serve NMSii's answers to AI assistants over MCP, on stdio
"""


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args[:1] == ["mcp"]:
        # Imported only here, so opening the TUI does not load the MCP SDK.
        from .mcp_server import main as serve

        return serve()
    if args[:1] in (["-h"], ["--help"], ["help"]):
        print(USAGE, end="")
        return 0
    if args:
        print(USAGE, end="", file=sys.stderr)
        return 2

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
