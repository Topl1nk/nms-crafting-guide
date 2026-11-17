"""The "Planetary data" the game shows for a planet: its weather, sentinels, flora and fauna, in the game's own words.

A port of the routines in NMS.exe (build 184271) that decide them and pick their texts, from what planet_gen.py knows of the planet
(its biome, variant, size, whether it is the start planet) and the system (star colour, galaxy):

    0x16cc250  stage A: flora and fauna level, sentinel level for each of the four sentinel settings (0x16ccb80 is its sentinel step)
    0x16cd310  the weather: its kind, how stormy and whether extreme
    0x16ce410  the texts: a prefix per kind (WEATHER_BARREN, RARITY_LOW, SENTINEL_DEFAULT ...) and a number drawn among the texts under it

Each routine has its own random generator, started from a stage seed of the planet's seed (planet_word.stage_seed): stage 0 for
stage A, 12 for the weather, 21 for the texts. The weights come from the game's files (data/planet_generator.json, "data").

What depends on the player's game and is read from the save: the game mode and the sentinel setting. Only the ordinary modes are
worked out (the game treats the "custom" and "creative" ones with extra rules that are not ported): planet_data() returns None
for them.

Checked against the game's own routines, run in an emulator over a running game (scripts/check_planets_against_game.py --data).
"""
from __future__ import annotations

import json

import numpy as np

import paths
import planet_gen
import planet_word

F = np.float32
_MULT = 0x5A76F899
EPS = F(1.1920929e-07)
LEVEL_WORD = ["RARITY_NONE", "RARITY_LOW", "RARITY_MID", "RARITY_HIGH"]
SENTINEL_WORD = ["SENTINEL_RARE", "SENTINEL_DEFAULT", "SENTINEL_AGGRESSIVE", "SENTINEL_CORRUPT"]
# weather kinds (the order of the game's weather list) and the weather word prefixes by biome (GcBiomeType): in a calm, a normal and
# an extreme spell
CALM = ["WEATHER_LUSH_CLEAR", "WEATHER_TOXIC_CLEAR", "WEATHER_HEAT_CLEAR", "WEATHER_RADIO_CLEAR", "WEATHER_COLD_CLEAR", "WEATHER_BARREN_CLEAR",
        "WEATHER_DEAD", "WEATHER_GLITCH", "WEATHER_RED", "WEATHER_GREEN", "WEATHER_BLUE", "WEATHER_DEAD", "WEATHER_SWAMP_CLEAR",
        "WEATHER_LAVA_CLEAR", "WEATHER_WATERWORLD", "WEATHER_GASGIANT"]
NORMAL = ["WEATHER_LUSH", "WEATHER_TOXIC", "WEATHER_HEAT", "WEATHER_RADIO", "WEATHER_COLD", "WEATHER_BARREN", "WEATHER_DEAD", "WEATHER_GLITCH",
          "WEATHER_RED", "WEATHER_GREEN", "WEATHER_BLUE", "WEATHER_DEAD", "WEATHER_SWAMP", "WEATHER_LAVA", "WEATHER_WATERWORLD", "WEATHER_GASGIANT"]
EXTREME = ["WEATHER_LUSHEXTREME", "WEATHER_TOXICEXTREME", "WEATHER_HEATEXTREME", "WEATHER_RADIOEXTREME", "WEATHER_COLDEXTREME",
           "WEATHER_BARRENEXTREME", "WEATHER_DEAD", "WEATHER_GLITCH", "WEATHER_RED", "WEATHER_GREEN", "WEATHER_BLUE", "WEATHER_DEAD",
           "WEATHER_SWAMP_EXTREME", "WEATHER_LAVA_EXTREME", "WEATHER_WATERWORLD", "WEATHER_GASGIANT"]
TOXIC_WEATHER, BUBBLE_WEATHER, DUST_WEATHER = 4, 12, 1
# how many texts the game has under each prefix (the keys PREFIX1..PREFIXN); scripts/build_biomes.py checks them against the game
COUNTS = {"RARITY_HIGH": 10, "RARITY_INFESTED": 6, "RARITY_LOW": 10, "RARITY_MID": 10, "RARITY_NONE": 10, "RARITY_ROBOT": 1, "RARITY_WEIRD": 8,
          "SENTINEL_AGGRESSIVE": 9, "SENTINEL_CORRUPT": 7, "SENTINEL_DEFAULT": 10, "SENTINEL_RARE": 12, "WEATHER_BARREN": 10,
          "WEATHER_BARRENEXTREME": 10, "WEATHER_BARREN_CLEAR": 8, "WEATHER_BLUE": 10, "WEATHER_COLD": 10, "WEATHER_COLDEXTREME": 10,
          "WEATHER_COLD_CLEAR": 8, "WEATHER_DEAD": 10, "WEATHER_GASGIANT": 4, "WEATHER_GLITCH": 12, "WEATHER_GREEN": 10, "WEATHER_HEAT": 10,
          "WEATHER_HEATEXTREME": 10, "WEATHER_HEAT_CLEAR": 8, "WEATHER_LAVA": 11, "WEATHER_LAVA_CLEAR": 10, "WEATHER_LAVA_EXTREME": 11,
          "WEATHER_LUSH": 10, "WEATHER_LUSHEXTREME": 10, "WEATHER_LUSH_CLEAR": 10, "WEATHER_RADIO": 10, "WEATHER_RADIOEXTREME": 10,
          "WEATHER_RADIO_CLEAR": 8, "WEATHER_RED": 10, "WEATHER_SWAMP": 10, "WEATHER_SWAMP_CLEAR": 10, "WEATHER_SWAMP_EXTREME": 10,
          "WEATHER_TOXIC": 12, "WEATHER_TOXICEXTREME": 12, "WEATHER_TOXIC_CLEAR": 10, "WEATHER_WATERWORLD": 1}
