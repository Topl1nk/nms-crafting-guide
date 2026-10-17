# What changed with Cosmos

The data in `data/` was rebuilt from the game files of **No Man's Sky Cosmos
7.06, build 180836** (GOG build 60091801558572527, archives dated 2026-09-30),
with hgpaktool 1.1.3 and MBINCompiler v7.04.1-pre3, on 2026-10-17. Before that
it came from NMS-Handbook, last updated in February 2026, which does not record
the game version it parsed.

So this is the difference between that Handbook snapshot and Cosmos 7.06. It
is not strictly Cosmos alone: anything a patch between February and Cosmos
changed shows up here too, and some of the added items (the season 22/23
expedition rewards, the Twitch drops) look older than Cosmos. The extractor
itself adds nothing: rebuilt from the same game tables, the Handbook path and
the game path give identical `data/`, and every item and recipe the two
snapshots share came through unchanged apart from the lines below.

## In short

- **Refining: four new recipes, nothing retuned.** Every one of the 357
  existing refiner recipes keeps its amounts, time and operation. The new ones
  all have the same shape, 5 of a new deep-space material → 1 of something
  familiar in 90 s on a portable refiner (40 units an hour):
  - 5 Comet Dust → 1 Silver (Crystal Processing)
  - 5 Contaminated Metal → 1 Magnetised Ferrite (Metal Decontamination)
  - 5 Gelatinous Fibres → 1 Faecium (Toxin Extraction)
  - 5 Corrupted Ichor → 1 Nanite Cluster (Devitrification)
- **Cooking: no changes.** Still 1,323 recipes, all identical.
- **Items: 51 new, none removed.** The ones that matter here are the four new
  substances above (Comet Dust, Contaminated Metal, Gelatinous Fibres,
  Corrupted Ichor) and a new item type, `SpaceSalvage`: twelve high-value
  products processed at a deep-space outpost purely to be sold, among them
  Reactor Core (220,000 units), Pathogen Sac (201,000), Viral Heart (190,000)
  and Data Packet (185,000). The rest are charts, eggs, expedition rewards and
  Twitch drops.
- Two jellyfish catches, Spawn of Arcadia and Child of Aquarius, changed type from
  Component to Curiosity. Four descriptions were reworded: the Whale Beacon now
  tells you to use Relay Song, two bioship eggs had a typo fixed, and one
  Twitch ship gained a description.

## Guide claims this changes

The test suite asserts the numbers the written guides state. Cosmos changed
three of them. The guide (`20.refiner-recipes.md` and the notes that repeat
it) and the tests were both updated to the Cosmos 7.06 values:

| Claim | Test | Was | Cosmos 7.06 |
| --- | --- | --- | --- |
| Refining recipe count | `test_data.py::test_recipe_counts` | 357 | 361 (cooking unchanged at 1,323) |
| Items no refiner recipe produces | `test_data.py::test_twentynine_items_cannot_be_refined_into_existence` (was `test_twentyfive_...`) | 25 | 29: the four new materials are only ever inputs |
| Nanite converters | `test_ease_food.py::test_nanite_ladder_matches_the_guide` | 14 | 15: 5 Corrupted Ichor → 1 Nanite Cluster, 40/h, second slowest |

Still true: the three ×6 loops (Condensed Carbon, Chlorine, Ionised Cobalt),
Living Pearl → 100 Gold, Tier 0 reaching exactly 30 materials, asteroids adding
9, Larval/Hadal Core at 3,000 nanites/hour as the best converter and Runaway
Mould at 24/hour as the worst, Hyaline Brain → 230 nanites.

The storage layout (`data/storage.json`) gained one family rule so the twelve
`SpaceSalvage` items go to 7 - Sellables instead of the Inbox, since the game's
own description says they are processed to be sold.

## The full report

Generated with `uv run python scripts/data_diff.py --base 75a52ba` (the last
commit built from NMS-Handbook); `mise run extract-diff` gives the same report
against the last commit after the next patch.

### Summary

- Recipes: 1680 → 1684 (357 refining, 1323 cooking → 361 refining, 1323 cooking)
- Recipes added 4, removed 0, changed 0
- Items: 1447 → 1498 (added 51, removed 0, 2 field changes, 4 descriptions reworded)

### Refining

#### Added (4)

| Recipe | Time | Operation |
|---|---|---|
| 5 Comet Dust → 1 Silver | 90s | Crystal Processing |
| 5 Contaminated Metal → 1 Magnetised Ferrite | 90s | Metal Decontamination |
| 5 Gelatinous Fibres → 1 Faecium | 90s | Toxin Extraction |
| 5 Corrupted Ichor → 1 Nanite Cluster | 90s | Devitrification |

### Cooking: no changes

### Items

#### Added (51)

