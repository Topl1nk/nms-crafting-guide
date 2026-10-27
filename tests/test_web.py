"""The static site against the Python it mirrors.

scripts/build_web.py exports the answers; site/src/lib/core.js redoes the cheap
parts in the browser -- the chain tree walk, inventory matching, portal
arithmetic. These run that JS under node and hold it to the Python, so the web
page and the TUI cannot quietly disagree. Without node the cross-checks skip;
the export checks, and the ones that only read the site's source, still run.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from nms_items import graph
from nms_items.model import SOURCE_SETS, Book
from nms_items.portals import Address

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_web  # noqa: E402

NODE = shutil.which("node")
SITE = ROOT / "site"
# A plain ES module with no Svelte in it, so node runs it as it is.
CORE = (SITE / "src" / "lib" / "core.js").as_uri()

# What the site keeps in localStorage, under `nms-items:`. Visitors have these
# saved from the hand-written page that came before the Svelte one; a renamed
# key would quietly forget their inventory or their portal addresses.
STORAGE_KEYS = {"inventory", "locations", "theme", "accent", "big", "fs", "sym", "glow",
                "save-on", "save-skip", "save-slot", "lang"}

# Deep chains, shallow ones, a loop, a cooked dish and something unreachable.
TARGETS = ["TECHFRAG", "ANTIMATTER", "HYPERFUEL1", "STELLAR2", "MICROCHIP", "FOOD_R_FLOUR",
           "BLUE2", "AF_METAL"]
QTYS = [1, 7]


@pytest.fixture(scope="module")
def book() -> Book:
    return Book()


@pytest.fixture(scope="module")
def bundle(book: Book) -> dict:
    return build_web.build(book)


def run_node(script: str, payload: dict) -> object:
    result = subprocess.run(
        [NODE, "--input-type=module", "-e", script],
        input=json.dumps(payload), capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def test_bundle_is_consistent(bundle: dict) -> None:
    n = len(bundle["recipes"])
    for tier in bundle["tiers"]:
        for via in tier["via"].values():
            assert all(0 <= index < n for index in via.values())
            assert all(bundle["recipes"][i]["out"][0] == item for item, i in via.items())
    for recipe in bundle["recipes"]:
        for item_id, _ in recipe["in"]:
            assert item_id in bundle["ease"]
    assert len(bundle["glyphs"]) == 16
    assert [g["hex"] for g in bundle["glyphs"]] == list("0123456789ABCDEF")
    stores = len(bundle["storage"]["outcomes"])
    assert all(0 <= item["store"] < stores for item in bundle["items"].values())


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_chain_plans_match_python(book: Book, bundle: dict) -> None:
    cases = []
    for t, name in enumerate(SOURCE_SETS):
        for cook in (False, True):
            for target in TARGETS:
                for qty in QTYS:
                    cases.append({"tier": t, "cook": cook, "target": target, "qty": qty})

    script = f"""
import {{ plan }} from "{CORE}";
let raw = ""; for await (const c of process.stdin) raw += c;
const {{ bundle, cases }} = JSON.parse(raw);
const out = cases.map((c) => {{
  const t = bundle.tiers[c.tier];
  const p = plan(bundle.recipes, t.via[c.cook ? "all" : "refine"], new Set(t.sources), c.target, c.qty);
  return {{ raw: p.raw, steps: p.steps, seconds: p.seconds, ok: p.ok }};
}});
console.log(JSON.stringify(out));
"""
    results = run_node(script, {"bundle": bundle, "cases": cases})

    names = list(SOURCE_SETS)
    for case, js in zip(cases, results):
        domains = ("refine", "cook") if case["cook"] else ("refine",)
        py = graph.plan(book, case["target"], set(SOURCE_SETS[names[case["tier"]]]),
                        case["qty"], domains)
        assert js["ok"] == py.ok, case
        assert js["raw"] == py.raw_totals, case
        assert js["steps"] == py.steps, case
        assert js["seconds"] == pytest.approx(py.total_seconds), case


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_inventory_matches_python(book: Book, bundle: dict) -> None:
    have = {"OXYGEN": 50, "FUEL1": 120, "LAND1": 40, "CATALYST1": 9, "ASTEROID1": 300, "GAS3": 2}
    script = f"""
