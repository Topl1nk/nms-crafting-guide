"""Retake the README screenshots (docs/img/site-*.webp: English; docs/img/<code>/site-*.webp: one set per language) and, with --steam,
the pictures of the Steam guide (NMSii/steam-guide/images-en/NN-name.jpg).

    python scripts/readme_shots.py                 every language
    python scripts/readme_shots.py en ru ja        only these (codes as in LANGS below; "en" is the English set)
    python scripts/readme_shots.py --steam         the Steam guide's pictures too (English only)
    python scripts/readme_shots.py --no-launcher   without the pages that need the desktop program (Planets, Settings)

Two servers, both on 127.0.0.1, shot in headless Chrome at 1920x1080, dark theme, a language at a time:
  * the built site (dist/, `node node_modules/vite/bin/vite.js build`) for the pages that need nothing but the data; My items is
    filled with a typed list (INVENTORY);
  * the desktop program (desktop/nms_crafting_guide.py --server), for Planets and Settings, which read the game save and the
    installed pictures. The save is the player's own, so what it holds is cleaned on its way to the page (see clean()): the planets
    and systems the player named, the bases' names are dropped, and only what the game itself names is shown.
Needs `pip install playwright pillow` and Chrome (channel="chrome"). The program is started with the Python that has its
requirements (lz4, numpy, pillow): NMS_LAUNCHER_PYTHON, else this one. Item names come from the language packs of the program's
data folder (every language must be built: desktop/languages.py does it by itself in the background).
See docs/UPDATING-README.md for the whole routine.
"""
import functools
import http.server
import io
import json
import os
import pathlib
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

from PIL import Image
from playwright.sync_api import sync_playwright

APP = pathlib.Path(__file__).resolve().parent.parent
OUT = APP / "docs" / "img"
STEAM = APP.parent / "steam-guide"
LANGS = {"en": "english", "ru": "russian", "pt-BR": "brazilianportuguese", "pt": "portuguese", "es": "spanish", "fr": "french",
         "de": "german", "it": "italian", "nl": "dutch", "pl": "polish", "ja": "japanese", "ko": "korean",
         "zh-CN": "simplifiedchinese", "zh-TW": "traditionalchinese"}
PAGES = [("recipes", "#/recipes"), ("nanites", "#/nanites"), ("cooking", "#/cooking"), ("tree-picker", "#/tree"),
         ("tree", "#/tree/STELLAR2"), ("wiki", "#/wiki"), ("portals", "#/portals"), ("multitools", "#/multitools"),
         ("inventory", "#/inventory")]
# The pages of the desktop program: "settings" is the Wiki with the settings menu open.
LAUNCHER_PAGES = [("planets", "#/planets"), ("settings", "#/wiki?item=YELLOW2")]
# The Steam guide's pictures, in the order of its text: (page name, file name).
STEAM_ORDER = [("recipes", "01-recipes"), ("tree", "02-tree"), ("cooking", "03-cooking"), ("nanites", "04-nanites"),
               ("portals", "05-portals"), ("planets", "06-planets"), ("wiki", "07-wiki"), ("inventory", "08-inventory"),
               ("multitools", "09-multitools"), ("settings", "10-settings")]
# What My items shows: item names (English, as in data.json) and how many.
INVENTORY = {"Ammonia": 3, "Copper": 12, "Nitrogen": 5, "Chromatic Metal": 40, "Gold": 25, "Silver": 18, "Platinum": 9,
             "Antimatter": 2, "Warp Cell": 6, "Nanite Cluster": 150, "Pure Ferrite": 60, "Condensed Carbon": 22, "Sodium": 100,
             "Oxygen": 80, "Carbon": 45, "Indium": 14, "Cadmium": 8, "Emeril": 11}


def serve_dist() -> str:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(APP / "dist"))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}/"


