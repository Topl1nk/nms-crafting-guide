"""Read the planet types (biomes) out of the installed game into data/biomes.json.

    mise run ... python scripts/build_biomes.py [--game DIR]

Two tables carry what the Planets page can say about a planet type: biomefilenames (the terrain variants each type has)
and biomelistperstartype (how likely a type is around a star of each colour). Both are unpacked and decompiled the way
extract_game.py does the recipe tables, into their own folder under .cache/ so the recipe extraction is left alone.

What the game files do NOT carry is which resources a planet has: each biome file holds only a mining category
(Fuel or Earth, Common), and the deposits themselves live in the generator's code. So nothing of that is written here.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_game as eg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "biomes.json"
WORK = eg.CACHE / "biomes"
BIOMES = "metadata/simulation/solarsystem/biomes"
FILES = [f"{BIOMES}/biomefilenames.mbin", f"{BIOMES}/biomelistperstartype.mbin"]


def unpack(game: Path) -> Path:
    wanted: dict[str, list[str]] = {}
    for pak, name in eg.pak_listing(game):
        if any(fnmatch.fnmatchcase(name, f) for f in FILES):
            wanted.setdefault(pak, []).append(name)
    if sum(len(v) for v in wanted.values()) != len(FILES):
        sys.exit("the biome tables are not where they were: check the game build and the unpack filters")
    mbin = WORK / "mbin"
    shutil.rmtree(WORK, ignore_errors=True)
    mbin.mkdir(parents=True)
    for pak, names in wanted.items():
        args = ["-U", "-O", str(mbin)]
        for name in sorted(set(names)):
            args += ["-f", name]
        eg._run_pak([*args, pak])
    mxml = WORK / "mxml"
    mxml.mkdir()
    result = subprocess.run([eg.mbincompiler(), "-y", "-Q", "-d", str(mxml), str(mbin)], capture_output=True, text=True)
    log = result.stdout + result.stderr
    if "[WARN]" in log or "[ERROR]" in log or len(list(mxml.rglob("*.MXML"))) != len(FILES):
        sys.exit("MBINCompiler did not read the biome tables:\n" + log)
    return mxml / BIOMES


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "desktop"))
import planet_word  # noqa: E402

# The texts the planet's word is picked from (desktop/planet_word.py) and the two words "Planet" and "Moon" they end in.
WORD_KEYS = ([f"{prefix}{i}" for prefix, n in planet_word.WORDS.values() for i in range(1, n + 1)] + ["PLANETCLASS1", "PLANETCLASS2"]
             # and what a made-up planet name is put together from: its template and the word added to it (Delta, Sigma ...)
             + [f"NAMEGEN_PLANET_STYLE_{i}" for i in range(1, 11)] + [f"NAMEGEN_PLANET_ADORN_{i}" for i in range(1, 11)])


def check_word_counts(english: dict[str, str]) -> None:
    """The game takes as many texts as it finds under PREFIX1, PREFIX2, ...; if a patch adds or drops one, the number it
    picks changes, so the counts in planet_word.WORDS must follow."""
    for prefix, n in planet_word.WORDS.values():
        found = 0
        while english.get(f"{prefix}{found + 1}"):
            found += 1
        if found != n:
            sys.exit(f"the game has {found} texts under {prefix}, planet_word.py counts {n}: update WORDS in desktop/planet_word.py")


def word_texts(text: dict[str, str]) -> dict[str, str]:
    return {k: text.get(k, "") for k in WORD_KEYS}


def convert(folder: Path) -> dict:
    files = ET.parse(folder / "biomefilenames.MXML").getroot()
    variants: dict[str, int] = {}
    for prop in files.find("Property"):  # the first Property is BiomeFiles; its children are the types
        options = prop.find("Property[@name='FileOptions']")
        if options is not None:
            variants[prop.get("name")] = len(options)

    stars: dict[str, dict[str, float]] = {}
    lists = ET.parse(folder / "biomelistperstartype.MXML").getroot()
    for star in lists.find("Property[@name='StarType']"):
        odds = star.find("Property[@name='BiomeProbability']")
        stars[star.get("name")] = {p.get("name"): float(p.get("value")) for p in odds}

    # Only the types a star can actually give; the share is within one star colour, in percent.
    types = []
    for name, n in variants.items():
        share = {}
        for star, odds in stars.items():
            total = sum(odds.values())
            if total and odds.get(name):
                share[star] = round(100 * odds[name] / total, 1)
        if share:
            types.append({"id": name, "variants": n, "stars": share})
    return {"stars": list(stars), "types": types}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--game", help="No Man's Sky install (default $NMS_GAME_DIR)")
    args = parser.parse_args(argv)
    game = eg.game_dir(args.game)
    data = convert(unpack(game))
    paths = sorted((eg.MXML_DIR / "language").glob("*.MXML"))
    check_word_counts(eg.load_language(paths, "english"))
    data["words"] = word_texts(eg.load_language(paths))  # in the language data/ is built in (NMS_LANG)
    data = {
        "_source": "metadata/simulation/solarsystem/biomes/{biomefilenames,biomelistperstartype}.mbin of the installed game",
        "_note": "Planet types, how many terrain variants each has and its share among the planets of a star colour. "
                 "The game files do not say which resources a planet type has, so none are listed.",
        **data,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(data['types'])} planet types")
    return 0


if __name__ == "__main__":
    sys.exit(main())
