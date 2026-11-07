"""NMSii as a desktop app: a tiny local web server for the built site (dist/) and the browser's "app" mode, i.e. a plain window with
no tabs or address bar. The server stops when the window is closed. Nothing leaves this computer.

    nmsii                  open the window
    nmsii --server         no window: serve and print the address (for tests)
    nmsii --tool NAME ...  internal: run a helper in a child process (hgpaktool, extract), so the packaged program needs no Python
"""
import functools
import http.server
import json
import os
import runpy
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import paths  # noqa: E402

# A windowed program (no console) has no stdout/stderr: give the prints somewhere to go.
for _name in ("stdout", "stderr"):
    if getattr(sys, _name) is None:
        setattr(sys, _name, open(os.devnull, "w"))


def run_tool(argv: list[str]) -> int:
    """`--tool hgpaktool ARGS` is the hgpaktool command line; `--tool extract ARGS` is scripts/extract_game.py."""
    name, rest = argv[0], argv[1:]
    if os.name == "nt":  # the console programs the tools start (MBINCompiler) must not each open a window
        original = subprocess.Popen.__init__

        def quiet(self, *a, **kw):
            # A hidden console, not CREATE_NO_WINDOW: MBINCompiler (.NET) touches the console and fails when there is none.
            info = kw.get("startupinfo") or subprocess.STARTUPINFO()
            info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            info.wShowWindow = 0  # SW_HIDE
            kw["startupinfo"] = info
            original(self, *a, **kw)
        subprocess.Popen.__init__ = quiet
    if name == "hgpaktool":
        from hgpaktool.cli import run
        sys.argv = ["hgpaktool", *rest]
        run()
        return 0
    if name == "extract":
        sys.argv = [str(paths.EXTRACT_SCRIPT), *rest]
        runpy.run_path(str(paths.EXTRACT_SCRIPT), run_name="__main__")
        return 0
    if name == "langs":
        sys.argv = [str(paths.LANGS_SCRIPT), *rest]
        runpy.run_path(str(paths.LANGS_SCRIPT), run_name="__main__")
        return 0
    print(f"unknown tool {name}", file=sys.stderr)
    return 2


if len(sys.argv) > 2 and sys.argv[1] == "--tool":
    sys.exit(run_tool(sys.argv[2:]))

import languages  # noqa: E402
import nms_save  # noqa: E402
import pictures  # noqa: E402


# The window's lifetime is not the browser process's: with a profile that is already running (Edge lingers in the background
# after its window closes, or a second NMSii is started) a new msedge.exe hands its window to that process and exits at once,
# which used to stop the server under a window that was just opened. So the page itself says it is there: a ping every
# 10 s, and a beacon when it is closed. The server stops when the page has gone, whatever the browser process does.
HEARTBEAT = (b"<script>(function(){var p=function(){fetch('/api/ping',{method:'POST',keepalive:true}).catch(function(){})};"
             b"p();setInterval(p,10000);addEventListener('pagehide',function(){navigator.sendBeacon('/api/bye')})})()</script>")


class Life:
    """Whether a page is still looking at the server. Throttled background timers can slip to a minute, hence the 130 s."""

    def __init__(self):
        self.started = time.monotonic()
        self.last = None   # time of the last ping
        self.bye = None    # time of a close beacon; a reload sends one and pings again at once, which cancels it
        self.done = threading.Event()

    def ping(self):
        self.last, self.bye = time.monotonic(), None

    def goodbye(self):
        self.bye = time.monotonic()

    def watch(self):
        while not self.done.wait(1):
            now = time.monotonic()
            if "running" in (pictures.state["state"], *(s["state"] for s in languages.state.values())):
                continue  # an installation in progress is not cut off, even by a closed window
            if (self.bye is not None and now - self.bye > 5
                    or self.last is None and now - self.started > 90  # the page never came up
                    or self.last is not None and now - self.last > 130):
                break
        self.done.set()


