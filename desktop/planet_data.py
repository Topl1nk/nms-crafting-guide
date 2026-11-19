"""The "Planetary data" the game shows for a planet: its weather, sentinels, flora and fauna, in the game's own words.

A port of the routines in NMS.exe (build 184271) that decide them and pick their texts, from what planet_gen.py knows of the planet
(its biome, variant, size, whether it is the start planet) and the system (star colour, galaxy):

    0x16cc250  stage A: flora and fauna level, sentinel level for each of the four sentinel settings (0x16ccb80 is its sentinel step)
    0x16cd310  the weather: its kind, how stormy and whether extreme
    0x16cd970  the substances: the common, uncommon and rare one (stage 19); the full generator that runs it is 0x16c59b0
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
        _t = {"files": {tuple(map(int, k.split(","))): v for k, v in raw["files"].items()}, "storms": raw["storms"], "globals": raw["globals"],
              "substances": raw["substances"], "plants": raw["plants"], "voxel": raw["voxel"], "common": raw["common"], "optional": raw["optional"],
              "creatures": raw["creatures"], "roles": raw["roles"], "palettes": raw["palettes"], "tiles": raw["tiles"], "water": raw["water"], "gas": raw["gas"], "atmospheres": raw["atmospheres"]}
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

# Which planets can be scrap worlds. The game files a planet class (0x16cc6e6: start planet 3, weird 4, infested 5, waterworld 6, gas giant
# 7, dead 0, any other 2) and looks up a chance per class in a table of its own memory ([0, 1, 1, 1, 0, 0, 0, 0 ...], read out of the running
# game: it is not in the global files that build_biomes.py unpacks) and a draw of at most 0.2 (the constant at 0x4bf652c) decides.
_SCRAP_CLASS = {0: False, 1: True, 2: True, 3: True, 4: False, 5: False, 6: False, 7: False}
_SCRAP_CHANCE = F(0.2)


def _class(body: planet_gen.Body) -> int:
    if body.start:
        return 3
    if body.biome == 7:
        return 4
    if body.subtype == planet_gen.SUBTYPE["Infested"]:
        return 5
    return {14: 6, 15: 7, 6: 0}.get(body.biome, 2)


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
    # the scrap flag (0x16cca91): the stage's own state is drawn once more after the sentinel loop, which worked on copies of it, so the
    # draw is the sentinel loop's first one; but not on a weird planet
    scrap = int(body.biome != 7 and _SCRAP_CLASS[_class(body)] and _draw(list(state)) <= _SCRAP_CHANCE)
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
    return {"flora": flora, "fauna": fauna, "extra": extra, "scrap": scrap, "sentinels": sentinels, "weather_kind": wkind, "weather_class": klass,
            "weather_extreme": extreme}


# the chances of the game's three swamp and lava picks below (constants of the exe, 0x4bf61e4, 0x4bf6b60, 0x4bf71b8)
_SWAMP_ODDS = (F(0.15), F(0.33), F(0.66))
_SUBSTANCE_STAGE = 19


def substances(seed: int, body: planet_gen.Body, star: int, extreme: int) -> dict:
    """The three substances the planet's resource list shows apart from its plants, bones and scrap: the common one (by the star's
    colour, an extreme planet has the activated one), the uncommon one (by biome; swamp and lava planets draw among a few) and the
    rare one (drawn from the game's list). Loc-free ids such as "YELLOW2"; 0x16cd970, its random generator is stage 19."""
    table = _tables()["substances"]
    state = _state(planet_word.stage_seed(seed, _SUBSTANCE_STAGE))
    s = state[0] * _MULT + state[1]
    low1 = s & 0xFFFFFFFF
    s = low1 * _MULT + (s >> 32)
    chance = F((s & 0xFFFFFFFF) * 2.0 ** -32)
    rare = table["rare"][(low1 * len(table["rare"])) >> 32]
    biome = body.biome if 0 <= body.biome < len(table["biome"]) else 0
    if biome == 13 or body.subtype == planet_gen.SUBTYPE["Lava"]:
        uncommon = table["biome"][13 if _SWAMP_ODDS[1] > chance else 5]
    elif biome == 12 or body.subtype == planet_gen.SUBTYPE["Swamp"]:
        uncommon = table["biome"][12 if _SWAMP_ODDS[0] > chance else 16 if _SWAMP_ODDS[1] > chance else 12 if _SWAMP_ODDS[2] <= chance else 0]
    else:
        uncommon = table["biome"][biome]
    common = table["extreme" if extreme == 1 else "star"][star]
    return {"common": common, "uncommon": uncommon, "rare": rare}


def plant_hint(body: planet_gen.Body) -> str:
    """The plant in the planet's resource list (an item id such as PLANT_DUST, cactus flesh), "" where it has none. The game's list
    of each Lush to Barren biome (data "plants") is always on, but it asks for the planet's biome with the swamp and lava variants
    counted as biomes of their own, so those variants have none (0x16d2df0)."""
    sub = planet_gen.SUBTYPE
    biome = 12 if body.subtype == sub["Swamp"] else 13 if body.subtype == sub["Lava"] else body.biome
    return _tables()["plants"].get(str(biome), "")


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
           "flora": pick(3, flora), "fauna": pick(4, "RARITY_WEIRD" if body.biome == 7 else LEVEL_WORD[lv["fauna"]]), "sentinels": pick(5 + setting, SENTINEL_WORD[lv["sentinels"][setting]]),
           "extra": pick(2, "RARITY_LOW" if lv["extra"] else "RARITY_MID")}
    paradise = (body.biome == 0 and lv["weather_extreme"] == 0 and lv["weather_class"] == 0 and lv["sentinels"][setting] == 0)
    out["word"] = planet_word.word_key(seed, body.biome, body.subtype, paradise) or None
    return out


