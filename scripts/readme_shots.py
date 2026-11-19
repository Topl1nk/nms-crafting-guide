"""Retake the README screenshots: docs/img/site-*.webp (English) and docs/img/<code>/site-*.webp (one set per language).

    python scripts/readme_shots.py            every language
    python scripts/readme_shots.py en ru ja   only these (codes as in LANGS below; "en" is the English set)

The built site (dist/, `npm run build` or `node node_modules/vite/bin/vite.js build`) is served on 127.0.0.1 and shot in headless
Chrome at 1920x1080, dark theme, a language at a time. Needs `pip install playwright pillow` and Chrome (channel="chrome").
No save is read: the page has no launcher here, so My items is filled with a typed list (INVENTORY). The page words come from
site/src/lang/, and the game's item names from dist/lang/<language>.json, which must hold every language: they come from
`build_langs.py` (needs the game installed; see docs/UPDATING-README.md).
See docs/UPDATING-README.md for the whole routine.
"""
import functools
import http.server
import io
import json
import pathlib
import sys
import threading
import time

from PIL import Image
from playwright.sync_api import sync_playwright

APP = pathlib.Path(__file__).resolve().parent.parent
OUT = APP / "docs" / "img"
LANGS = {"en": "english", "ru": "russian", "pt-BR": "brazilianportuguese", "pt": "portuguese", "es": "spanish", "fr": "french",
         "de": "german", "it": "italian", "nl": "dutch", "pl": "polish", "ja": "japanese", "ko": "korean",
         "zh-CN": "simplifiedchinese", "zh-TW": "traditionalchinese"}
PAGES = [("recipes", "#/recipes"), ("nanites", "#/nanites"), ("cooking", "#/cooking"), ("tree-picker", "#/tree"),
         ("tree", "#/tree/STELLAR2"), ("wiki", "#/wiki"), ("portals", "#/portals"), ("multitools", "#/multitools"),
         ("inventory", "#/inventory")]
# What My items shows: item names (English, as in data.json) and how many.
INVENTORY = {"Ammonia": 3, "Copper": 12, "Nitrogen": 5, "Chromatic Metal": 40, "Gold": 25, "Silver": 18, "Platinum": 9,
             "Antimatter": 2, "Warp Cell": 6, "Nanite Cluster": 150, "Pure Ferrite": 60, "Condensed Carbon": 22, "Sodium": 100,
             "Oxygen": 80, "Carbon": 45, "Indium": 14, "Cadmium": 8, "Emeril": 11}


def serve() -> str:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(APP / "dist"))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}/"


def main(only: list[str]) -> None:
    base = serve()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        probe = browser.new_page()
        items = probe.request.get(base + "data.json").json()["items"]
        probe.close()
        inv = {k: INVENTORY[v["name"]] for k, v in items.items() if v["name"] in INVENTORY}
        for code, game in LANGS.items():
            if only and code not in only:
                continue
            ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1, color_scheme="dark")
            ctx.add_init_script(
                f"localStorage.setItem('nms-items:lang', JSON.stringify({json.dumps(game)}));"
                "localStorage.setItem('nms-items:theme', JSON.stringify('dark'));"
                f"localStorage.setItem('nms-items:inventory', JSON.stringify({json.dumps(inv)}));")
            page = ctx.new_page()
            folder = OUT if code == "en" else OUT / code
            folder.mkdir(parents=True, exist_ok=True)
            for name, route in PAGES:
                page.goto(base + route)
                page.reload()
                page.wait_for_load_state("networkidle")
                time.sleep(3.0 if name.startswith("tree") else 2.0)  # the trees draw themselves
                Image.open(io.BytesIO(page.screenshot())).save(folder / f"site-{name}.webp", "WEBP", quality=82)
            print(code, "done", flush=True)
            ctx.close()
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:])
