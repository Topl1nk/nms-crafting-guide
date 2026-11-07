"""The game's own pictures, taken from the player's install with one call: the item icons, the pictures of the storage places and
the sign of units, written as webp files into pictures/icons/, which the launcher serves at /icons/ (launch.py). Nothing of the game
is kept anywhere else, and nothing is sent anywhere.

    python tools/pictures.py            # install (or update) from the game found
    python tools/pictures.py --status   # what is installed and where the game is

The steps: find the game (NMS_GAME_DIR, Steam's libraries, the GOG folder); read the game's item tables, which gives the picture of
every item (app/scripts/extract_game.py, with MBINCompiler); take those pictures out of the game's .pak archives with hgpaktool; turn
them from the game's texture format into webp.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

ICONS = paths.ICONS
RAW = paths.CACHE / "pictures_raw"
DONE_MARK = paths.PICTURES / "complete"  # written when an installation ran to its end; without it the pictures may be a part
TABLES = paths.CACHE / "game" / "json"  # where scripts/extract_game.py writes, given NMS_CACHE
UI = "textures/ui/frontend/icons/"
CHUNK = 250  # names to a hgpaktool run (about 18 000 characters of command line; Windows allows 32 000)

# The pictures that are not an item's: line key -> the game's own picture of that place (the keys are those of site/src/lib/store.js).
PLACES = {
    **{f"STORE_{n}": f"{UI}buildable/buildable.container.{n}.dds" for n in range(10)},
    "STORE_exosuit": f"{UI}categories/invcat.exosuit.dds",
    "STORE_processor": f"{UI}categories/invcat.cooking1.dds",
    "STORE_cold": f"{UI}categories/invcat.hovercraft.dds",
    "STORE_exocraft": f"{UI}categories/invcat.car.dds",
    "STORE_ship": f"{UI}categories/invcat.ship.dds",
    "STORE_freighter": f"{UI}categories/invcat.freighter.dds",
    "STORE_act_discard": f"{UI}buildable/bazaar.compostbin.dds",
    "UNITS": f"{UI}substances/currency.units.dds",
}

state = {"state": "idle", "step": "", "done": 0, "total": 0, "error": ""}
_lock = threading.Lock()


def find_game() -> Path | None:
    """The No Man's Sky install: NMS_GAME_DIR, then each Steam library, then GOG's usual places."""
    candidates = []
    if os.environ.get("NMS_GAME_DIR"):
        candidates.append(Path(os.environ["NMS_GAME_DIR"]))
    remembered = paths.PICTURES / "game_dir.txt"
    if remembered.exists():
        candidates.append(Path(remembered.read_text(encoding="utf-8").strip()))
    if os.name != "nt":  # Steam on Linux (the game runs under Proton, its files are the same)
        home = Path.home()
        for steam in (home / ".local/share/Steam", home / ".steam/steam", home / ".var/app/com.valvesoftware.Steam/.local/share/Steam"):
            vdf = steam / "steamapps" / "libraryfolders.vdf"
            if vdf.exists():
                for lib in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8", errors="replace")):
                    candidates.append(Path(lib) / "steamapps" / "common" / "No Man's Sky")
            candidates.append(steam / "steamapps" / "common" / "No Man's Sky")
    for base in filter(None, (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES"))):
        vdf = Path(base) / "Steam" / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            for lib in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8", errors="replace")):
                candidates.append(Path(lib.replace("\\\\", "\\")) / "steamapps" / "common" / "No Man's Sky")
        candidates.append(Path(base) / "Steam" / "steamapps" / "common" / "No Man's Sky")
        candidates.append(Path(base) / "GOG Galaxy" / "Games" / "No Man's Sky")
    candidates.append(Path("C:/GOG Games/No Man's Sky"))
    return next((p for p in candidates if (p / "GAMEDATA" / "PCBANKS").is_dir()), None)


def installed() -> int:
    return len(list(ICONS.glob("*.webp"))) if ICONS.is_dir() else 0


def status() -> dict:
    game = find_game()
    return {"game": str(game) if game else "", "have": installed(), "complete": DONE_MARK.exists(), **state}


def _say(step: str, done: int = 0, total: int = 0) -> None:
    state.update(step=step, done=done, total=total)


def _hgpaktool() -> list[str]:
    return paths.self_command("hgpaktool")


def tool_env(game: Path) -> dict:
    """The environment the game-reading helper tools (extract, langs) are started with."""
    return {**os.environ, "NMS_GAME_DIR": str(game), "MBINCOMPILER": str(paths.mbincompiler()),
            "NMS_CACHE": str(paths.CACHE), "NMS_HGPAKTOOL": json.dumps(_hgpaktool()), "PYTHONUTF8": "1"}


def tables(game: Path, force: bool = False) -> None:
    """The game's item tables, read out of its archives into the cache (once, unless forced)."""
    if force or not (TABLES / "Substance_Table.json").exists():
        run = subprocess.run([*paths.self_command("extract"), "--game", str(game), "all"],
                             capture_output=True, text=True, env=tool_env(game))
        if run.returncode:
            raise RuntimeError((run.stdout + run.stderr)[-400:])


