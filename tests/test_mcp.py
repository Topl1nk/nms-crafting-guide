"""The MCP server against the modules it wraps.

mcp_server.py is meant to add names and shape, never numbers of its own, so
each tool is checked against the function it calls: graph.plan for chains,
the nanite ladder, StorageGuide.place, food.by_effect, Address. Then the
whole thing once over the protocol, in-process, and once as `nms mcp` on real
stdio, the way an assistant launches it.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import anyio
import pytest
from mcp import Client, StdioServerParameters
from mcp.server.mcpserver.exceptions import ResourceError, ToolError

from nms_items import food, graph, mcp_server as m
from nms_items.model import SOURCE_SETS, data_source
from nms_items.portals import Address, LocationBook

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def d() -> m.Data:
    return m.data()


# -- names or IDs -------------------------------------------------------------------


def test_resolve_takes_ids_names_and_case(d):
    assert m.resolve("STELLAR2").id == "STELLAR2"
    assert m.resolve("stellar2").id == "STELLAR2"
    assert m.resolve("Chromatic Metal").id == "STELLAR2"
    assert m.resolve("chromatic metal").id == "STELLAR2"
    # An exact name wins over the longer names it is a prefix of.
    assert m.resolve("Carbon").id == "FUEL1"


def test_resolve_refuses_to_guess(d):
    with pytest.raises(ToolError, match="ambiguous.*Ferrite Dust"):
        m.resolve("ferrit")
    with pytest.raises(ToolError, match="No item"):
        m.resolve("qqqqqqqqqq")


def test_search_items_fuzzy(d):
    assert m.search_items("antimater")["items"][0]["id"] == "ANTIMATTER"
    ids = [row["id"] for row in m.search_items("TECHFRAG")["items"]]
    assert ids[0] == "TECHFRAG"
    names = [row["name"] for row in m.search_items("ferrite")["items"]]
    assert "Ferrite Dust" in names and "Pure Ferrite" in names


# -- each tool against the module it wraps ------------------------------------------


def test_item_info(d):
    info = m.item_info("Chromatic Metal")
    item = d.book.items["STELLAR2"]
    assert info["value"] == item.value
    assert info["made_by_total"] == len(d.book.produced_by["STELLAR2"])
    assert info["used_in_total"] == len(d.book.consumed_by["STELLAR2"])
    assert info["gettable"]["label"] == d.ease.of("STELLAR2").label
    assert info["storage"]["label"] == d.storage.place(item).label
    assert "<" not in info["description"]
    for row in info["made_by"]:
        assert row["output"]["id"] == "STELLAR2"
    dish = m.item_info("FOOD_R_EYEICE")
    assert dish["buff"]["stat"] == d.book.items["FOOD_R_EYEICE"].effect


@pytest.mark.parametrize(
    "target,qty,tier,cooking",
    [("FUEL2", 5, 0, False), ("TECHFRAG", 50, 0, False), ("STELLAR2", 3, 2, False),
     ("FOOD_R_FLOUR", 2, 0, True), ("ANTIMATTER", 1, 0, False)],
)
def test_plan_chain_matches_graph(d, target, qty, tier, cooking):
    name = list(SOURCE_SETS)[tier]
    sources = set(SOURCE_SETS[name])
    domains = ("refine", "cook") if cooking else ("refine",)
    want = graph.plan(d.book, target, sources, qty, domains)
    got = m.plan_chain(d.book.name(target), qty, tier, cooking)
    assert got["makeable"] == want.ok
    assert got["steps"] == want.steps
    assert got["machine_seconds"] == pytest.approx(want.total_seconds)
    assert {r["id"]: r["qty"] for r in got["raw_materials"]} == want.raw_totals
    assert got["tree"]["qty"] == qty
    if not want.ok:
        assert "note" in got


def test_search_recipes(d):
    out = m.search_recipes("chlorine", domain="refine", sort="rate")
    want = d.book.search("chlorine", "refine")
    assert out["total"] == len(want)
    rates = [r["output_per_hour"] for r in out["recipes"]]
    assert rates == sorted(rates, reverse=True)
    made = m.search_recipes(item="Chromatic Metal", role="output", limit=200)
    assert made["total"] == len(d.book.produced_by["STELLAR2"])
    assert all(r["output"]["id"] == "STELLAR2" for r in made["recipes"])


def test_nanite_routes(d):
    ladder = graph.nanite_ladder(d.book)
    out = m.nanite_routes(limit=100)
    assert out["total"] == len(ladder)
    assert [r["index"] for r in out["routes"]] == [row.recipe.index for row in ladder]
    assert out["routes"][0]["nanites_per_hour"] == pytest.approx(ladder[0].per_hour, abs=0.1)


def test_cooking_by_buff(d):
    groups = food.by_effect(d.book)
    every = m.cooking_by_buff(limit=1000)["buffs"]
    assert [g["buff"] for g in every] == list(groups)
    cold = m.cooking_by_buff("cold")["buffs"]
    assert [g["buff"] for g in cold] == ["Cold Resistance"]
    assert [x["id"] for x in cold[0]["dishes"]] == \
        [x.item.id for x in groups["Cold Resistance"][:10]]
    with pytest.raises(ToolError):
        m.cooking_by_buff("no such buff at all")


def test_where_to_store(d):
    for item_id in ("ASTEROID2", "TECHFRAG", "FOOD_R_EYEICE"):
        placement = d.storage.place(d.book.items[item_id])
        got = m.where_to_store(d.book.name(item_id))
        assert got["id"] == item_id
        assert got["label"] == placement.label
        assert got["advice"] == placement.advice()


def test_craftable_from(d):
    have = {"FUEL1": 100, "OXYGEN": 30}
    out = m.craftable_from({"Carbon": 100, "oxygen": 30, "not an item": 4})
    assert out["unrecognised"].keys() == {"not an item"}
    now = graph.craftable_now(d.book, have, ("refine",))
    near = graph.one_hop_away(d.book, have, ("refine",))
    assert out["craftable_total"] == len(now)
    assert [(r["index"], r["batches"]) for r in out["craftable"]] == \
        [(r.index, n) for r, n in now]
    assert out["one_short_total"] == len(near)
    cooked = m.craftable_from({"Carbon": 100}, allow_cooking=True)
    assert cooked["one_short_total"] == len(graph.one_hop_away(d.book, {"FUEL1": 100}))


def test_convert_portal_address():
    # The example in portals.py's own error message, there and back.
    galactic = m.convert_portal_address("042F:0078:0D55:006A", planet=1)
    address = Address.from_galactic("042F:0078:0D55:006A", 1)
    assert galactic["portal_code"] == address.portal_code
    assert galactic["glyphs"] == address.glyph_names
    back = m.convert_portal_address(galactic["portal_code"])
    assert back["galactic"] == "042F:0078:0D55:006A"
    assert back["input"] == "portal code"
    assert m.convert_portal_address(galactic["portal_code"], planet=3)["planet_index"] == 3
    assert "note" in m.convert_portal_address("042F:0078:0D55:006A")
    with pytest.raises(ToolError):
        m.convert_portal_address("hello")


def test_saved_locations():
    book = LocationBook.load()
    assert m.saved_locations()["total"] == len(book.locations)
    tools = m.saved_locations("multi")
    assert tools["total"] == len(book.search(kind="multi-tool"))
    assert all(row["kind"] == "multi-tool" for row in tools["locations"])
    with pytest.raises(ToolError):
        m.saved_locations("spaceship-ish")


def test_guide_resources(d):
    assert m.guide_page("guide").startswith("# How to read NMSii")
    assert "TECHFRAG" in m.item_page("TECHFRAG")
    with pytest.raises(ResourceError):
        m.guide_page("nope")


def test_every_result_is_json(d):
    for result in (m.item_info("Gold"), m.plan_chain("TECHFRAG", 10),
                   m.nanite_routes(), m.cooking_by_buff(), m.saved_locations()):
        json.dumps(result)


# -- over the protocol ---------------------------------------------------------------


def _check_session(server) -> None:
    async def run() -> None:
        async with Client(server) as client:
            tools = {t.name for t in (await client.list_tools()).tools}
            assert tools == {fn.__name__ for fn in m.TOOLS}

            result = await client.call_tool("plan_chain", {"item": "Condensed Carbon", "qty": 5})
            assert not result.is_error
            assert result.structured_content["target"]["id"] == "FUEL2"

            bad = await client.call_tool("item_info", {"item": "ferrit"})
            assert bad.is_error
            assert "Ferrite Dust" in bad.content[0].text

            source = await client.read_resource("nmsii://source")
            assert json.loads(source.contents[0].text) == data_source()

            guide = await client.read_resource("nmsii://guide/nanites")
            assert guide.contents[0].text.startswith("# Nanites")

            prompts = {p.name for p in (await client.list_prompts()).prompts}
            assert "plan_refining_chain" in prompts

    anyio.run(run)


def test_in_process(d):
    _check_session(m.build_server())


def test_stdio_subprocess():
    """`nms mcp` itself, over a pipe, the way Claude Code or Desktop runs it."""
    env = {"PYTHONPATH": str(ROOT / "src"), "NMS_ITEMS_DATA": str(ROOT / "data")}
    if "XDG_STATE_HOME" in os.environ:
        env["XDG_STATE_HOME"] = os.environ["XDG_STATE_HOME"]
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "nms_items", "mcp"], env=env, cwd=str(ROOT))
    _check_session(params)
