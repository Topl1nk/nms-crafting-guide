"""Vim-flavoured versions of the two widgets the app is built from.

The app was already modal in the vim sense -- single letters are commands and
`/` opens the search box -- but the motions were missing and there was no way
out of the search field except Enter. These add both.

Nothing here overrides an existing key: j, k, g, G, ctrl+d and ctrl+u were all
unbound, so the action keys (f, s, p, r, c, a, i, n, e, m, d) keep their
meanings. `d` stays "detail pane" and `n` stays "nanites" -- neither has a job
in a read-only list that a vim user would miss.
"""

from __future__ import annotations

from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widgets import DataTable, Input, Tree

# How long a lone `g` waits for its partner before giving up.
GG_TIMEOUT = 0.7


class VimDataTable(DataTable):
    """A DataTable that moves under hjkl, gg/G and ctrl+d/ctrl+u."""

    BINDINGS = [
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
        # Horizontal scroll rather than cursor movement: these tables are
        # row-cursored and wider than their pane, so h/l should pan the view.
        Binding("h", "scroll_left", "left", show=False),
        Binding("l", "scroll_right", "right", show=False),
        Binding("ctrl+d", "page_down", "half page down", show=False),
        Binding("ctrl+u", "page_up", "half page up", show=False),
        Binding("G", "scroll_bottom", "bottom", show=False),
        Binding("g", "maybe_top", "top (gg)", show=False),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._g_pending = False
        self._g_timer = None

    def action_maybe_top(self) -> None:
        """`gg` goes to the top; a lone `g` does nothing and forgets itself."""
        if self._g_pending:
            self._cancel_g()
            self.action_scroll_top()
            return
        self._g_pending = True
        self._g_timer = self.set_timer(GG_TIMEOUT, self._cancel_g)

    def _cancel_g(self) -> None:
        self._g_pending = False
        if self._g_timer is not None:
            self._g_timer.stop()
            self._g_timer = None

    def on_key(self, event) -> None:
        # Any other key ends a pending `g`, so `g` then `j` is not a jump.
        if self._g_pending and event.key != "g":
            self._cancel_g()


class VimVerticalScroll(VerticalScroll):
    """The same motions for the scrollable prose panes."""

    BINDINGS = [
        Binding("j", "scroll_down", "down", show=False),
        Binding("k", "scroll_up", "up", show=False),
        Binding("ctrl+d", "page_down", "half page down", show=False),
        Binding("ctrl+u", "page_up", "half page up", show=False),
        Binding("G", "scroll_end", "bottom", show=False),
        Binding("g", "scroll_home", "top", show=False),
    ]


class SearchInput(Input):
    """Insert mode: Escape leaves it the way it does in vim.

    Escape posts its own message rather than reusing Submitted -- on the
    inventory screen submitting means "add this item", which is not what
    leaving the field should do.
    """

    BINDINGS = [
        Binding("escape", "leave", "normal mode", show=False),
    ]

    class Escaped(Message):
        """Posted when the user leaves the field without submitting."""

        def __init__(self, input: "SearchInput") -> None:
            super().__init__()
            self.input = input

    def action_leave(self) -> None:
        self.post_message(self.Escaped(self))


class VimTree(Tree):
    """The chain plan's tree, under the same motions.

    h and l collapse and expand here rather than panning, which is what they do
    in every vim-keyed file tree.
    """

    BINDINGS = [
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
        Binding("h", "cursor_parent", "collapse", show=False),
        Binding("l", "select_cursor", "expand", show=False),
        Binding("g", "scroll_home", "top", show=False),
        Binding("G", "scroll_end", "bottom", show=False),
        Binding("ctrl+d", "page_down", "half page down", show=False),
        Binding("ctrl+u", "page_up", "half page up", show=False),
    ]