def start_program(port: int) -> subprocess.Popen:
    """The desktop program, without its window, on its own port; it believes itself the version in NMS_SHOTS_VERSION (so Settings
    shows "you have the latest version"), the last release by default."""
    version = os.environ.get("NMS_SHOTS_VERSION")
    if not version:
        tag = subprocess.run(["git", "describe", "--tags", "--abbrev=0"], cwd=APP, capture_output=True, text=True).stdout.strip()
        version = tag.lstrip("v") or "0.0.0"
    env = {**os.environ, "NMS_CRAFTING_GUIDE_VERSION": version, "PYTHONUTF8": "1"}
    python = os.environ.get("NMS_LAUNCHER_PYTHON", sys.executable)
    proc = subprocess.Popen([python, str(APP / "desktop" / "nms_crafting_guide.py"), "--server", "--port", str(port)], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/saves", timeout=2).read()
            return proc
        except OSError:
            time.sleep(0.5)
    proc.kill()
    raise SystemExit("the desktop program did not come up")


def clean(report: dict) -> dict:
    """The save's report with what is the player's own left out: a planet or system the player gave a name (the save holds it, so it is
    not the game's), the names of bases, ships and exocraft. The pages then show only names the game made up itself."""
    report = dict(report)
    report["planets"] = [{**p, "bases": ["" for _ in p.get("bases", [])]} for p in report.get("planets", [])
                         if p.get("name_source") != "save" and p.get("system_name_source") != "save"]
    report["containers"] = []
    return report


def serve_cleaned(upstream: int) -> str:
    """A server in front of the desktop program that passes everything on and cleans the save's report on the way (clean()). (Chrome's
    request interception, page.route, fails in the Playwright of this script's era, so the page is pointed at this instead.)"""
    class Proxy(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def forward(self, method: str) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) if method == "POST" else None
            request = urllib.request.Request(f"http://127.0.0.1:{upstream}{self.path}", data=body, method=method,
                                             headers={"Origin": f"http://127.0.0.1:{upstream}"})
            try:
                with urllib.request.urlopen(request, timeout=300) as res:
                    status, kind, data = res.status, res.headers.get("Content-Type", "application/octet-stream"), res.read()
            except urllib.error.HTTPError as err:
                status, kind, data = err.code, err.headers.get("Content-Type", "text/plain"), err.read()
            if self.path.startswith("/api/save?") and status == 200:
                data = json.dumps(clean(json.loads(data)), ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self.forward("GET")

        def do_POST(self):
            self.forward("POST")

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}/"


def shoot(page, base: str, route: str, name: str) -> bytes:
    page.goto(base + route)
    page.reload()
    page.wait_for_load_state("networkidle")
    if name == "planets":
        page.wait_for_selector("tbody tr", timeout=120000)  # the save is read and the planets worked out first (the first read is slow)
    if name == "settings":
        page.click("#theme")
        time.sleep(1.0)
        page.wait_for_selector(".panel:not([hidden])")
        time.sleep(2.0)  # the update check answers
    else:
        time.sleep(4.0 if name == "planets" else 3.0 if name.startswith("tree") else 2.0)  # the trees and the globe draw themselves
    return page.screenshot()


def main(args: list[str]) -> None:
    steam = "--steam" in args
    launcher = "--no-launcher" not in args
    only = [a for a in args if not a.startswith("--")]
    dist = serve_dist()
    program = start_program(18890) if launcher else None
    cleaned = serve_cleaned(18890) if launcher else ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            probe = browser.new_page()
            items = probe.request.get(dist + "data.json").json()["items"]
            probe.close()
            inv = {k: INVENTORY[v["name"]] for k, v in items.items() if v["name"] in INVENTORY}
            for code, game in LANGS.items():
                want_steam = steam and code == "en"
                if only and code not in only and not (want_steam and not only):
                    continue
                ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1, color_scheme="dark")
                ctx.add_init_script(
                    f"localStorage.setItem('nms-items:lang', JSON.stringify({json.dumps(game)}));"
                    "localStorage.setItem('nms-items:theme', JSON.stringify('dark'));"
                    f"localStorage.setItem('nms-items:inventory', JSON.stringify({json.dumps(inv)}));")
                page = ctx.new_page()
                shots: dict[str, bytes] = {}
                for name, route in PAGES:
                    shots[name] = shoot(page, dist, route, name)
                if program:
                    for name, route in LAUNCHER_PAGES:
                        shots[name] = shoot(page, cleaned, route, name)
                if not only or code in only:
                    folder = OUT if code == "en" else OUT / code
                    folder.mkdir(parents=True, exist_ok=True)
                    for name, png in shots.items():
                        Image.open(io.BytesIO(png)).convert("RGB").save(folder / f"site-{name}.webp", "WEBP", quality=82)
                if want_steam:
                    folder = STEAM / "images-en"
                    folder.mkdir(parents=True, exist_ok=True)
                    for name, file in STEAM_ORDER:
                        if name in shots:
                            Image.open(io.BytesIO(shots[name])).convert("RGB").save(folder / f"{file}.jpg", "JPEG", quality=88)
                print(code, "done", flush=True)
                ctx.close()
            browser.close()
    finally:
        if program:
            program.kill()


if __name__ == "__main__":
    main(sys.argv[1:])