# The terrain stage (0x16cbfb0 and 0x16cae10, stage seed 4): the size class of the planet's terrain, its water and whether it has hazards. The
# integers at 0x5012044 and 0x5012048 (10 and 21) and the floats 0.2, 35, 450, 10, 120 and 1500 of the water are constants of the exe, read out
# of the running game. Each noise layer or feature that is on and drawn spends more draws on its own variation (30 and 12 of them).
_SIZE_FROM, _SIZE_TO = F(10), F(21)
_WATER = F(120)
_LAYER_DRAWS, _FEATURE_DRAWS = 30, 12


def terrain(seed: int, body: planet_gen.Body, star: int) -> dict:
    """{"size_index": the terrain's size class (0..30), "water": the depth of the sea (0 none, 120 usual), "hazard": the planet has
    hazard areas (caves with them)}; checked against the game on every planet of tests/fixtures/planet_resources.json."""
    t = _file(_tables(), body)["terrain"]
    state = _state(planet_word.stage_seed(seed, 4))

    def draw_int() -> int:
        s = state[0] * _MULT + state[1]
        state[0], state[1] = s & 0xFFFFFFFF, s >> 32
        return state[0]

    def draw() -> np.float32:
        return F(draw_int() * 2.0 ** -32)

    low, high = int(_SIZE_FROM), int(_SIZE_TO)
    if star == 4:
        size = (((31 - high) * draw_int()) >> 32) + high
    elif body.extra:
        size = (((high - (low + 1)) * draw_int()) >> 32) + low + 1
    else:
        size = (low * draw_int()) >> 32
    moon, giant, water_world = body.size == planet_gen.MOON, body.biome == 15, body.biome == 14
    if (moon and star != 4) or body.start or body.biome in (6, 7):
        wet = False
    elif water_world:
        wet = True
    else:
        wet = F(t["WaterActiveFrequency"]) > draw()
    water = F(0)
    if wet:
        water = _WATER
        if star == 4:
            deep = min(F(t["HighWaterActiveFrequency"]), F(0.2)) > draw()
            water = F(10) if moon else F(35) if giant else F(1500) if water_world else F(450) if deep else _WATER
    layers = _tables()["voxel"][size]
    for i in range(8):
        on = layers["noise"][i] and F(t["NoiseLayers"][i]) > draw()
        if i == 7:
            on = False if water > _WATER else True if water > F(1) else on
        if on:
            for _ in range(_LAYER_DRAWS):
                draw_int()
    for j in range(7):
        if layers["features"][j] and F(t["Features"][j]) > draw():
            for _ in range(_FEATURE_DRAWS):
                draw_int()
    hazard = bool(layers["cave"] and F(t["Caves"][0]) > draw())
    return {"size_index": size, "water": float(water), "hazard": hazard}


