# NMS Items — No Man's Sky refining & cooking, in the terminal

A **TUI** for the two lookups you actually make while playing: *what does this
refine into*, and *how do I get that from what I'm carrying*. Plus a printable
**cheat sheet** of the recipes worth memorising.

Every number comes from the game's own recipe table — 357 refining and 1,323
cooking recipes — not from a wiki transcription. The written guides this grew
out of live in the Suika Box vault under `01.projects/03.no-mans-sky/`;
[`20.refiner-recipes.md`](../../Documents/Suika%20Box/01.projects/03.no-mans-sky/20.refiner-recipes.md)
is the prose version of what this app queries.

![the recipe list](docs/img/recipes.svg)

---

## What's inside

| | |
| --- | --- |
| ⌨️ **`nms`** | The TUI: fuzzy search, reverse lookup, chain planning, inventory. `mise run tui` |
| 🖨️ **Cheat sheet** | Two-page landscape A4 ([Typst](https://typst.app)), Catppuccin **Latte** for print and **Mocha** for screens. `mise run pdf` |
| 🧮 **Recipe graph** | Chain planner that answers "cheapest way to N of X from things I can pick up" — the same graph walk that produced the Tier 0/1/2 lists in the notes |
| 📦 **Inventory** | Type what you're carrying; see what refines right now and what you're one ingredient short of |

---

## Using it

```fish
mise install        # uv + typst
mise run setup      # fonts for the PDF (paru)
mise run sync       # python deps
mise run tui        # go
```

### Keys

| | |
| --- | --- |
| `/` | search — output, ingredient or operation name |
| `f` `s` | cycle domain (refining / cooking / all) and sort |
| `p` `r` | recipes that **produce** the highlighted item / that **consume** it |
| `Enter` | pivot to everything touching that item · `Backspace` clears the filter |
| `c` | **chain plan** it — inside: `t` source tier, `n` quantity, `k` allow cooking |
| `a` `i` | add to inventory / open the inventory screen |
| `d` | show/hide the detail pane — it hides itself below 100 columns |
| `?` | full help |

### Reading the columns

- **Mult** — units out per unit in. `x6 loop` means the recipe feeds itself:
  `1 Chlorine + 2 Oxygen → 6 Chlorine` multiplies the seed six times, which is
  the only kind of recipe that grows a stack out of nothing.
- **Time** — one batch, from the game files. The in-game display is often wrong.
- **Machine** — Portable/Personal (1 input), Medium (2), Large (3).
- **Rate / Profit** — units per hour with one machine kept fed, and the
  base-value difference across one batch.

### The chain planner

Pick any item, press `c`, and it works backwards to a source set — by default
the five things you can pick up on any planet (Oxygen, Carbon, Ferrite Dust,
Di-hydrogen, Sodium), `t` widens that to asteroids and then an atmosphere
harvester. The cost it minimises is **refiner-seconds per unit**, so the plan is
the one that ties up a machine for the least time, not merely the shortest one.

![a production chain](docs/img/chain.svg)

If nothing reaches the target it says so and lists what the item *is* made
from — that is how you find out something has to be looted rather than refined.

![inventory](docs/img/inventory.svg)

---

## Where the data comes from

[NMS-Handbook](https://github.com/ApexFatality93/NMS-Handbook) parses
`NMS_REALITY_GCRECIPETABLE.MXML` straight out of the game files into JSON.
`scripts/fetch_source.py` pulls four of its tables into `.cache/` (gitignored)
and `scripts/build_data.py` flattens them into the two committed files the app
reads:

| | |
| --- | --- |
| `data/items.json` | 693 items — name, category, rarity, base value |
| `data/recipes.json` | 1,680 recipes — flat, with ratio, loop multiplier, batch time, profit and rate precomputed |
| `data/cheatsheet.json` | the subset the PDF prints |

After a game patch:

```fish
mise run refresh    # fetch → normalise → re-pick the cheat sheet → rebuild PDFs
mise run test       # 13 checks, including the numbers the written guides assert
```

The test suite is the point of that second command: it asserts the claims the
notes make — the three ×6 loops, Living Pearl → 100 Gold, Tier 0 reaching
exactly 30 materials, the 25 items no recipe produces — so if upstream or the
game moves a ratio, it fails loudly instead of quietly printing a wrong sheet.

---

## Tasks

| Task | Does |
| --- | --- |
| `mise run tui` | the app |
| `mise run dev` | the app with live CSS reload, for editing `app.tcss` |
| `mise run web` | serve it in a browser on `:8000` |
| `mise run pdf` | both cheat-sheet PDFs into `docs/pdf/` |
| `mise run pdf-watch` | rebuild the light PDF on every save |
| `mise run refresh` | full data rebuild from upstream |
| `mise run test` | pytest — data integrity + a headless pass over the TUI |
| `mise run screenshot` | regenerate the SVGs in this README |

---

## Layout

```
src/nms_items/
  model.py     items, recipes, the forward/reverse indexes, search
  graph.py     chain planning (Knuth's AND-OR Dijkstra), reachability, inventory queries
  inventory.py what you're carrying, persisted to XDG state
  app.py       the recipe table + detail pane
  screens.py   chain, inventory, help
scripts/       fetch, normalise, pick cheat-sheet rows, screenshots
cheatsheet.typ the PDF
```
