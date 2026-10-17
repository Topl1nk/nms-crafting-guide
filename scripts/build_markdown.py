"""The site as markdown, for crawlers and language models.

The page at nmsii.dlu.one is a JavaScript app behind hash routes, so anything
that reads HTML without running it sees an empty shell. This writes the same
content as plain files -- llms.txt (https://llmstxt.org), one markdown page per
section and per item, llms-full.txt, a sitemap and robots.txt.

Everything here renders the bundle `build_web.build()` returns -- the very dict
that becomes web/data.json -- and nothing else, so the markdown cannot say
something the page does not. The one computation redone is the chain tree walk,
`plan()` below, which is core.js's `plan()` line for line; tests/test_markdown.py
holds it to both graph.plan and the JS.

Run by scripts/build_web.py, after data.json (`mise run web:data`), or alone
with `mise run web:md`, which rebuilds the same bundle and prints the sizes.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from nms_items.portals import Address  # noqa: E402

SITE = "https://nmsii.dlu.one"
REPO = "https://github.com/rdlu/nms-items-interface"
HANDBOOK = "https://github.com/ApexFatality93/NMS-Handbook"

# The section pages, in the site's nav order, with the line llms.txt gives each.
SECTIONS = [
    ("guide", "How to read it",
     "What every column means, how gettable is scored, and how the chain planner chooses"),
    ("recipes", "Recipes",
     "Every refining and cooking recipe: inputs, output, multiplier, batch time, machine, rate, profit, gettable"),
    ("nanites", "Nanites",
     "Every route to nanites, ranked by nanites per hour per refiner, with where each input drops"),
    ("cooking", "Cooking",
     "Every cooked dish grouped by the buff eating it gives, with potency, value and recipe"),
    ("multitools", "Multi-tools",
     "The multi-tool types and weapons compared, where the free S-class ones come from, upgrade tips"),
    ("storage", "Storage",
     "Where every item belongs in the storage guide's ten-container layout, or whether to sell or junk it"),
    ("portals", "Portal addresses",
     "Portal glyphs and galactic coordinates, how to convert between them, and the saved places worth going"),
]

# Tried in this order for an item page's chain: the narrowest source set first,
# refining before cooking -- the site's own default is Tier 0, refining only.
CHAIN_TRIES = [(tier, key) for tier in range(3) for key in ("refine", "all")]


# -- formatting: core.js's helpers, so the numbers read the same --------------

def g(x: float) -> str:
    return f"{x:g}"


def fmt_int(n: float) -> str:
    # Math.round, not Python's banker's rounding.
    return f"{math.floor(n + 0.5):,}"


def fmt_signed(n: float) -> str:
    return ("+" if n >= 0 else "-") + fmt_int(abs(n))


def multiplier_label(r: dict) -> str:
    if r["loop"] > 1:
        return f"x{g(r['loop'])} loop"
    if r["ratio"] == int(r["ratio"]):
        return f"x{g(r['ratio'])}"
    return f"x{r['ratio']:.2f}"


def time_label(seconds: float) -> str:
    if not seconds:
        return "-"
    if seconds < 60:
        return f"{g(seconds)}s"
    if seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.0f}m" if minutes >= 10 else f"{minutes:.1f}m"
    return f"{seconds / 3600:.1f}h"


def fmt_time(seconds: float) -> str:
    if seconds < 60:
        return f"{g(seconds)}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


def machine_short(machine: str) -> str:
    return machine.split(" ")[0].replace("Nutrient", "Processor")


def qty_label(n: int, name: str) -> str:
    return f"{n} {name}" if n > 1 else name


def cell(text: object) -> str:
    """One table cell: a pipe or a newline would break the row."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def table(head: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(head) + " |", "|" + "|".join(" --- " for _ in head) + "|"]
    lines += ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


# -- the chain planner's tree walk (core.js plan) ------------------------------

