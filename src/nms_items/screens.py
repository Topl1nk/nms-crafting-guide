"""The screens that sit on top of the recipe table: chains, inventory, help."""

from __future__ import annotations

from functools import partial
from typing import Iterator

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)

from . import food, graph, multitools, portals
from .commands import ModeCommand, ModeCommands, mode
from .ease import EaseIndex
from .widgets import SearchInput, VimDataTable, VimTree, VimVerticalScroll

# Footer groups. Keys that all do the same kind of thing say what that is once.
FILTER = Binding.Group("filter")
ITEM = Binding.Group("item")
SAVED = Binding.Group("saved")
COPY = Binding.Group("copy")
from .model import SOURCE_SETS, Book
from .portals import Address, AddressError, Location, LocationBook
from .inventory import Inventory


def fmt_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:g}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


class QuantityModal(ModalScreen[int | None]):
    """Ask for a number. Used for chain targets and inventory counts."""

    BINDINGS = [Binding("escape", "cancel", "cancel")]

    def __init__(self, title: str, value: int = 1) -> None:
        super().__init__()
        self.title_text = title
        self.value = value

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Static(self.title_text, id="modal-title")
            yield Input(value=str(self.value), id="modal-input")

    def on_mount(self) -> None:
        inp = self.query_one("#modal-input", Input)
        inp.focus()
        inp.action_end()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        try:
            self.dismiss(max(1, int(event.value.strip())))
        except ValueError:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ChainScreen(Screen):
    """A production plan: how to get N of an item out of a source tier."""

    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "back"),
        Binding("t", "cycle_tier", "source tier"),
        Binding("n", "set_qty", "quantity"),
        # Not k: that is cursor-up in the tables now.
        Binding("C", "toggle_cooking", "incl. cooking"),
    ]

    COMMANDS = {ModeCommands}

    def __init__(self, book: Book, target: str, qty: int = 1) -> None:
        super().__init__()
        self.book = book
        self.target = target
        self.qty = qty
        self.tier_names = list(SOURCE_SETS)
        self.tier_index = 0
        self.with_cooking = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="chain-summary")
        yield VimTree("plan", id="chain-tree")
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"Chain - {self.book.name(self.target)}"
        self.refresh_plan()

    def palette_commands(self) -> Iterator[ModeCommand]:
        for i, name in enumerate(self.tier_names):
            yield mode(
                "Source", name, partial(self._set_tier, i), i == self.tier_index,
                "What the plan is allowed to start from",
            )
        yield mode(
            "Recipes", "refining only", partial(self._set_cooking, False),
            not self.with_cooking,
        )
        yield mode(
            "Recipes", "refining and cooking", partial(self._set_cooking, True),
            self.with_cooking,
        )
        yield ModeCommand("Quantity", "How many to plan for", self.action_set_qty)

    def _set_tier(self, index: int) -> None:
        self.tier_index = index
        self.refresh_plan()

    def _set_cooking(self, on: bool) -> None:
        self.with_cooking = on
        self.refresh_plan()

    @property
    def domains(self) -> tuple[str, ...]:
        return ("refine", "cook") if self.with_cooking else ("refine",)

    def refresh_plan(self) -> None:
        tier_name = self.tier_names[self.tier_index]
        sources = set(SOURCE_SETS[tier_name])
        plan = graph.plan(self.book, self.target, sources, self.qty, self.domains)

        summary = self.query_one("#chain-summary", Static)
        tree = self.query_one("#chain-tree", VimTree)
        tree.clear()

        name = self.book.name(self.target)
        head = [
            f"[b]{self.qty} x {name}[/b]",
            f"from [b]{tier_name}[/b]  -  {', '.join(self.book.name(s) for s in sorted(sources))}",
        ]

        if not plan.ok:
            head.append("")
            head.append(
                "[#f38ba8]Not reachable from this source set.[/]  "
                "Press [b]t[/b] for a wider tier"
                + ("" if self.with_cooking else ", [b]k[/b] to allow cooking recipes")
                + "."
            )
            producers = self.book.produced_by.get(self.target, [])
            if producers:
                head.append("")
                head.append("[#a6adc8]It is made by:[/]")
                for recipe in producers[:6]:
                    head.append(f"  {recipe.inputs_label} -> {recipe.output_label}")
            else:
                head.append("")
                head.append("[#a6adc8]No recipe produces it - this one you have to find.[/]")
            summary.update("\n".join(head))
            tree.root.label = "nothing to do"
            return

        raw = "  ".join(
            f"{count} {self.book.name(item_id)}"
            for item_id, count in sorted(
                plan.raw_totals.items(), key=lambda kv: -kv[1]
            )
        )
        head.append("")
        head.append(f"[#a6e3a1]Gather:[/] {raw}")
        head.append(
            f"[#a6adc8]{plan.steps} refining step(s), "
            f"{fmt_time(plan.total_seconds)} of machine time "
            f"(one refiner, unattended).[/]"
        )
        if not self.with_cooking:
            head.append("[#a6adc8]Refining only - press k to allow cooking recipes.[/]")
        summary.update("\n".join(head))

        tree.root.label = f"{self.qty} x {name}"
        tree.root.data = self.target
        self._add_children(tree.root, plan.root)
        tree.root.expand_all()

    def _add_children(self, node, step: graph.Step) -> None:
        if step.recipe:
            node.label = (
                f"{step.qty} x {self.book.name(step.item_id)}"
                f"   [{step.recipe.operation} x{step.batches}"
                f", {fmt_time(step.recipe.time * step.batches)}"
                f", {step.recipe.machine}]"
            )
        for child in step.children:
            if child.recipe:
                sub = node.add("", expand=True)
                self._add_children(sub, child)
            else:
                tag = "gather" if child.raw else "find"
                sub = node.add_leaf(
                    f"{child.qty} x {self.book.name(child.item_id)}   ({tag})"
                )
                sub.data = child.item_id

    def action_cycle_tier(self) -> None:
        self.tier_index = (self.tier_index + 1) % len(self.tier_names)
        self.refresh_plan()

    def action_toggle_cooking(self) -> None:
        self.with_cooking = not self.with_cooking
        self.refresh_plan()

    def action_set_qty(self) -> None:
        def done(value: int | None) -> None:
            if value:
                self.qty = value
                self.refresh_plan()

        self.app.push_screen(
            QuantityModal(f"How many {self.book.name(self.target)}?", self.qty), done
        )