def install(force: bool = False) -> None:
    """The whole job, in this thread; `state` says how far it has got."""
    from PIL import Image

    game = find_game()
    if game is None:
        raise RuntimeError("game not found")
    paths.PICTURES.mkdir(parents=True, exist_ok=True)
    (paths.PICTURES / "game_dir.txt").write_text(str(game), encoding="utf-8")

    DONE_MARK.unlink(missing_ok=True)
    _say("tables")
    tables(game, force)

    want: dict[str, list[str]] = {}  # lower-case dds path -> the names it is saved under
    for table in ("Substance_Table.json", "Product_Table.json"):
        for item_id, row in json.loads((TABLES / table).read_text(encoding="utf-8")).items():
            icon = (row.get("Icon_Filename") or "").lower()
            if icon:
                want.setdefault(icon, []).append(item_id)
    for name, path in PLACES.items():
        want.setdefault(path.lower(), []).append(name)

    _say("listing")
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([*_hgpaktool(), "-L", "-p", str(game / "GAMEDATA" / "PCBANKS")], cwd=tmp, check=True, capture_output=True)
        listing = (Path(tmp) / "filenames.txt").read_text(errors="replace").splitlines()
    found: dict[str, list[str]] = {}
    pak = ""
    for line in listing:
        if line.startswith("Listing "):
            pak = line.removeprefix("Listing ").strip()
        elif line.strip().lower() in want:
            found.setdefault(pak, []).append(line.strip())

    RAW.mkdir(parents=True, exist_ok=True)
    ICONS.mkdir(parents=True, exist_ok=True)
    total = sum(len(set(v)) for v in found.values())
    done = 0
    _say("pictures", 0, total)
    for pak, names in found.items():
        names = sorted(set(names))
        for start in range(0, len(names), CHUNK):  # a short command line, but few runs: each one reads the archive's index again
            chunk = names[start:start + CHUNK]
            args = [*_hgpaktool(), "-U", "-O", str(RAW)]
            for name in chunk:
                args += ["-f", name]
            run = subprocess.run([*args, pak], capture_output=True, text=True)
            if run.returncode:
                raise RuntimeError((run.stdout + run.stderr)[-400:])
            for name in chunk:
                src = RAW / name
                if not src.is_file():
                    continue
                try:
                    with Image.open(src) as im:
                        im = im.convert("RGBA")
                        im.thumbnail((128, 128))
                        for out in want[name.lower()]:
                            im.save(ICONS / f"{out}.webp", quality=85, method=4)  # method 6 is 60 times slower for 6% less
                except Exception:  # noqa: BLE001 - one picture that cannot be read is left out
                    pass
            done += len(chunk)
            _say("pictures", done, total)
    DONE_MARK.write_text("1", encoding="utf-8")
    _say("done", total, total)


def start(force: bool = False) -> bool:
    """Begin the job in the background; False when one is already running."""
    with _lock:
        if state["state"] == "running":
            return False
        state.update(state="running", step="find", done=0, total=0, error="")

    def work() -> None:
        try:
            install(force)
            state["state"] = "done"
        except Exception as exc:  # noqa: BLE001 - shown in the page
            state.update(state="error", error=f"{exc}")
    threading.Thread(target=work, daemon=True).start()
    return True


if __name__ == "__main__":
    if "--status" in sys.argv:
        print(json.dumps(status(), indent=1))
    else:
        start("--force" in sys.argv)
        import time
        while state["state"] == "running":
            time.sleep(1)
            print(state["step"], state["done"], "/", state["total"])
        print(json.dumps(status(), indent=1))
        sys.exit(0 if state["state"] == "done" else 1)
