"""The main screen: a filterable recipe table with a detail pane."""

from __future__ import annotations

from functools import partial
from typing import Iterator

from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from .commands import ModeCommand, ModeCommands, mode
from .ease import EaseIndex
from .inventory import Inventory
from .model import Book, Recipe
from .portals import LocationBook
from .storage import StorageGuide
from .themes import THEMES, TRANSPARENT, load_theme, save_theme
from .widgets import SearchInput, VimDataTable
from .screens import (
    ChainScreen,
    FoodScreen,
    HelpScreen,
    InventoryScreen,
    MultiToolScreen,
    NaniteScreen,
    PortalScreen,
    QuantityModal,
    StorageScreen,
)

# Keep the table responsive: filtering 1,680 rows on every keystroke is fine,
# rendering them all is not.
MAX_ROWS = 400

# Below this width the detail pane costs more than it gives -- the table loses
# its Mult/Time/Machine columns to make room -- so it hides itself.
MIN_WIDTH_FOR_DETAIL = 100

BAND_COLOUR = {
    "easy": "$success",
    "ok": "$warning",
    "work": "$warning-darken-2",
    "hard": "$error",
}

DOMAINS: list[tuple[str | None, str]] = [
    ("refine", "Refining"),
    ("cook", "Cooking"),
    (None, "All recipes"),
]

SORTS: list[tuple[str, str]] = [
    ("mult", "multiplier"),
    ("time", "fastest"),
    ("rate", "output/hour"),
    ("profit", "units profit"),
    ("ease", "how gettable"),
    ("name", "name"),
]


# Footer groups: five keys that all open another screen say "screens" once
# instead of five times, which is most of what was overflowing the bar.
GO = Binding.Group("screens")
FILTER = Binding.Group("filter")


def sort_key(mode: str, ease: EaseIndex):
    if mode == "mult":
        return lambda r: (-max(r.loop, r.ratio), r.time)
    if mode == "time":
        return lambda r: (r.time or 1e9, -r.ratio)
    if mode == "rate":
        return lambda r: (-r.rate, r.time)
    if mode == "profit":
        return lambda r: (-r.profit, r.time)
    if mode == "ease":
        return lambda r: (-ease.of_recipe(r).score, r.time)
    return lambda r: (r.output_name, r.inputs_label)