def plan(recipes: list[dict], via: dict[str, int], sources: set[str],
         target: str, qty: int = 1) -> dict:
    """core.js `plan()` over the exported `via` map, returning the same shape."""
    raw: dict[str, int] = {}
    steps = 0

    def build(item_id: str, need: int, depth: int) -> dict:
        nonlocal steps
        if item_id in sources or item_id not in via or depth > 12:
            raw[item_id] = raw.get(item_id, 0) + need
            return {"id": item_id, "qty": need, "raw": item_id in sources, "children": []}
        recipe = recipes[via[item_id]]
        batches = math.ceil(need / recipe["out"][1])
        steps += 1
        step = {"id": item_id, "qty": need, "recipe": via[item_id], "batches": batches,
                "children": []}
        for ing, n in recipe["in"]:
            step["children"].append(build(ing, n * batches, depth + 1))
        return step

    def seconds(step: dict) -> float:
        own = recipes[step["recipe"]]["time"] * step["batches"] if "recipe" in step else 0.0
        return own + sum(seconds(child) for child in step["children"])

    root = build(target, qty, 0)
    return {"root": root, "raw": raw, "steps": steps, "seconds": seconds(root),
            "ok": "recipe" in root or root["raw"]}


# -- the renderer ---------------------------------------------------------------

