"""Dracula's accents on neutral greys, and a version with no background at all.

Stock Dracula paints its background #282A36, which has more blue in it than
red or green -- the tint that reads as "bluey" next to a black terminal. Both
themes here keep the accents exactly and swap that for grey:

dracula-clear    the terminal's own background shows through (transparency
                 and all); only input boxes and the cursor row get a fill.
dracula-neutral  the same, painted: opaque greys at Dracula's brightness.

The choice persists in the XDG state dir next to the inventory.
"""

from __future__ import annotations

import json

from textual.theme import Theme

from .inventory import state_path

ACCENTS = dict(
    primary="#BD93F9",    # purple
    secondary="#8BE9FD",  # cyan
    accent="#FF79C6",     # pink
    success="#50FA7B",
    warning="#F1FA8C",
    error="#FF5555",
    foreground="#F8F8F2",
)

DRACULA_CLEAR = Theme(
    name="dracula-clear",
    dark=True,
    background="ansi_default",
    surface="ansi_default",
    panel="#2E2E2E",
    variables={
        # Textual derives muted text from the background colour; with no
        # background colour it gives up and returns white. So say it outright.
        "text-muted": "#A0A0A0",
    },
    **ACCENTS,
)

DRACULA_NEUTRAL = Theme(
    name="dracula-neutral",
    dark=True,
    # Panes a step darker than the screen, like the Mocha look this replaced.
    background="#232323",
    surface="#1C1C1C",
    panel="#2E2E2E",
    **ACCENTS,
)

THEMES = [DRACULA_CLEAR, DRACULA_NEUTRAL]
DEFAULT_THEME = DRACULA_CLEAR.name

# Themes that leave the background to the terminal. Textual only draws the
# terminal's default colour as-is when ANSI colours are switched on; left off,
# it converts it to an opaque RGB guess.
TRANSPARENT = {DRACULA_CLEAR.name}


def settings_path():
    return state_path().with_name("settings.json")


def load_theme() -> str:
    try:
        return str(json.loads(settings_path().read_text())["theme"])
    except (OSError, ValueError, KeyError, TypeError):
        return DEFAULT_THEME


def save_theme(name: str) -> None:
    path = settings_path()
    try:
        settings = json.loads(path.read_text())
    except (OSError, ValueError):
        settings = {}
    settings["theme"] = name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=1))
