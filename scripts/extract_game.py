"""Extract the recipe, product and substance tables from the installed game.

This replaces the dependency on NMS-Handbook, which publishes the same tables
as JSON but only as often as someone gets round to it. The game files are the
original; reading them directly means a patch can be picked up the day it
lands, and the version the data came from is known exactly.

Three stages, each runnable on its own so a failure can be retried alone:

  unpack     hgpaktool pulls the few .MBIN files needed out of the game's
             HGPAK archives into .cache/game/mbin/
  decompile  MBINCompiler turns them into MXML in .cache/game/mxml/, and this
             script refuses to go on if it did not recognise every file --
             MBINCompiler itself only warns and exits 0 on a version mismatch
  convert    the MXML is parsed (stdlib xml) into .cache/game/json/, in the
             same shape as the NMS-Handbook JSON, so build_data.py stays the
             one place that normalises recipes whichever source fed it

`version` prints the installed game's version and build next to the pinned
MBINCompiler, and checks that the compiler still reads this build's tables.

Nothing is written inside the game install. Extracted game files stay in
.cache/game/ (gitignored); only the normalised data/*.json is committed.

    uv run python scripts/extract_game.py [--game DIR] {version,unpack,decompile,convert,all}

The game directory defaults to $NMS_GAME_DIR, then the GOG install below.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "game"
MBIN_DIR = CACHE / "mbin"
MXML_DIR = CACHE / "mxml"
JSON_DIR = CACHE / "json"

DEFAULT_GAME = Path.home() / "Games" / "No Man's Sky"
GOG_GAME_ID = "1446213994"

TABLES = "metadata/reality/tables"
RECIPES = f"{TABLES}/nms_reality_gcrecipetable"
PRODUCTS = f"{TABLES}/nms_reality_gcproducttable"
SUBSTANCES = f"{TABLES}/nms_reality_gcsubstancetable"
# Item names live in a dozen numbered language tables (one per content
# update), and which table holds which string is not predictable, so all of
# the English ones are read. "english" is UK English: Ionised, Faecium.
LANG = os.environ.get("NMS_LANG", "english").lower()
LANGUAGE_GLOB = f"language/nms_*_{LANG}.mbin"

PAK_FILTERS = [f"{RECIPES}.mbin", f"{PRODUCTS}.mbin", f"{SUBSTANCES}.mbin",
               "language/nms_*_english.mbin", LANGUAGE_GLOB]


def game_path(arg: str | None = None) -> Path:
    return Path(arg or os.environ.get("NMS_GAME_DIR") or DEFAULT_GAME)


def find_game(arg: str | None = None) -> Path | None:
    """The install, or None when there is none (CI, a machine without it)."""
    path = game_path(arg)
    return path if (path / "GAMEDATA" / "PCBANKS").is_dir() else None


def game_dir(arg: str | None) -> Path:
    path = find_game(arg)
    if path is None:
        sys.exit(f"no GAMEDATA/PCBANKS under {game_path(arg)}\n"
                 "Point --game or $NMS_GAME_DIR at the No Man's Sky install.")
    return path


# --- MXML parsing -------------------------------------------------------------

def mxml_value(el: ET.Element):
    """One MXML <Property> as plain Python.

    MXML has three shapes, told apart by the `value` attribute:
      leaf    <Property name="X" value="1" />                    -> "1"
      struct  <Property name="X" value="GcType"> children        -> dict
      list    <Property name="X"> children all also named X       -> list
    The struct test has to come first: an enum wrapper such as
    <Property name="Rarity" value="GcRarity"><Property name="Rarity" .../>
    looks like a one-item list by name alone. A childless property with no
    value is an empty list or struct; None covers both.
    """
    children = list(el)
    if not children:
        return el.get("value")
    name = el.get("name")
    if el.get("value") is None and all(c.get("name") == name for c in children):
        return [mxml_value(c) for c in children]
    return {c.get("name"): mxml_value(c) for c in children}


def parse_mxml(path: Path) -> tuple[str, dict]:
    """(template, top-level fields) of one MXML file."""
    root = ET.parse(path).getroot()
    return root.get("template", ""), {c.get("name"): mxml_value(c) for c in root}


def enum(value) -> str:
    """The member name inside an enum wrapper, e.g. {"Rarity": "Common"}."""
    if isinstance(value, dict):
        return next(iter(value.values()), "") or ""
    return value or ""


def load_language(paths: list[Path], target: str | None = None) -> dict[str, str]:
    # English is always read: an id with no English text is not a real item
    # (UI strings, hidden entries) and the app drops it, so it must stay
    # empty in another language too.
    target = (target or LANG).lower()
    english: dict[str, str] = {}
    local: dict[str, str] = {}
    for path in paths:
        lang = path.stem.rsplit("_", 1)[-1].lower()
        if lang not in ("english", target):
            continue
        _, top = parse_mxml(path)
        for entry in top.get("Table") or []:
            if lang == "english":
                english[entry["Id"]] = entry.get("English") or ""
            if lang == target:
                # The column is the language's name in the game's own casing
                # ("Russian", "BrazilianPortuguese"): find it, do not guess it.
                column = next((k for k in entry if k.lower() == target), "")
                local[entry["Id"]] = entry.get(column) or ""
    if target == "english":
        return english
    # English rides along under "en:<id>": the storage rules match English subtitles.
    return {**{key: (local.get(key) or value) if value else "" for key, value in english.items()},
            **{f"en:{key}": value for key, value in english.items()}}


# --- conversion to the NMS-Handbook shape --------------------------------------
#
# Only the fields build_data.py reads, plus the loc keys beside their text so a
# wrong lookup can be traced. Values stay strings, as upstream had them: the
# normaliser already parses them, and this keeps the two sources identical.

def _texts(row: dict, lang: dict[str, str], *keys: str) -> dict[str, str]:
    out = {}
    for key in keys:
        loc = row.get(key) or ""
        out[key] = loc
        out[f"{key}_Text"] = lang.get(loc, "") if loc else ""
    return out


def hex_colour(c) -> str:
    """The game's {R,G,B,A} floats as #rrggbb (the colour an item is tinted with in the UI)."""
    try:
        return "#" + "".join(f"{round(min(1.0, max(0.0, float(c[k]))) * 255):02x}" for k in "RGB")
    except (TypeError, KeyError, ValueError):
        return ""


