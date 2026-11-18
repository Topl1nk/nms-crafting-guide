"""The system attributes of NMS.exe's generator (build 184271), the tail of its routine at 0x1354ac0: how many planets a system has, its star
colour, whether it is abandoned, empty (no race), a pirate system, and the bytes of the planet descriptors that follow from them.

third_party/nms_namegen guesses most of this from labelled systems; this follows the game's own code, draw by draw, and agrees with the
routine run in an emulator (scripts/check_planets_against_game.py --system) on 400 random systems for every field below. What it leaves
out: the "wealth" and "conflict" numbers, which the routine adjusts from a map of the galaxy's density that is not in the game files.

The random numbers: a stream seeded by indexPrimedPRNG (the first word of a block cipher keyed by the address, in nms_namegen), each
draw "lo, hi = lo * 0x5A76F899 + hi" with the new lo as the value, a draw among n picking (lo * n) >> 32.
"""
from __future__ import annotations

import numpy as np

import planet_data

F = np.float32
_MULT = 0x5A76F899
# the galaxy's shape: the system index where the purple systems start and how many there are (0x1354330)
_PURPLE_FROM, _PURPLE_COUNT = 0x3E8, 0x41


def attributes(ua: int) -> dict:
    """ua: the address with the galaxy in bits 32-39 and the system index in bits 40-51. Keys: star (0 yellow .. 4 purple), planets
    (the count the routine draws), prime, safe_start, race (0-2, or 7: no race), abandoned, pirate, purple_gas (the purple
    system's gas giant layout), purple_full (its six bodies)."""
    from nms_namegen.iprng import indexPrimedPRNG
    from nms_namegen.region import voxelAttributes

    g = planet_data._tables()["globals"]
    abandoned_odds = [F(x) for x in g["AbandonedSystemProbability"]]
    empty_odds = [F(x) for x in g["EmptySystemProbability"]]
    pirate_odds = [F(x) for x in g["PirateSystemProbability"]]
    ssi = (ua >> 40) & 0xFFF
    va = voxelAttributes(((ssi << 32) | (ua & 0xFFFFFFFF)) & 0xFFFFFFFFFFF)
    guide, black_holes, atlas, renegade = va["guide_star_count"], va["black_hole_count"], va["atlas_station_count"], va["guide_star_renegade_count"]
    index = ssi - 1                                   # the routine counts systems from 0
    seed = indexPrimedPRNG(ua) & 0xFFFFFFFF
    rol = ((seed << 16) | (seed >> 16)) & 0xFFFFFFFF
    s = (seed + (seed == 0)) * _MULT + (rol ^ seed)
    st = [s & 0xFFFFFFFF, (s >> 32) & 0xFFFFFFFF]

    def draw() -> int:
        t = st[0] * _MULT + st[1]
        st[0], st[1] = t & 0xFFFFFFFF, (t >> 32) & 0xFFFFFFFF
        return st[0]

    def odds(d: int) -> np.float32:
        return F(d * 2.0 ** -32)

    star = safe = 0
    if index < guide:
        planets = (st[0] >> 30) + 3
        safe = ((planets * draw()) >> 32) + 1
        special = False
    else:
        if ((st[0] * 100) >> 32) < 0x1E:
            star = ((draw() * 3) >> 32) + 1
        special = False
        diff = index - guide
        if black_holes > 0 and 0 <= diff < black_holes:
            star, special = 0, True
        if atlas > 0 and 0 <= diff - black_holes < atlas and index < _PURPLE_FROM:
            star, special = 0, True
        planets = ((draw() * 6) >> 32) + 1
        if renegade < 10 and not special and star == 0:
            safe = ((draw() * (planets + 1)) >> 32)
    draw()                                            # economy
    draw()                                            # wealth
    draw()                                            # conflict
    race = (draw() * 3) >> 32
    if index < renegade:
        star = ((draw() * 3) >> 32) + 1
    if _PURPLE_FROM <= index < _PURPLE_FROM + _PURPLE_COUNT:
        star = 4
    abandoned = abandoned_odds[star] > odds(draw())
    if not abandoned and empty_odds[star] > odds(draw()):
        race = 7
    room = 6 - planets
    prime = 0
    if room >= 1:
        prime = 2 if ((draw() * 100) >> 32) < g["PercentChanceExtraPrime"] and room >= 2 else 1
    gas = full = False
    if star == 4:
        prime += planets
        planets = 0
        if ((draw() * 100) >> 32) < 15:
            gas = True
            full = ((draw() * 100) >> 32) < 66
        if full:
            planets, prime = 0, 6
    pirate = False
    if (star != 0 or safe == 0) and not abandoned and race != 7:
        pirate = pirate_odds[star] > odds(draw())
    return {"star": star, "planets": planets, "prime": prime, "safe_start": safe, "race": race, "abandoned": bool(abandoned), "pirate": bool(pirate),
            "purple_gas": gas, "purple_full": full}
