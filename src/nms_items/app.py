"""The main screen: a filterable recipe table with a detail pane."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from .ease import EaseIndex
from .inventory import Inventory
from .model import Book, Recipe
from .widgets import SearchInput, VimDataTable
from .screens import (
    ChainScreen,
    FoodScreen,
    HelpScreen,
    InventoryScreen,
    MultiToolScreen,
    NaniteScreen,
    QuantityModal,
)

# Keep the table responsive: filtering 1,680 rows on every keystroke is fine,
# rendering them all is not.
MAX_ROWS = 400

# Below this width the detail pane costs more than it gives -- the table loses
# its Mult/Time/Machine columns to make room -- so it hides itself.
MIN_WIDTH_FOR_DETAIL = 100

BAND_COLOUR = {
    "easy": "#a6e3a1",
    "ok": "#f9e2af",
    "work": "#fab387",
    "hard": "#f38ba8",
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
        Binding("p", "filter_produces", "produced by"),
        Binding("r", "filter_consumes", "used in"),
        Binding("c", "chain", "chain"),
        Binding("a", "add_to_inventory", "+inventory"),
        Binding("i", "inventory", "inventory"),
        Binding("n", "nanites", "nanites"),
        Binding("e", "effects", "food effects"),
        Binding("m", "multitools", "multi-tools"),
        Binding("d", "toggle_detail", "detail pane"),
        Binding("backspace", "clear_item_filter", "clear filter"),
        # Escape in normal mode clears what you searched for; Escape in the
        # search box just leaves insert mode and keeps it.
        Binding("escape", "clear_search", "clear search", show=False),
    ]

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
            note.append(f"{role} [b #f9e2af]{self.book.name(self.item_filter)}[/]")
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
            self.query_one("#detail", Static).update("[#a6adc8]No recipe matches.[/]")

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
            f"[b #f9e2af]{recipe.output_label}[/]",
            f"[#a6adc8]{out.subtitle if out else ''}[/]",
            "",
            f"[b]{recipe.inputs_label}[/]",
            f"  -> [b]{recipe.output_label}[/]",
            "",
            f"[#89b4fa]Operation[/]  {recipe.operation}",
            f"[#89b4fa]Machine[/]    {recipe.machine}",
            f"[#89b4fa]Batch time[/] {recipe.time_label}",
            f"[#89b4fa]Multiplier[/] {recipe.multiplier_label}",
            f"[#89b4fa]Rate[/]       {recipe.rate:,.0f}/h per machine",
            f"[#89b4fa]Profit[/]     {recipe.profit:+,} units per batch",
            f"[#89b4fa]Gettable[/]   {self.ease.of_recipe(recipe).label}"
            f"  [#a6adc8](hardest ingredient)[/]",
            "",
            "[#89b4fa]Ingredients[/]",
        ]
        for ing in recipe.inputs:
            item = book.items.get(ing.id)
            have = self.inv.items.get(ing.id, 0)
            stock = f"  [#a6e3a1](have {have})[/]" if have else ""
            ease = self.ease.of(ing.id)
            lines.append(
                f"  {ing.n} x {book.name(ing.id)}"
                f"  [#a6adc8]{item.value if item else 0}u[/]{stock}"
                f"  [{BAND_COLOUR[ease.band]}]{ease.label}[/]"
            )
            lines.append(f"     [#a6adc8]{ease.describe(book)}[/]")

        others = [r for r in book.produced_by.get(recipe.output.id, []) if r.index != recipe.index]
        if others:
            lines += ["", f"[#89b4fa]Other ways to make it[/]  ({len(others)})"]
            for alt in sorted(others, key=lambda r: -max(r.loop, r.ratio))[:5]:
                lines.append(f"  {alt.inputs_label}  [#a6adc8]{alt.multiplier_label}[/]")
            lines.append("  [#a6adc8]press p to list them all[/]")

        uses = book.consumed_by.get(recipe.output.id, [])
        if uses:
            lines += ["", f"[#89b4fa]Used in[/]  {len(uses)} recipe(s) - press r"]

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
        self.domain_index = (self.domain_index + 1) % len(DOMAINS)
        self.refresh_rows()

    def action_cycle_sort(self) -> None:
        self.sort_index = (self.sort_index + 1) % len(SORTS)
        self.refresh_rows()

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

    def action_nanites(self) -> None:
        self.app.push_screen(NaniteScreen(self.book, self.ease))

    def action_effects(self) -> None:
        self.app.push_screen(FoodScreen(self.book))

    def action_multitools(self) -> None:
        self.app.push_screen(MultiToolScreen())

    def action_toggle_detail(self) -> None:
        self.detail_on = not self.detail_on
        self._update_detail_visibility()
        if self.detail_on and self.app.size.width < MIN_WIDTH_FOR_DETAIL:
            self.notify("Terminal too narrow for the detail pane")


class RecipeApp(App):
    """Holds the data and the two keys that make sense everywhere."""

    CSS_PATH = "app.tcss"
    TITLE = "NMS Items"

    BINDINGS = [
        Binding("question_mark", "help", "help"),
        Binding("q", "quit", "quit"),
    ]

    def __init__(self, book: Book | None = None) -> None:
        super().__init__()
        self.book = book or Book()
        self.ease = EaseIndex(self.book)
        self.inv = Inventory()

    def on_mount(self) -> None:
        self.push_screen(RecipeScreen(self.book, self.ease, self.inv))

    def action_help(self) -> None:
        self.push_screen(HelpScreen())