LIFE = Life()


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path in ("/", "/index.html"):
            body = (paths.DIST / "index.html").read_bytes().replace(b"</body>", HEARTBEAT + b"</body>", 1)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if url.path == "/api/saves":
            return self.send_json(nms_save.listing())
        if url.path == "/api/save":
            # Only a file the listing itself offers: never a path from the URL.
            q = urllib.parse.parse_qs(url.query)
            want = (q.get("account", [""])[0], q.get("file", [""])[0])
            match = [f for f in nms_save.save_files() if (f.parent.name, f.name) == want]
            if not match:
                return self.send_json({"error": "no such save"}, 404)
            try:
                return self.send_json(nms_save.report(match[0]))
            except Exception as exc:  # noqa: BLE001 - shown in the page
                return self.send_json({"error": f"{type(exc).__name__}: {exc}"}, 500)
        if url.path == "/api/pictures":
            return self.send_json({**pictures.status(), "saves": len(nms_save.save_files())})
        if url.path == "/api/lang":
            return self.send_json(languages.status(urllib.parse.parse_qs(url.query).get("code", [""])[0]))
        if url.path.startswith("/lang/"):
            # The texts built from the player's game (languages.py), else what the build holds.
            name = urllib.parse.unquote(url.path.removeprefix("/lang/"))
            mine = (paths.LANGS / name).resolve()
            if mine.parent == paths.LANGS.resolve() and mine.is_file():
                body = mine.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        if url.path.startswith("/icons/"):
            # The player's own pictures first (written by pictures.py), else what the build holds.
            name = urllib.parse.unquote(url.path.removeprefix("/icons/"))
            mine = (pictures.ICONS / name).resolve()
            if mine.parent == pictures.ICONS.resolve() and mine.is_file():
                body = mine.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/webp")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        super().do_GET()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        # Only this page may ask: a page of another site cannot make the launcher read the game's files.
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin", "")
        if not host.startswith("127.0.0.1:") or (origin and origin != f"http://{host}"):
            return self.send_json({"error": "forbidden"}, 403)
        if url.path == "/api/ping":
            LIFE.ping()
            return self.send_json({})
        if url.path == "/api/bye":
            LIFE.goodbye()
            return self.send_json({})
        if url.path == "/api/lang/build":
            try:
                return self.send_json({"started": languages.start(urllib.parse.parse_qs(url.query).get("code", [""])[0])}, 202)
            except ValueError:
                return self.send_json({"error": "bad language"}, 400)
        if url.path == "/api/pictures/install":
            force = urllib.parse.parse_qs(url.query).get("force", ["0"])[0] == "1"
            return self.send_json({"started": pictures.start(force)}, 202)
        self.send_json({"error": "not found"}, 404)


def find_browser() -> str | None:
    """A Chromium-family browser, which has the "app" window mode: Edge or Chrome on Windows (Edge ships with it), whichever
    of the usual names is installed elsewhere."""
    if os.name == "nt":
        for var in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
            base = os.environ.get(var)
            if not base:
                continue
            for rel in (r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe",
                        r"BraveSoftware\Brave-Browser\Application\brave.exe"):
                path = Path(base) / rel
                if path.exists():
                    return str(path)
    for name in ("microsoft-edge", "microsoft-edge-stable", "google-chrome", "google-chrome-stable", "chromium",
                 "chromium-browser", "brave-browser", "vivaldi", "msedge", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None


def main() -> int:
    only_server = "--server" in sys.argv  # no window: for tests, prints the address
    if not (paths.DIST / "index.html").exists():
        print(f"{paths.DIST} has no site: it has not been built.", file=sys.stderr)
        return 1
    handler = functools.partial(Quiet, directory=str(paths.DIST))
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 0
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    threading.Thread(target=server.serve_forever, daemon=True).start()

    if only_server:
        print(url, flush=True)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        return 0
    browser = find_browser()
    if browser:
        paths.PROFILE.mkdir(parents=True, exist_ok=True)
        # Not waited for (see HEARTBEAT): the browser process may hand the window over and exit at once.
        subprocess.Popen([browser, f"--app={url}", f"--user-data-dir={paths.PROFILE}",
                          "--window-size=1366,860", "--no-first-run", "--no-default-browser-check"])
    else:
        webbrowser.open(url)  # no browser with an app window: a tab in the default one, which the same beacon ends
    threading.Thread(target=LIFE.watch, daemon=True).start()
    try:
        LIFE.done.wait()
    except KeyboardInterrupt:
        pass
    server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