def _common(row: dict, lang: dict[str, str]) -> dict:
    return {
        "Colour_Hex": hex_colour(row.get("Colour")),
        **_texts(row, lang, "Name", "NameLower", "Subtitle", "Description", "Symbol"),
        "Subtitle_Text_En": lang.get(f"en:{row.get('Subtitle') or ''}", ""),
        "BaseValue": row.get("BaseValue", "0"),
        "Category": enum(row.get("Category")),
        "Rarity": enum(row.get("Rarity")),
        "Legality": enum(row.get("Legality")),
        "CookingIngredient": row.get("CookingIngredient", "false"),
        "Icon_Filename": (row.get("Icon") or {}).get("Filename", ""),
    }


def convert_substances(table: list[dict], lang: dict[str, str]) -> dict:
    return {row["ID"]: _common(row, lang) for row in table}


def convert_products(table: list[dict], lang: dict[str, str]) -> dict:
    products = {}
    for row in table:
        stat = enum(row.get("FoodBonusStat"))
        products[row["ID"]] = {
            **_common(row, lang),
            "Type": enum(row.get("Type")),
            "Consumable": row.get("Consumable", "false"),
            "CookingValue": row.get("CookingValue", "0"),
            "FoodBonusStatType": stat,
            # The stat's display name is a loc string keyed by the enum name
            # itself: Suit_Protection -> SUIT_PROTECTION -> "Hazard
            # Protection Battery".
            "FoodBonusStatTypeText": (
                "" if stat in ("", "Unspecified") else lang.get(stat.upper(), stat)),
            "WikiCategory": row.get("WikiCategory", ""),
            "IsCraftable": row.get("IsCraftable", "false"),
        }
    return products


