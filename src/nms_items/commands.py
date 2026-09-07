"""The command palette, wired to the modes each screen already has.

Every screen in this app has a handful of modes reached by cycling a key: `f`
walks refining -> cooking -> all, `s` walks six sorts, `o` walks mine/shared.
Cycling is fast once you know the order and opaque until you do -- you press
`s` four times to reach "units profit" and there is nothing on screen that
tells you it was ever an option.

So the same modes are also commands. Ctrl+P, type "profit", Enter. The palette
lists them all when you open it with an empty query, marks the one you are
already in, and gets a screen's worth of footer bar back: the keys that had to
be spelled out in the bar can now be grouped or hidden without becoming secret.

A screen opts in by implementing `palette_commands()` and setting
`COMMANDS = {ModeCommands}`.
"""

from __future__ import annotations

from typing import Callable, Iterable, NamedTuple

from textual.command import DiscoveryHit, Hit, Hits, Provider

# The mark on the mode you are already in. The palette is a list of states, not
# a list of verbs, so saying which one is current is most of its value.
CURRENT = "●"
OTHER = "·"


class ModeCommand(NamedTuple):
    """One palette entry: what it is called, what it does, and whether it is on."""

    title: str
    help: str
    run: Callable[[], None]
    # True/False for one of a set of modes; None for a plain action, which
    # gets a blank mark so the two kinds still line up in the list.
    current: bool | None = None

    @property
    def mark(self) -> str:
        if self.current is None:
            return " "
        return CURRENT if self.current else OTHER

    @property
    def display(self) -> str:
        return f"{self.mark} {self.title}"


def mode(
    group: str,
    title: str,
    run: Callable[[], None],
    current: bool = False,
    help: str = "",
) -> ModeCommand:
    """A command named "Group: title", so typing either half finds it."""
    return ModeCommand(f"{group}: {title}", help, run, current)


class ModeCommands(Provider):
    """Serves whatever the active screen puts in `palette_commands()`."""

    def _commands(self) -> Iterable[ModeCommand]:
        getter = getattr(self.screen, "palette_commands", None)
        return getter() if getter is not None else ()

    async def discover(self) -> Hits:
        for command in self._commands():
            yield DiscoveryHit(command.display, command.run, help=command.help)

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for command in self._commands():
            score = matcher.match(command.title)
            if score > 0:
                # Highlight the title, but keep the current-mode mark in front.
                yield Hit(
                    score,
                    matcher.highlight(command.display),
                    command.run,
                    help=command.help,
                )
