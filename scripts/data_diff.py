"""Report what changed in data/items.json + recipes.json against a git commit.

After `mise run extract` (or any data rebuild) this answers "what did the
patch actually change?": recipes added, removed or retuned, items added or
removed, and changed values, names and food stats. Markdown, so it can go
straight into a PR or docs/.

A recipe is identified by its domain, output and the *set* of input ids;
amounts, batch time and operation name are what can change under that
identity. Two recipes that share an identity (the same inputs in different
amounts) are paired up in order.

    uv run python scripts/data_diff.py [--base REF] [--out FILE]

--base defaults to HEAD, so it compares the working tree's data/ with the
last commit. Run via `mise run extract-diff`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# Item fields worth a line each when they change. Description edits are only
# counted: they are mostly lore rewording and would drown the table.
ITEM_FIELDS = ["name", "kind", "type", "category", "rarity", "value",
               "subtitle", "effect", "potency", "edible"]


def at_ref(ref: str, name: str) -> object:
    out = subprocess.run(["git", "show", f"{ref}:data/{name}"], cwd=ROOT,
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"cannot read data/{name} at {ref}: {out.stderr.strip()}")
    return json.loads(out.stdout)


def identity(recipe: dict) -> tuple:
    return (recipe["domain"], recipe["output"]["id"],
            tuple(sorted(i["id"] for i in recipe["inputs"])))


def detail(recipe: dict) -> tuple:
    return (recipe["output"]["n"],
            tuple(sorted((i["id"], i["n"]) for i in recipe["inputs"])),
            recipe["time"], recipe["operation"])


def group(recipes: list[dict]) -> dict[tuple, list[dict]]:
    out: dict[tuple, list[dict]] = {}
    for recipe in recipes:
        out.setdefault(identity(recipe), []).append(recipe)
    for rows in out.values():
        rows.sort(key=detail)
    return out


def fmt_time(seconds: float) -> str:
    return f"{seconds:g}s"


class Names:
    def __init__(self, *books: dict) -> None:
        self.books = books

    def __call__(self, item_id: str) -> str:
        for book in self.books:
            if item_id in book:
                return book[item_id]["name"]
        return item_id

    def recipe(self, r: dict) -> str:
        ins = " + ".join(f"{i['n']} {self(i['id'])}" for i in r["inputs"])
        return f"{ins} → {r['output']['n']} {self(r['output']['id'])}"


def diff(old_items: dict, new_items: dict, old_recipes: list, new_recipes: list) -> str:
    name = Names(new_items, old_items)
    lines: list[str] = []
    add = lines.append

    # -- recipes ---------------------------------------------------------------
    old_g, new_g = group(old_recipes), group(new_recipes)
    added, removed, changed = [], [], []
    for key in sorted(set(old_g) | set(new_g)):
        olds, news = old_g.get(key, []), new_g.get(key, [])
        unmatched_new = [r for r in news if detail(r) not in {detail(o) for o in olds}]
        unmatched_old = [r for r in olds if detail(r) not in {detail(n) for n in news}]
        for o, n in zip(unmatched_old, unmatched_new):
            changed.append((o, n))
        removed += unmatched_old[len(unmatched_new):]
        added += unmatched_new[len(unmatched_old):]

    def counts(recipes: list) -> str:
        r = sum(1 for x in recipes if x["domain"] == "refine")
        return f"{r} refining, {len(recipes) - r} cooking"

    add("## Summary\n")
    add(f"- Recipes: {len(old_recipes)} → {len(new_recipes)} "
        f"({counts(old_recipes)} → {counts(new_recipes)})")
    add(f"- Recipes added {len(added)}, removed {len(removed)}, changed {len(changed)}")

    item_added = sorted(set(new_items) - set(old_items))
    item_removed = sorted(set(old_items) - set(new_items))
    item_changed: list[tuple[str, str, object, object]] = []
    described = 0
    for key in sorted(set(old_items) & set(new_items)):
        o, n = old_items[key], new_items[key]
        for field in ITEM_FIELDS:
            if o.get(field) != n.get(field):
                item_changed.append((key, field, o.get(field), n.get(field)))
        if o.get("description") != n.get("description"):
            described += 1
    add(f"- Items: {len(old_items)} → {len(new_items)} (added {len(item_added)}, "
        f"removed {len(item_removed)}, {len(item_changed)} field changes, "
        f"{described} descriptions reworded)")
    add("")

    for domain, title in (("refine", "Refining"), ("cook", "Cooking")):
        a = [r for r in added if r["domain"] == domain]
        d = [r for r in removed if r["domain"] == domain]
        c = [(o, n) for o, n in changed if o["domain"] == domain]
        if not (a or d or c):
            add(f"## {title}: no changes\n")
            continue
        add(f"## {title}\n")
        if a:
            add(f"### Added ({len(a)})\n")
            add("| Recipe | Time | Operation |\n|---|---|---|")
            for r in a:
                add(f"| {name.recipe(r)} | {fmt_time(r['time'])} | {r['operation']} |")
            add("")
        if d:
            add(f"### Removed ({len(d)})\n")
            add("| Recipe | Time | Operation |\n|---|---|---|")
            for r in d:
                add(f"| {name.recipe(r)} | {fmt_time(r['time'])} | {r['operation']} |")
            add("")
        if c:
            add(f"### Changed ({len(c)})\n")
            add("| Before | After | Time | Operation |\n|---|---|---|---|")
            for o, n in c:
                t = (fmt_time(n["time"]) if o["time"] == n["time"]
                     else f"{fmt_time(o['time'])} → {fmt_time(n['time'])}")
                op = (n["operation"] if o["operation"] == n["operation"]
                      else f"{o['operation']} → {n['operation']}")
                add(f"| {name.recipe(o)} | {name.recipe(n)} | {t} | {op} |")
            add("")

    # -- items -----------------------------------------------------------------
    add("## Items\n")
    if item_added:
        add(f"### Added ({len(item_added)})\n")
        add("| Id | Name | Type | Subtitle | Value |\n|---|---|---|---|---|")
        for key in item_added:
            i = new_items[key]
            add(f"| `{key}` | {i['name']} | {i.get('type', '')} | {i.get('subtitle', '')} "
                f"| {i.get('value', 0):,} |")
        add("")
    if item_removed:
        add(f"### Removed ({len(item_removed)})\n")
        add("| Id | Name | Type |\n|---|---|---|")
        for key in item_removed:
            i = old_items[key]
            add(f"| `{key}` | {i['name']} | {i.get('type', '')} |")
        add("")
    if item_changed:
        add(f"### Changed fields ({len(item_changed)})\n")
        add("| Item | Field | Before | After |\n|---|---|---|---|")
        for key, field, o, n in item_changed:
            add(f"| {name(key)} (`{key}`) | {field} | {o!r} | {n!r} |")
        add("")
    if not (item_added or item_removed or item_changed):
        add("No item changes.\n")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diff data/ against a git commit")
    parser.add_argument("--base", default="HEAD", help="git ref to compare with (default HEAD)")
    parser.add_argument("--out", type=Path, help="write the report here instead of stdout")
    args = parser.parse_args(argv)

    report = diff(
        at_ref(args.base, "items.json"), json.loads((DATA / "items.json").read_text()),
        at_ref(args.base, "recipes.json"), json.loads((DATA / "recipes.json").read_text()),
    )
    if args.out:
        args.out.write_text(report + "\n")
        print(f"wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
