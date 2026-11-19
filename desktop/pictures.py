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
SET = "7"  # which set of pictures the installation takes (raise it when PLACES gains a picture): an older mark means "install again"
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
    # the pictures of the Discoveries menu's planetary data (the Planets page): its four rows, and the three kinds of finds
    **{f"PLANET_{n}": f"{UI}discovery/planetdata.{n}.dds" for n in ("weather", "sentinels", "flora", "fauna")},
    "PLANET_resources": f"{UI}discovery/planetdata.dds",
    **{f"FIND_{n}": f"{UI}discovery/categories.{n}.dds" for n in ("flora", "fauna")},
    "FIND_mineral": f"{UI}discovery/categories.minerald.dds",
    # the game's emblem of each kind of planet (its pets' biome pictures): the name of a type here, the game's word for it there
    **{f"BIOME_{k}": f"{UI}pets/biomes/binocs.planet.{v}.dds" for k, v in (
        ("Lush", "lush"), ("Toxic", "toxic"), ("Scorched", "fire"), ("Radioactive", "radioactive"), ("Frozen", "cold"),
        ("Barren", "barren"), ("Dead", "mech"), ("Weird", "weird"))},
    "HINT_bones": f"{UI}u4products/product.bones.dds",  # the planet's "Ancient Bones" among its resources
    "PLANET_base": f"{UI}buildable/buildable.basecoreflag.dds",  # your base on a planet
    # The planet hints that are not an item: the game's pictures of the same names in its missions ("Vile Brood" and "Swarm" ones).
    # The game's own planet page keeps its mapping in the program, not in the data, so these are the nearest the files give.
    "HINT_bugs": f"{UI}missions/mission.bugbutt.on.dds",
    "HINT_swarm": f"{UI}missions/mission.swarm.on.dds",
}

# The grey layers the game builds a planet's globe of on its Discoveries page: five terrain, five water and five cloud pictures, the sea of
# a waterworld, the shadows and the glows (the game tints them in code: desktop/planet_globe.py says in what, render_globe() lays them up).
GLOBE = "textures/ui/frontend/components/discovery/planets."
GLOBE_LAYERS = ([f"{GLOBE}{kind}.{n}.dds" for kind in ("terrain", "water", "clouds") for n in range(1, 6)]
                + [f"{GLOBE}{n}.dds" for n in ("water.full", "shadow", "innerglow", "outerglow", "rings.1")])
# the layers over and under the planet and their tints (the game's own layout of the page, ui/pagediscovery/planetelement): RGB, opacity
GLOBE_OUTER = ("outerglow", (1.0, 1.0, 1.0), 0.749)
GLOBE_OVER = (("shadow", (0.1216, 0.0588, 0.0314), 0.502), ("shadow", (0.0, 0.0902, 0.1216), 0.502), ("innerglow", (0.6588, 0.8706, 0.9333), 0.702))
GLOBE_CLOUD = (0.9373, 1.0, 0.9961)
GLOBE_EXPOSURE = 1.9  # the game shows the page brighter than the plain tints: the factor that makes one globe (Ciusil) as bright as in a screenshot of it
_globes: dict[tuple, bytes] = {}


def render_globe(terrain: int, terrain_rgb, water: int, water_rgb, waterworld: bool, cloud: int, opacity: float, size: int = 128) -> bytes | None:
    """The picture of a planet's globe as the game lays it up, a webp of size x size; None where the game's pictures are not installed.
    terrain, water, cloud: which of the five pictures (water 0: no sea)."""
    key = (terrain, tuple(terrain_rgb), water, tuple(water_rgb), waterworld, cloud, round(opacity, 3), size)
    if key in _globes:
        return _globes[key]
    from io import BytesIO

    from PIL import Image, ImageChops

    def layer(name: str):
        path = RAW / f"{GLOBE}{name}.dds"
        return Image.open(path).convert("RGBA") if path.is_file() else None

    def tinted(im, rgb, alpha=1.0):
        gray = im.convert("L")
        out = ImageChops.multiply(Image.merge("RGB", (gray, gray, gray)), Image.new("RGB", im.size, tuple(min(255, round(c * 255)) for c in rgb)))
        out.putalpha(im.split()[3].point(lambda v: int(v * alpha)))
        return out

    parts = [(GLOBE_OUTER[0], GLOBE_OUTER[1], GLOBE_OUTER[2]), (f"terrain.{terrain}", terrain_rgb, 1.0)]
    if waterworld:
        parts.append(("water.full", water_rgb, 1.0))
    elif water:
        parts.append((f"water.{water}", water_rgb, 1.0))
    parts += [(f"clouds.{cloud}", GLOBE_CLOUD, opacity * 0.8), *GLOBE_OVER]  # the layout's cloud opacity (0.8) times the planet's
    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    for name, rgb, alpha in parts:
        im = layer(name)
        if im is None:
            return None
        canvas.alpha_composite(tinted(im, rgb, alpha))
    r, g, b, a = canvas.split()
    canvas = Image.merge("RGBA", ([ch.point(lambda v: min(255, round(v * GLOBE_EXPOSURE))) for ch in (r, g, b)] + [a]))
    canvas = canvas.crop((100, 100, 412, 412))  # the glow round the planet and nothing beyond it
    canvas = canvas.resize((size, size), Image.LANCZOS)
    out = BytesIO()
    canvas.save(out, "WEBP", quality=88, method=4)
    if len(_globes) > 2000:
        _globes.clear()
    _globes[key] = out.getvalue()
    return _globes[key]


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
    done = DONE_MARK.exists() and DONE_MARK.read_text(encoding="utf-8").strip() == SET
    return {"game": str(game) if game else "", "have": installed(), "complete": done, **state}


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
    for path in GLOBE_LAYERS:
        want.setdefault(path, [])  # taken out for the globes, not kept as pictures of their own

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
    DONE_MARK.write_text(SET, encoding="utf-8")
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
