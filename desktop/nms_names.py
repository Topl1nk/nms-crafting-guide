"""The names No Man's Sky gives to regions, star systems and planets, worked out from an address or a planet seed.

The game does not store these names; it makes them up from the address every time, with a small random generator and a table of
which letters may follow which. This is a port to plain Python (no numpy) of the work of the community's nms_namegen
(https://github.com/hadsh/nms_namegen, MIT licence, (c) 2026 Stuart Coyle & had.sh & GGF; the licence text is in THIRD_PARTY.md),
which was found by reading the game; it is not the game's own code and it is not guaranteed to match every name after a game
update. The letter table is data/namegen.json.gz (scripts/build_namegen.py turns their letter_map.json into it).

    system_name(code, galaxy)   code: the portal code as a number (planet, system, y, z, x: 12 hex digits), galaxy from 0
    planet_name(seed)           seed: the planet's seed, as the game's discovery record keeps it (DD.VP[0])
    planet_seeds(code, galaxy)  the seeds of every body of the system, for a planet whose seed the save does not hold

Floating point: the generator compares float32 and float64 numbers; numpy does that implicitly, here the float32 one is rounded
by struct, the float64 ones are Python floats (the same IEEE numbers).
"""
from __future__ import annotations

import gzip
import json
import math
import struct
from functools import lru_cache

import paths

M32 = 0xFFFFFFFF
M64 = 0xFFFFFFFFFFFFFFFF
MULTIPLIER = 0x5A76F899
CONST_A = 0x64DD81482CBD31D7
CONST_B = 0xE36AA5C613612997
TINY = 2.3283064370807974e-10  # 2**-32 as the generator writes it
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]
ADORNMENTS = ["Prime", "Major", "Minor", "Alpha", "Beta", "Gamma", "Delta", "Omega", "Sigma", "Tau"]
STYLES = ["%PROCNORM%", "%PROCNORM% %ADORNMENT%", "%PROCNORM% %NUMERAL%", "%PROCNORM% %SHORTCODE%", "%PROCLONG% %PROCSHORT%",
          "%PROCSHORT% %LONGCODE%", "%PROCNORM%", "%PROCNORM% %ADORNMENT%", "%PROCNORM% %NUMERAL%", "Style 9", "New %PROCNORM%"]
# The chance, per star colour (yellow, green, blue, red, purple), that a system is abandoned: float32 values as the game holds them.
ABANDONED = [0.0, 0.10000000149011612, 0.10000000149011612, 0.0, 0.3499999940395355]


@lru_cache(maxsize=1)
def _data() -> dict:
    with gzip.open(paths.RES / "data" / "namegen.json.gz", "rt", encoding="ascii") as f:
        return json.load(f)


def _f32(x: float) -> float:
    return struct.unpack("<f", struct.pack("<f", x))[0]


class PRNG:
    def __init__(self, seed: int):
        self.seed = seed

    def step(self) -> None:
        self.seed = (self.seed & M32) * MULTIPLIER + (self.seed >> 32)

    def random(self, n: int) -> int:  # 0 .. n-1
        self.step()
        return ((self.seed & M32) * n) >> 32

    def randi(self) -> int:
        self.step()
        return self.seed & M32


def _vowel(name: str, rng: PRNG, at: int) -> str:
    return name[:at] + "aeiou"[rng.random(5)] + name[at:]


def _consonant_run(name: str) -> int:
    run = 0
    for i, c in enumerate(name):
        if run < 3:
            run = run + 1 if c not in "aeiou" else 0
        elif c not in "aeiouy":
            return i - 3
        else:
            run = 0
    return -1