def _extreme_applies(body: planet_gen.Body, extreme: int, kind: int) -> bool:
    """0x9bfd50: an extreme planet that is not Lush or Barren, and whose weather is not one of the plain kinds."""
    biome = 12 if body.subtype == planet_gen.SUBTYPE["Swamp"] else 13 if body.subtype == planet_gen.SUBTYPE["Lava"] else body.biome
    if extreme == 0 or biome == 0 or body.biome == 5:
        return False
    return not (kind <= 0xF and (0xB007 >> kind) & 1)


def objects(seed: int, body: planet_gen.Body, lv: dict, ground: dict, setting: int = 2) -> list[list]:
    """The entries of the game's lists of objects a planet gets (0x16d2b00, stage seed 7), in order, each [name, resource hint, ...]: the
    hints of them are what the Discoveries menu lists besides the substances (ancient bones, salvage, plants, bugs, swarm debris).
    The lists are sorted by their order, each takes its own draws, entries that do not suit the planet are left out after drawing."""
    t = _tables()
    sub, biome = body.subtype, body.biome
    mapped = 12 if sub == planet_gen.SUBTYPE["Swamp"] else 13 if sub == planet_gen.SUBTYPE["Lava"] else biome
    sentinel = lv["sentinels"][2]    # the routine always looks at the "normal" combat setting
    extreme = _extreme_applies(body, lv["weather_extreme"], lv["weather_kind"])
    water, hazard = ground["water"], ground["hazard"]

    def skipped(e: list, u: np.float32) -> bool:
        tile = e[4]
        return bool((tile in (4, 7) and water <= 0) or (tile == 5 and not hazard) or u > F(e[3]) or (body.empty and e[0] == "LEVELONEOBJECTS"))

    def suits(lst: dict, u: np.float32) -> bool:
        f = dict(zip(("extreme_weather", "extreme_sentinels", "corrupt", "deep", "only_infested", "only_scrap", "not_scrap", "not_extreme", "not_start",
                      "not_weird", "not_dead", "not_giant", "not_infested"), lst["flags"]))
        ok = True
        if f["extreme_weather"]:
            ok = extreme
        if f["extreme_sentinels"]:
            ok = ok and sentinel == 2
        if f["corrupt"]:
            ok = ok and sentinel == 3
        if f["deep"]:
            ok = ok and water > 120
        if f["not_extreme"]:
            ok = ok and not extreme and sentinel != 2
        if f["not_start"]:
            ok = ok and not body.start
        if lst["biome"] != 16:
            ok = ok and mapped == lst["biome"]
        for key, bad in (("not_weird", mapped == 7), ("not_giant", mapped == 15), ("not_dead", mapped == 6), ("not_infested", sub == 24)):
            if f[key]:
                ok = ok and not bad
        if f["only_infested"]:
            ok = ok and sub == 24
        if f["only_scrap"]:
            ok = ok and bool(lv["scrap"])
        if f["not_scrap"]:
            ok = ok and not lv["scrap"]
        chance = lst["sub"][sub] if 0 <= sub < len(lst["sub"]) and lst["sub"][sub] >= 0 else lst["chance"]
        return bool(ok and F(chance) > u)

    state = _state(planet_word.stage_seed(seed, 7))

    def pdraw() -> int:
        s = state[0] * _MULT + state[1]
        state[0], state[1] = s & 0xFFFFFFFF, s >> 32
        return state[0]

    lo, hi = pdraw(), pdraw()
    h = (hi << 32) | lo
    h = (((h >> 33) ^ h) * 0x64DD81482CBD31D7) & 0xFFFFFFFFFFFFFFFF
    h = (((h >> 33) ^ h) * 0xE36AA5C613612997) & 0xFFFFFFFFFFFFFFFF
    local = _state((h >> 33) ^ h)

    def ldraw() -> int:
        s = local[0] * _MULT + local[1]
        local[0], local[1] = s & 0xFFFFFFFF, s >> 32
        return local[0]

    entries = [(e[2], False, e) for e in _file(t, body)["objects"]] + [(e[2], False, e) for e in t["common"]]
    entries += [(max([f[2] for f in lst["files"]] or [0]), True, lst) for lst in t["optional"]]
    entries.sort(key=lambda x: x[0])          # stable, as the game's sort
    out: list[list] = []
    for _, is_list, item in entries:
        u = F(ldraw() * 2.0 ** -32)
        if not is_list:
            if not skipped(item, u):
                ldraw()
                out.append(item)
            continue
        if not suits(item, u):
            continue
        count = (((item["max"] - item["min"] + 1) * ldraw()) >> 32) + item["min"]
        total = F(0)
        for f in item["files"]:
            if not skipped(f, F(1.0)):
                total = F(total + F(f[3]))
        for _ in range(count):
            target = F(F(F(pdraw() * 2.0 ** -32) * total) + F(0))
            acc, chosen = F(0), None
            for f in item["files"]:
                if skipped(f, F(1.0)) or any(o is f for o in out):
                    continue
                if not target < acc and F(F(f[3]) + acc) >= target:
                    chosen = f
                    break
                acc = F(acc + F(f[3]))
            if chosen is not None:
                pdraw()
                out.append(chosen)
                total = F(total - F(chosen[3]))
    return out


