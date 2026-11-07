"""Item texts in every language the installed game ships: web/lang/<language>.json.

The data in data/ is built in one language (build_data.py, NMS_LANG). This reads
the game's other language tables the same way and writes just the texts that
differ by language, so the site can switch language without a second build:

    web/languages.json     {"base": "russian", "list": [{"code", "name"}, ...]}
    web/lang/<code>.json   {"items": {id: [name, subtitle, description, symbol]},
                            "ops":   {text in the base language: text here},
                            "fx":    {buff stat id: text}}

Which languages exist is read from the game's archives, not listed here: a
patch that adds one needs no code change. Needs the cache from
`extract_game.py all` (it keys the texts) and the game install (the languages
themselves). One language takes about half a minute.

    NMS_GAME_DIR=... python scripts/build_langs.py [--only french,german]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import extract_game as eg  # noqa: E402

CACHE = eg.CACHE
WORK = CACHE / "lang"
# NMS_LANG_OUT: where the packaged desktop app (desktop/languages.py) wants the files, as its program folder is read-only.
WEB = Path(os.environ["NMS_LANG_OUT"]) if os.environ.get("NMS_LANG_OUT") else ROOT / "web"


def plain(text: str) -> str:
    """As build_web.plain, which is not imported: it pulls in the whole site build."""
    text = re.sub(r"<IMG>[^<]*<>", "", text)
    text = re.sub(r"<[A-Z_0-9]*>", "", text)
    return re.sub(r"\s*\(\s*\)", "", text).strip()

# Each language's own name for itself. The game ships the tables, not these
# labels; a language missing here is shown under its code.
NATIVE = {
    "english": "English", "usenglish": "English (US)", "russian": "Русский", "french": "Français",
    "german": "Deutsch", "italian": "Italiano", "spanish": "Español", "latinamericanspanish": "Español (Latinoamérica)",
    "portuguese": "Português", "brazilianportuguese": "Português (Brasil)", "polish": "Polski",
    "dutch": "Nederlands", "japanese": "日本語", "korean": "한국어", "simplifiedchinese": "简体中文",
    "traditionalchinese": "繁體中文", "tencentchinese": "简体中文 (Tencent)", "turkish": "Türkçe", "ukrainian": "Українська", "czech": "Čeština",
}


def texts_of(game: Path, lang: str) -> dict[str, str]:
    """Every loc key -> text in `lang` (English where the game has none)."""
    stage = WORK / lang
    mbin, mxml = stage / "mbin", stage / "mxml"
    eg.unpack(game, mbin, [f"language/nms_*_{lang}.mbin", "language/nms_*_english.mbin"])
    eg.decompile(mbin, mxml)
    try:
        return eg.load_language(sorted((mxml / "language").glob("*.MXML")), lang)
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def keys_of_items() -> dict[str, dict]:
    """item id -> the loc keys of its name, subtitle, description and buff stat."""
    out: dict[str, dict] = {}
    for table in ("Product_Table.json", "Substance_Table.json"):  # substances win, as in build_data
        for item, row in json.loads((CACHE / "json" / table).read_text(encoding="utf-8")).items():
            out[item] = {"name": row.get("NameLower") or row.get("Name") or "", "sub": row.get("Subtitle") or "",
                         "desc": row.get("Description") or "", "sym": row.get("Symbol") or "", "stat": row.get("FoodBonusStatType") or ""}
    return out


def recipe_name_keys() -> list[str]:
    _, top = eg.parse_mxml(eg.MXML_DIR / f"{eg.RECIPES}.MXML")
    return sorted({row.get("RecipeName") or "" for row in top.get("Table") or []} - {""})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game")
    ap.add_argument("--only", help="comma-separated languages (default: every one the game has)")
    args = ap.parse_args()

    game = eg.game_dir(args.game)
    found = eg.game_languages(game)
    wanted = [x for x in found if not args.only or x in args.only.split(",")]
    # The texts the data was built in are always read too: the page's "ops" are keyed by them (below).
    langs = wanted + [x for x in ("english",) if x in found and x not in wanted]
    print(f"game languages: {', '.join(found)}")
    wiki_ids = list(json.loads((ROOT / "data" / "wiki.json").read_text(encoding="utf-8")))
    keys = keys_of_items()
    rkeys = recipe_name_keys()
    stats = sorted({k["stat"] for k in keys.values() if k["stat"] not in ("", "Unspecified")})

    def pick(text: dict[str, str], k: str) -> str:
        return text.get(k, "") if k else ""

    built: dict[str, dict] = {}
    for lang in langs:
        print(f"  {lang} ...", flush=True)
        t = texts_of(game, lang)
        built[lang] = {
            "items": {i: [pick(t, keys[i]["name"]) or i, pick(t, keys[i]["sub"]),
                          plain(pick(t, keys[i]["desc"])), pick(t, keys[i]["sym"])] for i in wiki_ids if i in keys},
            "ops": {k: pick(t, k) for k in rkeys},
            "fx": {s: t.get(s.upper(), "") for s in stats},
        }

    # The language data/ was built in: the one whose item names it matches.
    items = json.loads((ROOT / "data" / "items.json").read_text(encoding="utf-8"))
    base = max(built, key=lambda lang: sum(
        built[lang]["items"].get(i, [""])[0] == v["name"] for i, v in list(items.items())[:300]))

    # "ops" is keyed by the loc key above; the site only knows the text it was
    # built with, so re-key it by the base language's text.
    base_ops = dict(built[base]["ops"])
    for data in built.values():
        data["ops"] = {base_ops[k]: v for k, v in data["ops"].items() if base_ops[k] and v}
    (WEB / "lang").mkdir(parents=True, exist_ok=True)
    for lang in wanted:
        (WEB / "lang" / f"{lang}.json").write_text(
            json.dumps(built[lang], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if not args.only:  # a list of only some of the languages would hide the others from the page
        (WEB / "languages.json").write_text(json.dumps({
            "base": base,
            "list": [{"code": c, "name": NATIVE.get(c, c)} for c in built],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {len(wanted)} languages to {WEB / 'lang'} (data is in {base})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