_t: dict | None = None


def _tables() -> dict:
    global _t
    if _t is None:
        raw = json.loads((paths.RES / "data" / "planet_generator.json").read_text(encoding="utf-8"))["data"]
        _t = {"files": {tuple(map(int, k.split(","))): v for k, v in raw["files"].items()}, "storms": raw["storms"], "globals": raw["globals"]}
    return _t


def _state(entry: int) -> list[int]:
    lo, hi = entry & 0xFFFFFFFF, entry >> 32
    return [(lo + (lo == 0)) & 0xFFFFFFFF, ((((lo << 16) | (lo >> 16)) & 0xFFFFFFFF) ^ hi ^ lo) & 0xFFFFFFFF]


def _draw(state: list[int]) -> np.float32:
    s = state[0] * _MULT + state[1]
    state[0], state[1] = s & 0xFFFFFFFF, s >> 32
    return F(state[0] * 2.0 ** -32)


def _weighted(state: list[int], weights: list[float]) -> int:
    """Stage A's draw among four levels (the first whose running total passes the draw)."""
    total = F(0)
    for w in weights:
        total = F(total + F(w))
    target = F(F(_draw(state) * total) + F(0))
    acc = F(0)
    for i, w in enumerate(weights):
        if not target < acc and F(acc + F(w)) > target:
            return i
        acc = F(acc + F(w))
    return 0


def _sentinel_level(g: dict, k: int, state: list[int], body: planet_gen.Body, star: int, kind: int, galaxy_kind: int, index: int) -> int:
    """The sentinel level 0..3 (rare, default, aggressive, corrupt) for the sentinel setting k (0 off .. 3 the most), as stage A's loop
    draws it; every setting starts from the same random state."""
    if k == 0:
        return 0
    state = list(state)
    low, aggressive = F(g["LowSentinelProbability"]), F(g["AggressiveSentinelProbability"])
    if k >= 3:
        low, aggressive = F(g["LowSentinelProbabilitySurvival"]), F(g["AggressiveSentinelProbabilitySurvival"])
    elif k <= 1:
        aggressive = F(0)
    if kind == 1:
        level = int(low <= _draw(state))
    elif star == 4 and index == 1:  # the second body of a purple system
        level = 3
    elif k >= 3 and body.biome == 0 and body.subtype != planet_gen.SUBTYPE["Swamp"]:
        level = int(F(g["NonAggressiveLushSurvivalProbabability"]) <= _draw(state)) + 1
    elif kind == 2:
        level = 0
    elif aggressive > _draw(state):
        level = 2
    else:
        level = int(low <= _draw(state))
    if galaxy_kind == 2 and kind != 1 and F(g["ViciousSentinelProbability"]) > _draw(state):
        level = 2
    if body.biome == 15 and level >= 2:
        level = 0
    if level == 2 and F(g["CorruptSentinelProbability"]) > _draw(state):
        level = 3
    return level

