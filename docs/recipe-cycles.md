# Real loops in the recipes

Date: 2026-10-25. Computed over all 361 refining recipes and 1323 cooking recipes (Cosmos 7.06 data, `web/data.json`).
Script: [scripts/recipe_cycles.py](../scripts/recipe_cycles.py) (`python scripts/recipe_cycles.py refine`; it needs numpy and
scipy, which the project itself does not).

(The Russian original of this note is in [ru/recipe-cycles.md](ru/recipe-cycles.md).)

## What counts as a loop

A set of recipes that, run in the right proportions, **spends nothing from outside**: for every item "made minus spent" is
at least zero, and for at least one item it is above zero (the profit). Put a starting handful in once and everything keeps
turning by itself. This is a linear problem over all the recipes at once (not a search over pairs): each recipe is checked
for whether it belongs to such a set, then the set is cut down to a minimal one.

**This is not a loop:** "1 Chlorine + 2 Oxygen → 6 Chlorine". The chlorine came back, but the oxygen was spent and no recipe
restores it. That is why the label "x6 loop" on the site was wrong and was replaced by "1→6".

## Result

- Refining: **146 minimal closed sets**, 8 of them of two recipes (the clearest ones, below).
- Cooking: none that is real. The only "loop" is "Wild Yeast → Wild Yeast" (1 for 1, from itself into itself, no profit).

## Paired recipes with a profit (symbiosis)

Catalytic pairs around Chromatic Metal: **no ingredient is used up except the catalyst metal itself, which comes back whole,
and there is more Chromatic Metal left.**

| Pair | What we do | Result of one turn |
|---|---|---|
| **Indium** | 1× "2 Indium → 4 Chromatic Metal" and 2× "1 Indium + 1 Chromatic Metal → 2 Indium" | Indium 0 (all of it back), **+2 Chromatic Metal** |
| **Quartzite** | 1× "2 Quartzite → 4 Chromatic Metal" and 2× "1 Quartzite + 1 Chromatic Metal → 2 Quartzite" | Quartzite 0, **+2 Chromatic Metal** |
| **Emeril** | 1× "2 Emeril → 3 Chromatic Metal" and 2× "1 Emeril + 1 Chromatic Metal → 2 Emeril" | Emeril 0, **+1 Chromatic Metal** |

You need to start once with 2 pieces of the catalyst metal; after that Chromatic Metal is made with no outside raw.
Time: about 25–40 s on a portable refiner and 2×90 s on a medium one per turn.

**Di-hydrogen and its jelly** (the shortest real pair): "30 Di-hydrogen → 1 Di-hydrogen Jelly" (120 s) and
"1 Di-hydrogen Jelly → 40 Di-hydrogen" (1000 s). The round: 30 put in, 40 got out: **+10 (a gain of 1.33 times)**, nothing
else is needed. Both recipes run on a portable refiner; the jelly is made fast, but comes back slowly.

## Exchanges with no loss and no profit (neutral pairs)

There and back, the result exactly zero, useful for turning one kind into another:
Carbon ⇄ Condensed Carbon (2→1 and 1→2), Cobalt ⇄ Ionised Cobalt (2→1 and 1→2),
Magnetised Ferrite ⇄ Pure Ferrite (1→2 and 2→1), Salt ⇄ Chlorine (2→1 and 1→2).

## A loop of four recipes: the Condensed Carbon "engine"

| Recipe | Times |
|---|---|
| 1 Faecium + 1 Condensed Carbon → 3 Condensed Carbon | 1 |
| 2 Carbon + 1 Mordite → 3 Faecium | 0.67 |
| 1 Condensed Carbon → 2 Carbon | 0.67 |
| 3 Faecium → 2 Mordite | 0.33 |

Everything put in comes back, and **+1.33 Condensed Carbon** is left per turn. (There is a second variant of 4 recipes with
"1 Faecium + 1 Mordite → 2 Condensed Carbon", profit +0.33.) A little Faecium and Mordite are needed at the very start.

## Long loops (6–11 recipes)

Dozens more are found: making Sodium Nitrate and Sodium from Faecium/Mordite and Marrow Bulb (6 recipes, +0.75 Sodium Nitrate
per turn), Cobalt (8, +18 Cobalt) and Magnetised Ferrite (9, +1.5 Magnetised Ferrite). The full list:
`python scripts/recipe_cycles.py refine`.

## What to keep in mind

- **The seed.** Every loop needs a starting stock of its inner items (the catalyst, Faecium, Mordite). Where to get it, the loop
  does not say.
- **Time and refiners** are not part of the condition "closed": the jelly comes back in 1000 s, and the Indium loop takes about
  3.5 min per turn.
- Items the game gives out as loot or raw material count as "made" only if some recipe makes them. The other raws are left out of
  the loops on purpose: they do not come out of thin air.
