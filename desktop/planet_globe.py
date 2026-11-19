"""What a planet's globe on the game's Discoveries page is made of: which of the game's layers and in which colours.

The game builds the globe's picture parameters in the planet routine (NMS.exe 0x16c44c0, build 184271) and its layers in 0xfd29b0:

    terrain  one of five terrain pictures (TERRAIN 1..5), tinted with the first colour of the planet's RockLight palette
    water    one of five (WATER 1..5), where the planet has a sea, tinted with the colour of the planet's water (one of 19 water
             settings, drawn at stage 17; its colour is worked out from the setting's scatter and transmittance colours)
    clouds   one of five (CLOUDS 1..5), as opaque as the weather is stormy (the weather class halved)

Which picture of five each is comes from the first three draws of the planet's own seed. The palette colours are the game's 66 palettes
of the planet (stage 2 of the planet's seed, 0x63a460): the palette file of the planet's type and variant, else the game's base file.

Checked against the game's own routine run in an emulator (see scripts/check_planets_against_game.py): the terrain colour, the water
colour and the water setting of every planet tried. Not worked out: the rings of a planet (the system generator's flag) and the colour
of a gas giant.
"""
from __future__ import annotations

import math

import numpy as np

import planet_data
import planet_gen
import planet_word as pw

F = np.float32
BASE = "metadata/simulation/solarsystem/colours/basecolourpalettes.mbin"  # the palettes a biome's file falls back to
MODE = {"Inactive": 0, "_1": 1, "_4": 2, "_8": 3, "_16": 4, "All": 5}
ROCK_LIGHT = 39  # the palette the terrain colour comes from: after 39 palettes of 5 colours, two draws each
WATER_STAGE = 17  # the stage of the planet's seed the water setting is drawn at (after two draws)
# the log2 the game's water-colour routine uses (a polynomial over the mantissa), and its constants (NMS.exe 0x2c5d20)
_LOG = [F(0.051421381533145905), F(0.009136402048170567), F(0.13657398521900177), F(0.2411404848098755), F(0.3469993472099304),
        F(0.4786171615123749), F(0.7211589217185974), F(1.4426896572113037)]
_EPS, _LN2 = F(0.009999999776482582), F(0.6931471824645996)
_U = 2.0 ** -32 * (1 + 2.0 ** -32)


def _quantise(mode: int, i: int) -> int:
    """Which of a palette's 64 colours an index means in the palette's mode (the game's colour lookup, 0x21fe40)."""
    if mode == 1:
        return 0
    if mode == 2:
        return ((((i & 7) >> 2) + (i >> 5) * 8)) << 2
    if mode == 3:
        return i & 7
    if mode == 4:
        return (((i & 7) >> 1) + (i >> 4) * 8) * 2
    return i


_CLOSE = F(2.3283064e-10)  # two colours of a palette closer than this (squared distance) are the same: the pick moves on to the next index


def _palette(file: str, palette: int) -> tuple[int, list]:
    """The palette's mode and 64 colours in the biome's palette file, else in the base file (the game's group 16)."""
    t = planet_data._tables()["palettes"]
    mode, colours = t.get(file, t[BASE]).get(str(palette)) or t[BASE][str(palette)]
    if mode == "Inactive":  # the biome's file does not make this palette: the base file does
        mode, colours = t[BASE][str(palette)]
    return MODE[mode], colours


def pick(file: str, palette: int, slot: int, seed: int) -> list[float]:
    """The colour in slot 0..4 of the planet's palette (the game's palette picker 0x63ab90 over the planet's colour seed): every slot
    draws two numbers, takes the colour the palette's mode makes of them and, if an earlier slot has that colour, the next index."""
    m, colours = _palette(file, palette)
    a, b = pw._state(pw.stage_seed(pw.stage_seed(seed, 2), 0))
    if palette == 0:  # grass is made again, from the second hash of the state after palette 51 (so it is not the one of the first pass)
        for _ in range(52 * 10):
            a, b = pw._step(a, b)
        for _ in range(2):  # two hashes of two draws each; the second one is the grass seed
            l1, h1 = pw._step(a, b)
            l2, h2 = pw._step(l1, h1)
            seed_hash = pw._mix((l2 << 32) | l1)
            a, b = l2, h2
        a, b = pw._state(seed_hash)
    else:
        for _ in range(palette * 10):  # every palette before it takes five slots of two draws
            a, b = pw._step(a, b)
    chosen: list[list[float]] = []
    for _ in range(slot + 1):
        a, b = pw._step(a, b)
        d1 = a
        a, b = pw._step(a, b)
        hi, lo = d1 >> 29, a >> 29
        index = (0 if m == 1 else ((lo >> 2) + (hi >> 2) * 8) * 4 if m == 2 else lo if m == 3 else ((lo >> 1) + (hi >> 1) * 8) * 2 if m == 4
                 else lo + hi * 8)
        for tries in range(65):
            colour = colours[_quantise(m, index)]
            if tries == 64 or not any(F(sum(float(F(F(x) - F(y)) ** 2) for x, y in zip(c, colour))) < _CLOSE for c in chosen):
                break
            index = (index + 1) & 63
        chosen.append(colour)
    return list(chosen[slot])