class RecipeScreen(Screen):
    """The recipe list.

    This is a Screen rather than the App itself for one reason: App bindings
    stay live under every other screen, so with `s` and `f` defined up there,
    pressing them on the nanite or cooking screen would silently re-sort a
    table nobody was looking at.
    """

    BINDINGS = [
        Binding("slash", "focus_search", "search"),
        Binding("f", "cycle_domain", "domain"),
        Binding("s", "cycle_sort", "sort"),
        Binding("p", "filter_produces", "produced by", group=FILTER),
        Binding("r", "filter_consumes", "used in", group=FILTER),
        Binding("backspace", "clear_item_filter", "clear filter", group=FILTER),
        Binding("c", "chain", "chain"),
        Binding("a", "add_to_inventory", "+inv"),
        Binding("n", "nanites", "nanites", group=GO),
        Binding("e", "effects", "food effects", group=GO),
        Binding("m", "multitools", "multi-tools", group=GO),
        # Capital P: lowercase p is already "produced by" on this table.
        Binding("P", "portals", "portals", group=GO),
        Binding("i", "inventory", "inventory", group=GO),
        Binding("w", "storage", "where it goes", group=GO),
        Binding("d", "toggle_detail", "detail"),
        # Escape in normal mode clears what you searched for; Escape in the
        # search box just leaves insert mode and keeps it.
        Binding("escape", "clear_search", "clear search", show=False),
    ]

    COMMANDS = {ModeCommands}

    def __init__(self, book: Book, ease: EaseIndex, inventory: Inventory) -> None:
        super().__init__()
        self.book = book
        self.ease = ease
        self.inv = inventory
        self.domain_index = 0
        self.sort_index = 0
        self.query_text = ""
        self.item_filter: str | None = None
        self.item_role = "any"
        self.rows: list[Recipe] = []
        self.detail_on = True
        self._debounce = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield SearchInput(
            placeholder="search recipes - output, ingredient or operation", id="search"
        )
        yield Static(id="filter-note")
        with Horizontal(id="body"):
            yield VimDataTable(id="table", cursor_type="row", zebra_stripes=True)
            yield Static(id="detail")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#table", VimDataTable)
        # Widths are tuned so the whole row fits beside the detail pane on an
        # 80-column terminal's worth of table (the pane takes a third).
        table.add_column("Make", width=24)
        table.add_column("From", width=40)
        table.add_column("Mult", width=8)
        table.add_column("Time", width=6)
        table.add_column("Machine", width=8)
        self.refresh_rows()
        self._update_detail_visibility()
        table.focus()

    def on_resize(self) -> None:
        self._update_detail_visibility()

    def _update_detail_visibility(self) -> None:
        self.query_one("#detail", Static).display = (
            self.detail_on and self.app.size.width >= MIN_WIDTH_FOR_DETAIL
        )

    # -- command palette --------------------------------------------------

    def palette_commands(self) -> Iterator[ModeCommand]:
        """Both cycles as flat lists, so `s` stops being a guessing game."""
        for i, (_, label) in enumerate(DOMAINS):
            yield mode(
                "Recipes", label, partial(self._set_domain, i),
                i == self.domain_index,
            )
        for i, (_, label) in enumerate(SORTS):
            yield mode(
                "Sort", label, partial(self._set_sort, i), i == self.sort_index,
            )
        yield ModeCommand("Nanite ladder", "Every route to nanites, ranked",
                          self.action_nanites)
        yield ModeCommand("Cooking effects", "What each dish does when eaten",
                          self.action_effects)
        yield ModeCommand("Multi-tools", "Types, weapons, getting the good ones",
                          self.action_multitools)
        yield ModeCommand("Portal addresses", "Glyphs, coordinates, saved places",
                          self.action_portals)
        yield ModeCommand("Inventory", "What you are carrying",
                          self.action_inventory)
        yield ModeCommand("Where does it go?", "Which storage container an item belongs in",
                          self.action_storage)
        if self.query_text or self.item_filter:
            yield ModeCommand("Clear search and filters", "Back to the full list",
                              self.action_clear_search)
        yield ModeCommand(
            "Detail pane", "Show or hide the pane on the right",
            self.action_toggle_detail,
        )

    def _set_domain(self, index: int) -> None:
        self.domain_index = index
        self.refresh_rows()

    def _set_sort(self, index: int) -> None:
        self.sort_index = index
        self.refresh_rows()

    # -- data ------------------------------------------------------------

    @property
    def domain(self) -> str | None:
        return DOMAINS[self.domain_index][0]

    def refresh_rows(self, keep_cursor: bool = False) -> None:
        table = self.query_one("#table", VimDataTable)
        cursor = table.cursor_row if keep_cursor else 0

        matches = self.book.search(
            self.query_text, self.domain, self.item_filter, self.item_role
        )
        matches.sort(key=sort_key(SORTS[self.sort_index][0], self.ease))
        self.rows = matches[:MAX_ROWS]

        table.clear()
        for recipe in self.rows:
            table.add_row(
                recipe.output_label,
                recipe.inputs_label,
                recipe.multiplier_label,
                recipe.time_label,
                recipe.machine_short,
                key=str(recipe.index),
            )

        note = [f"[b]{DOMAINS[self.domain_index][1]}[/]"]
        note.append(f"sorted by [b]{SORTS[self.sort_index][1]}[/]")
        if self.item_filter:
            role = {
                "output": "produced by",
                "input": "used in",
                "any": "anything touching",
            }[self.item_role]
            note.append(f"{role} [b $warning]{self.book.name(self.item_filter)}[/]")
        shown = len(self.rows)
        total = len(matches)
        note.append(f"{shown} of {total}" if total > shown else f"{total} recipes")
        if len(self.inv):
            note.append(f"inventory: {len(self.inv)} items")
        self.query_one("#filter-note", Static).update("   ".join(note))

        if self.rows:
            table.move_cursor(row=min(cursor, len(self.rows) - 1))
            self.show_detail(self.rows[min(cursor, len(self.rows) - 1)])
        else:
            self.query_one("#detail", Static).update("[$text-muted]No recipe matches.[/]")

    def current_recipe(self) -> Recipe | None:
        table = self.query_one("#table", VimDataTable)
        if not self.rows or table.cursor_row < 0:
            return None
        if table.cursor_row >= len(self.rows):
            return None
        return self.rows[table.cursor_row]

    # -- detail pane -----------------------------------------------------

    def show_detail(self, recipe: Recipe) -> None:
        book = self.book
        out = book.items.get(recipe.output.id)
        lines = [
            f"[b $warning]{recipe.output_label}[/]",
            f"[$text-muted]{out.subtitle if out else ''}[/]",
            "",
            f"[b]{recipe.inputs_label}[/]",
            f"  -> [b]{recipe.output_label}[/]",
            "",
            f"[$primary]Operation[/]  {recipe.operation}",
            f"[$primary]Machine[/]    {recipe.machine}",
            f"[$primary]Batch time[/] {recipe.time_label}",
            f"[$primary]Multiplier[/] {recipe.multiplier_label}",
            f"[$primary]Rate[/]       {recipe.rate:,.0f}/h per machine",
            f"[$primary]Profit[/]     {recipe.profit:+,} units per batch",
            f"[$primary]Gettable[/]   {self.ease.of_recipe(recipe).label}"
            f"  [$text-muted](hardest ingredient)[/]",
        ]
        if out:
            placement = self.app.storage.place(out)
            lines.append(
                f"[$primary]Store[/]      {placement.label}  [$text-muted](w for more)[/]"
            )
        lines += [
            "",
            "[$primary]Ingredients[/]",
        ]
        for ing in recipe.inputs:
            item = book.items.get(ing.id)
            have = self.inv.items.get(ing.id, 0)
            stock = f"  [$success](have {have})[/]" if have else ""
            ease = self.ease.of(ing.id)
            lines.append(
                f"  {ing.n} x {book.name(ing.id)}"
                f"  [$text-muted]{item.value if item else 0}u[/]{stock}"
                f"  [{BAND_COLOUR[ease.band]}]{ease.label}[/]"
            )
            lines.append(f"     [$text-muted]{ease.describe(book)}[/]")

        others = [r for r in book.produced_by.get(recipe.output.id, []) if r.index != recipe.index]
        if others:
            lines += ["", f"[$primary]Other ways to make it[/]  ({len(others)})"]
            for alt in sorted(others, key=lambda r: -max(r.loop, r.ratio))[:5]:
                lines.append(f"  {alt.inputs_label}  [$text-muted]{alt.multiplier_label}[/]")
            lines.append("  [$text-muted]press p to list them all[/]")

        uses = book.consumed_by.get(recipe.output.id, [])
        if uses:
            lines += ["", f"[$primary]Used in[/]  {len(uses)} recipe(s) - press r"]

        self.query_one("#detail", Static).update("\n".join(lines))

    # -- events ----------------------------------------------------------

    def on_input_changed(self, event: SearchInput.Changed) -> None:
        if event.input.id != "search":
            return
        self.query_text = event.value
        if self._debounce is not None:
            self._debounce.stop()
        self._debounce = self.set_timer(0.12, self.refresh_rows)

    def on_input_submitted(self, event: SearchInput.Submitted) -> None:
        if event.input.id == "search":
            self.query_one("#table", VimDataTable).focus()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.cursor_row < len(self.rows):
            self.show_detail(self.rows[event.cursor_row])

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        recipe = self.current_recipe()
        if recipe:
            self.item_filter = recipe.output.id
            self.item_role = "any"
            self.refresh_rows()

    # -- actions ---------------------------------------------------------

    def action_focus_search(self) -> None:
        """`/` is insert mode; Escape or Enter puts you back in normal mode."""
        self.query_one("#search", SearchInput).focus()

    def on_search_input_escaped(self, event: SearchInput.Escaped) -> None:
        self.query_one("#table", VimDataTable).focus()

    def action_cycle_domain(self) -> None:
        self._set_domain((self.domain_index + 1) % len(DOMAINS))

    def action_cycle_sort(self) -> None:
        self._set_sort((self.sort_index + 1) % len(SORTS))

    def action_filter_produces(self) -> None:
        recipe = self.current_recipe()
        if recipe:
            self.item_filter = recipe.output.id
            self.item_role = "output"
            self.refresh_rows()

    def action_filter_consumes(self) -> None:
        recipe = self.current_recipe()
        if recipe:
            self.item_filter = recipe.output.id
            self.item_role = "input"
            self.refresh_rows()

    def action_clear_search(self) -> None:
        if not self.query_text and not self.item_filter:
            return
        self.query_text = ""
        self.item_filter = None
        self.item_role = "any"
        self.query_one("#search", SearchInput).value = ""
        self.refresh_rows()

    def action_clear_item_filter(self) -> None:
        if self.item_filter:
            self.item_filter = None
            self.item_role = "any"
            self.refresh_rows()

    def action_chain(self) -> None:
        recipe = self.current_recipe()
        if recipe:
            self.app.push_screen(
                ChainScreen(self.book, recipe.output.id, recipe.output.n)
            )

    def action_add_to_inventory(self) -> None:
        recipe = self.current_recipe()
        if not recipe:
            return
        item_id = recipe.output.id

        def done(value: int | None) -> None:
            if value:
                total = self.inv.add(item_id, value)
                self.notify(f"{self.book.name(item_id)}: {total}")
                self.refresh_rows(keep_cursor=True)

        self.app.push_screen(
            QuantityModal(f"Add how many {self.book.name(item_id)}?", recipe.output.n),
            done,
        )

    def action_inventory(self) -> None:
        def done(_result=None) -> None:
            self.refresh_rows(keep_cursor=True)

        self.app.push_screen(InventoryScreen(self.book, self.inv), done)

    def action_storage(self) -> None:
        """Open on the highlighted output, since that is usually the question."""
        recipe = self.current_recipe()
        query = recipe.output_name if recipe else ""
        self.app.push_screen(StorageScreen(self.book, self.app.storage, self.inv, query))

    def action_nanites(self) -> None:
        self.app.push_screen(NaniteScreen(self.book, self.ease))

    def action_effects(self) -> None:
        self.app.push_screen(FoodScreen(self.book))

    def action_multitools(self) -> None:
        self.app.push_screen(MultiToolScreen())

    def action_portals(self) -> None:
        self.app.push_screen(PortalScreen(self.app.locations))

    def action_toggle_detail(self) -> None:
        self.detail_on = not self.detail_on
        self._update_detail_visibility()
        if self.detail_on and self.app.size.width < MIN_WIDTH_FOR_DETAIL:
            self.notify("Terminal too narrow for the detail pane")


