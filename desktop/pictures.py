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
SET = "6"  # which set of pictures the installation takes (raise it when PLACES gains a picture): an older mark means "install again"
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

# The grey layers the game builds a planet's globe of on its Discoveries page (it tints them in code, so each globe is composed here).
GLOBE = "textures/ui/frontend/components/discovery/planets."
GLOBE_LAYERS = [f"{GLOBE}{n}.dds" for n in ("7.terrain", "7.water", "7.continents", "7.clouds", "7.shadow", "7.innerglow", "outerglow", "water.full", "gasgiant.1", "gasgiant.1.clouds")]
# Colours of the terrain, the water and the rim, one globe for each kind of planet. They are our reading of what each type looks like.
GLOBES = {
    "Lush": ((110, 160, 70), (60, 130, 210), (150, 205, 255)),
    "Toxic": ((160, 175, 50), (190, 215, 70), (210, 235, 90)),
    "Scorched": ((200, 120, 60), (230, 90, 40), (255, 170, 90)),
    "Radioactive": ((200, 160, 70), (215, 35, 40), (190, 240, 100)),  # red water: seen on a radioactive planet in the game
    "Frozen": ((205, 225, 245), (140, 195, 240), (200, 235, 255)),
    "Barren": ((195, 155, 115), None, (230, 190, 140)),
    "Dead": ((130, 130, 140), None, (180, 180, 190)),
    "Weird": ((175, 95, 205), (60, 205, 205), (210, 150, 255)),
    "Swamp": ((95, 125, 60), (80, 110, 50), (160, 200, 110)),
    "Lava": ((95, 55, 45), (255, 100, 25), (255, 140, 60)),
    "Waterworld": ((60, 120, 190), (50, 110, 210), (140, 200, 255)),
    "Red": ((195, 80, 70), (230, 140, 90), (255, 140, 120)),
    "Green": ((80, 170, 90), (150, 220, 100), (150, 240, 160)),
    "Blue": ((70, 110, 205), (110, 200, 240), (140, 180, 255)),
    "GasGiant": ((205, 165, 115), None, (240, 210, 160)),
}


def _globes() -> None:
    """One picture of a globe for each kind of planet, laid together of the game's grey layers."""
    from PIL import Image, ImageChops

    def layer(name: str):
        return Image.open(RAW / f"{GLOBE}{name}.dds").convert("RGBA")

    def tint(im, rgb, alpha=1.0, lift=150):
        r, g, b, a = im.split()
        gray = im.convert("L").point(lambda v: min(255, int(lift + v * (255 - lift) / 255 * 0.9 + v * 0.0)))
        out = ImageChops.multiply(Image.merge("RGB", (gray, gray, gray)), Image.new("RGB", im.size, rgb))
        out.putalpha(a.point(lambda v: int(v * alpha)))
        return out

    shadow = layer("7.shadow")
    def mix(rgb, other, k):
        return tuple(int(c * (1 - k) + o * k) for c, o in zip(rgb, other))

    for name, (land, water, rim) in GLOBES.items():
        # In the game the ground stays near its own grey-brown; the colour of the type shows in the water layer and the rim is pale.
        land = land if name == "GasGiant" else mix(land, (205, 190, 175), 0.65)
        rim = mix(rim, (255, 255, 255), 0.7)
        if name == "GasGiant":
            globe = tint(layer("gasgiant.1"), land)
            globe.alpha_composite(tint(layer("gasgiant.1.clouds"), (255, 255, 255), 0.6))
            globe = globe.crop(globe.getbbox())  # this one is drawn smaller on its canvas than the others
            globe.thumbnail((128, 128))
            globe.save(ICONS / f"GLOBE_{name}.webp", quality=85, method=4)
            continue
        else:
            globe = tint(layer("7.terrain"), land, lift=60)
            if name == "Waterworld":  # the sea covers all of it (the small set's "full water", drawn larger to fit)
                sea = layer("water.full").crop((120, 120, 392, 392)).resize(globe.size, Image.LANCZOS)
                globe.alpha_composite(tint(sea, water, 0.85))
            elif water:
                globe.alpha_composite(tint(layer("7.water"), water))
            globe.alpha_composite(tint(layer("7.continents"), land, 0.6, lift=60))
            globe.alpha_composite(tint(layer("7.clouds"), (255, 255, 255), 0.7, lift=235))
        shade = Image.new("RGBA", globe.size, (0, 0, 10, 0))
        shade.putalpha(shadow.split()[3].point(lambda v: int(v * 0.65)))
        globe.alpha_composite(shade)
        globe.alpha_composite(tint(layer("7.innerglow"), rim))
        halo = layer("outerglow").crop((105, 105, 408, 408)).resize((int(512 * 303 / 272), int(512 * 303 / 272)), Image.LANCZOS)
        canvas = Image.new("RGBA", halo.size, (0, 0, 0, 0))
        canvas.alpha_composite(tint(halo, rim, 0.8))  # the halo round the globe
        canvas.alpha_composite(globe, ((halo.width - 512) // 2, (halo.height - 512) // 2))
        globe = canvas
        globe.thumbnail((128, 128))
        globe.save(ICONS / f"GLOBE_{name}.webp", quality=85, method=4)

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
    _globes()
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
