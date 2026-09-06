"""Recipe data: loading, indexing and search.

`Book` is the whole read-only side of the app. It loads the two generated files
from data/, builds the forward and reverse indexes, and answers the questions
the UI asks: search, what makes X, what X is used in.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path


def find_data_dir() -> Path:
    """Locate data/, whether running from the repo or an installed copy.

    $NMS_ITEMS_DATA wins; otherwise walk up from this file looking for a data/
    directory with recipes.json in it. Walking up is what makes an editable
    install and a plain `python -m nms_items` from the checkout both work.
    """
    override = os.environ.get("NMS_ITEMS_DATA")
    if override:
        return Path(override)
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data"
        if (candidate / "recipes.json").is_file():
            return candidate
    return here.parent.parent.parent / "data"


DATA_DIR = find_data_dir()

# The five things the guides say you can pick up on the surface of essentially
# any planet -- the default starting set for chain planning.
TIER0 = ["OXYGEN", "FUEL1", "LAND1", "LAUNCHSUB", "CATALYST1"]
# Add a few minutes of shooting asteroids in any system.
ASTEROIDS = ["ASTEROID1", "ASTEROID2", "ASTEROID3", "ROCKETSUB"]
# Add one atmosphere harvester.
NITROGEN = ["GAS3"]

SOURCE_SETS: dict[str, list[str]] = {
    "Tier 0 - any planet": TIER0,
    "Tier 1 - + asteroids": TIER0 + ASTEROIDS,
    "Tier 2 - + harvester": TIER0 + ASTEROIDS + NITROGEN,
}


@dataclass(frozen=True, slots=True)
class Item:
    id: str
    name: str
    kind: str
    subtitle: str
    category: str
    rarity: str
    value: int
    description: str = ""

    @property
    def search_key(self) -> str:
        return f"{self.name} {self.category} {self.subtitle}".lower()


@dataclass(frozen=True, slots=True)
class Ingredient:
    id: str
    n: int


@dataclass(slots=True)
class Recipe:
    index: int
    domain: str  # "refine" | "cook"
    operation: str
    output: Ingredient
    inputs: tuple[Ingredient, ...]
    time: float
    machine: str
    ratio: float
    loop: float
    profit: int
    rate: float
    # Filled in by Book so a recipe can render itself without a lookup table.
    names: dict[str, str] = field(default_factory=dict, repr=False)

    @property
    def output_name(self) -> str:
        return self.names.get(self.output.id, self.output.id)

    @property
    def inputs_label(self) -> str:
        return " + ".join(
            f"{ing.n} {self.names.get(ing.id, ing.id)}" if ing.n > 1
            else self.names.get(ing.id, ing.id)
            for ing in self.inputs
        )

    @property
    def output_label(self) -> str:
        return f"{self.output.n} {self.output_name}" if self.output.n > 1 else self.output_name

    @property
    def multiplier_label(self) -> str:
        """The headline number: seed growth for loops, else units out per unit in."""
        if self.loop > 1:
            return f"x{self.loop:g} loop"
        if self.ratio == int(self.ratio):
            return f"x{self.ratio:g}"
        return f"x{self.ratio:.2f}"

    @property
    def time_label(self) -> str:
        if not self.time:
            return "-"
        if self.time < 60:
            return f"{self.time:g}s"
        if self.time < 3600:
            minutes = self.time / 60
            return f"{minutes:.0f}m" if minutes >= 10 else f"{minutes:.1f}m"
        return f"{self.time / 3600:.1f}h"

    @property
    def machine_short(self) -> str:
        """Column-width version of `machine`; the pane shows the full name."""
        return self.machine.split(" ")[0].replace("Nutrient", "Processor")

    @property
    def search_key(self) -> str:
        return f"{self.output_name} {self.inputs_label} {self.operation}".lower()


class Book:
    """The recipe book: items, recipes and the indexes over them."""

    def __init__(self, data_dir: Path | None = None) -> None:
        data_dir = data_dir or DATA_DIR
        items_path = data_dir / "items.json"
        recipes_path = data_dir / "recipes.json"
        if not items_path.exists() or not recipes_path.exists():
            raise FileNotFoundError(
                f"No recipe data in {data_dir}.\n"
                "Run:  mise run fetch  &&  mise run build-data"
            )

        raw_items: dict = json.loads(items_path.read_text())
        self.items: dict[str, Item] = {
            key: Item(
                id=key,
                name=row["name"],
                kind=row["kind"],
                subtitle=row.get("subtitle", ""),
                category=row.get("category", ""),
                rarity=row.get("rarity", ""),
                value=row.get("value", 0),
                description=row.get("description", ""),
            )
            for key, row in raw_items.items()
        }
        names = {key: item.name for key, item in self.items.items()}

        self.recipes: list[Recipe] = []
        for i, row in enumerate(json.loads(recipes_path.read_text())):
            self.recipes.append(
                Recipe(
                    index=i,
                    domain=row["domain"],
                    operation=row["operation"],
                    output=Ingredient(row["output"]["id"], row["output"]["n"]),
                    inputs=tuple(Ingredient(x["id"], x["n"]) for x in row["inputs"]),
                    time=row["time"],
                    machine=row["machine"],
                    ratio=row["ratio"],
                    loop=row.get("loop", 0.0),
                    profit=row["profit"],
                    rate=row["rate"],
                    names=names,
                )
            )

        # Forward index: what produces this item. Reverse: what consumes it.
        self.produced_by: dict[str, list[Recipe]] = {}
        self.consumed_by: dict[str, list[Recipe]] = {}
        for recipe in self.recipes:
            self.produced_by.setdefault(recipe.output.id, []).append(recipe)
            for ing in recipe.inputs:
                self.consumed_by.setdefault(ing.id, []).append(recipe)

    # -- lookups ---------------------------------------------------------

    def name(self, item_id: str) -> str:
        item = self.items.get(item_id)
        return item.name if item else item_id

    def by_name(self, text: str) -> Item | None:
        """Exact (case-insensitive) name lookup, for typed inventory entry."""
        return self._name_index.get(text.strip().lower())

    @cached_property
    def _name_index(self) -> dict[str, Item]:
        return {item.name.lower(): item for item in self.items.values()}

    def search_items(self, query: str, limit: int = 30) -> list[Item]:
        query = query.strip().lower()
        if not query:
            return []
        starts = [i for i in self.items.values() if i.name.lower().startswith(query)]
        contains = [
            i for i in self.items.values()
            if query in i.name.lower() and not i.name.lower().startswith(query)
        ]
        return (starts + contains)[:limit]

    def search(
        self,
        query: str = "",
        domain: str | None = None,
        item_id: str | None = None,
        role: str = "any",
    ) -> list[Recipe]:
        """Filter the recipe list.

        query   substring over output, inputs and operation name
        domain  "refine" | "cook" | None for both
        item_id restrict to recipes touching this item
        role    with item_id: "output", "input" or "any"
        """
        if item_id:
            if role == "output":
                pool = self.produced_by.get(item_id, [])
            elif role == "input":
                pool = self.consumed_by.get(item_id, [])
            else:
                seen: dict[int, Recipe] = {}
                for recipe in self.produced_by.get(item_id, []):
                    seen[recipe.index] = recipe
                for recipe in self.consumed_by.get(item_id, []):
                    seen[recipe.index] = recipe
                pool = list(seen.values())
        else:
            pool = self.recipes

        terms = query.lower().split()
        result = []
        for recipe in pool:
            if domain and recipe.domain != domain:
                continue
            if terms:
                key = recipe.search_key
                if not all(term in key for term in terms):
                    continue
            result.append(recipe)
        return result
