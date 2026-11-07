"""The game's item texts (names, descriptions) in the language the player picks, built from their own game on demand.

The site ships with the page's words in every language, but the item texts are Hello Games' and are not in the build. Like the
pictures (pictures.py), they are read from the installed game: one language takes about a minute, once, and is kept in
LANGS/<language>.json, which the launcher serves at /lang/ (nmsii.py).
"""
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
    run = subprocess.run([*paths.self_command("langs"), "--game", str(game), "--only", code],
                         capture_output=True, text=True, env=env)
    if run.returncode or not (paths.LANGS / f"{code}.json").is_file():
        raise RuntimeError((run.stdout + run.stderr)[-400:])


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
