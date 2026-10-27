"""NMSii as an MCP server: the computed answers, for AI assistants.

An assistant asked "how do I make Antimatter" will otherwise answer from
whatever wiki text it half-remembers, from some older patch. This serves the
answers the TUI and the site give -- the same Book, graph, ease, storage, food
and portal code, nothing recomputed here -- over the Model Context Protocol,
on stdio: `nms mcp`.

Read-only on purpose. The inventory and the saved addresses are the two
things the TUI writes; here an inventory is an argument, not state, and the
saved addresses are only listed.

The tool functions are plain functions over plain arguments returning
JSON-friendly dicts, so the tests call them directly; `build_server()` wraps
them for the protocol.
"""

from __future__ import annotations

import difflib
import re
import sys
from functools import cache
from typing import Any, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError
from mcp.types import ToolAnnotations

from . import food, graph
from .ease import TIER_ORDER, EaseIndex
from .model import DATA_DIR, SOURCE_SETS, Book, Item, Recipe, data_source
from .portals import KINDS, ORIGINS, AddressError, Address, LocationBook, resolve_choice
from .storage import StorageGuide

SITE = "https://nmsii.dlu.one"

Domain = Literal["refine", "cook", "all"]
Sort = Literal["mult", "time", "rate", "profit", "ease", "name"]
Tier = Literal[0, 1, 2]


# -- shared state ----------------------------------------------------------------


class Data:
    """Everything the tools read, loaded once per process.

    The locations file is re-read per call instead: the TUI writes it while
    this server may be running, and a stale list would be the wrong answer.
    """

    def __init__(self, book: Book | None = None) -> None:
        self.book = book or Book()
        self.ease = EaseIndex(self.book)
        self.storage = StorageGuide.load()


@cache
def data() -> Data:
    return Data()


# -- turning objects into readable dicts -------------------------------------------

# The game's own text markup: <FUEL>carbon<> colours a word in-game and is
# noise anywhere else.
_MARKUP = re.compile(r"<[A-Z_]*>")


def _plain(text: str) -> str:
    return _MARKUP.sub("", text).strip()