_EMPTY = "EMPTY"


def _step(s: list[int]) -> int:
    x = s[0] * _MULT + s[1]
    s[0], s[1] = x & 0xFFFFFFFF, x >> 32
    return s[0]


def _child(s: list[int]) -> list[int]:
    """The game's fork: two draws of s make the seed of a new generator."""
    lo1, lo2 = _step(s), _step(s)
    h = (lo2 << 32) | lo1
    h = (((h >> 33) ^ h) * 0x64DD81482CBD31D7) & 0xFFFFFFFFFFFFFFFF
    h = (((h >> 33) ^ h) * 0xE36AA5C613612997) & 0xFFFFFFFFFFFFFFFF
    return _state((h >> 33) ^ h)


def fauna_level(seed: int, body: planet_gen.Body, level: int, ground: dict) -> int:
    """The planet's fauna level (0 none, 1 low, 2 mid, 3 high) once the game has chosen its creature kinds (0x16d6050, stage seed 10):
    stage A's level stays unless the planet's ground creatures turn out to be none ("EMPTY", one draw in ten), when it drops to 1, or to
    0 if its air, water and cave creatures are none too. The kinds come from the lists of creaturegenerationdata (data "creatures"),
    each pick is the first draw of a generator made from two draws of the one before (the game's stack of generators); checked on the
    creature slots of every planet of tests/fixtures/planet_creatures.json. The start planet keeps stage A's level."""
    if body.start:
        return level
    slots, _ = creature_slots(seed, body, level, ground)
    if slots[0] == _EMPTY and body.biome != 14:
        return 0 if all(slots[k] == _EMPTY for k in (1, 2, 3)) else 1
    return level


def creature_slots(seed: int, body: planet_gen.Body, level: int, ground: dict) -> tuple[list, list]:
    """The creature kinds [ground, air, water, cave] the game picks for a planet and the generator stack it leaves behind (see fauna_level)."""
    t = _tables()["creatures"]
    state = _state(planet_word.stage_seed(seed, 10))
    step, child = _step, _child

    stack = [state, child(state)]          # the creature routine's generator, seeded from two draws, above the stage's own

    def fork() -> None:
        stack.append(child(stack[-1]))

    def pick(options: list) -> str | None:
        fork()
        u = F(step(stack[-1]) * 2.0 ** -32)
        stack.pop()
        total = F(0)
        for _, w in options:
            total = F(total + F(w))
        target = F(F(u * total) + F(0))
        for name, w in options:
            target = F(target - F(w))
            if F(0) >= target:
                return name
        return None

    water, hazard, biome = ground["water"], ground["hazard"], body.biome
    wet = water > 0 and not F(120) > F(water)
    slots: list[str | None] = [None] * 4    # ground, air, water, cave
    fork()
    step(stack[-1])
    step(stack[-1])
    stack.pop()
    fork()

    def table(opt: dict) -> None:
        fork()
        u = F(step(stack[-1]) * 2.0 ** -32)
        if not F(opt["gate"]) < u:
            lists = opt["lists"]
            if biome != 14:
                slots[0] = pick(lists["Ground"])
            if wet:
                slots[2] = pick(lists["Water"])
            slots[1] = pick(lists["Air"])
            if hazard:
                slots[3] = pick(lists["Cave"])
            if opt["override"]:
                for k in (0, 2, 1, 3):
                    slots[k] = slots[k] or _EMPTY
        stack.pop()

    if level == 0:
        slots = [_EMPTY] * 4
    else:
        special = t["empty"] if body.empty else t["purple"] if body.star == 4 else t["abandoned"] if body.abandoned else None
        if special is not None:
            table(special)
        if all(s is None for s in slots):
            if biome == 7:
                table(t["sub"][body.subtype])
            own = t["biome"][biome]
            if all(s is None for s in slots) and any(own["lists"].values()):
                table(own)
    fork()
    stack.pop()
    if biome == 14:
        slots[0] = slots[3] = _EMPTY
    fork()
    generic = t["generic"]
    slots[0] = slots[0] or pick(generic["Ground"])
    slots[1] = slots[1] or pick(t["only_air"] if slots[0] == _EMPTY else generic["Air"])
    if slots[2] is None and wet:
        slots[2] = pick(generic["Water"])
    if slots[3] is None and hazard:
        slots[3] = pick(generic["Cave"])
    return slots, stack


