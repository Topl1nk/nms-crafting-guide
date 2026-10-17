"""The markdown version of the site against data.json and the planners.

scripts/build_markdown.py renders the bundle build_web.build() returns, and
redoes one computation itself: the chain tree walk. These check that every item
got a page, that a sample of pages prints the bundle's numbers, that the tree
walk agrees with graph.plan and with core.js, that every link llms.txt gives
resolves to a generated file, and that data.json fits its schema.
"""

from __future__ import annotations

import json
import posixpath
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from nms_items import graph
from nms_items.model import Book

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_markdown  # noqa: E402
import build_web  # noqa: E402

NODE = shutil.which("node")
CORE = (ROOT / "web" / "core.js").as_uri()

# Raw, one step, deep, a loop, cooked, a nanite route, loot, needs-a-seed.
SAMPLE = ["OXYGEN", "FUEL2", "TECHFRAG", "WATER2", "FOOD_R_FLOUR", "AF_METAL", "STELLAR2",
          "HYPERFUEL1", "MICROCHIP"]


@pytest.fixture(scope="module")
def book() -> Book:
    return Book()


@pytest.fixture(scope="module")
def bundle(book: Book) -> dict:
    return build_web.build(book)


@pytest.fixture(scope="module")
def md(bundle: dict) -> build_markdown.Markdown:
    return build_markdown.Markdown(bundle, "2026-01-01", "2026-01-02")


@pytest.fixture(scope="module")
def pages(md: build_markdown.Markdown) -> dict[str, str]:
    return md.pages()


def test_every_item_has_a_page(bundle: dict, pages: dict[str, str]) -> None:
    item_pages = {p for p in pages if p.startswith("md/items/")} - {"md/items/index.md"}
    assert item_pages == {f"md/items/{i}.md" for i in bundle["items"]}
    index = pages["md/items/index.md"]
    for item_id in bundle["items"]:
        assert f"({item_id}.md)" in index


@pytest.mark.parametrize("item_id", SAMPLE)
def test_item_page_numbers_match_bundle(bundle: dict, pages: dict[str, str],
                                        item_id: str) -> None:
    item = bundle["items"][item_id]
    page = pages[f"md/items/{item_id}.md"]
    assert page.startswith(f"# {item['name']}\n")
    assert f"**Base value**: {build_markdown.fmt_int(item['value'])} units" in page
    outcome = bundle["storage"]["outcomes"][item["store"]]
    assert outcome["label"] in page and outcome["advice"] in page
    made = [r for r in bundle["recipes"] if r["out"][0] == item_id]
    used = [r for r in bundle["recipes"] if any(i == item_id for i, _ in r["in"])]
    assert f"## Made by ({len(made)})" in page
    assert f"## Used in ({len(used)})" in page
    # One table row per recipe, with the recipe's own rate.
    for section, rows in (("Made by", made), ("Used in", used)):
        body = page.split(f"## {section}")[1].split("\n## ")[0]
        table_rows = [line for line in body.splitlines() if line.startswith("| ")][2:]
        assert len(table_rows) == len(rows)
        rates = sorted(line.split(" | ")[6] for line in table_rows)
        assert rates == sorted(build_markdown.fmt_int(r["rate"]) for r in rows)


def test_nanite_page_matches_ladder(bundle: dict, pages: dict[str, str]) -> None:
    rows = [line for line in pages["md/nanites.md"].splitlines() if line.startswith("| ")][2:]
    assert len(rows) == len(bundle["nanites"])
    for line, n in zip(rows, bundle["nanites"]):
        r = bundle["recipes"][n["recipe"]]
        cells = [c.strip() for c in line.strip("|").split(" | ")]
        assert cells[1] == str(r["out"][1])
        assert cells[3] == build_markdown.fmt_int(r["rate"])
        assert cells[4] == f"{n['per_input']:.2f}"


def test_recipe_page_has_every_recipe(bundle: dict, pages: dict[str, str]) -> None:
    rows = [line for line in pages["md/recipes.md"].splitlines()
            if line.startswith("| ") and not line.startswith(("| Make", "| ---"))]
    assert len(rows) == len(bundle["recipes"])


