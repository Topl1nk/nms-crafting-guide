"""What the game's solar-system generator makes of a system: its bodies, and each body's type (biome) and variant (subtype).

The save keeps a planet's seed and type number only; the variant ("Standard", "Infested", "Variant_B", ...) is not in it, yet the
words the game puts before "Planet" (planet_word.py) and the biome file it generates the planet from depend on it. The game works
the variant out again from the system's address every time, and so does this: a port of the routines in NMS.exe (build 184271) that
do it, from the address down to a planet's biome and variant:

    0x1355660  the list of bodies: size classes, moons, one seed per body (nms_namegen's planetSeeds, made exact here)
    0x1683ec0  the orbits: only its random draws matter (their number is fixed below)
    0x1682bf0  the biome of every body, then 0x1683d10 and the archive table: its variant

The system's own attributes (how many planets, which star, where the start planet is) come from nms_namegen (third_party/).
The game's weights are in data/planet_generator.json (scripts/build_biomes.py unpacks them from the installed game).

Checked by running the game's own routines (scripts/check_planets_against_game.py, which emulates NMS.exe over a running game's
memory): 459 random systems and the 68 systems of a real save agree on seed, size class, biome and variant of every body. nms_namegen
gets the attributes of about one system in 250 wrong; a planet whose seed or biome the save knows is therefore compared with
what this makes of it (find()) and gets no answer where they differ.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass

import numpy as np

import paths

F = np.float32
_MULT = 0x5A76F899
_MIX_A = 0x64DD81482CBD31D7
_MIX_B = 0xE36AA5C613612997
_MASK = (1 << 64) - 1
UA_BITS = (1 << 52) - 1  # galaxy (8 bits at 32), system (12 bits at 40) and the voxel; the planet index (bits 52..55) is left out

# GcBiomeType and GcBiomeSubType.BiomeSubTypeEnum, as numbers (libMBIN, the game's own enumerations)
BIOME = {"Lush": 0, "Toxic": 1, "Scorched": 2, "Radioactive": 3, "Frozen": 4, "Barren": 5, "Dead": 6, "Weird": 7, "Red": 8, "Green": 9,
         "Blue": 10, "Test": 11, "Swamp": 12, "Lava": 13, "Waterworld": 14, "GasGiant": 15, "All": 16}
SUBTYPE = {"None": 0, "Standard": 1, "HighQuality": 2, "Structure": 3, "Beam": 4, "Hexagon": 5, "FractCube": 6, "Bubble": 7, "Shards": 8,
           "Contour": 9, "Shell": 10, "BoneSpire": 11, "WireCell": 12, "HydroGarden": 13, "HugePlant": 14, "HugeLush": 15, "HugeRing": 16,
           "HugeRock": 17, "HugeScorch": 18, "HugeToxic": 19, "Variant_A": 20, "Variant_B": 21, "Variant_C": 22, "Variant_D": 23,
           "Infested": 24, "Swamp": 25, "Lava": 26, "Worlds": 27, "Remix_A": 28, "Remix_B": 29, "Remix_C": 30, "Remix_D": 31}
INFESTED = SUBTYPE["Infested"]
# The galaxy's kind, by galaxy number modulo 20 (NMS.exe 0x4b00510): 4 is the ordinary one; 1 and 3 give a yellow-star system the
# biome odds of the table rows below (the game's "Lush"/"Abandoned" galaxies), 2 is unused here.
GALAXY_KIND = [4, 4, 2, 4, 4, 4, 1, 4, 4, 3, 4, 1, 4, 4, 2, 4, 4, 4, 3, 4]
# star colours 0..4, then the two extra rows of biomelistperstartype in the order the generator indexes them (rows 5 and 6)
YELLOW_ROW = {3: 5, 1: 6}
GAS_GIANT, MOON = 4, 3  # the size class numbers of a giant and of a moon

_tables: dict | None = None


def tables() -> dict:
    global _tables
    if _tables is None:
        raw = json.loads((paths.RES / "data" / "planet_generator.json").read_text(encoding="utf-8"))
        _tables = {
            "files": {int(k): [(s, F(w), F(p)) for s, w, p in v] for k, v in raw["files"].items()},
            "archive": {int(k): [(s, F(w), F(p)) for s, w, p in v] for k, v in raw["archive"].items()},
            "lists": raw["lists"],
            "rows": [([F(x) for x in r["prob"]], [F(x) for x in r["prime"]]) for r in raw["rows"]],
            "dead_to_weird": F(raw["dead_to_weird"]),
        }
    return _tables


def _mix(v: int) -> int:
    v ^= v >> 33
    v = (v * _MIX_A) & _MASK
    v ^= v >> 33
    v = (v * _MIX_B) & _MASK
    return v ^ (v >> 33)


class _Rng:
    """The generator's random numbers: a 64-bit state in two words, a draw is the new low word."""

    def __init__(self, x: int):
        lo, hi = x & 0xFFFFFFFF, x >> 32
        self.lo = (lo + (lo == 0)) & 0xFFFFFFFF
        self.hi = ((((lo << 16) | (lo >> 16)) & 0xFFFFFFFF) ^ hi ^ lo) & 0xFFFFFFFF

    def next(self) -> int:
        s = self.lo * _MULT + self.hi
        self.lo, self.hi = s & 0xFFFFFFFF, s >> 32
        return self.lo