def _ref(item_id: str, qty: int | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {"id": item_id, "name": data().book.name(item_id)}
    if qty is not None:
        row["qty"] = qty
    return row


def _recipe(recipe: Recipe) -> dict[str, Any]:
    gate = data().ease.of_recipe(recipe)
    return {
        "recipe": f"{recipe.inputs_label} -> {recipe.output_label}",
        "index": recipe.index,
        "domain": recipe.domain,
        "operation": recipe.operation,
        "output": _ref(recipe.output.id, recipe.output.n),
        "inputs": [_ref(ing.id, ing.n) for ing in recipe.inputs],
        "machine": recipe.machine,
        "time_seconds": recipe.time,
        "time": recipe.time_label,
        "multiplier": recipe.multiplier_label,
        "ratio": recipe.ratio,
        "loop": recipe.loop,
        "output_per_hour": round(recipe.rate, 1),
        "profit_units": recipe.profit,
        "gettable": gate.label,
    }


def _gettable(item_id: str) -> dict[str, Any]:
    e = data().ease.of(item_id)
    row: dict[str, Any] = {
        "label": e.label,
        "band": e.band,
        "score": round(e.score, 1),
        "describe": e.describe(data().book),
    }
    if e.tier is not None:
        row["tier"] = TIER_ORDER[e.tier]
    if e.seeds:
        row["seeds"] = [_ref(s) for s in e.seeds]
    if e.where:
        row["where"] = e.where
    if e.note:
        row["note"] = e.note
    return row


def _storage(item: Item) -> dict[str, Any]:
    placement = data().storage.place(item)
    row = {
        "home": placement.home.label,
        "action": placement.verdict,
        "label": placement.label,
        "advice": placement.advice(),
        "why": placement.why,
    }
    if placement.home.note:
        row["home_note"] = placement.home.note
    return row


def _item_summary(item: Item) -> dict[str, Any]:
    return {
        "id": item.id,
        "name": item.name,
        "category": item.category,
        "subtitle": item.subtitle,
        "value": item.value,
    }


def _seconds(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:g}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


# -- names or IDs ------------------------------------------------------------------


def _fuzzy(query: str, limit: int) -> list[Item]:
    """Name or ID, best first: exact, then prefix/substring, then near-misses.

    The near-misses are what make "chromatic metl" or "antimater" still land;
    Book.search_items alone only finds what is spelled right.
    """
    book = data().book
    q = query.strip()
    if not q:
        return []
    hits: dict[str, Item] = {}
    exact = book.items.get(q.upper()) or book.by_name(q)
    if exact:
        hits[exact.id] = exact
    for item in book.search_items(q, limit=limit * 2):
        hits.setdefault(item.id, item)
    upper = q.upper()
    for item in book.items.values():
        if upper in item.id:
            hits.setdefault(item.id, item)
    if len(hits) < limit:
        names = {item.name.lower(): item for item in book.items.values()}
        for name in difflib.get_close_matches(q.lower(), list(names), n=limit, cutoff=0.7):
            hits.setdefault(names[name].id, names[name])
    return list(hits.values())[:limit]


def resolve(text: str) -> Item:
    """One item from a name or an ID, or a ToolError that offers candidates.

    An exact ID or name always wins. Anything else that matches more than one
    item is an error rather than a guess: a chain planned for the wrong item
    looks just as confident as one for the right one.
    """
    book = data().book
    q = text.strip()
    item = book.items.get(q) or book.items.get(q.upper()) or book.by_name(q)
    if item:
        return item
    candidates = _fuzzy(q, 8)
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ToolError(f"No item called {text!r}. Try search_items.")
    options = ", ".join(f"{c.name} ({c.id})" for c in candidates)
    raise ToolError(f"{text!r} is ambiguous; pass a name or ID exactly. Candidates: {options}")


# -- the tools -----------------------------------------------------------------------


def search_items(query: str, limit: int = 20) -> dict[str, Any]:
    """Find items by name or game ID, tolerating partial words and typos.

    Returns id, name, category, subtitle and base value for each match, best
    first. Use the id (or the exact name) with the other tools.
    """
    rows = _fuzzy(query, max(1, min(limit, 100)))
    return {"query": query, "count": len(rows), "items": [_item_summary(i) for i in rows]}


def item_info(item: str, recipe_limit: int = 15) -> dict[str, Any]:
    """Everything NMSii knows about one item (name or ID).

    Base value, category, description, the buff it grants if it is food, where
    it belongs in storage, how gettable it is, and the recipes that make it and
    use it (up to `recipe_limit` each, with totals).
    """
    it = resolve(item)
    book = data().book
    made_by = book.produced_by.get(it.id, [])
    used_in = book.consumed_by.get(it.id, [])
    row: dict[str, Any] = {
        **_item_summary(it),
        "type": it.type,
        "rarity": it.rarity,
        "description": _plain(it.description),
        "storage": _storage(it),
        "gettable": _gettable(it.id),
        "made_by_total": len(made_by),
        "made_by": [_recipe(r) for r in sorted(made_by, key=lambda r: r.time)[:recipe_limit]],
        "used_in_total": len(used_in),
        "used_in": [
            _recipe(r)
            for r in sorted(used_in, key=lambda r: (-max(r.loop, r.ratio), r.time))[:recipe_limit]
        ],
        "page": f"{SITE}/md/items/{it.id}.md",
    }
    if it.effect and it.potency > 0:
        row["buff"] = {
            "stat": it.effect,
            "potency": round(it.potency, 3),
            "good_for": food.EFFECT_USE.get(it.effect_id, ""),
        }
    return row


def search_recipes(
    query: str = "",
    domain: Domain = "all",
    sort: Sort = "mult",
    item: str | None = None,
    role: Literal["any", "output", "input"] = "any",
    limit: int = 25,
) -> dict[str, Any]:
    """Filter and sort the recipe table, as the TUI's main screen does.

    query: words that must all appear in the output, inputs or operation name.
    domain: "refine" (refiners), "cook" (Nutrient Processor) or "all".
    sort: "mult" (multiplier), "time" (fastest), "rate" (output per hour),
    "profit" (units gained per batch), "ease" (most gettable inputs), "name".
    item/role: only recipes that make ("output"), use ("input") or touch
    ("any") this item, by name or ID.
    """
    # The TUI's own sort keys; imported here because app.py pulls in Textual's
    # widgets, which only this tool needs and only on first call.
    from .app import sort_key

    book = data().book
    item_id = resolve(item).id if item else None
    rows = book.search(query, None if domain == "all" else domain, item_id, role)
    rows.sort(key=sort_key(sort, data().ease))
    limit = max(1, min(limit, 200))
    return {
        "total": len(rows),
        "shown": min(limit, len(rows)),
        "sort": sort,
        "recipes": [_recipe(r) for r in rows[:limit]],
    }


def _step(step: graph.Step, sources: set[str]) -> dict[str, Any]:
    row = _ref(step.item_id, step.qty)
    if step.recipe is None:
        # A source item is picked up; anything else the set cannot make has to
        # be found -- the gettable note says where, when the guides know.
        row["get"] = "gather" if step.raw else "find"
        if not step.raw:
            row["gettable"] = _gettable(step.item_id)["label"]
        return row
    row["recipe"] = f"{step.recipe.inputs_label} -> {step.recipe.output_label}"
    row["machine"] = step.recipe.machine
    row["batches"] = step.batches
    row["time"] = _seconds(step.recipe.time * step.batches)
    row["from"] = [_step(child, sources) for child in step.children]
    return row


def plan_chain(
    item: str, qty: int = 1, tier: Tier = 0, allow_cooking: bool = False
) -> dict[str, Any]:
    """The cheapest way to make `qty` of an item from what you can pick up.

    tier 0: anything on any planet (Oxygen, Carbon, Ferrite Dust, Sodium,
    Di-hydrogen); 1 adds asteroid metals; 2 adds Nitrogen from a harvester.
    Cheapest means least refiner time (Knuth's AND-OR Dijkstra over the recipe
    graph). Returns the recipe tree, the raw materials to gather or find, and
    the total machine time. allow_cooking adds Nutrient Processor recipes.
    """
    it = resolve(item)
    if qty < 1:
        raise ToolError("qty must be at least 1")
    tier_name = TIER_ORDER[tier]
    sources = set(SOURCE_SETS[tier_name])
    domains = ("refine", "cook") if allow_cooking else ("refine",)
    p = graph.plan(data().book, it.id, sources, qty, domains)
    raw = [
        {**_ref(item_id, n), "get": "gather" if item_id in sources else "find"}
        for item_id, n in sorted(p.raw_totals.items(), key=lambda kv: -kv[1])
    ]
    result: dict[str, Any] = {
        "target": _ref(it.id, qty),
        "tier": tier_name,
        "sources": [_ref(s) for s in sorted(sources)],
        "recipes": "refining and cooking" if allow_cooking else "refining only",
        "makeable": p.ok,
        "steps": p.steps,
        "machine_seconds": p.total_seconds,
        "machine_time": _seconds(p.total_seconds),
        "raw_materials": raw,
        "tree": _step(p.root, sources),
    }
    if not p.ok:
        result["note"] = (
            f"Nothing in {tier_name} makes it: {_gettable(it.id)['describe']}."
            + (" Try a wider tier." if tier < 2 else "")
            + ("" if allow_cooking else " Try allow_cooking.")
        )
    return result


def nanite_routes(limit: int = 30) -> dict[str, Any]:
    """Every recipe that outputs nanites, best nanites-per-hour first.

    per_hour is one refiner kept fed; per_input is nanites per unit of input
    consumed; units_spent is the base value of one batch's inputs. The
    gettable label says how reachable the hardest input is.
    """
    rows = graph.nanite_ladder(data().book)
    return {
        "total": len(rows),
        "routes": [
            {
                **_recipe(row.recipe),
                "nanites_per_batch": row.nanites,
                "nanites_per_hour": round(row.per_hour, 1),
                "nanites_per_input": round(row.per_input, 3),
                "units_spent": row.units_cost,
            }
            for row in rows[: max(1, limit)]
        ],
    }


def cooking_by_buff(buff: str | None = None, limit: int = 10) -> dict[str, Any]:
    """Cooked dishes grouped by the stat eating them boosts, strongest first.

    buff: optional words matched against the stat name ("cold", "mining") or
    what it is good for ("underwater"); omit it to list every buff. potency is
    the game's 0-1 quality rating; uplift is units gained per batch over the
    ingredients. Each dish carries its quickest recipe.
    """
    terms = (buff or "").lower().split()
    groups = []
    for effect, dishes in food.by_effect(data().book).items():
        use = food.EFFECT_USE.get(dishes[0].item.effect_id, "")
        if terms and not all(t in f"{effect} {use}".lower() for t in terms):
            continue
        groups.append({
            "buff": effect,
            "good_for": use,
            "dishes_total": len(dishes),
            "dishes": [
                {
                    **_ref(d.item.id),
                    "potency": round(d.potency, 3),
                    "value": d.value,
                    "uplift_units": d.uplift,
                    "recipes_that_make_it": d.ways,
                    "quickest_recipe": _recipe(d.recipe),
                }
                for d in dishes[: max(1, limit)]
            ],
        })
    if terms and not groups:
        known = ", ".join(food.by_effect(data().book))
        raise ToolError(f"No buff matches {buff!r}. Buffs: {known}")
    return {"buffs": groups}


def where_to_store(item: str) -> dict[str, Any]:
    """Where an item belongs in the storage guide's ten-container layout.

    Also says when to keep it on you, sell it, junk it or use it at once,
    and why. One home per item is what makes "send to storage" sort itself.
    """
    it = resolve(item)
    return {**_ref(it.id), **_storage(it)}


def craftable_from(
    inventory: dict[str, int], allow_cooking: bool = False, limit: int = 50
) -> dict[str, Any]:
    """What you can make right now from what you carry, and what is one short.

    inventory maps item names or IDs to counts, e.g. {"Carbon": 200,
    "FUEL2": 50}. Returns craftable recipes with how many batches fit, and the
    recipes missing exactly one ingredient, with how much of it. Unrecognised
    names are listed rather than failing the call.
    """
    have: dict[str, int] = {}
    unknown: dict[str, str] = {}
    for key, count in inventory.items():
        try:
            item_id = resolve(key).id
        except ToolError as exc:
            unknown[key] = str(exc)
            continue
        if count > 0:
            have[item_id] = have.get(item_id, 0) + int(count)
    domains = ("refine", "cook") if allow_cooking else ("refine",)
    book = data().book
    now = graph.craftable_now(book, have, domains)
    near = graph.one_hop_away(book, have, domains)
    limit = max(1, min(limit, 300))
    result: dict[str, Any] = {
        "inventory": [_ref(i, n) for i, n in sorted(have.items())],
        "recipes": "refining and cooking" if allow_cooking else "refining only",
        "craftable_total": len(now),
        "craftable": [{**_recipe(r), "batches": n} for r, n in now[:limit]],
        "one_short_total": len(near),
        "one_short": [
            {**_recipe(r), "missing": [_ref(i, n) for i, n in missing]}
            for r, missing in near[:limit]
        ],
    }
    if unknown:
        result["unrecognised"] = unknown
    return result


def _address(address: Address, given: str) -> dict[str, Any]:
    x, y, z = address.voxel
    return {
        "portal_code": address.portal_code,
        "portal_grouped": address.portal_grouped,
        "galactic": address.galactic,
        "glyphs": address.glyph_names,
        "planet_index": address.planet,
        "system_index": f"{address.system:03X}",
        "voxel": {"x": x, "y": y, "z": z},
        "share_link": address.share_link,
        "warnings": address.warnings,
        "input": given,
    }


def convert_portal_address(text: str, planet: int | None = None) -> dict[str, Any]:
    """Convert between a portal code and a galactic (signal booster) address.

    text: 12 hex digits (the portal glyphs, e.g. "10A4F3E7C2D1"), a galactic
    address "XXXX:YYYY:ZZZZ:SSSS", or an nmsportals share link. planet (0-15)
    is the first glyph: a galactic address does not carry it, so it defaults
    to 0 there; given with a portal code, it replaces the code's own. Returns
    both forms, the twelve glyph names in dialling order, and the signed voxel
    position from the galaxy centre.
    """
    if planet is not None and not 0 <= planet <= 15:
        raise ToolError("planet is one glyph: 0-15")
    try:
        address = Address.parse(text, planet or 0)
    except AddressError as exc:
        raise ToolError(str(exc)) from exc
    given = "galactic" if ":" in text else "portal code"
    if given == "portal code" and planet is not None:
        address = address.with_planet(planet)
    row = _address(address, given)
    if given == "galactic" and planet is None:
        row["note"] = "A galactic address has no planet index; planet 0 was used."
    return row


def saved_locations(
    kind: str | None = None, query: str = "", origin: str | None = None
) -> dict[str, Any]:
    """The portal addresses saved in NMSii (data/locations.json).

    kind: multi-tool, starship, freighter, base, planet, system or other
    (a prefix like "multi" works). origin: "mine" or "shared". query: words
    matched against name, detail, where and source. Each comes with its
    galaxy, both address forms and the glyph names.
    """
    kind_key = resolve_choice(kind, KINDS) if kind else None
    if kind and not kind_key:
        raise ToolError(f"kind is one of: {', '.join(KINDS)}")
    origin_key = resolve_choice(origin, ORIGINS) if origin else None
    if origin and not origin_key:
        raise ToolError(f"origin is one of: {', '.join(ORIGINS)}")
    book = LocationBook.load()
    rows = book.search(query, kind_key, origin_key)
    return {
        "total": len(rows),
        "locations": [
            {
                "name": loc.name,
                "kind": loc.kind,
                "origin": loc.origin_label,
                "galaxy": loc.galaxy_label,
                "detail": loc.detail,
                "where": loc.where,
                "source": loc.source,
                "added": loc.added,
                **{k: v for k, v in _address(loc.address, "saved").items()
                   if k in ("portal_code", "galactic", "glyphs", "share_link")},
            }
            for loc in rows
        ],
    }


TOOLS = [
    search_items,
    item_info,
    search_recipes,
    plan_chain,
    nanite_routes,
    cooking_by_buff,
    where_to_store,
    craftable_from,
    convert_portal_address,
    saved_locations,
]


# -- the markdown guide, from the site export -------------------------------------

GUIDE_PAGES = ["guide", "recipes", "nanites", "cooking", "multitools", "storage", "portals"]


@cache
def _markdown() -> Any:
    """The site's markdown renderer over the site's bundle.

    Both live in scripts/, beside the export they belong to, so they are
    imported from the checkout rather than copied into the package; an
    installed copy without scripts/ simply has no guide resources.
    """
    scripts = DATA_DIR.parent / "scripts"
    if not (scripts / "build_markdown.py").is_file():
        raise ResourceError(
            f"The markdown guide needs NMSii's scripts/ beside data/; read it at {SITE}/llms.txt"
        )
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import build_markdown
    import build_web

    return build_markdown.Markdown(build_web.build(data().book))


def guide_page(page: str) -> str:
    md = _markdown()
    if page not in GUIDE_PAGES:
        raise ResourceError(f"No guide page {page!r}; pages: {', '.join(GUIDE_PAGES)}")
    return getattr(md, "guide" if page == "guide" else f"{page}_page")()


def item_page(item_id: str) -> str:
    md = _markdown()
    if item_id not in md.items:
        raise ResourceError(f"No item {item_id!r}; item pages are keyed by game ID")
    return md.item_page(item_id)


# -- the protocol side ----------------------------------------------------------------


def instructions() -> str:
    s = data_source() or {}
    version = s.get("summary") or "game version not recorded"
    return (
        "NMSii answers No Man's Sky crafting questions from the game's own recipe "
        f"tables ({version}): refining and cooking recipes, the cheapest refining "
        "chain from raw materials, nanite routes, cooking buffs, where items belong "
        "in storage, portal address conversion and saved addresses. Prefer these "
        "tools to remembered wiki numbers, which are often from older patches. "
        "Every tool takes item names or game IDs; when a name is ambiguous the "
        "error lists candidates, and search_items finds the right one."
    )


def build_server() -> MCPServer:
    server = MCPServer(
        "nmsii",
        title="NMSii - No Man's Sky Items Interface",
        instructions=instructions(),
        website_url=SITE,
    )
    read_only = ToolAnnotations(read_only_hint=True, open_world_hint=False)
    for fn in TOOLS:
        server.tool(annotations=read_only)(fn)

    @server.resource(
        "nmsii://source",
        name="source",
        title="Data provenance",
        description="Which game build the recipe data was extracted from, when, and with what tools",
        mime_type="application/json",
    )
    def source() -> dict:
        return data_source() or {"from": "unknown", "summary": "data/source.json is missing"}

    @server.resource(
        "nmsii://guide/{page}",
        name="guide",
        title="NMSii guide pages",
        description=(
            "The site's section pages as markdown: " + ", ".join(GUIDE_PAGES)
            + ". 'guide' explains the columns, the source tiers and the chain planner."
        ),
        mime_type="text/markdown",
    )
    def guide(page: str) -> str:
        return guide_page(page)

    @server.resource(
        "nmsii://items/{item_id}",
        name="item-page",
        title="Item page",
        description="One item's page as markdown: value, storage, buff, recipes, cheapest chain",
        mime_type="text/markdown",
    )
    def item(item_id: str) -> str:
        return item_page(item_id)

    @server.prompt(
        title="Plan a refining chain",
        description="Work out how to make an item from raw materials, with NMSii's planner",
    )
    def plan_refining_chain(item: str, qty: str = "1") -> str:
        return (
            f"I want {qty} of {item} in No Man's Sky. Use the NMSii tools: resolve "
            "the item with search_items if the name is unclear, then plan_chain from "
            "tier 0, widening to tier 1 or 2 only if it is not makeable. Give me the "
            "raw materials to gather, the refiner steps in order with batch counts, "
            "and the total machine time. If an input has to be found, say where "
            "item_info's gettable section says it drops."
        )

    return server


def main() -> int:
    try:
        data()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    build_server().run("stdio")
    return 0