class Markdown:
    """Every markdown file, from one bundle."""

    def __init__(self, bundle: dict, data_date: str = "", built: str = "") -> None:
        self.b = bundle
        self.items = bundle["items"]
        self.recipes = bundle["recipes"]
        self.data_date = data_date
        self.built = built or date.today().isoformat()
        self.produced: dict[str, list[int]] = {}
        self.consumed: dict[str, list[int]] = {}
        for index, r in enumerate(self.recipes):
            self.produced.setdefault(r["out"][0], []).append(index)
            for item_id, _ in r["in"]:
                self.consumed.setdefault(item_id, []).append(index)
        self.cooking_use = {c["effect"]: c["use"] for c in bundle["cooking"]}

    # -- lookups, as site/src/lib/data.js does them

    def name(self, item_id: str) -> str:
        item = self.items.get(item_id)
        return item["name"] if item else item_id

    def ease(self, item_id: str) -> dict:
        return self.b["ease"].get(item_id) or {
            "label": "loot (unknown)", "band": "hard", "score": 25,
            "describe": "", "where": "", "note": ""}

    def recipe_ease(self, r: dict) -> dict:
        # The hardest ingredient is what gates a recipe.
        return min((self.ease(i) for i, _ in r["in"]), key=lambda e: e["score"])

    def inputs(self, r: dict) -> str:
        return " + ".join(qty_label(n, self.name(i)) for i, n in r["in"])

    def output(self, r: dict) -> str:
        return qty_label(r["out"][1], self.name(r["out"][0]))

    def outcome(self, item_id: str) -> dict:
        return self.b["storage"]["outcomes"][self.items[item_id]["store"]]

    def recipe_row(self, r: dict) -> list[object]:
        return [self.output(r), r["out"][0], self.inputs(r), multiplier_label(r),
                time_label(r["time"]), machine_short(r["machine"]), fmt_int(r["rate"]),
                fmt_signed(r["profit"]), self.recipe_ease(r)["label"]]

    RECIPE_HEAD = ["Make", "ID", "From", "Mult", "Time", "Machine", "Rate/h", "Profit",
                   "Gettable"]

    def header(self, title: str, lede: str) -> str:
        return f"# {title}\n\n{lede}"

    def data_label(self) -> str:
        """"No Man's Sky Cosmos 7.06 (build 180836), extracted from the game
        files on 2026-10-17" -- or "" when the data does not say its version
        (no data/source.json, or the NMS-Handbook fallback)."""
        s = self.b.get("source") or {}
        if s.get("from") != "game" or not s.get("version"):
            return ""
        name = " ".join(x for x in ("No Man's Sky", s.get("game"), s["version"]) if x)
        build = f" (build {s['build']})" if s.get("build") else ""
        when = f" on {s['extracted']}" if s.get("extracted") else ""
        return f"{name}{build}, extracted from the game files{when}"

    def source_line(self) -> str:
        label = self.data_label()
        if label:
            return f"Generated {self.built}. Data: {label}. Interactive version: {SITE}/"
        when = f"recipe data as of {self.data_date}" if self.data_date else \
            "recipe data date not recorded"
        return (f"Generated {self.built} from the game's recipe tables via "
                f"[NMS-Handbook]({HANDBOOK}) ({when}). Interactive version: {SITE}/")

    # -- sections

    def guide(self) -> str:
        tiers = "\n".join(
            f"- **{t['name']}**: {', '.join(sorted(self.name(s) for s in t['sources']))}"
            for t in self.b["tiers"])
        return f"""{self.header("How to read NMSii", self.source_line())}

NMSii, the No Man's Sky Items Interface, is a terminal app with a web front
end. Both read the same data: every recipe, batch time and base value comes
from the game's own recipe table, not a wiki. These markdown pages are the
site's content as text; item IDs are the game's own, and every item has a page
at `md/items/<ID>.md`.

## Reading the columns

- **Mult**: units out per unit in. `x6 loop` means the recipe feeds itself:
  1 Chlorine + 2 Oxygen -> 6 Chlorine multiplies the seed six times, the only
  kind of recipe that grows a stack out of nothing.
- **Time**: one batch, from the game files. The in-game display is often wrong.
- **Machine**: Portable/Personal refiner (1 input), Medium (2), Large (3); the
  Nutrient Processor ("Processor") cooks.
- **Rate**: units of output per hour with one machine kept fed.
- **Profit**: the base-value difference across one batch, in units. It says
  nothing about nanites; those get their own page.
- **Gettable**: how reachable the hardest ingredient is. `T0/T1/T2 +n` means
  refinable from the Tier 0 / 1 / 2 source set, n refining steps away
  (`T0 raw` is something you pick up). `needs seed` means refinable, but
  wanting a material none of those tiers contain, typically a stellar metal you
  need two units of, ever. `loot (easy|medium|hard|unknown)` means no recipe
  makes it, with how much of a detour the guides make it sound.

## Source tiers

What the chain planner and the Gettable column count as free:

{tiers}

## The chain planner

It works backwards from a target item to a source set. The recipe table is an
AND-OR graph: an item can come from any one of several recipes, but a recipe
needs all of its inputs. The planner runs Knuth's generalisation of Dijkstra
over it: settle the cheapest item, then relax every recipe whose inputs are now
all settled. Cost is **refiner-seconds per unit of output**, with source items
free, so for each item it keeps the one recipe that ties a machine up for the
least time, not the one with the fewest steps.

The plan for N of an item walks those choices from the target down: batches =
ceil(need / units per batch), each ingredient needed batches x its count, until
it reaches a source item (gather it) or an item nothing in the set makes (find
it). Machine time is the sum of batch time x batches over every step, on one
refiner, unattended. By default it uses refining recipes only; allowing cooking
adds the Nutrient Processor's.

Each item page shows the cheapest chain for one unit, from the narrowest tier
that reaches it. On the site, `{SITE}/#/chain/<ID>` plans any quantity from any
tier.

## Nanites

Nanites (item `TECHFRAG`) are the second currency, and a units column misleads
about them. The nanite page ranks every route by nanites per hour on one
refiner kept fed; "per item" is nanites per unit of input consumed, and "value
spent" the base value of one batch's inputs.

## Cooking

Every cooked product grants a temporary buff and multiplies base value, so the
dish you eat is the dish you sell: cook the batch, eat one, sell the rest.
Potency is the game's own 0-1 quality rating for the buff; uplift is what one
batch adds over its ingredients' value.

## Storage

From the storage guide's section 10: ten numbered containers plus single-purpose
stores, one home per item, so the game's auto-routing ("send to storage") sorts
everything once one of each item is in its container. The rules match the
guide's named items first, then families by the game's subtitle and type; the
first match wins, and no match means 9 - Inbox. Some items are better sold,
junked or used at once.

## Inventory

The site's inventory page (kept in the browser only) lists what the items you
carry make right now, and the recipes you are one ingredient short of. It has
no markdown version: it depends on what you type in.

## Data

- `{SITE}/data.json`: everything above as one JSON bundle, described by
  `{SITE}/data.schema.json`.
- Source and issue tracker: {REPO}
"""

    def recipes_page(self) -> str:
        parts = [self.header("Recipes", self.source_line()),
                 f"{len(self.recipes)} recipes. Columns are explained in [the guide](guide.md); "
                 "each item has a page at `items/<ID>.md`. Sorted by output name."]
        for domain, title in (("refine", "Refining"), ("cook", "Cooking")):
            rows = sorted((r for r in self.recipes if r["domain"] == domain),
                          key=lambda r: (self.name(r["out"][0]).lower(), self.inputs(r)))
            parts.append(f"## {title} ({len(rows)})\n\n"
                         + table(self.RECIPE_HEAD, [self.recipe_row(r) for r in rows]))
        return "\n\n".join(parts) + "\n"

    def nanites_page(self) -> str:
        rows = []
        for n in self.b["nanites"]:
            r = self.recipes[n["recipe"]]
            e = self.recipe_ease(r)
            rows.append([self.inputs(r), r["out"][1], time_label(r["time"]), fmt_int(r["rate"]),
                         f"{n['per_input']:.2f}", fmt_int(n["units_cost"]), e["label"],
                         e["where"] or e["describe"]])
        return "\n\n".join([
            self.header("Nanites", self.source_line()),
            f"{len(rows)} ways to make nanites (`{self.b['nanite']}`), best nanites per hour "
            "first, one refiner kept fed.",
            table(["Refine", "Nanites", "Time", "Nanites/h", "Per item", "Value spent",
                   "Gettable", "Where it comes from"], rows),
        ]) + "\n"

    def cooking_page(self) -> str:
        groups = self.b["cooking"]
        total = sum(len(c["dishes"]) for c in groups)
        parts = [self.header("Cooking: what it does", self.source_line()),
                 f"{total} cooked dishes across {len(groups)} buffs. Pot = the game's own 0-1 "
                 "quality for the buff; Uplift = units gained over the ingredients, one batch; "
                 "Ways = how many recipes make the dish (one shown).",
                 table(["Boosts", "Dishes", "Good for"],
                       [[c["effect"], len(c["dishes"]), c["use"] or "-"] for c in groups])]
        for c in groups:
            rows = []
            for d in c["dishes"]:
                item, r = self.items[d["item"]], self.recipes[d["recipe"]]
                rows.append([item["name"], d["item"], f"{item['potency']:.2f}",
                             fmt_int(item["value"]), fmt_signed(r["profit"]), self.inputs(r),
                             time_label(r["time"]), d["ways"]])
            use = f"\n\nGood for: {c['use']}." if c["use"] else ""
            parts.append(f"## {c['effect']}{use}\n\n" + table(
                ["Dish", "ID", "Pot", "Value", "Uplift", "Cook from", "Time", "Ways"], rows))
        return "\n\n".join(parts) + "\n"

    def multitools_page(self) -> str:
        mt = self.b["multitools"]

        def procedure(p: dict) -> str:
            text = f"### {p['title']}\n\n" + "\n".join(
                f"{i}. {s}" for i, s in enumerate(p["steps"], 1))
            if p.get("note"):
                text += f"\n\n{p['note']}"
            if p.get("after"):
                text += "\n\n" + "\n".join(f"- {s}" for s in p["after"])
            return text

        return "\n\n".join([
            self.header("Multi-tools", self.source_line()),
            mt["_headline"],
            "## Types\n\n" + table(
                ["Type", "Damage", "Mining", "Scan", "Slots at spawn", "Notes"],
                [[t["type"], t["damage"], t["mining"], t["scan"], t["slots"], t["note"]]
                 for t in mt["types"]]),
            "## Weapons\n\n" + table(
                ["Weapon", "Like a", "Best hit", "Good", "Bad"],
                [[w["weapon"], w["kind"], w["best_hit"], w["pro"], w["con"]]
                 for w in mt["weapons"]]),
            "## Getting one\n\n" + "\n".join(
                f"- **{x['type']}** ({x['cost']}): {x['where']}. {x['how']}"
                for x in mt["getting"]),
            *(procedure(mt[k]) for k in ("sentinel_puzzle", "cabinet_trick", "hunting")),
            "## Tips\n\n" + "\n\n".join(f"### {r['title']}\n\n{r['body']}" for r in mt["rules"]),
            "## Where upgrades come from\n\n" + "\n".join(
                f"- **{u['kind']}**: {u['where']}. {u['note']}" for u in mt["upgrade_sources"]),
            "## Upgrade order\n\n" + "\n".join(
                f"{i}. {s}" for i, s in enumerate(mt["upgrade_order"], 1)),
            f"Portal addresses for these tools: [portals](portals.md). Source: {mt['_source']}",
        ]) + "\n"

    def storage_page(self) -> str:
        st = self.b["storage"]
        by_outcome: dict[int, list[str]] = {}
        for item_id, item in self.items.items():
            by_outcome.setdefault(item["store"], []).append(item_id)
        homes = [h for h in st["homes"] if h["key"] != "none"]
        count = {h["key"]: 0 for h in st["homes"]}
        for index, ids in by_outcome.items():
            count[st["outcomes"][index]["home"]] += len(ids)
        parts = [
            self.header("Where does it go?", self.source_line()),
            f"Every one of {len(self.items)} items gets a home, from the storage guide's "
            "section 10. Once one of an item is in its container, sending more to storage "
            "routes them there by itself. How the rules work: [the guide](guide.md#storage).",
            "## The layout\n\n" + table(
                ["Home", "Items", "What goes there"],
                [[h["label"], count[h["key"]], h["note"]] for h in homes]),
            "## Every item, by outcome",
        ]
        order = sorted(by_outcome, key=lambda i: (st["outcomes"][i]["label"],
                                                  st["outcomes"][i]["why"]))
        for index in order:
            o = st["outcomes"][index]
            ids = sorted(by_outcome[index], key=lambda i: self.name(i).lower())
            lines = "\n".join(
                f"- {self.items[i]['name']} (`{i}`)" + (f": {self.items[i]['sub']}"
                                                        if self.items[i]["sub"] else "")
                for i in ids)
            parts.append(f"### {o['verdict']}: {o['label']} ({len(ids)})\n\n"
                         f"{o['advice']} Why: {o['why']}.\n\n{lines}")
        return "\n\n".join(parts) + "\n"

    def portals_page(self) -> str:
        p = self.b["portals"]
        glyphs = table(["Digit", "Glyph"], [[f"{i:X}", n] for i, n in enumerate(p["glyph_names"])])
        rows = []
        for loc in p["locations"]:
            a = Address.parse(loc["code"])
            galaxy = loc.get("galaxy", 1)
            gname = p["galaxies"][galaxy - 1] if galaxy <= len(p["galaxies"]) else f"Galaxy {galaxy}"
            rows.append([loc["name"], loc.get("kind", "other"), loc.get("origin", "mine"),
                         a.portal_code, a.galactic, f"{galaxy}. {gname}", loc.get("detail", ""),
                         loc.get("where", ""), loc.get("source", ""), loc.get("added", "")])
        return "\n\n".join([
            self.header("Portal addresses", self.source_line()),
            "A **portal code** is twelve hex digits, one per glyph dialled at a portal: "
            "planet (1), system (3), Y (2), Z (3), X (3). A **galactic address** "
            "(`0824:007F:00F3:01AC`, what a signal booster shows) is X:Y:Z:system. The two "
            "frames disagree only about where zero is: portal coordinates count from the "
            "centre of the galaxy, galactic ones from a corner. The galactic form cannot carry "
            "the planet, so converting to a code needs it chosen (0 = the first planet).",
            "```\n"
            "galactic X = (portal X + 2047) % 4096      portal X = (galactic X + 2049) % 4096\n"
            "galactic Y = (portal Y +  127) %  256      portal Y = (galactic Y +  129) %  256\n"
            "galactic Z = (portal Z + 2047) % 4096      portal Z = (galactic Z + 2049) % 4096\n"
            "```",
            f"Portal `000000000000` is the galaxy centre, galactic `07FF:007F:07FF`. A system "
            f"index above 0x{p['max_system']:03X} is above what nmsportals treats as the maximum. "
            "Share links have the form `https://nmsportals.github.io/#<code>`.",
            "## The sixteen glyphs\n\n" + glyphs,
            "## Galaxies\n\n" + "\n".join(f"{i}. {n}" for i, n in enumerate(p["galaxies"], 1))
            + "\n\nThere are 256; past these the game numbers them.",
            f"## Saved places ({len(rows)})\n\n"
            f"Kinds: {', '.join(p['kinds'])}. Found: `mine` (stood there) or `shared` "
            f"(off a catalogue or a friend). New ones are shared as issues on {REPO}.\n\n"
            + table(["Name", "Kind", "Found", "Portal code", "Galactic", "Galaxy", "What is there",
                     "Finding it", "Source", "Added"], rows),
        ]) + "\n"

    # -- items

    def chain(self, item_id: str) -> tuple[dict, dict, str] | None:
        """The first tier/recipe set that makes or supplies the item."""
        for tier_index, key in CHAIN_TRIES:
            tier = self.b["tiers"][tier_index]
            p = plan(self.recipes, tier["via"][key], set(tier["sources"]), item_id)
            if p["ok"]:
                return p, tier, key
        return None

    def chain_md(self, item_id: str) -> str:
        found = self.chain(item_id)
        if not found:
            # Ease says why: loot and where it drops, or the seed it waits on.
            e = self.ease(item_id)
            return (f"Not reachable from any source tier, even with cooking. "
                    f"Gettable: {e['label']}, {e['describe']}.")
        p, tier, key = found
        recipes = "refining and cooking" if key == "all" else "refining only"
        if "recipe" not in p["root"]:
            return f"A source item in **{tier['name']}**: pick it up."

        def node(step: dict, depth: int) -> list[str]:
            pad = "  " * depth
            name = f"[{self.name(step['id'])}]({step['id']}.md)"
            if "recipe" not in step:
                tag = "gather" if step["raw"] else "find"
                return [f"{pad}- {step['qty']} x {name} ({tag})"]
            r = self.recipes[step["recipe"]]
            lines = [f"{pad}- {step['qty']} x {name}: {r['op']} x{step['batches']}, "
                     f"{fmt_time(r['time'] * step['batches'])}, {r['machine']}"]
            for child in step["children"]:
                lines += node(child, depth + 1)
            return lines

        gather = ", ".join(f"{n} {self.name(i)}" for i, n in
                           sorted(p["raw"].items(), key=lambda kv: -kv[1]))
        return "\n".join([
            f"1 x {self.name(item_id)} from **{tier['name']}**, {recipes}. "
            f"Gather: {gather}. {p['steps']} step(s), {fmt_time(p['seconds'])} of machine "
            "time (one refiner, unattended).",
            "",
            *node(p["root"], 0),
        ])

    def recipe_list(self, indexes: list[int], *, link_inputs: bool) -> str:
        rows = []
        for i in sorted(indexes, key=lambda i: (-max(self.recipes[i]["loop"],
                                                     self.recipes[i]["ratio"]),
                                                self.recipes[i]["time"])):
            r = self.recipes[i]
            make = (f"[{self.output(r)}]({r['out'][0]}.md)" if not link_inputs
                    else self.output(r))
            ins = (" + ".join(f"{qty_label(n, f'[{self.name(x)}]({x}.md)')}" for x, n in r["in"])
                   if link_inputs else self.inputs(r))
            rows.append([make, ins, r["op"], multiplier_label(r), time_label(r["time"]),
                         machine_short(r["machine"]), fmt_int(r["rate"]),
                         fmt_signed(r["profit"]), self.recipe_ease(r)["label"]])
        return table(["Make", "From", "Operation", "Mult", "Time", "Machine", "Rate/h",
                      "Profit", "Gettable"], rows)

    def item_page(self, item_id: str) -> str:
        item = self.items[item_id]
        o = self.outcome(item_id)
        facts = [
            ("ID", f"`{item_id}`"),
            ("What it is", item["sub"] or "-"),
            ("Category", item["cat"] or "-"),
            ("Base value", f"{fmt_int(item['value'])} units"),
            ("Storage", f"{o['verdict']}: {o['label']}. {o['advice']} Why: {o['why']}."),
        ]
        if "effect" in item:
            use = self.cooking_use.get(item["effect"])
            facts.append(("Eating it", f"{item['effect']} at potency {item['potency']:.2f}"
                          + (f" ({use})" if use else "")))
        if item_id in self.b["ease"]:
            e = self.ease(item_id)
            text = f"{e['label']}: {e['describe']}"
            if e["where"] and e["where"] != e["describe"]:
                text += f". Where: {e['where']}"
            if e["note"]:
                text += f". {e['note']}"
            facts.append(("Gettable", text))
        made = self.produced.get(item_id, [])
        used = self.consumed.get(item_id, [])
        site = (f"On the site: {SITE}/#/recipes?item={item_id} · chain planner "
                f"{SITE}/#/chain/{item_id}" if made or used else
                f"On the site: {SITE}/#/storage?q={quote(item['name'])}")
        parts = [f"# {item['name']}", "\n".join(f"- **{k}**: {v}" for k, v in facts), site]
        if made or used:
            parts.append("## Cheapest chain\n\n" + self.chain_md(item_id))
        parts.append(f"## Made by ({len(made)})\n\n"
                     + (self.recipe_list(made, link_inputs=True) if made
                        else "No recipe makes it."))
        parts.append(f"## Used in ({len(used)})\n\n"
                     + (self.recipe_list(used, link_inputs=False) if used
                        else "No recipe uses it."))
        parts.append("[All items](index.md) · [Recipes](../recipes.md) · [Guide](../guide.md)")
        return "\n\n".join(parts) + "\n"

    def items_index(self, prefix: str = "") -> str:
        by_cat: dict[str, list[str]] = {}
        for item_id, item in self.items.items():
            by_cat.setdefault(item["cat"] or "Uncategorised", []).append(item_id)
        parts = [self.header("All items", self.source_line()),
                 f"{len(self.items)} items by category, each linking to its page: base value, "
                 "storage, recipes that make and use it, and the cheapest chain."]
        for cat in sorted(by_cat):
            ids = sorted(by_cat[cat], key=lambda i: self.name(i).lower())
            lines = "\n".join(
                f"- [{self.items[i]['name']}]({prefix}{i}.md) `{i}`"
                + (f": {self.items[i]['sub']}" if self.items[i]["sub"] else "")
                + f", {fmt_int(self.items[i]['value'])}u" for i in ids)
            parts.append(f"## {cat} ({len(ids)})\n\n{lines}")
        return "\n\n".join(parts) + "\n"

    # -- the top-level files

    def llms_txt(self) -> str:
        n_refine = sum(r["domain"] == "refine" for r in self.recipes)
        sections = "\n".join(f"- [{title}]({SITE}/md/{key}.md): {line}"
                             for key, title, line in SECTIONS)
        label = self.data_label()
        if label:
            provenance = (
                f"Data: {label}. NMSii unpacks the game's recipe, product, substance and "
                "language tables itself and normalises them; earlier builds read the same "
                f"tables via [NMS-Handbook]({HANDBOOK}), still the fallback source.")
        else:
            when = (f"The recipe data was last regenerated on {self.data_date}"
                    if self.data_date
                    else "The recipe data's date was not recorded in this build")
            provenance = (
                f"The numbers come from the game files: [NMS-Handbook]({HANDBOOK}) parses "
                "the game's NMS_REALITY_GCRECIPETABLE.MXML and its product and substance "
                f"tables into JSON, and NMSii normalises them. {when}; the game version is "
                "not recorded upstream, so read it as the patch current on that date.")
        return f"""# NMSii — No Man's Sky Items Interface

> Recipes, nanites, cooking buffs, multi-tools, storage homes and portal addresses for No Man's Sky, computed from the game's own recipe tables: {len(self.items)} items, {n_refine} refining and {len(self.recipes) - n_refine} cooking recipes, the cheapest chain to make each item from what you can pick up, and every route to nanites ranked by nanites per hour.

{provenance} Where loot drops, the storage layout and the multi-tool notes are hand-written from community guides.

These files were generated on {self.built} by the export that builds the data of the interactive site at {SITE}/ (a JavaScript app), so they say what it shows. No Man's Sky and its data belong to Hello Games.

## Sections

{sections}

## Items

- [All items]({SITE}/md/items/index.md): every item by category, linking to one page per item ({SITE}/md/items/<ID>.md) with its base value, storage home, buff, every recipe making and using it, and the cheapest chain from Tier 0

## Data

- [data.json]({SITE}/data.json): the whole site's data as one JSON bundle
- [data.schema.json]({SITE}/data.schema.json): JSON Schema for data.json

## Optional

- [llms-full.txt]({SITE}/llms-full.txt): every section page and the item index in one file (the per-item pages are left out; they repeat the recipe tables)
- [Cheat sheet, print]({SITE}/pdf/nms-cheatsheet.pdf): the recipes worth memorising, landscape A4 PDF
- [Cheat sheet, screen]({SITE}/pdf/nms-cheatsheet-dark.pdf): the same, dark
- [Source code]({REPO}): the terminal app, the export and the data pipeline (GPL-3.0)
"""

    def llms_full(self, pages: dict[str, str]) -> str:
        # Every section and the item index, not the 1,400-odd item pages: they
        # are the recipe table again, cut per item, and would be most of the file.
        order = [f"md/{key}.md" for key, _, _ in SECTIONS] + ["md/items/index.md"]
        body = "\n\n---\n\n".join(
            f"<!-- {SITE}/{path} -->\n\n{pages[path]}" for path in order)
        return pages["llms.txt"] + "\n---\n\n" + body

    def pages(self) -> dict[str, str]:
        """Every generated text file, keyed by its path under web/."""
        out = {
            "md/guide.md": self.guide(),
            "md/recipes.md": self.recipes_page(),
            "md/nanites.md": self.nanites_page(),
            "md/cooking.md": self.cooking_page(),
            "md/multitools.md": self.multitools_page(),
            "md/storage.md": self.storage_page(),
            "md/portals.md": self.portals_page(),
            "md/items/index.md": self.items_index(),
        }
        for item_id in self.items:
            out[f"md/items/{item_id}.md"] = self.item_page(item_id)
        out["llms.txt"] = self.llms_txt()
        out["llms-full.txt"] = self.llms_full(out)
        out["sitemap.xml"] = sitemap(["", "llms.txt", "llms-full.txt",
                                      *sorted(p for p in out if p.startswith("md/"))],
                                     self.data_date)
        out["robots.txt"] = f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n"
        return out