class InventoryScreen(Screen):
    """What you are carrying, and what that unlocks."""

    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "back"),
        # `/` is insert mode here too. This screen used to open with the add
        # field focused, which made every letter key type instead of act -- so
        # the footer was correctly, and uselessly, empty on arrival.
        Binding("slash", "focus_add", "add item"),
        Binding("d,delete", "drop", "drop item", group=ITEM),
        Binding("e", "edit", "edit count", group=ITEM),
        Binding("x", "clear_all", "clear all", group=ITEM),
        # Not k: that is cursor-up in the tables now.
        Binding("C", "toggle_cooking", "incl. cooking"),
    ]

    COMMANDS = {ModeCommands}

    def __init__(self, book: Book, inventory: Inventory) -> None:
        super().__init__()
        self.book = book
        self.inv = inventory
        self.with_cooking = True

    def compose(self) -> ComposeResult:
        yield Header()
        yield SearchInput(
            placeholder="/ to add:  <item name> <count>   e.g. platinum 250",
            id="inv-add",
        )
        with Horizontal(id="inv-body"):
            with Vertical(id="inv-list"):
                yield Label("Carrying", classes="pane-title")
                yield VimDataTable(id="inv-table", cursor_type="row")
            with Vertical(id="inv-right"):
                yield Label("Can refine right now", classes="pane-title")
                yield VimDataTable(id="can-table", cursor_type="row")
                yield Label("One ingredient short", classes="pane-title")
                yield VimDataTable(id="near-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Inventory"
        self.query_one("#inv-table", DataTable).add_columns("Item", "Have", "Value")
        self.query_one("#can-table", DataTable).add_columns(
            "Make", "From", "Mult", "Batches"
        )
        self.query_one("#near-table", DataTable).add_columns("Make", "From", "Missing")
        self.refresh_all()
        self.query_one("#inv-table", VimDataTable).focus()

    def palette_commands(self) -> Iterator[ModeCommand]:
        yield mode(
            "Recipes", "refining only", partial(self._set_cooking, False),
            not self.with_cooking,
        )
        yield mode(
            "Recipes", "refining and cooking", partial(self._set_cooking, True),
            self.with_cooking,
        )
        yield ModeCommand("Add an item", "Type a name and a count",
                          self.action_focus_add)
        yield ModeCommand("Clear inventory", "Drop everything you are carrying",
                          self.action_clear_all)

    def _set_cooking(self, on: bool) -> None:
        self.with_cooking = on
        self.refresh_all()

    @property
    def domains(self) -> tuple[str, ...]:
        return ("refine", "cook") if self.with_cooking else ("refine",)

    def refresh_all(self) -> None:
        inv_table = self.query_one("#inv-table", DataTable)
        inv_table.clear()
        for item_id, count in sorted(
            self.inv.items.items(), key=lambda kv: self.book.name(kv[0])
        ):
            item = self.book.items.get(item_id)
            inv_table.add_row(
                self.book.name(item_id),
                str(count),
                f"{(item.value if item else 0) * count:,}",
                key=item_id,
            )

        can_table = self.query_one("#can-table", DataTable)
        can_table.clear()
        for recipe, batches in graph.craftable_now(
            self.book, self.inv.items, self.domains
        )[:200]:
            can_table.add_row(
                recipe.output_label,
                recipe.inputs_label,
                recipe.multiplier_label,
                str(batches),
                key=str(recipe.index),
            )

        near_table = self.query_one("#near-table", DataTable)
        near_table.clear()
        for recipe, missing in graph.one_hop_away(
            self.book, self.inv.items, self.domains
        )[:200]:
            need = ", ".join(f"{n} {self.book.name(i)}" for i, n in missing)
            near_table.add_row(
                recipe.output_label, recipe.inputs_label, need, key=str(recipe.index)
            )

    def action_focus_add(self) -> None:
        self.query_one("#inv-add", SearchInput).focus()

    def on_search_input_escaped(self, event: SearchInput.Escaped) -> None:
        """Leaving the add field must not add whatever is half-typed."""
        self.query_one("#inv-table", VimDataTable).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        if not text:
            return

        # Trailing number is the count; everything before it is the item name.
        parts = text.rsplit(" ", 1)
        count = 1
        name = text
        if len(parts) == 2 and parts[1].lstrip("+-").isdigit():
            name, count = parts[0], int(parts[1])

        item = self.book.by_name(name)
        if item is None:
            matches = self.book.search_items(name, limit=2)
            if len(matches) == 1:
                item = matches[0]
            elif not matches:
                self.notify(f"No item matching {name!r}", severity="error")
                return
            else:
                names = ", ".join(m.name for m in matches)
                self.notify(f"Ambiguous: {names}", severity="warning")
                return

        total = self.inv.add(item.id, count)
        self.notify(f"{item.name}: {total}")
        self.refresh_all()
        # Stay in the field: adding things comes in runs.

    def _selected_item(self) -> str | None:
        table = self.query_one("#inv-table", DataTable)
        if table.row_count == 0:
            return None
        try:
            return str(table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value)
        except Exception:
            return None

    def action_drop(self) -> None:
        item_id = self._selected_item()
        if item_id:
            self.inv.set(item_id, 0)
            self.refresh_all()

    def action_edit(self) -> None:
        item_id = self._selected_item()
        if not item_id:
            return

        def done(value: int | None) -> None:
            if value is not None:
                self.inv.set(item_id, value)
                self.refresh_all()

        self.app.push_screen(
            QuantityModal(
                f"How many {self.book.name(item_id)}?", self.inv.items.get(item_id, 1)
            ),
            done,
        )

    def action_clear_all(self) -> None:
        self.inv.clear()
        self.refresh_all()
        self.notify("Inventory cleared")

    def action_toggle_cooking(self) -> None:
        self._set_cooking(not self.with_cooking)


class NaniteScreen(Screen):
    """Every route to nanites, ranked by throughput and by how gettable it is.

    Nanites are the second currency and the units column says nothing useful
    about them -- 1 Salvaged Data is worth ~51k units and 15 nanites, and which
    of those you want depends entirely on the day. So they get their own view.
    """

    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "back"),
        Binding("s", "cycle_sort", "sort"),
    ]

    COMMANDS = {ModeCommands}

    SORTS = [
        ("rate", "nanites/hour"),
        ("ease", "how gettable"),
        ("per_input", "nanites per item"),
        ("nanites", "nanites per batch"),
    ]

    def __init__(self, book: Book, ease: EaseIndex) -> None:
        super().__init__()
        self.book = book
        self.ease = ease
        self.sort_index = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="nanite-note")
        yield VimDataTable(id="nanite-table", cursor_type="row", zebra_stripes=True)
        yield Static(id="nanite-detail")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Nanites"
        table = self.query_one("#nanite-table", DataTable)
        table.add_column("Refine", width=34)
        table.add_column("Nan", width=5)
        table.add_column("Time", width=6)
        table.add_column("Nan/h", width=7)
        table.add_column("Per item", width=9)
        table.add_column("Gettable", width=13)
        table.add_column("Where it comes from", width=44)
        self.rows = graph.nanite_ladder(self.book)
        self.refresh_rows()
        table.focus()

    def refresh_rows(self) -> None:
        key = self.SORTS[self.sort_index][0]
        if key == "rate":
            self.rows.sort(key=lambda r: -r.per_hour)
        elif key == "ease":
            self.rows.sort(key=lambda r: (-self.ease.of_recipe(r.recipe).score, -r.per_hour))
        elif key == "per_input":
            self.rows.sort(key=lambda r: -r.per_input)
        else:
            self.rows.sort(key=lambda r: -r.nanites)

        table = self.query_one("#nanite-table", DataTable)
        table.clear()
        for row in self.rows:
            ease = self.ease.of_recipe(row.recipe)
            table.add_row(
                row.recipe.inputs_label,
                str(row.nanites),
                row.recipe.time_label,
                f"{row.per_hour:,.0f}",
                f"{row.per_input:.2f}",
                ease.label,
                ease.where or ease.describe(self.book),
                key=str(row.recipe.index),
            )

        self.query_one("#nanite-note", Static).update(
            f"[b]{len(self.rows)}[/] ways to make nanites, sorted by "
            f"[b]{self.SORTS[self.sort_index][1]}[/]   "
            "[#a6adc8]one refiner, kept fed - press s to re-sort[/]"
        )
        if self.rows:
            self.show_detail(0)

    def show_detail(self, index: int) -> None:
        row = self.rows[index]
        ease = self.ease.of_recipe(row.recipe)
        lines = [
            f"[b #f9e2af]{row.recipe.inputs_label}[/] -> [b]{row.nanites} Nanite Cluster[/]"
            f"   [#a6adc8]{row.recipe.operation}, {row.recipe.machine}[/]",
            f"[#89b4fa]{row.per_hour:,.0f} nanites/hour[/] per refiner   "
            f"[#a6adc8]{row.per_input:.2f} per item consumed, "
            f"{row.units_cost:,} units of value spent[/]",
        ]
        if ease.where:
            lines.append(f"[#a6e3a1]{ease.where}[/]")
        else:
            lines.append(f"[#a6adc8]{ease.describe(self.book)}[/]")
        if ease.note:
            lines.append(f"[#a6adc8]{ease.note}[/]")
        self.query_one("#nanite-detail", Static).update("\n".join(lines))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if 0 <= event.cursor_row < len(self.rows):
            self.show_detail(event.cursor_row)

    def palette_commands(self) -> Iterator[ModeCommand]:
        for i, (_, label) in enumerate(self.SORTS):
            yield mode(
                "Sort", label, partial(self._set_sort, i), i == self.sort_index,
            )

    def _set_sort(self, index: int) -> None:
        self.sort_index = index
        self.refresh_rows()

    def action_cycle_sort(self) -> None:
        self.sort_index = (self.sort_index + 1) % len(self.SORTS)
        self.refresh_rows()