def test_chain_walk_matches_python(book: Book, bundle: dict) -> None:
    for t, tier in enumerate(bundle["tiers"]):
        sources = set(tier["sources"])
        for key, domains in build_web.DOMAIN_SETS.items():
            for target in SAMPLE:
                for qty in (1, 7):
                    ours = build_markdown.plan(bundle["recipes"], tier["via"][key], sources,
                                               target, qty)
                    py = graph.plan(book, target, sources, qty, domains)
                    case = (t, key, target, qty)
                    assert ours["ok"] == py.ok, case
                    assert ours["raw"] == py.raw_totals, case
                    assert ours["steps"] == py.steps, case
                    assert ours["seconds"] == pytest.approx(py.total_seconds), case


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_chain_walk_matches_core_js(bundle: dict, md: build_markdown.Markdown) -> None:
    # The very chain each sample page prints, against core.js on the same via.
    cases = []
    for target in SAMPLE:
        for tier_index, key in build_markdown.CHAIN_TRIES:
            cases.append({"tier": tier_index, "key": key, "target": target})
    script = f"""
import {{ plan }} from "{CORE}";
let raw = ""; for await (const c of process.stdin) raw += c;
const {{ bundle, cases }} = JSON.parse(raw);
console.log(JSON.stringify(cases.map((c) => {{
  const t = bundle.tiers[c.tier];
  return plan(bundle.recipes, t.via[c.key], new Set(t.sources), c.target, 1);
}})));
"""
    result = subprocess.run([NODE, "--input-type=module", "-e", script],
                            input=json.dumps({"bundle": bundle, "cases": cases}),
                            capture_output=True, text=True, check=True)
    for case, js in zip(cases, json.loads(result.stdout)):
        tier = bundle["tiers"][case["tier"]]
        ours = build_markdown.plan(bundle["recipes"], tier["via"][case["key"]],
                                   set(tier["sources"]), case["target"], 1)
        assert js["raw"] == ours["raw"], case
        assert js["steps"] == ours["steps"], case
        assert js["ok"] == ours["ok"], case
        assert js["seconds"] == pytest.approx(ours["seconds"]), case
        # The whole tree, not only its totals: the page prints every node.
        assert js["root"] == ours["root"], case


def test_llms_txt_links_resolve(pages: dict[str, str]) -> None:
    text = pages["llms.txt"]
    assert text.startswith("# NMSii — No Man's Sky Items Interface\n\n> ")
    links = re.findall(r"\]\((https://nmsii\.dlu\.one/[^)]+)\)", text)
    assert len(links) >= len(build_markdown.SECTIONS) + 3
    # Files the export writes beside the markdown; the PDFs are copied in CI.
    elsewhere = {"data.json", "data.schema.json", "pdf/nms-cheatsheet.pdf",
                 "pdf/nms-cheatsheet-dark.pdf"}
    for link in links:
        path = link.removeprefix(build_markdown.SITE + "/")
        assert path in pages or path in elsewhere, link
    assert (ROOT / "web" / "data.schema.json").is_file()
    for path in elsewhere:
        if path.startswith("pdf/"):
            assert (ROOT / "docs" / path).is_file(), path


def test_relative_links_resolve(pages: dict[str, str]) -> None:
    for path, text in pages.items():
        if not path.endswith(".md"):
            continue
        base = posixpath.dirname(path)
        for target in re.findall(r"\]\(([^)#:]+\.md)(?:#[^)]*)?\)", text):
            assert posixpath.normpath(posixpath.join(base, target)) in pages, (path, target)


def test_sitemap_lists_every_page(pages: dict[str, str]) -> None:
    locs = re.findall(r"<loc>([^<]+)</loc>", pages["sitemap.xml"])
    paths = {loc.removeprefix(build_markdown.SITE + "/") for loc in locs}
    assert "" in paths and "llms.txt" in paths
    assert {p for p in pages if p.startswith("md/")} <= paths
    assert "Sitemap: https://nmsii.dlu.one/sitemap.xml" in pages["robots.txt"]


def test_llms_full_stays_small(pages: dict[str, str]) -> None:
    full = pages["llms-full.txt"]
    assert len(full.encode()) < 3 * 1024 * 1024
    for key, _, _ in build_markdown.SECTIONS:
        assert pages[f"md/{key}.md"] in full