_ROLE_DOMAINS = ("Ground", "Air", "Water", "Cave")     # the slots of creature_slots, in the order the game visits them
_MAX_ROLES = 23


def creature_total(seed: int, body: planet_gen.Body, level: int, ground: dict) -> int | None:
    """How many creature roles the game makes for a planet: the number of species its Discoveries page counts the fauna out of (the length
    of the planet's creature list, 0x16d6050 after the slots). Each creature slot names an archetype (creaturegenerationarchetypes) that
    adds role tables, then a second pass adds some of its extra tables; every role of every table is switched on when a draw is not above
    its ProbabilityOfBeingEnabled, up to 23. Checked on the creature count the game made of every planet of tests/fixtures/planet_roles.json.
    None for the start planet, whose creatures the game picks by other rules."""
    if body.start:
        return None
    t = _tables()["roles"]
    slots, stack = creature_slots(seed, body, level, ground)
    stack.pop()                                         # the generic picks' generator, then the creature routine's own
    stack.pop()
    tables: list[str] = []

    def add(files: list[str], pick: int | None) -> None:
        _child(stack[-1])                               # the generator of the hemisphere limits: its draws change no count
        if pick is None:
            tables.extend(files)
            return
        left = list(files)
        while left and pick > 0:
            c = _child(stack[-1])
            tables.append(left.pop((_step(c) * len(left)) >> 32))
            pick -= 1

    def archetype(second: bool) -> None:
        for slot, domain in zip(slots, _ROLE_DOMAINS):
            if slot in (None, _EMPTY):
                continue
            entry = t["archetypes"][domain].get(slot)
            stack.append(_child(stack[-1]))
            if entry is not None:
                if not second:
                    add(entry["tables"], None)
                else:
                    for extra in entry["add"]:
                        add(extra["tables"], extra["max_add"])
            stack.pop()

    stack.append(_child(stack[-1]))
    archetype(False)
    stack.append(_child(stack[-1]))
    archetype(True)
    stack.pop()
    stack.pop()
    total = 0
    for name in tables:
        chances = t["tables"].get(name)
        if chances is None:
            continue
        first = _child(stack[-1])                       # each table and each role forks a generator of its own
        _child(first)
        for chance in chances:
            a = _child(first)
            _child(a)
            _child(a)
            if not F(F(_step(a) * 2.0 ** -32)) > F(chance) and total < _MAX_ROLES:
                total += 1
    return total


def describe(body: planet_gen.Body, setting: int | None, mode: int) -> dict | None:
    """The loc keys of a planet's "Planetary data" and its word, or None where they are not worked out (a game mode with extra rules,
    or a sentinel setting the save does not state clearly). Keys: weather, flora, sentinels, word (fauna is not worked out: None),
    substances (its common, uncommon and rare substance ids), plant (the item id of its plant resource, "" if none)."""
    if mode in (0, 6) or setting is None:
        return None
    lv = levels(body.seed, body, body.star, body.galaxy, body.index, setting)
    ground = terrain(body.seed, body, body.star)
    before = lv["fauna"]
    lv["fauna"] = fauna_level(body.seed, body, before, ground)
    out = texts(body.seed, body, lv, setting)
    out["fauna_total"] = creature_total(body.seed, body, before, ground)
    out["substances"] = substances(body.seed, body, body.star, lv["weather_extreme"])
    out["plant"] = plant_hint(body)
    out["scrap"] = bool(lv["scrap"])
    # what the game's lists of objects add to the resource list besides the substances, in its order: the bones and salvage of the
    # Discoveries menu, the plant, the bugs and the swarm debris (UI_BONES_HINT, PLANT_DUST, UI_SCRAP_HINT, UI_BUGS_HINT ...)
    out["hints"] = [e[1] for e in objects(body.seed, body, lv, ground, setting) if e[1]]
    return out