def sitemap(paths: list[str], lastmod: str = "") -> str:
    mod = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
    urls = "\n".join(f"  <url><loc>{xml_escape(f'{SITE}/{p}')}</loc>{mod}</url>" for p in paths)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{urls}\n</urlset>\n")


def data_date(root: Path) -> str:
    """When data/ last changed, from git; "" when git cannot say.

    A shallow clone knows only its tip, whose date is the push, not the data --
    pages.yml checks out the full history for this.
    """
    try:
        shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=root,
                                 capture_output=True, text=True, check=True).stdout.strip()
        if shallow == "true":
            return ""
        return subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", "data/recipes.json", "data/items.json"],
            cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def write(bundle: dict, web: Path, root: Path) -> dict[str, str]:
    pages = Markdown(bundle, data_date(root)).pages()
    # Generated wholesale: an item gone from the data must not leave its page.
    shutil.rmtree(web / "md", ignore_errors=True)
    for path, text in pages.items():
        dest = web / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
    md = sum(len(t.encode()) for p, t in pages.items() if p.startswith("md/"))
    items = sum(p.startswith("md/items/") and p != "md/items/index.md" for p in pages)
    full = len(pages["llms-full.txt"].encode())
    print(f"wrote web/md/ ({items} item pages, {md / 1024:.0f} KiB), "
          f"web/llms.txt, web/llms-full.txt ({full / 1024:.0f} KiB), sitemap.xml, robots.txt")
    return pages


def main() -> None:
    # Imported here so that build_web can import this module without a cycle.
    import build_web
    from nms_items.model import Book

    pages = write(build_web.build(Book()), build_web.WEB, ROOT)
    for path in ("llms.txt", "llms-full.txt", "sitemap.xml", "robots.txt",
                 *(f"md/{key}.md" for key, _, _ in SECTIONS), "md/items/index.md"):
        print(f"  {path:<22} {len(pages[path].encode()) / 1024:8.1f} KiB")


if __name__ == "__main__":
    main()