import {{ craftableNow, oneHopAway }} from "{CORE}";
let raw = ""; for await (const c of process.stdin) raw += c;
const {{ recipes, have }} = JSON.parse(raw);
const d = ["refine", "cook"];
console.log(JSON.stringify({{ can: craftableNow(recipes, have, d), near: oneHopAway(recipes, have, d) }}));
"""
    js = run_node(script, {"recipes": bundle["recipes"], "have": have})
    assert js["can"] == [[r.index, b] for r, b in graph.craftable_now(book, have)]
    assert js["near"] == [
        [r.index, [list(m) for m in missing]] for r, missing in graph.one_hop_away(book, have)
    ]


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_portal_conversion_matches_python(bundle: dict) -> None:
    texts = [
        "000000000000",
        "40E907FF0D6B",
        "6046FFAE4450",
        "056A:0086:07EF:00E9",
        "https://nmsportals.github.io/#21A3F8001234",
        "0FFF:00FF:0000:0429",
    ] + [loc["code"] for loc in bundle["portals"]["locations"]]
    script = f"""
import {{ Address }} from "{CORE}";
let raw = ""; for await (const c of process.stdin) raw += c;
console.log(JSON.stringify(JSON.parse(raw).texts.map((t) => {{
  const a = Address.parse(t, 3);
  return {{ code: a.code, galactic: a.galactic, voxel: a.voxel }};
}})));
"""
    for text, js in zip(texts, run_node(script, {"texts": texts})):
        py = Address.parse(text, 3)
        assert js == {"code": py.portal_code, "galactic": py.galactic,
                      "voxel": list(py.voxel)}, text


def test_storage_keys_unchanged() -> None:
    used = set()
    for path in (SITE / "src").rglob("*"):
        if path.suffix in {".js", ".svelte"}:
            text = path.read_text(encoding="utf-8")
            used |= set(re.findall(r'local\.(?:get|set)\("([^"]+)"', text))
    assert used == STORAGE_KEYS
    local = (SITE / "src" / "lib" / "local.js").read_text(encoding="utf-8")
    assert 'PREFIX = "nms-items:"' in local
    # The pre-paint theme script reads the same key, before any module loads.
    index = (SITE / "index.html").read_text(encoding="utf-8")
    assert 'localStorage.getItem("nms-items:theme")' in index


def test_every_route_has_a_view() -> None:
    # Shared links name these sections; a section without a view falls back to
    # the start page, and the link quietly stops meaning anything.
    app = (SITE / "src" / "App.svelte").read_text(encoding="utf-8")
    table = re.search(r"const VIEWS = \{(.*?)\};", app, re.S).group(1)
    assert set(re.findall(r"(\w+): \w+", table)) == {
        "home", "recipes", "multitools", "portals",
        "inventory", "help", "tree", "wiki",
    }


# The built site as an installable, offline app: scripts/check_pwa.mjs, which
# `npm run build` already runs after every build (so CI and the Pages workflow
# never ship a dist/ that fails it). Here for `mise run test:web` after a local
# build; skipped before the first one.
DIST = ROOT / "dist"
CHECK_PWA = ROOT / "scripts" / "check_pwa.mjs"
# The portable build runs from a local server inside an app window, so it
# registers no service worker (lib/pwa.svelte.js); there is no offline app to check.
PWA_OFF = "false &&" in (SITE / "src" / "lib" / "pwa.svelte.js").read_text(encoding="utf-8")
built = pytest.mark.skipif(NODE is None or PWA_OFF or not (DIST / "sw.js").exists(),
                           reason="needs node and a built dist/ (mise run web:build)")


def check_pwa(dist: Path) -> subprocess.CompletedProcess:
    return subprocess.run([NODE, str(CHECK_PWA), str(dist)], capture_output=True, text=True)


@built
def test_built_site_is_installable() -> None:
    result = check_pwa(DIST)
    assert result.returncode == 0, result.stderr
    assert "manifest ok" in result.stdout


@built
def test_check_pwa_catches_a_broken_build(tmp_path: Path) -> None:
    # The checker itself: a missing icon, a precached file gone, a bad scope.
    broken = tmp_path / "dist"
    shutil.copytree(DIST, broken, ignore=shutil.ignore_patterns("md", "pdf", "img", "llms*"))
    (broken / "icon-192.png").unlink()
    gone = next((broken / "assets").glob("*.css"))
    gone.unlink()
    manifest = json.loads((broken / "manifest.webmanifest").read_text(encoding="utf-8"))
    manifest["scope"] = "/elsewhere/"
    (broken / "manifest.webmanifest").write_text(json.dumps(manifest), encoding="utf-8")
    result = check_pwa(broken)
    assert result.returncode == 1
    assert "icon icon-192.png is not in" in result.stderr
    assert f"precaches assets/{gone.name}, which is not in" in result.stderr
    assert "scope resolves to" in result.stderr