def convert_recipes(table: list[dict], lang: dict[str, str], items: dict) -> tuple[dict, dict]:
    """(refining, cooking), each keyed by output id with the recipes nested.

    The game keeps one flat list with a Cooking flag; upstream split it in two
    and grouped by output, so this does the same, keeping the game's order.
    """
    refining: dict[str, dict] = {}
    cooking: dict[str, dict] = {}
    for row in table:
        result = row["Result"]
        out_id = result["Id"]
        target = cooking if row.get("Cooking") == "true" else refining
        if out_id not in target:
            item = items.get(out_id, {})
            target[out_id] = {
                "ProductID": out_id,
                **{k: item.get(k, "") for k in (
                    "Name", "Name_Text", "NameLower", "NameLower_Text",
                    "Subtitle", "Subtitle_Text", "Subtitle_Text_En", "Description", "Description_Text")},
                "Recipes": [],
            }
        target[out_id]["Recipes"].append({
            "RecipeId": row.get("Id", ""),
            "RecipeType": lang.get(row.get("RecipeType") or "", ""),
            "RecipeName": lang.get(row.get("RecipeName") or "", ""),
            "TimeToMake": row.get("TimeToMake", "0"),
            "Amount": result.get("Amount", "1"),
            "Ingredients": [
                {
                    "Id": ing["Id"],
                    "Type": enum(ing.get("Type")),
                    "NameLower_Text": items.get(ing["Id"], {}).get("NameLower_Text", ""),
                    "Amount": ing.get("Amount", "1"),
                }
                for ing in row.get("Ingredients") or []
            ],
        })
    return refining, cooking


def convert(mxml_dir: Path, out_dir: Path, source: dict | None = None) -> dict[str, int]:
    """MXML in, the four NMS-Handbook-shaped tables out. Returns row counts."""
    lang_paths = sorted((mxml_dir / "language").glob("*.MXML"))
    if not lang_paths:
        sys.exit(f"no language tables in {mxml_dir / 'language'} - run the decompile stage")
    lang = load_language(lang_paths)

    def table(stem: str, template: str) -> list[dict]:
        path = mxml_dir / f"{stem}.MXML"
        if not path.exists():
            sys.exit(f"missing {path} - run the decompile stage")
        found, top = parse_mxml(path)
        if found != template:
            sys.exit(f"{path.name}: expected template {template}, got {found!r}")
        return top.get("Table") or []

    substances = convert_substances(table(SUBSTANCES, "cGcSubstanceTable"), lang)
    products = convert_products(table(PRODUCTS, "cGcProductTable"), lang)
    # Substances win on an id collision, matching build_data.build_items.
    items = {**products, **substances}
    refining, cooking = convert_recipes(table(RECIPES, "cGcRecipeTable"), lang, items)

    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "Substance_Table.json": substances,
        "Product_Table.json": products,
        "Refining_Table.json": refining,
        "Cooking_Table.json": cooking,
    }
    for name, data in outputs.items():
        (out_dir / name).write_text(json.dumps(data, indent=1, ensure_ascii=False))
    if source is not None:
        (out_dir / "_source.json").write_text(json.dumps(source, indent=1))
    return {
        "substances": len(substances),
        "products": len(products),
        "refining": sum(len(r["Recipes"]) for r in refining.values()),
        "cooking": sum(len(r["Recipes"]) for r in cooking.values()),
    }


# --- version detection -----------------------------------------------------------

def exe_build(game: Path) -> str:
    """The build number from NMS.exe's version resource, e.g. "180836".

    Hello Games set FileVersion to the build number, which is the same on
    Steam and GOG, so this works for either install.
    """
    exe = game / "Binaries" / "NMS.exe"
    if not exe.exists():
        return ""
    data = exe.read_bytes()
    key = "ProductVersion\0".encode("utf-16-le")
    at = data.rfind(key)
    if at < 0:
        return ""
    tail = data[at + len(key): at + len(key) + 80].decode("utf-16-le", "ignore")
    return tail.lstrip("\0").split("\0", 1)[0].strip()