class FoodScreen(Screen):
    """What eating a cooked product actually does, per buff.

    Cooking is usually pitched as a money engine, and it is one -- but every
    dish also grants a temporary buff, and the files record which stat and how
    strongly. This is the "what should I eat before going down there" view.
    """

    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "back"),
        Binding("tab", "focus_next", "switch pane"),
    ]

    def __init__(self, book: Book) -> None:
        super().__init__()
        self.book = book
        self.groups = food.by_effect(book)
        self.effects = list(self.groups)
        self.current: list[food.Dish] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="food-note")
        with Horizontal(id="food-body"):
            with Vertical(id="food-left"):
                yield Label("Buff", classes="pane-title")
                yield VimDataTable(id="effect-table", cursor_type="row")
            with Vertical(id="food-right"):
                yield Label("Dishes, strongest first", classes="pane-title")
                yield VimDataTable(id="dish-table", cursor_type="row", zebra_stripes=True)
        yield Static(id="food-detail")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Cooking - what it does"
        effects = self.query_one("#effect-table", DataTable)
        effects.add_column("Boosts", width=26)
        effects.add_column("N", width=4)
        effects.add_column("Good for", width=28)
        for name in self.effects:
            group = self.groups[name]
            effects.add_row(
                name, str(len(group)), group[0].use or "-", key=name
            )

        dishes = self.query_one("#dish-table", DataTable)
        dishes.add_column("Dish", width=28)
        dishes.add_column("Pot", width=5)
        dishes.add_column("Value", width=9)
        dishes.add_column("Uplift", width=9)
        dishes.add_column("Cook from", width=40)
        dishes.add_column("Time", width=6)

        self.query_one("#food-note", Static).update(
            f"[b]{sum(len(g) for g in self.groups.values())}[/] cooked dishes across "
            f"[b]{len(self.effects)}[/] buffs   "
            "[#a6adc8]Pot = the game's own 0-1 quality for the buff · "
            "Uplift = units gained over the ingredients, one batch[/]"
        )
        self.show_effect(self.effects[0])
        effects.focus()

    def show_effect(self, name: str) -> None:
        self.current = self.groups[name]
        table = self.query_one("#dish-table", DataTable)
        table.clear()
        for dish in self.current:
            table.add_row(
                dish.item.name,
                f"{dish.potency:.2f}",
                f"{dish.value:,}",
                f"{dish.uplift:+,}",
                dish.recipe.inputs_label,
                dish.recipe.time_label,
            )
        self.show_dish(0)

    def show_dish(self, index: int) -> None:
        if not self.current:
            return
        dish = self.current[min(index, len(self.current) - 1)]
        ways = (
            f"   [#a6adc8]{dish.ways} recipes make it[/]" if dish.ways > 1 else ""
        )
        lines = [
            f"[b #f9e2af]{dish.item.name}[/]  [#a6adc8]{dish.item.subtitle}[/]{ways}",
            f"[#89b4fa]{dish.effect}[/] at potency [b]{dish.potency:.2f}[/]"
            + (f"  [#a6adc8]- {dish.use}[/]" if dish.use else ""),
            f"[#a6e3a1]{dish.recipe.inputs_label}[/] -> {dish.recipe.output_label}"
            f"   [#a6adc8]{dish.recipe.operation}, {dish.recipe.time_label}[/]",
            f"[#a6adc8]Sells for {dish.value:,} units; cooking one batch adds "
            f"{dish.uplift:,} over the ingredients.[/]",
        ]
        self.query_one("#food-detail", Static).update("\n".join(lines))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "effect-table":
            if 0 <= event.cursor_row < len(self.effects):
                self.show_effect(self.effects[event.cursor_row])
        elif event.data_table.id == "dish-table":
            self.show_dish(event.cursor_row)