| Id | Name | Type | Subtitle | Value |
|---|---|---|---|---|
| `ACCESS4` | AtlasPass v4 | Curiosity | Access Card | 2,613 |
| `ASTBELT1` | Comet Dust | Substance | Condensate Powder | 190 |
| `ASTEROID_CRYST` | Condensed Stellar Ice | SpaceSalvage | Valuable Comet Fragment | 13,000 |
| `CHART_HULK` | Salvage Claim | Curiosity | Deep-Space Cartographic Data | 45,000 |
| `CHART_PB_CHALL` | Challenger's Invitation | Curiosity | Arena League Invitation | 1,499 |
| `CHART_PB_CHAMP` | Champion's Invitation | Curiosity | Arena League Invitation | 1,499 |
| `CHART_SPACEBASE` | Habitable Asteroid Chart | Curiosity | Anomalous Cartographic Data | 30,000 |
| `EXPD_EGG_23` | Diplo Egg | Curiosity | Gentle Giant Embryo | 3,200 |
| `EXPD_GUN23` | Starbound v0.27 | Curiosity | Exclusive Multifunction Survival Device | 3,000 |
| `EXPD_SHIP23A` | Golden Rasamama S36 | Curiosity | Exclusive Spacecraft | 3,000 |
| `EXPD_SHIP23B` | Vintage Interceptor | Curiosity | Exclusive Spacecraft | 3,000 |
| `HULK1` | Contaminated Metal | Substance | Industrial Salvage | 240 |
| `HULK_AUX` | Auxiliary Core | SpaceSalvage | Rare Salvage Material | 56,000 |
| `HULK_BLACKBOX` | Data Packet | SpaceSalvage | Specialist Salvage Material | 185,000 |
| `HULK_CANISTER` | Compressed Plasma | SpaceSalvage | Rare Salvage Material | 49,000 |
| `HULK_COMMON` | Industrial Salvage | SpaceSalvage | Common Salvage Material | 32,000 |
| `HULK_CORE` | Reactor Core | SpaceSalvage | Rare Salvage Material | 220,000 |
| `HULK_DATACORE` | CPU Harness | SpaceSalvage | Rare Salvage Material | 52,000 |
| `HULK_LOCKBOX` | Stasis Locker | SpaceSalvage | Specialist Salvage Material | 93,000 |
| `HULK_REACTOR` | Fuel Rod | SpaceSalvage | Specialist Salvage Material | 21,000 |
| `HULK_SMUGGLE` | Suspicious Cargo | SpaceSalvage | Specialist Salvage Material | 32,000 |
| `S22_ECHO` | Pilot Echo | Curiosity | Unfragmented Traveller Essence | 1,600 |
| `S22_FRAG_B` | Weaver Echo | Curiosity | Lingering Soul Fragment | 1,600 |
| `S22_FRAG_G` | Sage Echo | Curiosity | Lingering Soul Fragment | 1,600 |
| `S22_FRAG_R` | Royal Echo | Curiosity | Lingering Soul Fragment | 1,600 |
| `S22_SIGNATURE` | Pilot Signature | Curiosity | Unfragmented Traveller Identification | 1,600 |
| `S23_BEACON` | Myth Beacon | Curiosity | Experimental Summoning Technology | 1,600 |
| `S23_ODD_EGG` | Void Egg | Curiosity | Living Curiosity | 32 |
| `S23_PRISMS_EGG` | Companion Egg | Curiosity | Viable Genetic Material | 0 |
| `S23_PROD` | Like-Seed | Curiosity | Window to a Dream | 1,600 |
| `SLIMEPOST1` | Gelatinous Fibres | Substance | Biometallic Strands | 235 |
| `SLIME_BLOB` | Viral Heart | SpaceSalvage | Semi-Sentient Protein Strand | 190,000 |
| `SLIME_STAR` | Pathogen Sac | SpaceSalvage | Pulsating Biomass | 201,000 |
| `SPEC_PB_EGG01` | Aeron Crab Egg | Curiosity | Shellseeker Companion | 800 |
| `SPEC_PB_EGG02` | Wandering Shrimp Tank Egg | Curiosity | Liquid-Suspended Consciousness | 800 |
| `SPEC_PB_EGG03` | Boundary Horror Egg | Curiosity | Spectral Anomaly | 800 |
| `SPEC_PB_EGG04` | Corrupted Quad Egg | Curiosity | Sentinel Spawn Capsule | 800 |
| `SPEC_PB_EGG05` | Geno-Prawn Egg | Curiosity | Abyssal Horror | 800 |
| `SWARMDUST` | Corrupted Ichor | Substance | Corrosive Biofluid | 1,616 |
| `SWARM_GUN` | Direwasp Disintegrator | Curiosity | Exclusive Multifunction Survival Device | 3,000 |
| `TREAT_FREELEVEL` | Retroviral Pellet | Curiosity | Genetic Mutator | 900 |
| `TWITCH_GUN31` | Memories of the Ancients | Curiosity | Exclusive Multifunction Survival Device | 3,000 |
| `TWITCH_GUN32` | Improvised Ion Generator | Curiosity | Exclusive Multifunction Survival Device | 3,000 |
| `TWITCH_GUN33` | Silent Shock Injector | Curiosity | Exclusive Multifunction Survival Device | 3,000 |
| `TWITCH_PET26` | X. Spellristreus Egg | Curiosity | Exclusive Companion Egg | 3,000 |
| `TWITCH_PET27` | N. Heydroadrus Egg | Curiosity | Exclusive Companion Egg | 3,000 |
| `TWITCH_SHIP61` | WK5 Mimar | Curiosity | Exclusive Spacecraft | 3,000 |
| `TWITCH_SHIP62` | Ratsu's Prospect | Curiosity | Exclusive Spacecraft | 3,000 |
| `TWITCH_SHIP63` | Unjiwua's Voyage LO5 | Curiosity | Exclusive Spacecraft | 3,000 |
| `TWITCH_SHIP64` | Mookaw NI8 | Curiosity | Exclusive Spacecraft | 3,000 |
| `TWITCH_SHIP65` | Halcyon Dance VQ6 | Curiosity | Exclusive Spacecraft | 3,000 |

#### Changed fields (2)

| Item | Field | Before | After |
|---|---|---|---|
| Spawn of Arcadia (`F_BOSS_JELLY`) | type | 'Component' | 'Curiosity' |
| Child of Aquarius (`F_JELLYCHILD`) | type | 'Component' | 'Curiosity' |