def _unit(draw: int) -> np.float32:
    return F(draw * 2.0 ** -32)


def _sum(values) -> np.float32:
    total = F(0)
    for v in values:
        total = F(total + v)
    return total


def _pick(weights, target, default: int) -> int:
    """The first entry whose running total reaches the target (the game's loop for biomes)."""
    acc = F(0)
    for i, w in enumerate(weights):
        if not (target < acc) and F(acc + w) >= target:
            return i
        acc = F(acc + w)
    return default


def _pick_variant(weights, target) -> int:
    """The first entry heavier than what is left of the target (the game's loop for variants)."""
    for i, w in enumerate(weights):
        if w > target:
            return i
        target = F(target - w)
    return len(weights)


@dataclass
class Body:
    seed: int
    size: int       # 0..2 for planets, MOON, GAS_GIANT
    parent: int     # the planet a moon circles, else -1
    biome: int = 0
    subtype: int = 0
    start: bool = False  # the system's start planet (bit 16 of a discovery record's second value)
    from_dead: bool = False  # a "Dead" planet the game turned into a "Weird" one
    star: int = 0    # the system's star colour (0 yellow, 1 green, 2 blue, 3 red, 4 purple)
    index: int = 0   # the body's number in the system minus one
    galaxy: int = 0
    extra: bool = False  # a body beyond the system's ordinary planets (descriptor byte +0x52: the prime planets and moons)
    empty: bool = False  # the system has no race (descriptor byte +0x4f)
    abandoned: bool = False  # the system is abandoned (descriptor byte +0x4e)


def _attributes(ua: int) -> dict:
    path = str(paths.RES / "third_party" / "nms_namegen")
    if path not in sys.path:
        sys.path.insert(0, path)
    from nms_namegen.system import systemAttributes
    galaxy, system = (ua >> 32) & 0xFF, (ua >> 40) & 0xFFF
    return systemAttributes((system << 32) | (ua & 0xFFFFFFFF), galaxy)


def _body_list(ua: int, attrs: dict) -> list[Body]:
    """0x1355660: size classes (a size-0 planet may take up to two moons after it), then the seeds, then the extra bodies."""
    rng = _Rng(_mix(ua))
    planets, prime, stop = attrs["planet_count"], attrs["prime_planet_count"], attrs["safe_start_planet"] - 1

    def seed() -> int:
        low = rng.next()
        return _mix((rng.next() << 32) | low)

    bodies: list[Body] = []
    if attrs.get("gas_giant"):
        bodies.append(Body(seed(), GAS_GIANT, -1))
        bodies += [Body(seed(), MOON, 0) for _ in range(planets + prime - 1)]
        return bodies

    # primary bodies: all sizes first, the seeds after them
    n = 0
    while n < planets:
        index = n
        size = (rng.next() * 3) >> 32
        n += 1
        bodies.append(Body(0, size, -1))
        if size == 0:
            moons = ((min(max(planets - n, 0), 2) + 1) * rng.next()) >> 32
            while moons > 0 and n != stop:
                bodies.append(Body(0, MOON, index))
                n += 1
                moons -= 1
    for b in bodies:
        b.seed = seed()
    # the extra ("prime") bodies: size, seed and moons one after the other
    total = planets + prime
    while n < total:
        index = n
        size = (rng.next() * 3) >> 32
        bodies.append(Body(seed(), size, -1))
        n += 1
        if size == 0:
            moons = ((min(max(total - n, 0), 2) + 1) * rng.next()) >> 32
            while moons > 0 and n != stop:
                bodies.append(Body(seed(), MOON, index))
                n += 1
                moons -= 1
    return bodies