def _letters(rng: PRNG, alphaset: int) -> str:
    sets = _data()["alphasets"]
    s = sets[alphaset & 7]
    r = rng.random(len(s) // 3) * 3
    return s[r:r + 3]


def _generate(rng: PRNG, alphaset: int, lo: int, hi: int) -> str:
    table = _data()["map"]
    name = _letters(rng, alphaset)
    alternate = bool(rng.randi() & 1)
    todo = rng.random(hi - lo + 1) + lo - 3
    add = todo
    if todo > 0:
        tries, i = 8, 0
        while i < todo:
            weights = table[str(alphaset)].get(name[i:i + 3])
            target = rng.randi() * TINY
            if weights is None:
                tries -= 1
                i -= 1
                alphaset = (alphaset + 1) & 0x08000007
                if tries == 0:
                    if add < 3:
                        break
                    more = _letters(rng, alphaset)
                    if name[i + 2] in "aeiou" and more[0] in "aeiou":
                        name += "'"
                    elif more[0] not in "aeiou":
                        name += "aeiou"[rng.random(5) & 0xFF]
                    name += more
                    tries = 1
                    i += 2
                    add -= 3
            else:
                if alternate:
                    target *= len(weights) - 1
                    pick = int(target + 0.5) if target > 0 else 0
                else:
                    total = 0.0
                    for pick, (_, w) in enumerate(weights):
                        total += w
                        if total >= target:
                            break
                name += weights[pick][0]
                add -= 1
            if len(name) > 63:
                name = name[:64]
            i += 1

    first, second = name[0], name[1]
    if first not in "aeiou" and second not in "aeiou" and (first != "s" or second not in "hklmnprtwy"):
        if not ((second == "h" and first in "ctw") or (second == "l" and first in "bcfgps") or (second == "r" and first in "bcdfgkpt")
                or (second == "w" and first in "dgt") or (second == "y" and first in "hmr")):
            name = _vowel(name, rng, 1)
    if len(name) > 1:
        last, before = name[-1], name[-2]
        if before != "g" or last in "aeiou":
            if ((last == "b" and before in "gn") or (last == "d" and before in "bdfghkmpst") or (last == "g" and before == "l")
                    or (last == "p" and before in "bdhkt") or (last == "r" and before in "bfg") or (last == "t" and before == "g")
                    or (last == "w" and before not in "aeiou")):
                name = _vowel(name, rng, len(name) - 1)
    at = _consonant_run(name)
    if at != -1:
        name = _vowel(name, rng, at + rng.random(3) + 1)
    return name


def _alphaset_of(n: int) -> int:
    return 2 if n == 0 else (n + 2 if n < 4 else 7)


def system_name(code: int, galaxy: int) -> str:
    coords = code & M32
    index = ((code & 0x0FFF00000000) >> 24) | galaxy
    rol = (((coords & 0xFFFF) << 16) | ((coords & 0xFFFF0000) >> 16)) ^ coords ^ index
    rol &= M32
    seed = ((coords + (1 if coords == 0 else 0)) * MULTIPLIER) + rol
    rng = PRNG(seed)
    name = _generate(rng, _alphaset_of(((seed & M32) * 5) >> 32), 6, rng.random(4) + 6).capitalize()
    if len(name) < 8 and rng.random(4) < 2:
        name += "-" + _generate(rng, _alphaset_of(rng.random(5)), 3, 5).capitalize()
    if rng.random(10) < 3:
        name += " " + ROMAN[min(rng.random(19) + 1, 19) - 1]
    return name


def planet_name(seed: int) -> str:
    low, high = seed & M32, seed >> 32
    rol = (((low & 0xFFFF) << 16) | ((low & 0xFFFF0000) >> 16)) ^ low ^ high
    rol &= M32
    rng = PRNG(((low + (1 if low == 0 else 0)) * MULTIPLIER) + rol)
    adornment = ((rng.seed & M32) * 10) >> 32
    code = rng.random(50) + 1
    short = rng.random(0x1A) + 0x41
    numeral = rng.random(0x12) + 2
    digit = rng.random(9) + 1
    alpha = rng.random(0x1A) + 0x41
    long = rng.random(0x59) + 0xB
    norm = _generate(rng, 7, 4, 8)
    short_name = _generate(rng, 5, 4, 5)
    long_name = _generate(rng, 7, 6, 10)
    style = rng.random(9)
    if not (0.0350000001 <= rng.randi() * TINY):
        style = 10
    return (STYLES[style].replace("%PROCNORM%", norm.capitalize()).replace("%PROCSHORT%", short_name.capitalize())
            .replace("%PROCLONG%", long_name.capitalize()).replace("%ADORNMENT%", ADORNMENTS[adornment])
            .replace("%SHORTCODE%", f"{chr(short)}{code % 0x50}").replace("%NUMERAL%", ROMAN[numeral - 1])
            .replace("%LONGCODE%", f"{long}/{chr(alpha)}{digit}"))


def _ror(x: int, r: int) -> int:
    r &= 63
    return ((x >> r) | (x << (64 - r))) & M64


def _round(a, b, c, d, ra, rb):
    a1 = (_ror(b, ra) ^ c) & M64
    b1 = (_ror(a, rb) ^ d) & M64
    return a1, b1, (b1 + c) & M64, (a1 + d) & M64


def _hash(a, b, c, d, key, seed):
    a, b, c, d = _round(a, b, c, d, -0x17, 0x18)
    a, b, c, d = _round(a, b, c, d, -0x5, 0x1B)
    a, d = (a + key + 1) & M64, (d + key + 1) & M64
    a, b, c, d = _round(a, b, c, d, -0x19, 0x1F)
    a, b, c, d = _round(a, b, c, d, 0x12, -0xC)
    a, b, c, d = _round(a, b, c, d, 0x6, -0x16)
    a, b, c, d = _round(a, b, c, d, -0x20, -0x20)
    a, d = (a + seed + 2) & M64, (d + key + seed + 2) & M64
    a, b, c, d = _round(a, b, c, d, -0xE, -0x10)
    a, b, c, d = _round(b, a, d, c, 0x7, 0xC)
    a, b, c, d = _round(b, a, d, c, -0x17, 0x18)
    a, b, c, d = _round(a, b, c, d, -0x5, 0x1B)
    a, b, c, d = (a + 3) & M64, (b + key) & M64, (c + key) & M64, (d + 3 + seed) & M64
    a, b, c, d = _round(a, b, c, d, -0x19, 0x1F)
    a, b, c, d = _round(a, b, c, d, 0x12, -0xC)
    a, b, c, d = _round(a, b, c, d, 0x6, -0x16)
    a, b, c, d = _round(a, b, c, d, -0x20, -0x20)
    a, b, c, d = (a + 4) & M64, (b + seed) & M64, (c + seed + key) & M64, (d + 4) & M64
    a, b, c, d = _round(a, b, c, d, -0xE, -0x10)
    a, b, c, d = _round(a, b, c, d, 0xC, 0x7)
    a, b, c, d = _round(a, b, c, d, -0x17, 0x18)
    return [(c + seed) & M64, _ror(a, 0x1B) ^ d, d, ((_ror(b, -0x5) ^ c) + 5) & M64]


def _primed(ua: int) -> int:
    seed = ua & 0xFFFFFFFFFF
    system_id = (ua >> 40) & 0xFFF
    key = (seed ^ 0x1BD11BDAA9FC1A22) & M64
    b = _ror(seed, 7) ^ seed
    out = _hash(seed, b, b + seed, seed + seed, key, seed)
    if system_id >= 9:
        index = system_id - 1
        a = ((index - 8) >> 3) + 1 + seed
        b = _ror(a, 7) ^ a
        out = _hash(a, b, b + a, a + a, key, seed)
        counter = (index - 8) & 7
    else:
        counter = system_id - 1
    pick = counter >> 1
    counter += 1
    return (out[pick] >> 32) & M64 if not counter & 1 else out[pick] & M64


def _voxel(code: int) -> dict:
    x, y, z = code & 0xFFF, (code & 0xFF000000) >> 24, (code & 0xFFF000) >> 12
    x, z, y = x - 0x1000 if x > 0x7FF else x, z - 0x1000 if z > 0x7FF else z, y - 0x100 if y > 0x7F else y
    v = {"guide": 0x78, "hole": 1, "atlas": 1, "renegade": 0}
    distance = int(math.sqrt(x * x + y * y + z * z))
    if distance < 8:
        v.update(guide=0, hole=0, atlas=0)
    if 8 < distance < 1440:
        v["renegade"] = 0x78 - min(max(int((distance - 8) * 120 / 1440), 0), 0x78)
    return v


def _mix(register: int) -> int:
    register = (((register >> 33) ^ register) * CONST_A) & M64
    register = (((register >> 33) ^ register) * CONST_B) & M64
    return (register >> 33) ^ register


def _system(code: int, galaxy: int) -> dict:
    """How many planets and moons a system holds. The draws the game makes for economy, wealth, conflict and race are only
    stepped over: they are not needed for a name, but every later draw depends on them."""
    code &= 0xFFFFFFFFFFF
    raw = (code & 0xFFF00000000) >> 32
    va = _voxel(code)
    sid = raw - 1  # the branches below compare the id less one; the universal address keeps the id as it is
    sys_seed = _primed((((raw << 8) | (galaxy & 0xFF)) << 32) | (code & M32)) & M32
    rol = ((((sys_seed & 0xFFFF) << 16) | ((sys_seed & 0xFFFF0000) >> 16)) ^ sys_seed) & M32
    seed = ((sys_seed + (1 if sys_seed == 0 else 0)) * MULTIPLIER) + rol
    rng = PRNG(seed)
    star, safe, prime, count, anomaly = 0, 0, 2, 1, 0
    if sid < va["guide"]:
        count = (((seed & M32) * 4) >> 32) + 3
        safe = rng.random(count) + 1
    else:
        if (((seed & M32) * 100) >> 32) < 30:
            star = rng.random(3) + 1
        gap = sid - va["guide"]
        if va["hole"] > 0 and 0 <= gap < va["hole"]:
            anomaly, star = 2, 0
        if va["atlas"] > 0 and 0 <= gap - va["hole"] < va["atlas"]:
            anomaly, star = 1, 0
        count = rng.random(6) + 1
        safe = 0 if va["renegade"] >= 10 or star != 0 or anomaly != 0 else rng.random(count + 1)
    for _ in range(4):
        rng.step()
    if sid < va["renegade"]:
        star = rng.random(3) + 1
    if 0x3E7 < sid < 0x429:
        star = 4
    rng.step()
    abandoned = _f32((rng.seed & M32) / 4294967296.0) < ABANDONED[star]
    if not abandoned:
        rng.step()
    diff = 6 - count
    if diff < 1:
        prime = 0
    elif rng.random(100) >= 33 or diff < 2:
        prime = 1
    giant = False
    if star == 4:
        prime += count
        count = 0
        if rng.random(100) < 15:
            giant = True
            if rng.random(100) < 66:
                count, prime = 0, 6
    return {"planet_count": count, "prime_planet_count": prime, "safe_start_planet": safe, "gas_giant": giant, "star_type": star}


def _body(rng: PRNG) -> int:
    low = rng.randi()
    high = rng.randi()
    return _mix((high << 32) | low)


def planet_seeds(code: int, galaxy: int) -> dict:
    s = _system(code, galaxy)
    coords = code & M32
    index = ((code & 0x0FFF00000000) >> 24) | galaxy
    register = _mix((index << 32) | coords)
    high = ((((register & 0xFFFF0000) >> 16) | ((register & 0xFFFF) << 16)) ^ (register & M32) ^ (register >> 32)) or 1
    rng = PRNG(high << 32 | (register & M32))
    primary, total, stop = s["planet_count"], s["planet_count"] + s["prime_planet_count"], s["safe_start_planet"] - 1
    seeds, moons, sizes = [], 0, []
    if s["gas_giant"]:
        return {"planet_seeds": [_body(rng) for _ in range(total)], "planet_count": 1, "moon_count": total - 1, "sizes": sizes}
    i = 0
    while i < primary:
        i += 1
        size = rng.random(3)
        sizes.append(size)
        if size == 0:
            n = rng.random(min(max(primary - i, 0), 2) + 1)
            if n > 0:
                while i != stop:
                    i += 1
                    n -= 1
                    moons += 1
                    if n <= 0:
                        break
    i = 0
    while i < primary:
        seeds.append(_body(rng))
        i += 1
    while i < total:
        size = rng.random(3)
        sizes.append(size)
        seeds.append(_body(rng))
        i += 1
        if size == 0:
            n = rng.random(min(max(total - i, 0), 2) + 1)
            while n > 0 and i != stop:
                seeds.append(_body(rng))
                moons += 1
                n -= 1
                i += 1
    return {"planet_seeds": seeds, "planet_count": total - moons, "moon_count": moons, "sizes": sizes}


def planet_seed(code: int, galaxy: int) -> int:
    """The seed of the planet a portal code points at (its first digit: 1 is the first body of the system)."""
    return planet_seeds(code, galaxy)["planet_seeds"][((code & 0xF00000000000) >> 44) - 1]