def terrain_colour(body: planet_gen.Body) -> list[float]:
    """The terrain colour, RGB 0..1: tile 1 of the planet's tile set, a colour of one of its palettes (which, the biome's tile type file
    says; the set is drawn by stage 5 of the planet's seed among the file's sets)."""
    t = planet_data._tables()
    f = t["files"].get((body.biome, body.subtype)) or {}
    sets = t["tiles"].get(f.get("tiles", ""), [[ROCK_LIGHT, 0, 1.0]])
    a, b = pw._state(pw.stage_seed(body.seed, 5))
    d, _ = pw._step(a, b)
    total = F(0)
    for _, _, p in sets:
        total = F(total + F(p))
    target = F(F(float(d) * _U) * total)
    cum, chosen = F(0), 0
    for i, (_, _, p) in enumerate(sets):
        cum = F(cum + F(p))
        if cum > target:
            chosen = i
            break
    palette, slot, _ = sets[chosen]
    return pick(f.get("palette", BASE), palette, slot, body.seed)


def water_setting(seed: int) -> int:
    """Which of the game's water settings the planet has (drawn by their weights)."""
    water = planet_data._tables()["water"]
    a, b = pw._state(pw.stage_seed(seed, WATER_STAGE))
    a, b = pw._step(a, b)
    a, b = pw._step(a, b)
    a, b = pw._step(a, b)
    total = F(0)
    for w in water:
        total = F(total + F(w["weight"]))
    c = F(2.0 ** -23)
    target = F(F(F(float(a) * _U) * F(total - c)) + c)
    cum = F(0)
    for i, w in enumerate(water):
        cum = F(cum + F(w["weight"]))
        if cum >= target:
            return i
    return 0


def _log2(x: np.float32) -> np.float32:
    m, e = math.frexp(float(x))
    t = F(F(F(m) + F(m)) - F(1.0))
    p = F(_LOG[0] - F(t * _LOG[1]))
    for sign, c in ((-1, _LOG[2]), (1, _LOG[3]), (-1, _LOG[4]), (1, _LOG[5]), (-1, _LOG[6]), (1, _LOG[7])):
        p = F(F(p * t) + c) if sign > 0 else F(F(p * t) - c)
    return F(F(p * t) + F(e - 1))


def _absorption(colour: list[float], distance: float) -> list[np.float32]:
    inv = F(F(1.0) / F(distance))
    return [F(F(-F(_log2(F(max(float(F(x)), float(_EPS)))) * _LN2)) * inv) for x in colour]


def water_colour(setting: int) -> list[float]:
    """The colour of a water setting on the globe (the game's routine at 0x16da2c0: the single-scattering albedo of the setting's
    scatter against its transmittance, turned into a reflectance); may be above 1."""
    w = planet_data._tables()["water"][setting]
    out = []
    for s, t in zip(_absorption(w["scatter"], w["scatter_distance"]), _absorption(w["transmittance"], w["transmittance_distance"])):
        albedo = F(s / F(s + t))
        rho = F(F(1.0 - albedo) / F(1.0 - F(F(0.8) * albedo)))
        root = F(math.sqrt(float(rho))) if rho >= 0 else F(0)
        out.append(float(F(F(F(5.0) * F(F(1.0) - F(F(0.139) * root))) * F(F(1.0) - root)) / F(F(1.0) + F(F(1.17) * root))))
    return out


def variants(seed: int) -> tuple[int, int, int]:
    """Which terrain, water and cloud picture (1..5) the planet has: the first three draws of its seed, a fifth of the range each."""
    a, b = pw._state(seed)
    out = []
    for _ in range(3):
        a, b = pw._step(a, b)
        out.append((a * 5 >> 32) + 1)
    return out[0], out[1], out[2]


def gas_colour(seed: int) -> list[float]:
    """The colour of a gas giant: its day sky colour set (stage 13 of its seed, one draw among the six, by weight) names an atmosphere
    and the game's atmosphere list gives that one's colour on the Discoveries page."""
    t = planet_data._tables()
    a, b = pw._state(pw.stage_seed(seed, 13))
    a, b = pw._step(a, b)
    c = F(2.0 ** -23)
    total = F(0)
    for _, w in t["gas"]:
        total = F(total + F(w))
    target = F(F(F(float(a) * _U) * F(total - c)) + c)
    cum = F(0)
    for name, w in t["gas"]:
        cum = F(cum + F(w))
        if cum >= target:
            return list(t["atmospheres"][name])
    return list(t["atmospheres"][t["gas"][0][0]])


def spec(body: planet_gen.Body, rings: bool = False) -> dict | None:
    """The globe of a planet: {"terrain": [variant, [r, g, b]], "water": [variant, [r, g, b]] or None, "waterworld": bool,
    "clouds": [variant, opacity], "rings": bool}, for a gas giant {"gas": [r, g, b], "rings": bool}. rings: whether the system's
    generator gave this body rings (planet_gen.ring_body)."""
    if body.biome == 15:
        return {"gas": [round(x, 4) for x in gas_colour(body.seed)], "rings": rings}
    t, w, c = variants(body.seed)
    ground = planet_data.terrain(body.seed, body, body.star)
    colour = [round(x, 4) for x in water_colour(water_setting(body.seed))]
    klass = planet_data.levels(body.seed, body, body.star, body.galaxy, body.index)["weather_class"]
    return {"terrain": [t, [round(x, 4) for x in terrain_colour(body)]],
            "water": [w, colour] if ground["water"] > 0 else None,
            "waterworld": False,  # the game builds a waterworld's globe of the same three layers (its sea is only deeper); the full-sea picture is not used
            "clouds": [c, min(1.0, 0.5 * klass)], "rings": rings}