def _orbit_draws(ua: int, bodies: list[Body], planets: int) -> _Rng:
    """The state of the system generator's random numbers when the biomes are drawn: the orbit code (0x1683ec0) has used a fixed
    number of draws before it: 2, three for every body among the first `planets` that is no moon, one for every of those planets
    that has moons."""
    rng = _Rng(ua)
    first = bodies[:planets]
    parents = {b.parent for b in bodies if b.size == MOON and 0 <= b.parent < planets}
    for _ in range(2 + 3 * sum(1 for b in first if b.size != MOON) + len(parents)):
        rng.next()
    return rng


def _variant(t: dict, biome: int, star: int, no_infested: bool, draw: int, repick: int) -> int:
    """0x1683d10 and the archive table: the variant of a body of this biome, from the draw that picked the biome's file list."""
    files = t["files"].get(biome) or []
    weights = [F(p) if star == 4 else F(w) for s, w, p in files]
    weights = [F(0) if (s == INFESTED and no_infested) else w for (s, _, _), w in zip(files, weights)]
    first = _pick_variant(weights, F(_unit(draw) * _sum(weights)) if files else F(0))
    chosen = files[first][0] if first < len(files) else 1
    if star == 4:
        return chosen
    archive = t["archive"].get(biome) or []
    if not archive:
        return chosen
    weights = [F(0) if (s == INFESTED and no_infested) else F(w) for s, w, _ in archive]
    pick = _pick_variant(weights, F(_unit(draw) * _sum(weights)))
    if pick < len(archive) and archive[pick][0] == INFESTED:
        return INFESTED
    if chosen == INFESTED:
        weights = [F(0) if s == INFESTED else F(w) for s, w, _ in archive]
        pick = _pick_variant(weights, F(_unit(repick) * _sum(weights)))
        return archive[pick][0] if pick < len(archive) else 1
    return chosen