# -- data.schema.json --------------------------------------------------------------

def check(schema: dict, value: object, defs: dict, where: str = "$") -> None:
    """The JSON Schema subset data.schema.json uses; no dependency for one file."""
    if "$ref" in schema:
        schema = defs[schema["$ref"].removeprefix("#/$defs/")]
    kinds = {"object": dict, "array": list, "string": str, "boolean": bool,
             "integer": int, "number": (int, float), "null": type(None)}
    if "type" in schema:
        # "type" is one name or a list of them, e.g. ["object", "null"].
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        assert any(isinstance(value, kinds[t]) for t in types), where
        if value is None:
            return
        if isinstance(value, bool):
            assert "boolean" in types, where
    if "enum" in schema:
        assert value in schema["enum"], where
    if "pattern" in schema:
        assert re.search(schema["pattern"], value), where
    if "minimum" in schema:
        assert value >= schema["minimum"], where
    if "maximum" in schema:
        assert value <= schema["maximum"], where
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            assert key in value, f"{where}.{key} missing"
        for key, sub in value.items():
            if key in props:
                check(props[key], sub, defs, f"{where}.{key}")
            elif isinstance(schema.get("additionalProperties"), dict):
                check(schema["additionalProperties"], sub, defs, f"{where}.{key}")
            else:
                assert schema.get("additionalProperties", True) is not False, \
                    f"{where}.{key} not in schema"
    if isinstance(value, list):
        assert len(value) >= schema.get("minItems", 0), where
        assert len(value) <= schema.get("maxItems", len(value)), where
        prefix = schema.get("prefixItems", [])
        for i, sub in enumerate(value):
            item_schema = prefix[i] if i < len(prefix) else schema.get("items")
            if item_schema:
                check(item_schema, sub, defs, f"{where}[{i}]")


def test_data_json_fits_schema(bundle: dict) -> None:
    schema = json.loads((ROOT / "web" / "data.schema.json").read_text(encoding="utf-8"))
    # Round-trip so the check sees what data.json holds, not Python objects.
    check(schema, json.loads(json.dumps(bundle)), schema["$defs"])


def test_bundle_says_which_game_build(bundle: dict) -> None:
    """data.json carries data/source.json, so the site can say what it is
    up to date with instead of a date guessed from git."""
    source = json.loads((ROOT / "data" / "source.json").read_text(encoding="utf-8"))
    s = bundle["source"]
    assert s["from"] == source["source"]
    if s["from"] == "game":
        assert s["version"] == source["game"]["version"]
        assert s["build"] == int(source["game"]["build"])
        assert s["extracted"] == source["extracted"]


def test_llms_txt_states_the_game_version(bundle: dict, pages: dict[str, str]) -> None:
    s = bundle["source"]
    if not s or s["from"] != "game":
        pytest.skip("data built from NMS-Handbook, which records no version")
    label = f"No Man's Sky {s['game']} {s['version']} (build {s['build']})"
    assert f"Data: {label}, extracted from the game files on {s['extracted']}" in pages["llms.txt"]
    assert label in pages["md/recipes.md"].split("\n\n")[1]  # the page header


def test_source_falls_back_without_a_version(bundle: dict) -> None:
    for source in (None, {"from": "handbook", "game": "", "version": "", "build": None,
                          "extracted": "2026-02-01", "summary": "", "tools": {}}):
        md = build_markdown.Markdown({**bundle, "source": source}, "2026-01-01", "2026-01-02")
        assert md.data_label() == ""
        assert "NMS-Handbook" in md.source_line()
        assert "2026-01-01" in md.llms_txt()


def test_app_markdown_links_exist(pages: dict[str, str]) -> None:
    # app.js points each page's footer link and <link rel=alternate> at its
    # markdown twin; every file it can name has to be one the export writes.
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    table = re.search(r"const MD_PAGES = \{(.*?)\};", app, re.S).group(1)
    targets = re.findall(r'"([^"]+\.md)"', table)
    assert len(targets) >= 8
    for path in [*targets, "llms.txt", "md/items/index.md"]:
        assert path in pages, path
    assert "md/items/${encodeURIComponent(item)}.md" in app
