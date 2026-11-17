"""The word the game puts before "Planet" ("Quagmire Planet"), worked out from a planet's seed, biome and variant.

The save keeps only a planet's seed and its biome number. The variant (subtype) is worked out from the system's address by
planet_gen.py. The game picks the word from a list of texts under a prefix (loc keys SWAMPBIOME1..14, TOXIC1..10, INFESTEDRAD1..3
...), the prefix depending on biome and variant, and the choice is made in NMS.exe (0x16ce410): the planet's seed is mixed into a
chain of 13 x 2 stage seeds, the 22nd of them starts the stage that names the planet, and its first random draw picks the number.
Read off the game's code and checked against four planets in the game (Todmoni, Nasiylvan Habik, Ciusil, Odale VI); the same random
generator and constants as nms_namegen.

Which prefix (what 0x16ce410 does before it draws):
  biome Weird          -> one prefix per variant (MSTRUCTBIOME ... HYDROGARDENBIOME, variants 3..13)
  variant Infested     -> INFESTED + LUSH, TOX, HOT, RAD, COLD, DUST for the biomes 0..5, INFESTED for the others
  variant Structure    -> the same with RUINED
  otherwise            -> the biome's own prefix, but SWAMPBIOME or LAVABIOME for the variants Swamp and Lava
A Lush planet with no storms and no sentinels is called "Paradise" instead; that needs the weather and sentinels, which are not
worked out yet, so Lush planets get no word.
word_key() returns the loc key, or "" where the word is not known.
"""
from __future__ import annotations

_MULT = 0x5A76F899
_MIX_A = 0x64DD81482CBD31D7
_MIX_B = 0xE36AA5C613612997
_MASK = (1 << 64) - 1
_STAGE = 21  # the stage that names the planet, of the 26 the planet seed is split into

# How many texts the game has under each prefix (the keys PREFIX1..PREFIXN). scripts/build_biomes.py checks the counts against the
# installed game.
COUNTS = {"LUSH": 10, "TOXIC": 10, "SCORCHED": 10, "IRRADIATED": 10, "FROZEN": 10, "BARREN": 10, "DEAD": 10, "GLITCHBIOME": 12,
          "REDBIOME": 10, "GREENBIOME": 10, "BLUEBIOME": 10, "SWAMPBIOME": 14, "LAVABIOME": 14, "WATERWORLD": 8, "GASGIANT": 1,
          "MSTRUCTBIOME": 3, "BEAMSBIOME": 3, "HEXAGONBIOME": 3, "FRACTCUBEBIOME": 3, "BUBBLEBIOME": 3, "SHARDSBIOME": 3,
          "CONTOURBIOME": 3, "IRRISHELLSBIOME": 3, "BONESPIREBIOME": 3, "WIRECELLSBIOME": 3, "HYDROGARDENBIOME": 3,
          "INFESTEDLUSH": 4, "INFESTEDTOX": 3, "INFESTEDHOT": 4, "INFESTEDRAD": 3, "INFESTEDCOLD": 3, "INFESTEDDUST": 4, "INFESTED": 1,
          "RUINEDLUSH": 4, "RUINEDTOX": 3, "RUINEDHOT": 4, "RUINEDRAD": 3, "RUINEDCOLD": 3, "RUINEDDUST": 4, "RUINED": 1}
BIOME_PREFIX = ["LUSH", "TOXIC", "SCORCHED", "IRRADIATED", "FROZEN", "BARREN", "DEAD", "GLITCHBIOME", "REDBIOME", "GREENBIOME",
                "BLUEBIOME", "DEAD", "SWAMPBIOME", "LAVABIOME", "WATERWORLD", "GASGIANT"]  # by GcBiomeType
WEIRD_PREFIX = {3: "MSTRUCTBIOME", 4: "BEAMSBIOME", 5: "HEXAGONBIOME", 6: "FRACTCUBEBIOME", 7: "BUBBLEBIOME", 8: "SHARDSBIOME",
                9: "CONTOURBIOME", 10: "IRRISHELLSBIOME", 11: "BONESPIREBIOME", 12: "WIRECELLSBIOME", 13: "HYDROGARDENBIOME"}
_SIX = ["LUSH", "TOX", "HOT", "RAD", "COLD", "DUST"]
INFESTED_PREFIX = ["INFESTED" + s for s in _SIX] + ["INFESTED"] * 10
RUINED_PREFIX = ["RUINED" + s for s in _SIX] + ["RUINED"] * 10
WEIRD, INFESTED, STRUCTURE, SWAMP, LAVA = 7, 24, 3, 25, 26  # the biome and the variants (planet_gen.SUBTYPE)
# the word after the planet's: "Planet", "Moon", "Giant" (loc keys), by the body's size class (planet_gen: 3 = moon, 4 = giant)
CLASS_KEY = {3: "PLANETCLASS2", 4: "DISC_TYPE_GIANT"}


def class_key(size: int) -> str:
    return CLASS_KEY.get(size, "PLANETCLASS1")


def _rol16(x: int) -> int:
    return ((x << 16) | (x >> 16)) & 0xFFFFFFFF


def _state(x: int) -> tuple[int, int]:
    lo, hi = x & 0xFFFFFFFF, x >> 32
    return (lo + (lo == 0)) & 0xFFFFFFFF, (_rol16(lo) ^ hi ^ lo) & 0xFFFFFFFF


def _step(a: int, b: int) -> tuple[int, int]:
    s = a * _MULT + b
    return s & 0xFFFFFFFF, s >> 32


def _mix(v: int) -> int:
    v ^= v >> 33
    v = (v * _MIX_A) & _MASK
    v ^= v >> 33
    v = (v * _MIX_B) & _MASK
    return v ^ (v >> 33)


def stage_seed(seed: int, stage: int = _STAGE) -> int:
    a, b = _state(seed)
    out = []
    for _ in range(13):
        l1, h1 = _step(a, b)
        l2, h2 = _step(l1, h1)
        out.append(_mix((l2 << 32) | l1))
        l3, h3 = _step(l2, h2)
        l4, h4 = _step(l3, h3)
        out.append(_mix((l4 << 32) | l3))
        a, b = l4, h4
    return out[stage]


def word_number(seed: int, count: int) -> int:
    """1..count: which of the prefix's texts the game shows for a planet with this seed."""
    low, _ = _step(*_state(stage_seed(seed)))
    return ((low * count) >> 32) + 1


def prefix(biome: int, subtype: int) -> str:
    """The prefix of the planet's word, "" where it is not known."""
    if biome == WEIRD:
        return WEIRD_PREFIX.get(subtype, "")
    if not 0 <= biome < len(BIOME_PREFIX):
        return ""
    if subtype == INFESTED:
        return INFESTED_PREFIX[biome]
    if subtype == STRUCTURE:
        return RUINED_PREFIX[biome]
    if biome == 0 and subtype != SWAMP:
        return ""  # may be "Paradise" (see above)
    return "SWAMPBIOME" if subtype == SWAMP else "LAVABIOME" if subtype == LAVA else BIOME_PREFIX[biome]


def word_key(seed: int, biome: int, subtype: int) -> str:
    """The loc key of the planet's word (e.g. "TOXIC4"), "" when it is not known."""
    name = prefix(biome, subtype)
    return f"{name}{word_number(seed, COUNTS[name])}" if name else ""