class RecipeApp(App):
    """Holds the data and the two keys that make sense everywhere."""

    CSS_PATH = "app.tcss"
    TITLE = "NMSii"

    BINDINGS = [
        Binding("question_mark", "help", "help"),
        Binding("q", "quit", "quit"),
    ]

    def __init__(self, book: Book | None = None) -> None:
        super().__init__()
        self.book = book or Book()
        self.ease = EaseIndex(self.book)
        self.inv = Inventory()
        self.locations = LocationBook.load()
        self.storage = StorageGuide.load()
        for theme in THEMES:
            self.register_theme(theme)
        name = load_theme()
        self.theme = name if name in self.available_themes else THEMES[0].name
        self._apply_transparency()

    def on_mount(self) -> None:
        # Subscribed after the startup theme is set, so only a choice made in
        # the palette is written back.
        self.theme_changed_signal.subscribe(self, self._theme_changed)
        self.push_screen(RecipeScreen(self.book, self.ease, self.inv))

    def _apply_transparency(self) -> None:
        """ANSI colour on for a see-through theme; otherwise each theme decides."""
        self.ansi_color = True if self.theme in TRANSPARENT else None

    def _theme_changed(self, theme) -> None:
        self._apply_transparency()
        save_theme(theme.name)
        # Table cells are coloured with resolved hex, not theme variables, so
        # the screen on top has to redraw them.
        redraw = getattr(self.screen, "recolour", None)
        if redraw is not None:
            redraw()

    def get_system_commands(self, screen: Screen):
        """Trim the built-ins to the two that mean anything here.

        The defaults add Keys, Maximize and Screenshot, which between them push
        this app's own modes off the bottom of the palette on open -- and the
        key reference is better on `?` than in a panel.
        """
        yield SystemCommand("Theme", "Change the colour theme",
                            self.action_change_theme)
        yield SystemCommand("Quit", "Leave", self.action_quit)

    def action_help(self) -> None:
        self.push_screen(HelpScreen())