def levels(seed: int, body: planet_gen.Body, star: int, galaxy: int, index: int, setting: int = 2) -> dict:
    """Stage A and the weather: flora and fauna level (0 none, 1 low, 2 mid, 3 high), the sentinel level for each setting, the
    weather kind (index in the game's weather list), how stormy (0 calm, 1 normal, 2/3 extreme) and whether extreme."""
    t, g = _tables(), _tables()["globals"]
    galaxy_kind = planet_gen.GALAXY_KIND[galaxy % 20]
    kind = 1 if body.start else 0
    # ---- stage A
    state = _state(planet_word.stage_seed(seed, 0))
    life = [0, 0, 0, 1]
    if kind == 1:
        flora, fauna = (2, 1) if galaxy_kind == 1 else (3, 2)
    else:
        flora = 0 if body.biome in (6, 14, 15) else _weighted(state, life)
        fauna = 0 if body.biome in (6, 15) else 3 if body.biome == 14 else _weighted(state, life)
    extra = int(_draw(state) > F(0.75))
    local = list(state)
    sentinels = [_sentinel_level(g, k, local, body, star, kind, galaxy_kind, index) for k in range(4)]
    # a corrupt level only stands where the level of the game's own sentinel setting is corrupt too
    sentinels = [2 if (s == 3 and sentinels[setting] != 3) else s for s in sentinels]
    # ---- weather
    wstate = _state(planet_word.stage_seed(seed, 12))
    weights = [F(x) for x in _file(t, body)["weather"][star]]
    total = F(0)
    for w in weights:
        total = F(total + w)
    target = F(F(_draw(wstate) * F(total - EPS)) + EPS)
    wkind, acc = 0, F(0)
    for i, w in enumerate(weights):
        acc = F(acc + w)
        if acc >= target:
            wkind = i
            break
    if kind == 1:
        if body.biome != 5 and wkind == DUST_WEATHER:
            wkind = 5
    elif wkind == 2 and sentinels[setting] == 3:
        wkind = 13
    klass = extreme = 0
    if kind == 0:
        extreme = int(F(g["ExtremePlanetChance"][star]) > _draw(wstate))
        storms = t["storms"][wkind]
        if F(storms["low"]) > _draw(wstate):
            klass = 1
        else:
            klass = 2 if (F(storms["high"]) > _draw(wstate) or extreme == 1) else 0
    if galaxy_kind == 2:
        if kind == 1:
            extreme = 1
        if F(g["ViciousWeatherProbability"]) > _draw(wstate):
            extreme = 1
        if F(g["ViciousStormProbability"]) > _draw(wstate):
            klass = 2
    if body.biome in (6, 7):
        klass = extreme = 0
    elif body.biome == 15:
        extreme, klass = 1, 0
    return {"flora": flora, "fauna": fauna, "extra": extra, "sentinels": sentinels, "weather_kind": wkind, "weather_class": klass,
            "weather_extreme": extreme}

def _file(t: dict, body: planet_gen.Body) -> dict:
    """The biome file the game uses for this body: the one of its variant, else the first the game has for the biome."""
    entry = t["files"].get((body.biome, body.subtype))
    if entry is None:
        entry = next(v for (b, s), v in sorted(t["files"].items()) if b == body.biome)
    return entry


def _weather_prefix(body: planet_gen.Body, kind: int, klass: int, extreme: int) -> str:
    family = EXTREME if extreme == 1 or klass in (2, 3) else CALM if klass == 0 else NORMAL
    if body.subtype == planet_gen.SUBTYPE["Swamp"] or body.biome == 12:
        return family[1] if kind == TOXIC_WEATHER else family[12]
    if body.subtype == planet_gen.SUBTYPE["Lava"]:
        return family[13]
    if body.biome == 5 and kind != DUST_WEATHER:
        return family[2]
    if kind == BUBBLE_WEATHER:
        return family[9]
    return family[body.biome]


def texts(seed: int, body: planet_gen.Body, lv: dict, setting: int = 2) -> dict:
    """The loc keys the game shows for the planet: its "Planetary data" words (fauna is not worked out: None) and its own word
    ("Paradise" for a calm Lush planet without sentinels)."""
    state = _state(planet_word.stage_seed(seed, 21))
    draws = []
    for _ in range(9):
        s = state[0] * _MULT + state[1]
        state[0], state[1] = s & 0xFFFFFFFF, s >> 32
        draws.append(state[0])

    def pick(i: int, prefix: str) -> str:
        return f"{prefix}{((draws[i] * COUNTS[prefix]) >> 32) + 1}"

    file = _file(_tables(), body)
    flora = file["flora"] or LEVEL_WORD[lv["flora"]]
    out = {"weather": pick(1, _weather_prefix(body, lv["weather_kind"], lv["weather_class"], lv["weather_extreme"])),
           "flora": pick(3, flora), "fauna": None, "sentinels": pick(5 + setting, SENTINEL_WORD[lv["sentinels"][setting]]),
           "extra": pick(2, "RARITY_LOW" if lv["extra"] else "RARITY_MID")}
    paradise = (body.biome == 0 and lv["weather_extreme"] == 0 and lv["weather_class"] == 0 and lv["sentinels"][setting] == 0)
    out["word"] = planet_word.word_key(seed, body.biome, body.subtype, paradise) or None
    return out


def describe(body: planet_gen.Body, setting: int | None, mode: int) -> dict | None:
    """The loc keys of a planet's "Planetary data" and its word, or None where they are not worked out (a game mode with extra rules,
    or a sentinel setting the save does not state clearly). Keys: weather, flora, sentinels, word (fauna is not worked out: None)."""
    if mode in (0, 6) or setting is None:
        return None
    lv = levels(body.seed, body, body.star, body.galaxy, body.index, setting)
    return texts(body.seed, body, lv, setting)
