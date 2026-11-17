"""The word the game puts before "Planet" ("Quagmire Planet"), worked out from a planet's seed and type.

The save keeps only a planet's seed and its type number. The game picks the word from a list of texts per type
(loc keys SWAMPBIOME1..14, TOXIC1..10, ...) and the choice is made in NMS.exe: the planet's seed is mixed into a chain of
13 x 2 stage seeds, the 22nd of them starts the stage that names the planet, and its first random draw picks the number.
Read off the game's code and checked against three planets in the game (Todmoni, Nasiylvan Habik, Ciusil); the same random
generator and constants as nms_namegen.

word_key() returns the loc key, or "" where the word depends on something the save does not hold: the Weird type (its
words depend on a variant) and any planet whose record carries more than the type number and one extra bit.
Not known from the save, so assumed: the planet is no moon, and its variant is not "infested" or "ruined" (those have
words of their own).
"""
from __future__ import annotations

_MULT = 0x5A76F899
_MIX_A = 0x64DD81482CBD31D7
_MIX_B = 0xE36AA5C613612997
_MASK = (1 << 64) - 1
_STAGE = 21  # the stage that names the planet, of the 26 the planet seed is split into

# The key prefix and how many texts the game has under it (the keys PREFIX1..PREFIXN), by biome number.
# scripts/build_biomes.py checks the counts against the installed game.
WORDS = {0: ("LUSH", 10), 1: ("TOXIC", 10), 2: ("SCORCHED", 10), 3: ("IRRADIATED", 10), 4: ("FROZEN", 10), 5: ("BARREN", 10),
         6: ("DEAD", 10), 8: ("REDBIOME", 10), 9: ("GREENBIOME", 10), 10: ("BLUEBIOME", 10), 12: ("SWAMPBIOME", 14),
         13: ("LAVABIOME", 14), 14: ("WATERWORLD", 8), 15: ("GASGIANT", 1)}


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
    """1..count: which of the type's texts the game shows for a planet with this seed."""
    low, _ = _step(*_state(stage_seed(seed)))
    return ((low * count) >> 32) + 1


def word_key(seed: int, vp1: int) -> str:
    """The loc key of the planet's word (e.g. "TOXIC4"), "" when it cannot be told from the save."""
    entry = WORDS.get(vp1 & 0xFFFF)
    if entry is None or vp1 >> 16 > 1:  # the bit 16 (0 or 1) is not understood; it did not change the word on the one planet checked (Nasiylvan Habik)
        return ""
    prefix, count = entry
    return f"{prefix}{word_number(seed, count)}"
