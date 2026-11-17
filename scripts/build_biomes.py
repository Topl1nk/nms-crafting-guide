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
GEN_OUT = ROOT / "data" / "planet_generator.json"
FILES = [f"{BIOMES}/biomefilenames.mbin", f"{BIOMES}/biomelistperstartype.mbin", f"{BIOMES}/biomefilenamesarchive.mbin"]


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
import planet_data  # noqa: E402
import planet_gen  # noqa: E402
import planet_word  # noqa: E402

# The texts the planet's word is picked from (desktop/planet_word.py) and the two words "Planet" and "Moon" they end in.
WORD_KEYS = ([f"{prefix}{i}" for prefix, n in planet_word.COUNTS.items() for i in range(1, n + 1)] + ["PLANETCLASS1", "PLANETCLASS2", "DISC_TYPE_GIANT", "UI_PARADISE_PLANET", "UI_DISC_MINERALS"]
             + [f"{prefix}{i}" for prefix, n in planet_data.COUNTS.items() for i in range(1, n + 1)]
             # and what a made-up planet name is put together from: its template and the word added to it (Delta, Sigma ...)
             + [f"NAMEGEN_PLANET_STYLE_{i}" for i in range(1, 11)] + [f"NAMEGEN_PLANET_ADORN_{i}" for i in range(1, 11)])


def check_word_counts(english: dict[str, str]) -> None:
    """The game takes as many texts as it finds under PREFIX1, PREFIX2, ...; if a patch adds or drops one, the number it
    picks changes, so the counts in planet_word.WORDS must follow."""
    for prefix, n in {**planet_word.COUNTS, **planet_data.COUNTS}.items():
        found = 0
        while english.get(f"{prefix}{found + 1}"):
            found += 1
        if found != n:
            sys.exit(f"the game has {found} texts under {prefix}, planet_word.py counts {n}: update COUNTS in desktop/planet_word.py or planet_data.py")


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


def unpack_named(game: Path, names: list[str], work: Path) -> Path:
    """Unpack and decompile exactly these files (lower-case game paths, .mbin); returns the folder of the .MXML files."""
    wanted: dict[str, list[str]] = {}
    want = {n.lower() for n in names}
    for pak, name in eg.pak_listing(game):
        if name.lower() in want:
            wanted.setdefault(pak, []).append(name)
    found = sum(len(v) for v in wanted.values())
    if found != len(want):
        sys.exit(f"{len(want) - found} of the {len(want)} files the planet data needs are not in the game: check the build and the paths")
    shutil.rmtree(work, ignore_errors=True)
    mbin, mxml = work / "mbin", work / "mxml"
    mbin.mkdir(parents=True)
    mxml.mkdir()
    for pak, pak_names in wanted.items():
        args = ["-U", "-O", str(mbin)]
        for name in sorted(set(pak_names)):
            args += ["-f", name]
        eg._run_pak([*args, pak])
    result = subprocess.run([eg.mbincompiler(), "-y", "-Q", "-d", str(mxml), str(mbin)], capture_output=True, text=True)
    log = result.stdout + result.stderr
    if "[WARN]" in log or "[ERROR]" in log or len(list(mxml.rglob("*.MXML"))) != len(want):
        sys.exit("MBINCompiler did not read the planet data files:\n" + log)
    return mxml