def gog_build_id(game: Path) -> str:
    info = game / f"goggame-{GOG_GAME_ID}.info"
    if not info.exists():
        return ""
    return str(json.loads(info.read_text()).get("buildId", ""))


def gog_version_name(build_id: str) -> str:
    """GOG's own label for a build, e.g. "7.06_Cosmos_180836". Online, best effort.

    The install records only an opaque build id; the release name ("7.06",
    "Cosmos") is on GOG's content service. Offline this returns "" and the
    exe's build number has to do.
    """
    if not build_id:
        return ""
    url = (f"https://content-system.gog.com/products/{GOG_GAME_ID}"
           "/os/windows/builds?generation=2")
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            builds = json.load(resp).get("items", [])
    except Exception:  # noqa: BLE001 - offline is a normal case, not an error
        return ""
    for build in builds:
        if str(build.get("build_id")) == build_id:
            return build.get("version_name", "")
    return ""


def game_version(game: Path) -> dict:
    build = exe_build(game)
    gog_id = gog_build_id(game)
    label = os.environ.get("NMS_GAME_VERSION") or gog_version_name(gog_id)
    # "7.06_Cosmos_180836" -> version 7.06, update Cosmos.
    match = re.match(r"(\d+\.\d+)_([A-Za-z ]+?)_(\d+)$", label)
    paks = sorted(game.glob("GAMEDATA/PCBANKS/*.pak"), key=lambda p: p.stat().st_mtime)
    return {
        "version": match.group(1) if match else "",
        "update": match.group(2) if match else "",
        "build": build or (match.group(3) if match else ""),
        "gog_build_id": gog_id,
        "label": label,
        "paks_dated": (dt.date.fromtimestamp(paks[-1].stat().st_mtime).isoformat()
                       if paks else ""),
    }


def describe(version: dict) -> str:
    name = " ".join(x for x in (version["update"], version["version"]) if x) or "unknown version"
    return f"{name}, build {version['build'] or '?'}"


# --- tools ----------------------------------------------------------------------

def mbincompiler() -> str:
    exe = os.environ.get("MBINCOMPILER") or shutil.which("MBINCompiler")
    if not exe:
        sys.exit("MBINCompiler not found. It is pinned in mise.toml: run `mise install`, "
                 "and run this through `mise run` so it is on PATH.")
    return exe


def mbincompiler_version(exe: str) -> str:
    out = subprocess.run([exe, "version"], capture_output=True, text=True).stdout
    return out.strip().removeprefix("MBINCompiler").strip()


def hgpaktool_version() -> str:
    try:
        from importlib.metadata import version
        return version("hgpaktool")
    except Exception:  # noqa: BLE001
        return ""


# --- stages -----------------------------------------------------------------------

def _hgpaktool() -> Path:
    tool = Path(sys.executable).parent / "hgpaktool"
    if not tool.exists():
        tool = tool.with_suffix(".exe")  # Windows
    if not tool.exists():
        sys.exit("hgpaktool is not installed. Run: uv sync --extra extract")
    return tool


