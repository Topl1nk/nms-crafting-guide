"""The game's item texts (names, descriptions) in the language the player picks, built from their own game on demand.

The site ships with the page's words in every language, but the item texts are Hello Games' and are not in the build. Like the
pictures (pictures.py), they are read from the installed game: one language takes about a minute, once, and is kept in
LANGS/<language>.json, which the launcher serves at /lang/ (nms_crafting_guide.py).
"""
import json
import os
import re
import subprocess
import threading
import time

import paths
import pictures

state: dict[str, dict] = {}  # language -> {"state": "running" | "done" | "error", "error": ""}
_lock = threading.Lock()


def status(code: str) -> dict:
    return {"have": (paths.LANGS / f"{code}.json").is_file(), **state.get(code, {"state": "idle", "error": ""})}


def _build(code: str) -> None:
    game = pictures.find_game()
    if game is None:
        raise RuntimeError("game not found")
    while pictures.state["state"] == "running":  # both read the same cache: one at a time
        time.sleep(1)
    pictures.tables(game)
    paths.LANGS.mkdir(parents=True, exist_ok=True)
    env = {**pictures.tool_env(game), "NMS_LANG_OUT": str(paths.LANGS.parent)}
    # Below normal priority: a language is built while the player uses the program, or the game.
    low = subprocess.BELOW_NORMAL_PRIORITY_CLASS if os.name == "nt" else 0
    run = subprocess.run([*paths.self_command("langs"), "--game", str(game), "--only", code],
                         capture_output=True, text=True, env=env, creationflags=low)
    if run.returncode or not (paths.LANGS / f"{code}.json").is_file():
        raise RuntimeError((run.stdout + run.stderr)[-400:])


def codes() -> list[str]:
    """The languages worth having an item-name pack of: the ones the build lists, without the two that share another's names (US
    English reads as English, Tencent Chinese as simplified Chinese)."""
    try:
        data = json.loads((paths.DIST / "languages.json").read_text(encoding="utf-8"))
        listed, base = [l["code"] for l in data["list"]], data.get("base")
    except (OSError, ValueError, KeyError):
        listed, base = [], None
    return [c for c in listed if c not in ("usenglish", "tencentchinese", base)]  # the base language's names are the page's own


def have() -> int:
    """How many of codes() are built."""
    return sum((paths.LANGS / f"{c}.json").is_file() for c in codes())


def names() -> dict:
    """Every item's names in all the languages that are built, for a search that does not care which language the page is in:
    {"languages": how many, "names": {item id: [name, ...]}}. Read from LANGS/<language>.json, which the page's own language
    loads the same way."""
    out: dict[str, list[str]] = {}
    for code in codes():
        try:
            items = json.loads((paths.LANGS / f"{code}.json").read_text(encoding="utf-8")).get("items", {})
        except (OSError, ValueError):
            continue
        for item, texts in items.items():
            if texts and texts[0] and texts[0] not in out.setdefault(item, []):
                out[item].append(texts[0])
    return {"languages": have(), "total": len(codes()), "names": out}


def start_all() -> bool:
    """Build every language that is not built yet, one after the other, in the background (about a minute each, once); False when
    that is already going on. Progress is in state["*"]."""
    with _lock:
        if state.get("*", {}).get("state") == "running":
            return False
        todo = [c for c in codes() if not (paths.LANGS / f"{c}.json").is_file()]
        state["*"] = {"state": "running", "error": "", "done": 0, "total": len(todo)}

    def work() -> None:
        for code in todo:
            try:
                _build(code)
            except Exception as exc:  # noqa: BLE001 - one language that fails does not stop the others
                state["*"]["error"] = f"{code}: {exc}"
            state["*"]["done"] += 1
        state["*"]["state"] = "done"
    threading.Thread(target=work, daemon=True).start()
    return True


def auto(delay: float = 60.0) -> None:
    """Passive: a minute after the program starts (when the page has had the machine to itself) the languages not built yet are built
    in the background, one after the other, at low priority, so that a name can be searched in any language without anything being
    switched on. Without the game there is nothing to build from. The program does not wait for it: closing the window ends it."""
    time.sleep(delay)
    if pictures.find_game() is not None and paths.mbincompiler().is_file():  # (a checkout without the fetched tools cannot build any)
        start_all()


def start(code: str) -> bool:
    """Begin building a language in the background; False when it is already being built."""
    if not re.fullmatch(r"[a-z]+", code):  # it ends up in a command line and a file name
        raise ValueError(code)
    with _lock:
        if state.get(code, {}).get("state") == "running":
            return False
        state[code] = {"state": "running", "error": ""}

    def work() -> None:
        try:
            _build(code)
            state[code] = {"state": "done", "error": ""}
        except Exception as exc:  # noqa: BLE001 - shown in the page
            state[code] = {"state": "error", "error": f"{exc}"}
    threading.Thread(target=work, daemon=True).start()
    return True