def planet_data_tables(game: Path, folder: Path) -> dict:
    """What desktop/planet_data.py works a planet's weather, sentinels, flora and fauna out from: the weather odds of every biome
    file per star colour and its flora text, the storm chances of each weather type, and the probabilities in the game's globals."""
    files = ET.parse(folder / "biomefilenames.MXML").getroot()
    options = {}  # (biome, variant) -> the game path of its biome file
    for biome in files.find("Property[@name='BiomeFiles']"):
        for o in biome.find("Property[@name='FileOptions']"):
            sub = planet_gen.SUBTYPE[o.find("Property[@name='SubType']/Property").get("value")]
            options[(planet_gen.BIOME[biome.get("name")], sub)] = o.find("Property[@name='Filename']").get("value").lower().replace(".mxml", ".mbin")
    weather_list = unpack_named(game, ["metadata/simulation/solarsystem/weather/weatherlist.mbin"], WORK / "weather_list")
    kinds = [(p.get("name"), p.get("value").lower().replace(".mxml", ".mbin"))
             for p in ET.parse(next(weather_list.rglob("weatherlist.MXML"))).getroot().find("Property[@name='Table']")]
    weather = unpack_named(game, [path for _, path in kinds], WORK / "weather")
    storms = []
    for _, path in kinds:
        root = ET.parse(next(weather.rglob(Path(path).stem + ".MXML"))).getroot()
        storms.append({"low": float(root.find("Property[@name='LowStormsChance']").get("value")),
                       "high": float(root.find("Property[@name='HighStormsChance']").get("value"))})
    biome_files = unpack_named(game, sorted(set(options.values())), WORK / "biome_files")
    per_file = {}
    for (biome, sub), path in options.items():
        root = ET.parse(next(biome_files.rglob(Path(path).stem + ".MXML"))).getroot()
        per_file[f"{biome},{sub}"] = {
            "flora": root.find("Property[@name='FloraLifeLocID']").get("value"),
            "weather": [[float(w.get("value")) for w in root.find("Property[@name='WeatherOptions']/Property[@name='%s']/Property" % star)]
                        for star in ("Yellow", "Green", "Blue", "Red", "Purple")]}
    glob = unpack_named(game, ["gcgameplayglobals.global.mbin", "gcsolargenerationglobals.global.mbin", "gcterrainglobals.global.mbin"], WORK / "globals")
    play = ET.parse(next(glob.rglob("gcgameplayglobals.global.MXML"))).getroot()
    solar = ET.parse(next(glob.rglob("gcsolargenerationglobals.global.MXML"))).getroot()
    terrain = ET.parse(next(glob.rglob("gcterrainglobals.global.MXML"))).getroot()
    # the substances of a planet: its common one by star colour (an extreme planet's: its own), its uncommon one by biome, its rare one drawn
    substances = {key: [p.get("value") for p in terrain.find(f"Property[@name='{name}']")]
                  for key, name in (("biome", "MiningSubstanceBiome"), ("star", "MiningSubstanceStar"), ("extreme", "MiningSubstanceStarExtreme"),
                                    ("rare", "MiningSubstanceRare"))}
    chance = {n: float(play.find(f"Property[@name='{n}']").get("value")) for n in (
        "AggressiveSentinelProbability", "AggressiveSentinelProbabilitySurvival", "LowSentinelProbability", "LowSentinelProbabilitySurvival",
        "CorruptSentinelProbability", "ViciousSentinelProbability", "ViciousStormProbability", "ViciousWeatherProbability",
        "NonAggressiveLushSurvivalProbabability")}
    chance["ExtremePlanetChance"] = [float(p.get("value")) for p in solar.find("Property[@name='ExtremePlanetChance']")]
    return {"weather_kinds": [k for k, _ in kinds], "storms": storms, "files": per_file, "globals": chance, "substances": substances}


def generator_tables(folder: Path) -> dict:
    """What desktop/planet_gen.py draws a planet's biome and variant from: the variants of every biome with their odds (the table
    the game picks a variant from, and the archive table it checks the pick against), the biomes a start planet, a moon of a purple
    system and a giant may have, and the biome odds per star colour with the rows of the two special galaxy kinds."""
    def options(path: Path) -> tuple[dict, ET.Element]:
        root = ET.parse(path).getroot()
        files = {}
        for biome in root.find("Property[@name='BiomeFiles']"):
            files[str(planet_gen.BIOME[biome.get("name")])] = [
                [planet_gen.SUBTYPE[o.find("Property[@name='SubType']/Property").get("value")],
                 float(o.find("Property[@name='Weight']").get("value")), float(o.find("Property[@name='PurpleSystemWeight']").get("value"))]
                for o in biome.find("Property[@name='FileOptions']")]
        return files, root

    files, root = options(folder / "biomefilenames.MXML")
    archive, _ = options(folder / "biomefilenamesarchive.MXML")
    lists = {key: [planet_gen.BIOME[e.find("Property").get("value")] for e in root.find(f"Property[@name='{name}']")]
             for key, name in (("start", "ValidStartPlanetBiome"), ("moon", "ValidPurpleMoonBiome"), ("giant", "ValidGiantPlanetBiome"))}
    per_star = ET.parse(folder / "biomelistperstartype.MXML").getroot()

    def row(e: ET.Element) -> dict:
        return {"prob": [float(p.get("value")) for p in e.find("Property[@name='BiomeProbability']")],
                "prime": [float(p.get("value")) for p in e.find("Property[@name='PrimeBiomeProbability']")]}

    rows = [row(s) for s in per_star.find("Property[@name='StarType']")] + [row(per_star.find(f"Property[@name='{n}']")) for n in ("LushYellow", "AbandonedYellow")]
    return {"_source": "metadata/simulation/solarsystem/biomes/{biomefilenames,biomefilenamesarchive,biomelistperstartype}.mbin of the installed game",
            "files": files, "archive": archive, "lists": lists, "rows": rows,
            "dead_to_weird": float(per_star.find("Property[@name='ConvertDeadToWeird']").get("value"))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--game", help="No Man's Sky install (default $NMS_GAME_DIR)")
    args = parser.parse_args(argv)
    game = eg.game_dir(args.game)
    folder = unpack(game)
    data = convert(folder)
    tables = generator_tables(folder)
    tables["data"] = planet_data_tables(game, folder)
    GEN_OUT.write_text(json.dumps(tables, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {GEN_OUT.relative_to(ROOT)}")
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