def _run_pak(args: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run([str(_hgpaktool()), *args], capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        sys.exit(f"hgpaktool failed:\n{result.stdout}{result.stderr}")


def pak_listing(game: Path) -> list[tuple[str, str]]:
    """(archive, file inside it) for every file in the game's archives. Headers
    only, well under a second."""
    with tempfile.TemporaryDirectory(prefix="nms-paklist-") as tmp:
        _run_pak(["-L", "-p", str(game / "GAMEDATA" / "PCBANKS")], cwd=Path(tmp))
        listing = (Path(tmp) / "filenames.txt").read_text(errors="replace").splitlines()
    out, pak = [], ""
    for line in listing:
        if line.startswith("Listing "):
            pak = line.removeprefix("Listing ").strip()
        elif pak and line.strip():
            out.append((pak, line.strip()))
    return out


LANGUAGE_FILE = re.compile(r"^language/nms_loc\d+_([a-z]+)\.mbin$")


def game_languages(game: Path) -> list[str]:
    """The text languages this install ships, read from its language tables
    (language/nms_loc<N>_<language>.mbin), so a new language in a patch shows up
    without a code change. English first, then alphabetical."""
    found = {m.group(1) for _, name in pak_listing(game) if (m := LANGUAGE_FILE.match(name))}
    return sorted(found, key=lambda x: (x != "english", x))


def unpack(game: Path, dest: Path = MBIN_DIR, filters: list[str] | None = None) -> list[Path]:
    """Pull the needed .MBIN files out of the game's archives.

    Which archive carries the tables is looked up each time rather than
    hard-coded, because it moves between patches (in Cosmos the tables are in
    NMSARC.Precache.pak and the language files in NMSARC.MetadataEtc.pak).
    `filters` replaces the default file list, for the language-only unpack.
    """
    # Unpack each file from the archive that holds it: hgpaktool treats an
    # exact path filter that a .pak lacks as an error, not a non-match.
    wanted: dict[str, list[str]] = {}
    for pak, name in pak_listing(game):
        if any(fnmatch.fnmatchcase(name, f) for f in (filters or PAK_FILTERS)):
            wanted.setdefault(pak, []).append(name)

    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    for pak, names in wanted.items():
        args = ["-U", "-O", str(dest)]
        for name in sorted(set(names)):
            args += ["-f", name]
        _run_pak([*args, pak])
    files = sorted(dest.rglob("*.mbin"))
    if filters is None:
        for stem in (RECIPES, PRODUCTS, SUBSTANCES):
            if not (dest / f"{stem}.mbin").exists():
                sys.exit(f"{stem}.mbin is in none of the game's archives - "
                         "did a patch rename or move it?")
    if not any(f.parent.name == "language" for f in files):
        sys.exit("no language tables found in the game's archives")
    return files


MXML_HEADER = re.compile(r"MBINCompiler version \(([\d.]+)\)")


def decompile(src: Path = MBIN_DIR, dest: Path = MXML_DIR) -> str:
    """MBIN -> MXML, failing loudly on anything MBINCompiler did not recognise.

    A table whose struct layout changed in a patch is not an error to
    MBINCompiler: it prints "[WARN]: File not recognized", skips the file and
    exits 0. Carrying on would build data/ from whatever stale MXML was left
    behind, so dest is emptied first and every expected file is checked for.
    Returns the compiler version stamped in the MXML headers.
    """
    exe = mbincompiler()
    expected = sorted(src.rglob("*.mbin"))
    if not expected:
        sys.exit(f"nothing to decompile in {src} - run the unpack stage")
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    result = subprocess.run([exe, "-y", "-Q", "-d", str(dest), str(src)],
                            capture_output=True, text=True)
    log = result.stdout + result.stderr
    problems = [line.strip() for line in log.splitlines()
                if "[WARN]" in line or "[ERROR]" in line]
    missing = [m.relative_to(src) for m in expected
               if not (dest / m.relative_to(src)).with_suffix(".MXML").exists()]
    if result.returncode != 0 or problems or missing:
        detail = "\n  ".join(problems + [f"not decompiled: {m}" for m in missing])
        sys.exit(
            f"MBINCompiler {mbincompiler_version(exe)} could not read every table:\n  {detail}\n"
            "The game's struct layouts changed. Pin the MBINCompiler release made for "
            "this patch in mise.toml (`mise run mbin:releases`), then `mise install`.")
    tables = dest / f"{RECIPES}.MXML"  # a language-only run has no recipe table
    header = tables.read_text(encoding="utf-8")[:300] if tables.exists() else ""
    found = MXML_HEADER.search(header)
    return found.group(1) if found else ""


def compiler_reads(game: Path) -> tuple[bool, str]:
    """(True, "") if the pinned MBINCompiler reads every table this build
    ships, else (False, why). Tried on a scratch copy; nothing in .cache/game
    or the install is touched. Shared by game:version and game:update."""
    with tempfile.TemporaryDirectory(prefix="nms-probe-") as tmp:
        tmp_path = Path(tmp)
        unpack(game, tmp_path / "mbin")
        try:
            decompile(tmp_path / "mbin", tmp_path / "mxml")
        except SystemExit as exc:
            return False, str(exc)
    return True, ""


def check_versions(game: Path) -> bool:
    """Print game and compiler versions; True if the compiler reads this build.

    MBINCompiler releases are numbered after the game version they were made
    for, but a release keeps working until a patch changes a struct it
    covers, so the numbers alone do not decide it. What does is whether it
    recognises every table this pipeline reads, so that is tried here on a
    scratch copy.
    """
    version = game_version(game)
    exe = mbincompiler()
    tool = mbincompiler_version(exe)
    print(f"game          {describe(version)}  ({game})")
    if version["gog_build_id"]:
        print(f"              GOG build id {version['gog_build_id']}"
              f"{', ' + version['label'] if version['label'] else ''}")
    print(f"archives      newest .pak dated {version['paks_dated']}")
    print(f"MBINCompiler  {tool}  (pinned in mise.toml)")
    print(f"hgpaktool     {hgpaktool_version() or 'not installed (uv sync --extra extract)'}")
    numbers = re.match(r"v?(\d+\.\d+)", tool)
    if numbers and version["version"] and numbers.group(1) != version["version"]:
        print(f"note          the release is numbered for {numbers.group(1)}, the game is "
              f"{version['version']}; what matters is whether it reads the tables:")
    readable, problem = compiler_reads(game)
    if not readable:
        print(f"MISMATCH      {problem}")
        return False
    print(f"match         yes: {tool} reads every table of build {version['build']}")
    return True


def provenance(game: Path, compiler: str) -> dict:
    """What data/source.json records. `compiler` is the version stamped in the
    MXML headers, i.e. what actually decompiled these files; the release tag
    beside it is what to pin to reproduce them."""
    version = game_version(game)
    exe = os.environ.get("MBINCOMPILER") or shutil.which("MBINCompiler")
    release = mbincompiler_version(exe) if exe else ""
    return {
        "source": "game",
        "summary": (f"Game files, No Man's Sky {describe(version)}, "
                    f"extracted {dt.date.today().isoformat()}"),
        "game": version,
        "tools": {"hgpaktool": hgpaktool_version(), "MBINCompiler": compiler,
                  "MBINCompiler_release": release},
        "extracted": dt.date.today().isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("stage", choices=["version", "unpack", "decompile", "convert", "all"])
    parser.add_argument("--game", help="No Man's Sky install (default $NMS_GAME_DIR, "
                        f"else {DEFAULT_GAME})")
    args = parser.parse_args(argv)

    if args.stage == "version":
        return 0 if check_versions(game_dir(args.game)) else 1

    if args.stage in ("unpack", "all"):
        files = unpack(game_dir(args.game))
        print(f"unpacked {len(files)} files into {MBIN_DIR.relative_to(ROOT)}")

    if args.stage in ("decompile", "all"):
        compiler = decompile()
        print(f"decompiled into {MXML_DIR.relative_to(ROOT)} with MBINCompiler {compiler}")

    if args.stage in ("convert", "all"):
        header = (MXML_DIR / f"{RECIPES}.MXML")
        if not header.exists():
            sys.exit(f"missing {header} - run the decompile stage")
        found = MXML_HEADER.search(header.read_text(encoding="utf-8")[:300])
        source = provenance(game_dir(args.game), found.group(1) if found else "")
        counts = convert(MXML_DIR, JSON_DIR, source)
        print(f"converted: {counts['substances']} substances, {counts['products']} products, "
              f"{counts['refining']} refining + {counts['cooking']} cooking recipes")
        print(f"source: {source['summary']}")
        print(f"wrote {JSON_DIR.relative_to(ROOT)}. Now: mise run data:build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