class MultiToolScreen(Screen):
    """Multi-tool reference: which type, which weapon, and how to get one.

    Everything else in the app is generated from the game's recipe tables; this
    is read from data/multitools.json, written out of the guides, because the
    files carry nothing useful about multi-tools.
    """

    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "back"),
        # Brackets rather than arrows: the tables are wider than the pane, so a
        # focused DataTable eats left/right for horizontal scrolling and the
        # tabs would only switch while the tab bar itself had focus.
        Binding("left_square_bracket", "prev_tab", "prev tab"),
        Binding("right_square_bracket", "next_tab", "next tab"),
        # The "getting one" tab ends in published portal addresses, so the
        # screen that dials them belongs a single key away.
        Binding("P", "portals", "portal addresses"),
    ]

    COMMANDS = {ModeCommands}

    TABS = [
        ("tab-types", "types"),
        ("tab-weapons", "weapons"),
        ("tab-getting", "getting one"),
        ("tab-tips", "tips"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.data = multitools.load()

    def palette_commands(self) -> Iterator[ModeCommand]:
        active = self.query_one("#mt-tabs", TabbedContent).active
        for pane_id, label in self.TABS:
            yield mode(
                "Tab", label, partial(self._set_tab, pane_id), pane_id == active,
            )
        yield ModeCommand(
            "Portal addresses for these tools",
            "The Euclid shortlist, filtered to multi-tools",
            self.action_portals,
        )

    def _set_tab(self, pane_id: str) -> None:
        self.query_one("#mt-tabs", TabbedContent).active = pane_id

    def action_portals(self) -> None:
        self.app.push_screen(PortalScreen(kind="multi-tool"))

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"[b #a6e3a1]{self.data.headline}[/]", id="mt-headline")
        with TabbedContent(id="mt-tabs"):
            with TabPane("Types", id="tab-types"):
                yield VimDataTable(id="type-table", cursor_type="row", zebra_stripes=True)
                yield Static(id="type-detail")
            with TabPane("Weapons", id="tab-weapons"):
                yield VimDataTable(id="weapon-table", cursor_type="row", zebra_stripes=True)
                yield Static(id="weapon-detail")
            with TabPane("Getting one", id="tab-getting"):
                yield VimVerticalScroll(Static(self._getting_text(), id="mt-getting"))
            with TabPane("Tips", id="tab-tips"):
                yield VimVerticalScroll(Static(self._tips_text(), id="mt-tips"))
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Multi-tools"

        types = self.query_one("#type-table", DataTable)
        types.add_column("Type", width=15)
        types.add_column("Damage", width=10)
        types.add_column("Mining", width=10)
        types.add_column("Scan", width=12)
        types.add_column("Slots", width=10)
        types.add_column("Notes", width=62)
        for row in self.data.types:
            types.add_row(
                row.type, row.damage, row.mining, row.scan, row.slots, row.note
            )

        weapons = self.query_one("#weapon-table", DataTable)
        weapons.add_column("Weapon", width=18)
        weapons.add_column("Like a", width=20)
        weapons.add_column("Best hit", width=10)
        weapons.add_column("Good", width=46)
        weapons.add_column("Bad", width=42)
        for weapon in self.data.weapons:
            weapons.add_row(
                weapon.weapon, weapon.kind, weapon.best_hit, weapon.pro, weapon.con
            )

        self._show_type(0)
        self._show_weapon(0)

    # -- panes -----------------------------------------------------------

    def _getting_text(self) -> str:
        lines = ["[b #89b4fa]Where each type comes from[/]", ""]
        for row in self.data.getting:
            lines.append(
                f"  [b]{row['type']}[/]  [#a6adc8]({row['cost']})[/]  {row['where']}"
            )
            lines.append(f"      [#a6adc8]{row['how']}[/]")
        for procedure in self.data.procedures:
            lines += ["", f"[b #89b4fa]{procedure.title}[/]"]
            for i, step in enumerate(procedure.steps, 1):
                lines.append(f"  {i}. {step}")
            if procedure.note:
                lines.append(f"  [#a6adc8]{procedure.note}[/]")
            for extra in procedure.after:
                lines.append(f"  [#f9e2af]-[/] {extra}")
        return "\n".join(lines)

    def _tips_text(self) -> str:
        lines = []
        for rule in self.data.rules:
            lines.append(f"[b #f9e2af]{rule.title}[/]")
            lines.append(f"  {rule.body}")
            lines.append("")
        lines.append("[b #89b4fa]Where upgrades come from[/]")
        for row in self.data.upgrade_sources:
            lines.append(
                f"  [b]{row['kind']}[/]  {row['where']}   [#a6adc8]{row['note']}[/]"
            )
        lines += ["", "[b #89b4fa]Upgrade order[/]"]
        for i, step in enumerate(self.data.upgrade_order, 1):
            lines.append(f"  {i}. {step}")
        return "\n".join(lines)

    def _show_type(self, index: int) -> None:
        row = self.data.types[min(index, len(self.data.types) - 1)]
        self.query_one("#type-detail", Static).update(
            f"[b #f9e2af]{row.type}[/]   "
            f"[#89b4fa]damage[/] {row.damage}   "
            f"[#89b4fa]mining[/] {row.mining}   "
            f"[#89b4fa]scan[/] {row.scan}   "
            f"[#89b4fa]slots at spawn[/] {row.slots}\n{row.note}"
        )

    def _show_weapon(self, index: int) -> None:
        weapon = self.data.weapons[min(index, len(self.data.weapons) - 1)]
        self.query_one("#weapon-detail", Static).update(
            f"[b #f9e2af]{weapon.weapon}[/]  [#a6adc8]{weapon.kind}, "
            f"best measured hit {weapon.best_hit}[/]\n"
            f"[#a6e3a1]+[/] {weapon.pro}\n[#f38ba8]-[/] {weapon.con}"
        )

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "type-table":
            self._show_type(event.cursor_row)
        elif event.data_table.id == "weapon-table":
            self._show_weapon(event.cursor_row)

    def _step_tab(self, delta: int) -> None:
        tabs = self.query_one("#mt-tabs", TabbedContent)
        panes = [pane.id for pane in tabs.query(TabPane)]
        tabs.active = panes[(panes.index(tabs.active) + delta) % len(panes)]

    def action_prev_tab(self) -> None:
        self._step_tab(-1)

    def action_next_tab(self) -> None:
        self._step_tab(1)


# The readout needs 58 usable columns for the glyph grid; below this total the
# saved-address list is dropped rather than squeezing both.
MIN_WIDTH_FOR_LIST = 100
READOUT_WIDTH = 62

# The two filters on the portal screen, "everything" first in both.
KIND_FILTERS: list[tuple[str | None, str]] = [(None, "everything")] + [
    (kind, kind) for kind in portals.KINDS
]
ORIGIN_FILTERS: list[tuple[str | None, str]] = [
    (None, "mine and shared"),
    ("mine", "my finds"),
    ("shared", "shared"),
]

# Which of the address's five fields each glyph belongs to, and the colour it
# gets. The same colour is used in the grouped code and in the numbered glyph
# list, so it is obvious at a glance which three glyphs are the X coordinate.
FIELD_SPANS = [
    ("planet", 1, "#f38ba8"),
    ("system", 3, "#89b4fa"),
    ("Y", 2, "#a6e3a1"),
    ("Z", 3, "#f9e2af"),
    ("X", 3, "#cba6f7"),
]
GLYPH_COLOURS = [colour for _, width, colour in FIELD_SPANS for _ in range(width)]

PORTAL_PRIMER = """\
[b #89b4fa]Portal addresses[/]

Paste either form above; it converts as you type.

  [b]portal code[/]        [#a6adc8]40E907FF0D6B[/]
    12 hex digits, one per glyph
  [b]galactic address[/]   [#a6adc8]056A:0086:07EF:00E9[/]
    what a signal booster shows
  [b]share link[/]         [#a6adc8]a nmsportals.github.io URL[/]

Type anything else and it searches what you saved.

[b #89b4fa]What the twelve glyphs are[/]

  [b #f38ba8]p[/] [b #89b4fa]SSS[/] [b #a6e3a1]YY[/] [b #f9e2af]ZZZ[/] [b #cba6f7]XXX[/]

  [#f38ba8]planet[/], [#89b4fa]system index[/], then the voxel as
  [#a6e3a1]height[/], [#f9e2af]width[/], [#cba6f7]length[/]. Portal coordinates put
  0,0,0 at the centre of the galaxy; a galactic
  address counts from a corner, which is the whole
  reason the two do not look alike.

[b #89b4fa]Dialling one[/]

  The 16 glyphs sit on the portal dial in a fixed
  order, 0-9 then A-F, so the hex digit [i]is[/] the
  position: [b]A[/] is the 11th symbol, every time. You
  need all 16 unlocked, not twelve.

[b #89b4fa]Sharing one[/]

  The same twelve glyphs point at a different star
  in each of the 256 galaxies, so an address alone
  is ambiguous. Saved ones carry their galaxy.
"""


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def _looks_like_address(text: str) -> bool:
    """Hex and separators only: they meant an address and mistyped it.

    Anything with a letter past F in it is a search term, not a bad address,
    so the error line stays quiet while you type a system name.
    """
    return bool(text) and all(ch in "0123456789abcdefABCDEF:,-. " for ch in text)


class LocationModal(ModalScreen[Location | None]):
    """Name an address so it is worth keeping. Tab between fields, Enter saves."""

    BINDINGS = [Binding("escape", "cancel", "cancel")]

    def __init__(self, code: str, existing: Location | None = None) -> None:
        super().__init__()
        self.code = code
        self.existing = existing

    def compose(self) -> ComposeResult:
        base = self.existing
        with Vertical(id="loc-modal-box"):
            yield Static(
                f"[b]Save[/] [#f9e2af]{self.code}[/]"
                f"   [#a6adc8]Tab moves, Enter saves, Esc cancels[/]",
                id="modal-title",
            )
            # Labelled single-line rows rather than seven bordered boxes: the
            # placeholder vanishes the moment you type, and with this many
            # fields that leaves you guessing which one you are in.
            yield from self._field("Name", "loc-name", base.name if base else "",
                                   "the system, usually")
            yield from self._field("Kind", "loc-kind",
                                   base.kind if base else "multi-tool",
                                   " | ".join(portals.KINDS))
            yield from self._field("Found", "loc-origin",
                                   base.origin if base else "mine",
                                   "mine (you found it) | shared (someone else did)")
            yield from self._field("Galaxy", "loc-galaxy",
                                   str(base.galaxy if base else 1),
                                   "galaxy number - 1 is Euclid")
            yield from self._field("There", "loc-detail-field",
                                   base.detail if base else "",
                                   "what is there - class, type, slots")
            yield from self._field("Finding", "loc-where", base.where if base else "",
                                   "how to find it once you arrive")
            yield from self._field("Source", "loc-source", base.source if base else "",
                                   "who shared it, or where you found it")

    def _field(
        self, label: str, field_id: str, value: str, placeholder: str
    ) -> ComposeResult:
        with Horizontal(classes="loc-field"):
            yield Label(label, classes="loc-label")
            yield Input(value=value, placeholder=placeholder, id=field_id)

    def on_mount(self) -> None:
        self.query_one("#loc-name", Input).focus()

    def _value(self, selector: str) -> str:
        return self.query_one(selector, Input).value.strip()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = self._value("#loc-name")
        if not name:
            self.notify("It needs a name", severity="warning")
            self.query_one("#loc-name", Input).focus()
            return
        kind = self._value("#loc-kind").lower()
        if kind not in portals.KINDS:
            kind = "other"
        origin = self._value("#loc-origin").lower()
        if origin not in portals.ORIGINS:
            origin = "mine"
        try:
            galaxy = max(1, int(self._value("#loc-galaxy") or 1))
        except ValueError:
            galaxy = 1
        self.dismiss(
            Location(
                name=name,
                code=self.code,
                kind=kind,
                origin=origin,
                galaxy=galaxy,
                detail=self._value("#loc-detail-field"),
                where=self._value("#loc-where"),
                source=self._value("#loc-source"),
                added=self.existing.added if self.existing else "",
            )
        )

    def action_cancel(self) -> None:
        self.dismiss(None)


class PortalScreen(Screen):
    """Convert an address, and keep the ones worth going back to.

    One box does both jobs: paste a portal code or a galactic address and it
    converts; type anything else and it searches what you have saved. That is
    the actual workflow -- you are either decoding something someone shared or
    looking for the thing you wrote down.
    """

    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "back"),
        Binding("slash", "focus_input", "convert / search"),
        Binding("f", "cycle_kind", "kind", group=FILTER),
        Binding("o", "cycle_origin", "mine/shared", group=FILTER),
        Binding("p", "cycle_planet", "planet glyph"),
        Binding("s", "save", "save", group=SAVED),
        Binding("e", "edit", "edit", group=SAVED),
        Binding("d,delete", "drop", "drop", group=SAVED),
        Binding("y", "copy_code", "code", group=COPY),
        Binding("Y", "copy_galactic", "galactic", group=COPY),
    ]

    COMMANDS = {ModeCommands}

    def __init__(
        self, book: LocationBook | None = None, kind: str | None = None
    ) -> None:
        super().__init__()
        self.locations = book or LocationBook.load()
        self.current: Address | None = None
        self.error = ""
        self.query_text = ""
        self.kind_index = next(
            (i for i, (k, _) in enumerate(KIND_FILTERS) if k == kind), 0
        )
        self.origin_index = 0
        self.planet = 0
        self.rows: list[Location] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield SearchInput(
            placeholder="paste a portal code, a galactic address or a share link "
            "- or type to search what you saved",
            id="portal-input",
        )
        with Horizontal(id="portal-body"):
            yield VimVerticalScroll(Static(id="portal-readout"), id="portal-left")
            with Vertical(id="portal-right"):
                yield Label(id="loc-title", classes="pane-title")
                yield VimDataTable(id="loc-table", cursor_type="row", zebra_stripes=True)
                yield Static(id="loc-detail")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Portals"
        self._fit_to_width()
        table = self.query_one("#loc-table", DataTable)
        table.add_column("Name", width=21)
        table.add_column("Kind", width=10)
        table.add_column("Found", width=6)
        table.add_column("Address", width=12)
        table.add_column("What is there", width=26)
        self.refresh_locations()
        self.refresh_readout()
        table.focus()

    def palette_commands(self) -> Iterator[ModeCommand]:
        for i, (_, label) in enumerate(KIND_FILTERS):
            yield mode(
                "Kind", label, partial(self._set_kind, i), i == self.kind_index,
            )
        for i, (_, label) in enumerate(ORIGIN_FILTERS):
            yield mode(
                "Found", label, partial(self._set_origin, i),
                i == self.origin_index,
            )
        if self.current is not None:
            yield ModeCommand(
                "Copy portal code", self.current.portal_code, self.action_copy_code)
            yield ModeCommand(
                "Copy galactic address", self.current.galactic,
                self.action_copy_galactic)
            yield ModeCommand(
                "Save this address", "Name it and keep it", self.action_save)
            yield ModeCommand(
                "Next planet glyph",
                "The one field a galactic address cannot carry",
                self.action_cycle_planet)

    def _set_kind(self, index: int) -> None:
        self.kind_index = index
        self.refresh_locations()

    def _set_origin(self, index: int) -> None:
        self.origin_index = index
        self.refresh_locations()

    def on_resize(self) -> None:
        self._fit_to_width()

    def _fit_to_width(self) -> None:
        """Under 100 columns the saved list goes and the readout takes it all.

        Same bargain the recipe screen strikes with its detail pane: the
        conversion is the thing you came for, the list is the luxury.
        """
        roomy = self.app.size.width >= MIN_WIDTH_FOR_LIST
        left = self.query_one("#portal-left", VimVerticalScroll)
        self.query_one("#portal-right", Vertical).display = roomy
        left.styles.width = READOUT_WIDTH if roomy else "1fr"
        # The divider is only a divider while there are two panes.
        left.set_class(not roomy, "-solo")

    # -- data ------------------------------------------------------------

    @property
    def kind(self) -> str | None:
        return KIND_FILTERS[self.kind_index][0]

    @property
    def origin(self) -> str | None:
        return ORIGIN_FILTERS[self.origin_index][0]

    def refresh_locations(self, keep_cursor: bool = False) -> None:
        table = self.query_one("#loc-table", DataTable)
        cursor = table.cursor_row if keep_cursor else 0
        self.rows = self.locations.search(self.query_text, self.kind, self.origin)

        table.clear()
        for loc in self.rows:
            table.add_row(
                loc.name, loc.kind, loc.origin, loc.code, loc.detail or "-"
            )
        self._update_pane_title(len(self.rows))

        if self.rows:
            table.move_cursor(row=min(cursor, len(self.rows) - 1))
            self.show_location(self.rows[min(cursor, len(self.rows) - 1)])
        elif len(self.locations):
            self.query_one("#loc-detail", Static).update(
                "[#a6adc8]Nothing matches. [b]f[/] widens the kind filter.[/]"
            )
        else:
            self.query_one("#loc-detail", Static).update(
                "[#a6adc8]Nothing saved yet - paste an address above and press "
                "[b]s[/], or edit data/locations.json.[/]"
            )

    def _update_pane_title(self, shown: int) -> None:
        """The two filters are only discoverable if the header says they are on."""
        title = ["Saved addresses"]
        if self.kind:
            title.append(KIND_FILTERS[self.kind_index][1])
        if self.origin:
            title.append(ORIGIN_FILTERS[self.origin_index][1])
        total = len(self.locations)
        count = f"{shown} of {total}" if shown != total else f"{total}"
        self.query_one("#loc-title", Label).update(
            f"{'  -  '.join(title)}   [#a6adc8]{count}"
            f"   ({self.locations.count('mine')} mine,"
            f" {self.locations.count('shared')} shared)[/]"
        )

    def current_location(self) -> Location | None:
        table = self.query_one("#loc-table", DataTable)
        if not self.rows or not 0 <= table.cursor_row < len(self.rows):
            return None
        return self.rows[table.cursor_row]

    # -- the readout -----------------------------------------------------

    def refresh_readout(self) -> None:
        self.query_one("#portal-readout", Static).update(self._readout_text())

    def _readout_text(self) -> str:
        if self.current is None:
            head = f"[#f38ba8]{self.error}[/]\n\n" if self.error else ""
            return head + PORTAL_PRIMER

        address = self.current
        code = address.portal_code
        grouped = " ".join(
            f"[b {colour}]{part}[/]"
            for (_, _, colour), part in zip(
                FIELD_SPANS, address.portal_grouped.split()
            )
        )
        lines = [
            f"{grouped}",
            "",
            f"[#89b4fa]Portal code[/]   [b]{code}[/]",
            f"[#89b4fa]Galactic[/]      [b]{address.galactic}[/]",
            f"[#89b4fa]Voxel[/]         {address.voxel_label}"
            f"  [#a6adc8]from centre[/]",
            f"[#89b4fa]Planet[/]        {ordinal(address.planet + 1)} of the system"
            f"  [#a6adc8](glyph {address.planet:X})[/]",
            f"[#89b4fa]System[/]        0x{address.system:03X}"
            f"  [#a6adc8]({address.system})[/]",
            f"[#89b4fa]Share link[/]",
            f"  [#a6adc8]{address.share_link}[/]",
        ]
        for warning in address.warnings:
            lines.append(f"[#f9e2af]![/] [#f9e2af]{warning}[/]")

        # Position, then the digit, then the name -- because at the dial you
        # count to the position and the digit is what you are counting to.
        lines += ["", "[b #89b4fa]Glyphs, in dial order[/]"]
        names = address.glyph_names
        for start in range(0, 12, 3):
            row = [
                f"[#a6adc8]{i + 1:>2}[/] [b {GLYPH_COLOURS[i]}]{code[i]}[/]"
                f" [{GLYPH_COLOURS[i]}]{names[i]:<9}[/]"
                for i in range(start, start + 3)
            ]
            lines.append("  " + "  ".join(row))

        saved = [loc for loc in self.locations.locations if loc.code == code]
        if saved:
            lines += ["", "[b #a6e3a1]Saved[/]"]
            for loc in saved:
                lines.append(
                    f"  {loc.name}  [#a6adc8]{loc.kind}, {loc.origin},"
                    f" {loc.galaxy_label}[/]"
                )
        else:
            lines += [
                "",
                "[#a6adc8][b]y[/] copies the code   [b]Y[/] the galactic address"
                "   [b]s[/] saves it   [b]p[/] changes the planet glyph[/]",
            ]
        return "\n".join(lines)

    def show_location(self, loc: Location) -> None:
        address = loc.address
        lines = [
            f"[b #f9e2af]{loc.name}[/]  [#a6adc8]{loc.kind}[/]"
            + (
                "  [#a6e3a1]found by me[/]"
                if loc.origin == "mine"
                else "  [#89b4fa]shared[/]"
            ),
            f"[#89b4fa]Address[/]     [b]{loc.code}[/]"
            f"   [#a6adc8]{address.galactic}[/]",
            f"[#89b4fa]Galaxy[/]      {loc.galaxy_label}",
        ]
        if loc.detail:
            lines.append(f"[#89b4fa]There[/]       {loc.detail}")
        if loc.where:
            lines.append(f"[#89b4fa]Finding it[/]  {loc.where}")
        trail = "  ".join(part for part in (loc.source, loc.added) if part)
        if trail:
            lines.append(f"[#a6adc8]{trail}[/]")
        self.query_one("#loc-detail", Static).update("\n".join(lines))

    # -- events ----------------------------------------------------------

    def on_input_changed(self, event: SearchInput.Changed) -> None:
        if event.input.id != "portal-input":
            return
        text = event.value.strip()
        if not text:
            self.current, self.error, self.query_text = None, "", ""
        else:
            try:
                self.current = Address.parse(text, self.planet)
                self.planet = self.current.planet
                self.error, self.query_text = "", ""
            except AddressError as exc:
                self.current = None
                self.error = str(exc) if _looks_like_address(text) else ""
                self.query_text = "" if _looks_like_address(text) else text
        self.refresh_locations()
        self.refresh_readout()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "portal-input":
            self.query_one("#loc-table", VimDataTable).focus()

    def on_search_input_escaped(self, event: SearchInput.Escaped) -> None:
        self.query_one("#loc-table", VimDataTable).focus()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.cursor_row < len(self.rows):
            self.show_location(self.rows[event.cursor_row])

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter on a saved row loads it into the converter."""
        loc = self.current_location()
        if loc:
            self.current = loc.address
            self.planet = self.current.planet
            self.error = ""
            self.refresh_readout()

    # -- actions ---------------------------------------------------------

    def action_focus_input(self) -> None:
        self.query_one("#portal-input", SearchInput).focus()

    def action_cycle_kind(self) -> None:
        self._set_kind((self.kind_index + 1) % len(KIND_FILTERS))

    def action_cycle_origin(self) -> None:
        """Your own finds, or the ones off a catalogue -- they age differently."""
        self._set_origin((self.origin_index + 1) % len(ORIGIN_FILTERS))

    def action_cycle_planet(self) -> None:
        """The planet glyph is the one a galactic address cannot tell you."""
        if self.current is None:
            self.notify("Nothing to change - paste an address first")
            return
        self.planet = (self.current.planet + 1) % 16
        self.current = self.current.with_planet(self.planet)
        self.refresh_readout()

    def action_copy_code(self) -> None:
        self._copy(self.current.portal_code if self.current else None, "portal code")

    def action_copy_galactic(self) -> None:
        self._copy(self.current.galactic if self.current else None, "galactic address")

    def _copy(self, text: str | None, what: str) -> None:
        if not text:
            self.notify("Nothing to copy", severity="warning")
            return
        self.app.copy_to_clipboard(text)
        self.notify(f"Copied {what}: {text}")

    def action_save(self) -> None:
        if self.current is None:
            self.notify("Paste an address first", severity="warning")
            return
        code = self.current.portal_code

        def done(loc: Location | None) -> None:
            if loc is None:
                return
            try:
                self.locations.add(loc)
            except OSError as exc:
                self.notify(f"Could not write {self.locations.path}: {exc}",
                            severity="error")
                return
            self.notify(f"Saved {loc.name} - {self.locations.path}")
            self.refresh_locations()
            self.refresh_readout()

        self.app.push_screen(LocationModal(code), done)

    def action_edit(self) -> None:
        loc = self.current_location()
        if loc is None:
            return
        index = next(
            (i for i, other in enumerate(self.locations.locations) if other is loc),
            None,
        )
        if index is None:
            return

        def done(updated: Location | None) -> None:
            if updated is None:
                return
            self.locations.locations[index] = updated
            try:
                self.locations.save()
            except OSError as exc:
                self.notify(f"Could not write: {exc}", severity="error")
                return
            self.refresh_locations(keep_cursor=True)

        self.app.push_screen(LocationModal(loc.code, existing=loc), done)

    def action_drop(self) -> None:
        loc = self.current_location()
        if loc is None:
            return
        index = next(
            (i for i, other in enumerate(self.locations.locations) if other is loc),
            None,
        )
        if index is None:
            return
        gone = self.locations.remove(index)
        if gone:
            self.notify(f"Dropped {gone.name}")
        self.refresh_locations(keep_cursor=True)


HELP_TEXT = """\
[b #89b4fa]NMS Items[/] - refining, cooking and chain lookup

[b]Ctrl+P - the command palette[/]
  Every mode this app has, by name, with a [b]●[/] on the one you are in.
  Open it and type: "profit" sorts by profit, "cooking" switches domain,
  "portal" opens the addresses, "shared" filters the saved list.
  This is the way out of guessing what the cycle keys cycle through -
  pressing s four times to reach "units profit" works, but nothing on
  screen ever told you that was an option.
  It is also why the footer can group its keys: nothing is hidden by
  being left out of the bar.

[b]Moving around (vim keys work everywhere)[/]
  j k            down / up          g g   top
  ctrl+d ctrl+u  half page          G     bottom
  h l            pan a wide table sideways
  /              search - this is insert mode: type freely, then
                 Esc or Enter to go back to normal mode
  Esc            in normal mode, clears the search and any filter

[b]Recipe list[/]
  Tab / Shift+Tab   move between search box and table
  f              cycle domain: refining -> cooking -> all
  s              cycle sort: multiplier, time, rate, profit, gettable, name
                 (or pick either one by name from Ctrl+P)
  p              show only recipes that PRODUCE the highlighted item
  r              show only recipes that CONSUME it (reverse lookup)
  Enter          pivot: everything touching the highlighted output
  Backspace      clear the item filter, back to the full list
  d              show/hide the detail pane (it hides itself under 100 columns)

[b]Planning[/]
  c              chain plan for the highlighted output
                 (inside: t = source tier, n = quantity, C = allow cooking)
  n              the nanite ladder - every route to nanites, ranked
  e              cooking effects - what each dish does when you eat it
  m              multi-tools - types, weapons, how to get the good ones
                 (inside: [ and ] move between the four tabs, P for the
                 portal addresses of the tools in the shortlist)
  P              portal addresses - convert glyphs to galactic coordinates
                 and back, and the places worth going
  a              add the highlighted output to your inventory
  i              inventory screen

[b]Inventory[/]
  / opens the add field, the same as everywhere else. Type
  "[i]item name count[/]" and press Enter - "platinum 250". A negative
  count subtracts, Esc goes back to normal mode.
  e   edit count      d   drop the item
  x   clear everything             C   include cooking recipes

[b]Portal addresses (P)[/]
  One box does both jobs. Paste a portal code (12 hex digits, one per
  glyph), a galactic address (0824:007F:00F3:01AC, what a signal booster
  shows) or a nmsportals.github.io link and it converts as you type;
  type anything else and it searches the addresses you have saved.
  y   copy the portal code       Y   copy the galactic address
  s   save what is converted     e   edit      d   drop
  f   filter by kind             o   filter by who found it
  p   change the planet glyph
  Enter on a saved row loads it back into the converter.

  Saved addresses are one of two kinds, and o cycles between them:
    mine     you stood there. Dated when you save it.
    shared   off a catalogue or from a friend. What is verified in one
             of those is the ADDRESS - the location is seeded to the
             coordinate and survives patches. Class, slot count and
             headline damage are somebody else's claim about somebody
             else's save, and they rot.

  The 16 glyphs sit on the portal dial in a fixed order, 0-9 then A-F,
  so the hex digit IS the position: A is the eleventh symbol, every
  time. You need all 16 unlocked, not twelve.

  An address is  p SSS YY ZZZ XXX  - planet, system index, then the
  voxel as height, width, length. Portal coordinates count from the
  centre of the galaxy and galactic ones from a corner, which is the
  whole reason the two forms do not look alike. The same twelve glyphs
  mean a different star in each of the 256 galaxies, so saved addresses
  carry theirs; galaxy 1 is Euclid.

[b]Reading the columns[/]
  Mult    units out per unit in. "x6 loop" means the recipe feeds itself:
          1 Chlorine + 2 Oxygen -> 6 Chlorine multiplies the seed six times.
  Time    one batch, from the game files. In-game display is often wrong.
  Rate    units per hour if you keep one machine fed.
  Profit  base-value difference, output minus inputs, for one batch. Says
          nothing about nanites - press n for those.
  Gettable  how reachable the hardest ingredient is.
          T0/T1/T2 +n   refinable from surface materials / asteroids /
                        an atmosphere harvester, n refining steps away
          needs seed    refinable, but wants a material none of those
                        tiers contain (a stellar metal, typically)
          loot (...)    no recipe makes it; the rating is how much of a
                        detour the guides make it sound

[b]Is cooking worth it, or should you just sell?[/]
  Both, in that order. Every cooked product carries a buff AND multiplies
  base value several times over, so the dish you eat and the dish you sell
  are the same dish. Cook the batch, eat one, sell the rest. The Uplift
  column on the e screen is what one batch adds over its ingredients.

[b]Data[/]
  357 refining and 1,323 cooking recipes parsed from the game's own
  recipe table by NMS-Handbook. Regenerate with: mise run fetch, then
  mise run build-data.
  Where loot comes from is the one thing the game files do not record;
  that lives in data/acquisition.json, written from the guides.
  Portal addresses are in data/locations.json - hand-editable, and
  what the s key on the portal screen writes to. It ships with the
  fifteen off the Euclid shortlists in guides 14 and 21, all marked
  shared; anything you add is marked mine by default.

j k  scroll     g G  top / bottom     Esc or q  close
"""


class HelpScreen(ModalScreen[None]):
    """The key reference. Scrollable, so it must not close on any keypress."""

    BINDINGS = [
        Binding("escape,q,question_mark,enter", "dismiss_help", "close"),
    ]

    def compose(self) -> ComposeResult:
        with VimVerticalScroll(id="help-box"):
            yield Static(HELP_TEXT)

    def on_mount(self) -> None:
        self.query_one("#help-box", VimVerticalScroll).focus()

    def action_dismiss_help(self) -> None:
        self.dismiss(None)