def _biomes(ua: int, attrs: dict, bodies: list[Body], rng: _Rng) -> None:
    """0x1682bf0: the biome and variant of every body (rng: the state after the orbits)."""
    t = tables()
    galaxy = (ua >> 32) & 0xFF
    kind = GALAXY_KIND[galaxy % 20]
    star = attrs["star_type"]
    prob, prime = t["rows"][YELLOW_ROW[kind] if star == 0 and kind in YELLOW_ROW else star]
    start_l, moon_l, giant_l = t["lists"]["start"], t["lists"]["moon"], t["lists"]["giant"]
    s_all, s_prime = _sum(prob), _sum(prime)
    s_start = _sum(prob[i] for i in start_l)
    s_moon, s_moon_prime = _sum(prob[:len(moon_l)]), _sum(prime[:len(moon_l)])
    s_giant, s_giant_prime = _sum(prob[:len(giant_l)]), _sum(prime[:len(giant_l)])
    planets, extra = attrs["planet_count"], attrs["prime_planet_count"]
    safe = attrs["safe_start_planet"]
    # the game's flag at +0x755 of the system: set where nms_namegen made the whole system one giant with its moons (six bodies);
    # a giant layout with fewer bodies keeps the biomes the table draws
    first_is_giant = bool(attrs.get("gas_giant")) and planets == 0
    second = _Rng(ua)  # the second random stream, used to turn Dead planets into Weird ones
    nonzero = 17 - sum(1 for v in prob if v == 0)
    index, previous = 0, None
    for _ in range(5000):
        if index >= planets:
            break
        start = safe > 0 and index == safe - 1
        no_start_draw = False
        if kind == 3 and start:
            biome, no_start_draw = 0, True
        elif start:
            biome = _by_list(start_l, prob, F(F(_unit(rng.next()) * s_start)), 4)
        elif star == 4 and bodies[index].size == MOON:
            biome = _by_list(moon_l, prob, F(F(_unit(rng.next()) * s_moon)), 6)
        elif bodies[index].size == GAS_GIANT:
            biome = _by_list(giant_l, prob, F(F(_unit(rng.next()) * s_giant)), 6)
        else:
            biome = _pick(prob, F(F(_unit(rng.next()) * s_all)), 0)
        if first_is_giant and index == 0:
            biome = 15
        no_infested = start and kind == 4
        pre = rng.lo, rng.hi
        draw = rng.next()
        again = (draw * _MULT + (((pre[0] * _MULT + pre[1]) >> 32))) & 0xFFFFFFFF
        variant = _variant(t, biome, star, no_infested, draw, again)
        # a body is kept unless it repeats its neighbour's biome (where the table allows another) or is one of the biomes a
        # start planet may not be
        differs = index == 0 or biome != previous or nonzero <= 1
        refuse = False
        if start:
            refuse = biome not in (6, 7, 15)
            if len(start_l) == 1:
                differs = True
        elif planets == 1 and not first_is_giant:
            refuse = True
        body = bodies[index]
        body.biome, body.subtype, body.start = biome, variant, start
        if (not (no_start_draw or index == 0) and not differs) or (refuse and biome in (6, 7, 14, 15)):
            continue
        previous = biome
        index += 1
    else:
        raise RuntimeError("the biome draw did not settle")
    if star != 4:  # Dead planets the game makes Weird
        for body in bodies[:planets]:
            if body.biome == 6 and t["dead_to_weird"] > _unit(second.next()):
                body.biome, body.from_dead = 7, True
                files = t["files"][7]
                body.subtype = files[(len(files) * second.next()) >> 32][0]
    # the extra bodies draw from a copy of the generator's stream, advanced by a number that depends on its next draw
    if extra:
        local = _Rng(0)
        local.lo, local.hi = rng.lo, rng.hi
        for _ in range(local.next() % 11 + 3):
            local.next()
        for k in range(extra):
            body = bodies[planets + k]
            draw = local.next()
            if star == 4 and body.size == MOON:
                biome = _by_list(moon_l, prime, F(_unit(draw) * s_moon_prime), 0)
            elif body.size == GAS_GIANT:
                biome = _by_list(giant_l, prime, F(_unit(draw) * s_giant_prime), 0)
            else:
                biome = _pick(prime, F(_unit(draw) * s_prime), 0)
            if first_is_giant and planets + k == 0:
                biome = 15
            pre = local.lo, local.hi
            draw = local.next()
            again = (draw * _MULT + ((pre[0] * _MULT + pre[1]) >> 32)) & 0xFFFFFFFF
            body.biome, body.subtype = biome, _variant(t, biome, star, False, draw, again)


def _by_list(entries: list[int], weights, target, default: int) -> int:
    acc = F(0)
    for i in entries:
        if not (target < acc) and F(acc + weights[i]) >= target:
            return i
        acc = F(acc + weights[i])
    return default


def bodies(system: int) -> list[Body]:
    """The bodies of the system at this address (galaxy, system and voxel bits; a planet index in it is ignored), in the order of
    their planet numbers minus one."""
    ua = system & UA_BITS
    attrs = _attributes(ua)
    body_list = _body_list(ua, attrs)
    _biomes(ua, attrs, body_list, _orbit_draws(ua, body_list, attrs["planet_count"]))
    import system_attr
    exact = system_attr.attributes(ua)
    for i, body in enumerate(body_list):
        body.star, body.index, body.galaxy = attrs["star_type"], i, (ua >> 32) & 0xFF
        body.extra, body.empty, body.abandoned = i >= exact["planets"], exact["race"] == 7, exact["abandoned"]
    return body_list


def find(address: int, seed: int, vp1: int) -> Body | None:
    """The body of a discovery record (its address with the planet number, the seed and the second value of its VP), only if this
    agrees with what the save says of it (seed, biome, start planet), else None."""
    try:
        listing = bodies(address)
    except (KeyError, IndexError, ValueError, RuntimeError):
        return None
    index = ((address >> 52) & 0xF) - 1
    if not 0 <= index < len(listing):
        return None
    body = listing[index]
    if body.seed != seed or body.biome != vp1 & 0xFFFF or body.start != bool(vp1 >> 16 & 1) or vp1 >> 17:
        return None
    return body
