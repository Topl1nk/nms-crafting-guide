"""The screens that sit on top of the recipe table: chains, inventory, help."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
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

from . import food, graph, multitools
from .ease import EaseIndex
from .model import SOURCE_SETS, Book
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
        Binding("k", "toggle_cooking", "incl. cooking"),
    ]

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
        yield Tree("plan", id="chain-tree")
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"Chain - {self.book.name(self.target)}"
        self.refresh_plan()

    @property
    def domains(self) -> tuple[str, ...]:
        return ("refine", "cook") if self.with_cooking else ("refine",)

    def refresh_plan(self) -> None:
        tier_name = self.tier_names[self.tier_index]
        sources = set(SOURCE_SETS[tier_name])
        plan = graph.plan(self.book, self.target, sources, self.qty, self.domains)

        summary = self.query_one("#chain-summary", Static)
        tree = self.query_one("#chain-tree", Tree)
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
        Binding("d,delete", "drop", "drop item"),
        Binding("e", "edit", "edit count"),
        Binding("x", "clear_all", "clear all"),
        Binding("k", "toggle_cooking", "incl. cooking"),
    ]

    def __init__(self, book: Book, inventory: Inventory) -> None:
        super().__init__()
        self.book = book
        self.inv = inventory
        self.with_cooking = True

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(
            placeholder="add to inventory:  <item name> <count>   e.g. platinum 250",
            id="inv-add",
        )
        with Horizontal(id="inv-body"):
            with Vertical(id="inv-list"):
                yield Label("Carrying", classes="pane-title")
                yield DataTable(id="inv-table", cursor_type="row")
            with Vertical(id="inv-right"):
                yield Label("Can refine right now", classes="pane-title")
                yield DataTable(id="can-table", cursor_type="row")
                yield Label("One ingredient short", classes="pane-title")
                yield DataTable(id="near-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Inventory"
        self.query_one("#inv-table", DataTable).add_columns("Item", "Have", "Value")
        self.query_one("#can-table", DataTable).add_columns(
            "Make", "From", "Mult", "Batches"
        )
        self.query_one("#near-table", DataTable).add_columns("Make", "From", "Missing")
        self.refresh_all()
        self.query_one("#inv-add", Input).focus()

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
        self.with_cooking = not self.with_cooking
        self.refresh_all()


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
        yield DataTable(id="nanite-table", cursor_type="row", zebra_stripes=True)
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
                yield DataTable(id="effect-table", cursor_type="row")
            with Vertical(id="food-right"):
                yield Label("Dishes, strongest first", classes="pane-title")
                yield DataTable(id="dish-table", cursor_type="row", zebra_stripes=True)
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
    ]

    def __init__(self) -> None:
        super().__init__()
        self.data = multitools.load()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"[b #a6e3a1]{self.data.headline}[/]", id="mt-headline")
        with TabbedContent(id="mt-tabs"):
            with TabPane("Types", id="tab-types"):
                yield DataTable(id="type-table", cursor_type="row", zebra_stripes=True)
                yield Static(id="type-detail")
            with TabPane("Weapons", id="tab-weapons"):
                yield DataTable(id="weapon-table", cursor_type="row", zebra_stripes=True)
                yield Static(id="weapon-detail")
            with TabPane("Getting one", id="tab-getting"):
                yield VerticalScroll(Static(self._getting_text(), id="mt-getting"))
            with TabPane("Tips", id="tab-tips"):
                yield VerticalScroll(Static(self._tips_text(), id="mt-tips"))
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


HELP_TEXT = """\
[b #89b4fa]NMS Items[/] - refining, cooking and chain lookup

[b]Recipe list[/]
  /              focus the search box (type to filter, Esc to leave)
  Tab / Shift+Tab   move between search box and table
  f              cycle domain: refining -> cooking -> all
  s              cycle sort: multiplier, time, rate, profit, name
  p              show only recipes that PRODUCE the highlighted item
  r              show only recipes that CONSUME it (reverse lookup)
  Enter          pivot: everything touching the highlighted output
  Backspace      clear the item filter, back to the full list
  d              show/hide the detail pane (it hides itself under 100 columns)

[b]Planning[/]
  c              chain plan for the highlighted output
                 (inside: t = source tier, n = quantity, k = allow cooking)
  n              the nanite ladder - every route to nanites, ranked
  e              cooking effects - what each dish does when you eat it
  m              multi-tools - types, weapons, how to get the good ones
                 (inside: [ and ] move between the four tabs)
  a              add the highlighted output to your inventory
  i              inventory screen

[b]Inventory[/]
  Type "[i]item name count[/]" and press Enter to add - "platinum 250".
  A negative count subtracts. e     edit count      d   drop the item
  x   clear everything             k   include cooking recipes

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

Press any key to close.
"""


class HelpScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape,q,question_mark,space,enter", "dismiss_help", "close")]

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="help-box"):
            yield Static(HELP_TEXT)

    def action_dismiss_help(self) -> None:
        self.dismiss(None)

    def on_key(self) -> None:
        self.dismiss(None)
