"""Updates of the program from its GitHub releases (https://github.com/Topl1nk/nms-crafting-guide/releases).

The program asks GitHub, in one request, which release is the latest and compares it with its own version (the VERSION file the
release build puts in the bundle, see .github/workflows/desktop.yml). Only that one request leaves the computer, and it carries
nothing about the player. Installing is a second step the player chooses, in Settings, or lets the program do by itself (the
"update automatically" switch is off until it is turned on): the installer (Windows) or the AppImage (Linux) of the release is
downloaded, its SHA-256 is checked against the digest GitHub gives for the file, and it is run. A checkout (no VERSION file) never
updates itself. NMS_CRAFTING_GUIDE_VERSION stands in for the file, for trying the page.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import paths

REPO = "Topl1nk/nms-crafting-guide"
LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
# The only place a file to run is ever taken from.
DOWNLOADS = f"https://github.com/{REPO}/releases/download/"
MIN_GAP = 600  # seconds between two asks of GitHub (it allows 60 an hour without a token)

# For trying the whole path without publishing anything: NMS_UPDATE_API names a release server on this computer (a JSON like
# GitHub's /releases/latest, files under the same address). Only a loopback address is taken; anything else is ignored.
_LOCAL = os.environ.get("NMS_UPDATE_API", "")
TESTING = _LOCAL.startswith("http://127.0.0.1:")
if TESTING:
    LATEST = _LOCAL
    DOWNLOADS = _LOCAL.split("/", 3)[0] + "//" + _LOCAL.split("/")[2] + "/"
    MIN_GAP = 0
LOCK = threading.Lock()

state = {"state": "idle", "current": "", "latest": "", "newer": False, "done": 0, "total": 0, "error": "", "checked": 0.0}
asset: dict = {}


def current_version() -> str:
    """The version this program was built as ("" for a checkout)."""
    env = os.environ.get("NMS_CRAFTING_GUIDE_VERSION")
    if env:
        return env.strip().lstrip("v")
    mark = paths.RES / "VERSION"
    return mark.read_text(encoding="utf-8").strip().lstrip("v") if mark.is_file() else ""


def parse(version: str) -> tuple[int, ...]:
    """"1.2.3" -> (1, 2, 3); "0.0.0-ab12cd3" (a build that is not a release) -> (0, 0, 0); anything else -> ()."""
    m = re.match(r"\d+(?:\.\d+)*", version or "")
    return tuple(int(x) for x in m.group(0).split(".")) if m else ()


def pick_asset(assets: list[dict]) -> dict | None:
    """The file of a release this platform installs: the Setup .exe on Windows, the AppImage on Linux."""
    want = (lambda n: n.endswith(".exe") and "Setup" in n) if os.name == "nt" else (lambda n: n.endswith(".AppImage"))
    for a in assets:
        url = a.get("browser_download_url", "")
        if want(a.get("name", "")) and url.startswith(DOWNLOADS):
            digest = a.get("digest") or ""
            return {"name": a["name"], "url": url, "size": int(a.get("size") or 0),
                    "sha256": digest.removeprefix("sha256:") if digest.startswith("sha256:") else ""}
    return None


def status() -> dict:
    with LOCK:
        cur = state["current"] or current_version()
        out = {k: v for k, v in state.items() if k != "checked"}
    # An update can only be put in place by a program that was installed (the bundle), and only when a file of the release fits
    return {**out, "current": cur, "supported": bool(cur) and (paths.FROZEN or TESTING)}


def check(force: bool = False) -> bool:
    """Ask GitHub for the latest release in the background; False when it is busy or asked a moment ago."""
    cur = current_version()
    with LOCK:
        state["current"] = cur
        if not cur or state["state"] != "idle":
            return False
        if not force and state["checked"] and time.monotonic() - state["checked"] < MIN_GAP:
            return False
        state["state"] = "checking"
        state["error"] = ""
    threading.Thread(target=_check, args=(cur,), daemon=True).start()
    return True


def _check(cur: str) -> None:
    global asset
    try:
        req = urllib.request.Request(LATEST, headers={"User-Agent": "nms-crafting-guide-updater", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=15) as res:
            release = json.load(res)
        latest = str(release.get("tag_name", "")).lstrip("v")
        found = pick_asset(release.get("assets", []))
        with LOCK:
            state["latest"] = latest
            state["newer"] = bool(found) and parse(latest) > parse(cur) > ()
            asset = found or {}
    except Exception as exc:  # noqa: BLE001 - shown in Settings; the next ask tries again
        with LOCK:
            state["error"] = f"{type(exc).__name__}: {exc}"[:200]
    finally:
        with LOCK:
            state["checked"] = time.monotonic()
            state["state"] = "idle"


def install(on_installing=None) -> bool:
    """Download the release found by check(), verify it and run it. `on_installing` is called once the installer is running (the
    program is to close then: a file in use cannot be replaced)."""
    with LOCK:
        if state["state"] != "idle" or not state["newer"] or not asset or not (paths.FROZEN or TESTING):
            return False
        state.update(state="downloading", done=0, total=asset["size"], error="")
        job = dict(asset)
    threading.Thread(target=_install, args=(job, on_installing), daemon=True).start()
    return True


def _install(job: dict, on_installing) -> None:
    try:
        folder = paths.HOME / "update"
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / job["name"]
        digest = hashlib.sha256()
        req = urllib.request.Request(job["url"], headers={"User-Agent": "nms-crafting-guide-updater"})
        with urllib.request.urlopen(req, timeout=30) as res, open(target, "wb") as out:
            while chunk := res.read(1 << 16):
                out.write(chunk)
                digest.update(chunk)
                with LOCK:
                    state["done"] += len(chunk)
        if job["sha256"] and digest.hexdigest() != job["sha256"]:
            raise ValueError("the downloaded file does not match its checksum")
        if job["size"] and target.stat().st_size != job["size"]:
            raise ValueError("the downloaded file is not complete")
        with LOCK:
            state["state"] = "installing"
        run(target)
        if on_installing:
            on_installing()
    except Exception as exc:  # noqa: BLE001
        with LOCK:
            state["error"] = f"{type(exc).__name__}: {exc}"[:200]
            state["state"] = "idle"


def run(target: Path) -> None:
    """Start the downloaded file, detached: the program closes, the installer replaces it, the new one starts."""
    if os.name == "nt":
        script = target.with_suffix(".cmd")
        # Silent: the installer closes a running copy itself (CloseApplications), and starts nothing afterwards (skipifsilent),
        # so the new program is started from here.
        script.write_text(f'@echo off\r\n"{target}" /SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS\r\nstart "" "{sys.executable}"\r\n', encoding="utf-8")
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
        subprocess.Popen(["cmd", "/c", str(script)], creationflags=flags, close_fds=True)
        return
    # An AppImage replaces itself: the file the running one came from is swapped for the new one, which is then started.
    own = os.environ.get("APPIMAGE")
    if not own:
        raise RuntimeError("not running from an AppImage")
    fresh = Path(own).with_name(Path(own).name + ".new")
    shutil.copyfile(target, fresh)
    fresh.chmod(0o755)
    os.replace(fresh, own)
    subprocess.Popen([own], start_new_session=True, close_fds=True)
