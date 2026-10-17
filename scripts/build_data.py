"""Normalise the recipe tables into data/items.json and data/recipes.json.

The tables arrive in the NMS-Handbook JSON shape from one of two places:

  --source game      .cache/game/json/, written by extract_game.py from the
                     installed game (the default)
  --source handbook  .cache/handbook/, downloaded by fetch_source.py

Both are the same game tables in the same shape, so this stays the one place
recipes get normalised whichever fed it. The source's provenance is copied
into data/source.json, so the committed data says which game build it is.

Upstream keys every recipe table by its *output* product and nests the recipes
inside, which is fine for a wiki page and useless for a lookup tool: there is no
flat recipe list, no reverse index, and ingredient metadata is duplicated into
every single recipe. This flattens all of that into two files:

  items.json    id -> {name, kind, category, rarity, value, ...}
  recipes.json  a flat list of {domain, output, inputs, time, machine, ...}

Everything the TUI needs is in those two files, so the app never touches the
upstream JSON (10 MB) or the network.

Run via `mise run data:build` after `mise run extract:convert` (or just
`mise run extract:all`), or `mise run data:build-handbook` after `mise run data:fetch`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# source -> (directory, the task that fills it)
SOURCES = {
    "game": (ROOT / ".cache" / "game" / "json", "mise run extract:all"),
    "handbook": (ROOT / ".cache" / "handbook", "mise run data:fetch"),
}
CACHE = SOURCES["game"][0]
DATA = ROOT / "data"

# Refiners are distinguished only by how many input slots they have, and the
# game files don't record which machine a recipe belongs to -- the ingredient
# count *is* the requirement. Cooking always uses the Nutrient Processor.
MACHINE_BY_INPUTS = {
    1: "Portable / Personal Refiner",
    2: "Medium Refiner",
    3: "Large Refiner",
}


# A handful of rows carry a placeholder rather than a real stat name.
_NO_EFFECT = {"", "None", "NONE"}


def _effect(text: str | None) -> str:
    return "" if (text or "") in _NO_EFFECT else str(text)


def _num(value: str | int | float | None, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def load(name: str) -> dict:
    path = CACHE / name
    if not path.exists():
        hint = next((task for d, task in SOURCES.values() if d == CACHE), "mise run extract:all")
        sys.exit(f"missing {path}\nRun `{hint}` first.")
    return json.loads(path.read_text())


def build_items(substances: dict, products: dict) -> dict:
    """One id -> item map across both upstream tables.

    Substances win on collision: the refiner deals in raw elements, and where an
    id exists in both tables the substance row is the one the recipes mean.
    """
    items: dict[str, dict] = {}

    for key, row in products.items():
        items[key] = {
            "name": row.get("NameLower_Text") or row.get("Name_Text", key),
            "kind": "product",
            "subtitle": row.get("Subtitle_Text", ""),
            "category": row.get("Category", ""),
            "rarity": row.get("Rarity", ""),
            "value": int(_num(row.get("BaseValue"))),
            "type": row.get("Type", ""),
            "cooking_ingredient": row.get("CookingIngredient") == "True",
            "description": row.get("Description_Text", ""),
            # Eating a cooked product grants a temporary buff. The files name
            # the stat it boosts and carry a 0-1 quality for it, which is the
            # only measure of strength they record.
            "effect": _effect(row.get("FoodBonusStatTypeText")),
            "effect_id": row.get("FoodBonusStatType", ""),
            "potency": round(_num(row.get("CookingValue")), 2),
            "edible": row.get("Consumable") == "true",
        }

    for key, row in substances.items():
        items[key] = {
            "name": row.get("NameLower_Text") or row.get("Name_Text", key),
            "kind": "substance",
            "type": "Substance",
            "subtitle": row.get("Subtitle_Text", ""),
            "category": row.get("Category", ""),
            "rarity": row.get("Rarity", ""),
            "value": int(_num(row.get("BaseValue"))),
            "cooking_ingredient": row.get("CookingIngredient") == "True",
            "description": row.get("Description_Text", ""),
        }

    return items


# Product types that never occupy a cargo slot: base parts, ship and suit
# cosmetics, emotes.
NOT_CARRIED = {"BuildingPart", "CustomisationPart", "Emote"}


def carriable(item: dict) -> bool:
    """True for an item you could find in your exosuit.

    Besides the types above, this drops the rows that only exist to drive the
    UI: standing changes and settlement stats ("Reward Item"), and templates
    whose name is filled in at runtime (%NAME%).
    """
    name = item["name"]
    return (
        item.get("type") not in NOT_CARRIED
        and item.get("subtitle") != "Reward Item"
        and bool(name.strip())
        and "%" not in name
    )


def build_recipes(table: dict, domain: str, items: dict) -> list[dict]:
    recipes: list[dict] = []

    for out_id, row in table.items():
        # Ensure the output itself is a known item even if it appears in neither
        # the substance nor the product table (a few cooking outputs do not).
        if out_id not in items:
            items[out_id] = {
                "name": row.get("NameLower_Text") or row.get("Name_Text", out_id),
                "kind": "product",
                "subtitle": row.get("Subtitle_Text", ""),
                "category": "",
                "rarity": "",
                "value": 0,
                "cooking_ingredient": False,
                "description": row.get("Description_Text", ""),
            }

        for recipe in row.get("Recipes", []):
            ingredients = recipe.get("Ingredients", [])
            if not ingredients:
                continue

            inputs = [
                {"id": ing["Id"], "n": int(_num(ing.get("Amount"), 1))}
                for ing in ingredients
            ]
            out_n = int(_num(recipe.get("Amount"), 1))
            time = _num(recipe.get("TimeToMake"))

            in_units = sum(i["n"] for i in inputs)
            seed = sum(i["n"] for i in inputs if i["id"] == out_id)
            in_value = sum(items.get(i["id"], {}).get("value", 0) * i["n"] for i in inputs)
            out_value = items[out_id]["value"] * out_n

            recipes.append(
                {
                    "domain": domain,
                    # Upstream prefixes these with "Requested Operation: " /
                    # "Processor Setting: "; RecipeName is the same string clean.
                    "operation": recipe.get("RecipeName", ""),
                    "output": {"id": out_id, "n": out_n},
                    "inputs": inputs,
                    "time": time,
                    "machine": (
                        "Nutrient Processor"
                        if domain == "cook"
                        else MACHINE_BY_INPUTS.get(len(inputs), "Large Refiner")
                    ),
                    # Units out per unit in. >1 means the refiner hands back
                    # more than it ate.
                    "ratio": round(out_n / in_units, 4) if in_units else 0.0,
                    # The guides' "x6 multiplier": for a self-loop recipe
                    # (1 Chlorine + 2 Oxygen -> 6 Chlorine) what matters is the
                    # growth of the *seed*, not of total inputs. 0 when the
                    # output is not also an input.
                    "loop": round(out_n / seed, 4) if seed else 0.0,
                    "profit": out_value - in_value,
                    # Units per hour, one machine, assuming it is kept fed.
                    "rate": round(out_n * 3600 / time, 2) if time else 0.0,
                }
            )

    return recipes


def main(argv: list[str] | None = None) -> int:
    global CACHE
    parser = argparse.ArgumentParser(description="Normalise the recipe tables into data/")
    parser.add_argument("--source", choices=sorted(SOURCES), default="game",
                        help="where the tables come from (default: game)")
    args = parser.parse_args(argv)
    CACHE = SOURCES[args.source][0]

    substances = load("Substance_Table.json")
    products = load("Product_Table.json")

    items = build_items(substances, products)
    recipes = build_recipes(load("Refining_Table.json"), "refine", items)
    recipes += build_recipes(load("Cooking_Table.json"), "cook", items)

    # Keep what a recipe touches, plus anything that can sit in an inventory
    # slot: the storage guide has to answer for a Gravitino Ball as much as for
    # Chlorine. What goes is the build menu, the cosmetics and the rows that
    # are not items at all.
    used: set[str] = set()
    for recipe in recipes:
        used.add(recipe["output"]["id"])
        used.update(i["id"] for i in recipe["inputs"])
    items = {k: v for k, v in items.items() if k in used or carriable(v)}

    DATA.mkdir(exist_ok=True)
    (DATA / "items.json").write_text(json.dumps(items, indent=1, sort_keys=True))
    (DATA / "recipes.json").write_text(json.dumps(recipes, indent=1))

    refine = sum(1 for r in recipes if r["domain"] == "refine")
    # A separate file, not a key inside items.json: that file is an id -> item
    # map, and every reader would have to learn to skip a "_source" row.
    source = load("_source.json")
    source["_source"] = ("Where data/items.json and data/recipes.json came from. "
                         "Written by scripts/build_data.py; do not edit by hand.")
    source["counts"] = {"items": len(items), "refine": refine, "cook": len(recipes) - refine}
    (DATA / "source.json").write_text(json.dumps(source, indent=1, sort_keys=True) + "\n")

    print(f"items:   {len(items)}")
    print(f"recipes: {len(recipes)}  ({refine} refining, {len(recipes) - refine} cooking)")
    print(f"source:  {source.get('summary', args.source)}")
    print(f"written to {DATA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
