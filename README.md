# NMS Items — No Man's Sky refining & cooking, in the terminal

A **TUI** for the two lookups you actually make while playing: *what does this
refine into*, and *how do I get that from what I'm carrying*. Plus a printable
**cheat sheet** of the recipes worth memorising.

Every number comes from the game's own recipe table — 357 refining and 1,323
cooking recipes — not from a wiki transcription. It grew out of a set of
written guides (the Suika Box notes); `20.refiner-recipes.md` is the prose
version of what this app queries.

![the recipe list](docs/img/recipes.svg)

---

## What's inside

| | |
| --- | --- |
| ⌨️ **`nms`** | The TUI: fuzzy search, reverse lookup, chain planning, inventory. `mise run tui` |
| 🖨️ **Cheat sheet** | Three-page landscape A4 ([Typst](https://typst.app)) — the money engine, the nanite ladder, the kitchen. Catppuccin **Latte** for print and **Mocha** for screens. `mise run pdf` |
| 🧮 **Recipe graph** | Chain planner that answers "cheapest way to N of X from things I can pick up" — the same graph walk that produced the Tier 0/1/2 lists in the notes |
| 💠 **Nanite ladder** | Every route to nanites ranked by nanites/hour, with how gettable each input is and where it drops |
| 🍳 **Cooking buffs** | What each dish does when you eat it, per stat, with what it sells for |
| 🔫 **Multi-tools** | The 8 types compared, the 5 weapons measured, and how to get the free S-class ones |
| 🌀 **Portal addresses** | Glyphs ↔ galactic coordinates, offline, plus the addresses from the guides — where the good tools and Exotics are |
| 🗄️ **Where does it go?** | Every item's home in the storage guide's layout — one of the ten Storage Containers, the Nutrient Processor, Cold Storage — or *sell*, *junk*, *use it now*. Type a home ("sell", "cold") to list everything that goes there |
| 📦 **Inventory** | Type what you're carrying; see what refines right now and what you're one ingredient short of |

---

## On the web

`web/` is a static version of the same screens — recipes, chain planner,
nanites, cooking, multi-tools, portal addresses with the glyphs drawn, storage,
inventory — for a phone next to the game or anyone without a terminal. No
server, no Python at runtime: `scripts/build_web.py` runs the same modules the
TUI uses and exports their answers into `web/data.json` (about 75 KB gzipped),
and the page only searches, sorts and draws. The chain tree walk, the inventory
matching and the portal arithmetic are the only logic redone in JavaScript
(`web/core.js`), and `tests/test_web.py` runs them under node against the
Python so the two cannot drift.

```fish
mise run site       # export data.json and serve web/ on localhost:8001
```

It is live at **[nms.dlu.one](https://nms.dlu.one)**.
`.github/workflows/pages.yml` runs the tests, exports the data and publishes
`web/` to GitHub Pages on every push to `main`; the cheat-sheet PDFs are
published with it. The custom domain is a repo setting, not a `CNAME` file --
an Actions deploy ignores one -- so `scripts/pages.py` manages it through `gh`
(`mise run pages-setup`, `pages-https`, `pages-status`). DNS is a Cloudflare
`CNAME` record `nms → rdlu.github.io`, DNS only, so GitHub can issue the
certificate. `mise run deploy` is the whole release: tests, push, watch.

It wears the same skin as the dotfiles and plugii sites: iA Writer Duo for
text, 0xProto for code, numbers and navigation (both self-hosted in
`web/fonts/` with their OFL licenses), square corners and `┌─ Title ───` pane
headings. Dracula accents on neutral greys in the dark, Alucard in the light.

What lives in the browser stays there: the inventory and any portal addresses
you save are kept in `localStorage`. *Export mine* on the portals page downloads
the saved addresses in `data/locations.json`'s shape, to merge into the file.

---

## Using it

```fish
mise install        # uv + typst
mise run setup      # fonts for the PDF, potrace for the glyphs (paru)
mise run sync       # python deps
mise run tui        # go
```

### Keys

`Ctrl+P` opens the **command palette**, which lists every mode the app has by
name and marks the one you are in:

```
● Recipes: Refining          ● Sort: multiplier        Nanite ladder
· Recipes: Cooking           · Sort: fastest           Portal addresses
· Recipes: All recipes       · Sort: units profit      Inventory
```

Type `profit` and press Enter to sort by profit; `shared` to filter saved
addresses to the ones other people found. Cycle keys are faster once you know
the order and opaque until you do — pressing `s` four times reaches "units
profit", but nothing on screen ever said that was an option. The palette is
also what lets the footer group its keys: nothing is hidden by being left out
of the bar.

**Themes.** The palette's *Theme* entry recolours the whole app, and the
choice is remembered. The default, `dracula-clear`, is Dracula's accents with
no background at all: your terminal's own shows through, transparency
included. `dracula-neutral` is the same accents on solid greys, because stock
Dracula's `#282A36` reads as blue next to a black terminal. Every Textual
built-in works too.

Vim motions work in every table, tree and scrollable pane:

| | |
| --- | --- |
| `j` `k` | down / up · `h` `l` pan a wide table sideways |
| `g g` `G` | top / bottom · `ctrl+d` `ctrl+u` half page |
| `/` | search — **insert mode**: type freely, `Esc` or `Enter` returns to normal mode |
| `Esc` | in normal mode, clears the search and any filter |

Then the actions:

| | |
| --- | --- |
| `f` `s` | cycle domain (refining / cooking / all) and sort — or pick either by name from `Ctrl+P` |
| `p` `r` | recipes that **produce** the highlighted item / that **consume** it |
| `Enter` | pivot to everything touching that item · `Backspace` clears the filter |
| `c` | **chain plan** it — inside: `t` source tier, `n` quantity, `C` allow cooking |
| `n` | the **nanite ladder** — every route to nanites, ranked |
| `e` | **cooking effects** — what each dish does when eaten |
| `m` | **multi-tools** — types, weapons, getting one, tips |
| `P` | **portal addresses** — convert glyphs, and the places worth going |
| `a` `i` | add to inventory / open the inventory screen (`/` opens its add field) |
| `w` | **where does it go?** — the storage container for an item, or whether to sell or junk it |
| `d` | show/hide the detail pane — it hides itself below 100 columns |
| `?` | full help |
| `ctrl+p` | command palette — every mode by name |

### Reading the columns

- **Mult** — units out per unit in. `x6 loop` means the recipe feeds itself:
  `1 Chlorine + 2 Oxygen → 6 Chlorine` multiplies the seed six times, which is
  the only kind of recipe that grows a stack out of nothing.
- **Time** — one batch, from the game files. The in-game display is often wrong.
- **Machine** — Portable/Personal (1 input), Medium (2), Large (3).
- **Rate / Profit** — units per hour with one machine kept fed, and the
  base-value difference across one batch. Profit is in units and says nothing
  about nanites; those get their own screen.
- **Gettable** — how reachable the hardest ingredient is. `T0/T1/T2 +n` means
  refinable from surface materials / asteroids / an atmosphere harvester, `n`
  refining steps away. `needs seed` means refinable but wanting a material none
  of those tiers contain — a stellar metal, typically, of which you need two
  units ever. `loot (...)` means no recipe makes it.

### The chain planner

Pick any item, press `c`, and it works backwards to a source set — by default
the five things you can pick up on any planet (Oxygen, Carbon, Ferrite Dust,
Di-hydrogen, Sodium), `t` widens that to asteroids and then an atmosphere
harvester. The cost it minimises is **refiner-seconds per unit**, so the plan is
the one that ties up a machine for the least time, not merely the shortest one.

![a production chain](docs/img/chain.svg)

If nothing reaches the target it says so and lists what the item *is* made
from — that is how you find out something has to be looted rather than refined.

### Nanites

Nanites are the second currency, and a units column is actively misleading
about them: one Salvaged Data is ~51,000 units *or* 15 nanites. Press `n` for
every route to nanites ranked by nanites/hour per refiner — which reproduces
the guide's finding that Larval and Hadal Cores (3,000/h) beat the headline
230-nanite Hyaline Brain (259/h) twelvefold, and that Runaway Mould is the
slowest converter in the game at 24/h.

Each row also carries how gettable the input is and where it drops.

![the nanite ladder](docs/img/nanites.svg)

### Cooking

Eat or sell? Both, in that order. Every cooked product grants a temporary buff
*and* multiplies base value several times over, so the dish you eat is the dish
you sell — cook the batch, eat one, sell the rest. Press `e` for the 19 buffs
and the strongest dishes for each, with what they sell for and what one batch
adds over its ingredients.

![cooking buffs](docs/img/food.svg)

### Multi-tools

Four tabs: the 8 types side by side, the 5 primary weapons with their measured
best hit, where each rare type comes from (three of them free — the Harmonic
Camp puzzle, Sentinel Pillars, Korvax Monolith interfaces), and the tips that
matter: adjacency is horizontal and vertical only, supercharged slots want a
2×2 block, and Damage Potential is not damage output.

![multi-tools](docs/img/multitools.svg)

### Portal addresses

Press `P`. One box does both jobs: paste a **portal code** (twelve hex digits,
one per glyph), a **galactic address** (`0824:007F:00F3:01AC`, what a signal
booster shows) or a nmsportals.github.io link and it converts as you type —
type anything else and it searches the addresses you have saved.

![portal addresses](docs/img/portals.svg)

It is [nmsportals.github.io](https://nmsportals.github.io/) offline, with the
same constants:

```
galactic X = (portal X + 2047) % 4096      portal X = (galactic X + 2049) % 4096
galactic Y = (portal Y +  127) %  256      portal Y = (galactic Y +  129) %  256
galactic Z = (portal Z + 2047) % 4096      portal Z = (galactic Z + 2049) % 4096
```

The two frames disagree only about where zero is — portal coordinates count
from the **centre** of the galaxy, galactic ones from a corner — which is the
whole reason the same place has two unrecognisably different addresses. The
test suite pins that on the one fact both agree about: portal `000000000000`
is the galaxy centre, and galactic coordinates call it `07FF:007F:07FF`.

An address reads `p SSS YY ZZZ XXX` — planet, system index, then the voxel as
height, width, length. The screen colours each field in the code, in the glyph
list and in the drawn symbols, so it is obvious which three glyphs are X.

🔑 **The hex digit is the position on the dial.** The 16 glyphs sit in a fixed
order, `0`–`9` then `A`–`F`, so `A` is the eleventh symbol, every time — and
you need all 16 unlocked, not twelve.

#### The symbols themselves

A hex code is only half an address: at the portal you are looking at sixteen
pictures, not sixteen digits. So the actual shapes are in here too, once, in
`data/glyphs.json` — outlines traced off the art
[nmsportals](https://nmsportals.github.io/) draws its dial with, plus the same
mask knocked down to braille for the terminal. `mise run glyphs` re-derives
both; it needs `potrace`, and it is deliberately **not** part of
`mise run refresh`, because the symbols do not change when the game patches.

One source, two shapes, because the two places a glyph appears want opposite
things. The cheat sheet wants **vectors**: the fill is left out of the traced
path, so the same shape prints dark on Latte and light on Mocha — a PNG of
white line art would simply vanish on paper. A terminal wants **characters**:
it cannot show a PNG and no ordinary font has these symbols, so the same mask
is also stored as braille, 2×4 dots per cell, which is the only resolution
fine enough to keep `sunset` from collapsing into a blob.

On the portal screen both the converter and the saved-address detail draw the
twelve symbols, coloured by field the way the hex already is. The layout is
whatever the pane can hold: twelve across at 8×4 cells wants 107 columns, at
6×3 it wants 83, and below that it stacks six and six on the field boundary —
planet, system and Y above, Z and X below. Under about 40 columns it gives up
and leaves the hex, which is all it ever had.

Whether that draws is up to the terminal, not the app. **Ghostty draws braille
itself**, with its internal sprite renderer rather than the font — ask it:

```fish
ghostty +show-face --string="A⣿"
# U+41 « A » found in face "JetBrains Mono".
# U+28FF « ⣿ » is handled by Ghostty's internal sprites.
```

so it is cell-perfect there whatever `font-family` says. A terminal that asks
the font instead needs one carrying `U+2800`–`U+28FF`: plain JetBrains Mono
does **not** have it, its Nerd Font build does, and so do most patched
monospace fonts. With neither you get boxes where the glyphs should be, and
nothing else on the screen changes.

Because nothing at runtime re-derives that file, `mise run pdf` checks it
against `portals.py` before drawing: one position out and every address on the
sheet would point at a different star, plausibly.

| | |
| --- | --- |
| `D` | dial an address glyph by glyph — for when all you have is the symbols, off a video or a screenshot |
| `y` `Y` | copy the portal code / the galactic address |
| `s` `e` `d` | save what is converted, edit it, drop it to the trash |
| `u` `T` | undo the last drop / show the trash |
| `f` `o` | filter the saved list by kind / by who found it |
| `p` | change the planet glyph — the one a galactic address cannot carry |
| `Enter` | on a saved row, loads it back into the converter |

#### Mine, and shared

Every saved address is one of two kinds, and `o` cycles between them:

| | |
| --- | --- |
| **mine** | you stood there. Stamped with the date you saved it. The default when you press `s` |
| **shared** | off a catalogue or from a friend |

That split is worth more than it looks. What is verified in a catalogue entry
is the **address** — the location is seeded to the coordinate and generally
survives a patch. The class, the slot count and the headline damage figure are
somebody else's claim about somebody else's save, and those rot. Your own finds
are the ones you can vouch for.

The save form takes a prefix for Kind and Found — `multi`, `s` — and refuses
anything it cannot read rather than correcting it quietly: a kind that is not a
kind used to become `other`, and a galaxy of `twelve` used to become Euclid,
both without a word. The address itself needs no checking, since the form only
opens on one that already parsed. Saving a code you already have is allowed —
one system can hold a tool *and* a ship — but it says so.

Nothing deletes outright. `d` moves an address to the trash, `u` takes the last
one back, `T` lists what is in there — and inside the trash `u` restores the row
you are on while `d` is the one that really deletes. The trash rides along in
the same file under `_trash`, keeping the drop date and the row it came from, so
undo puts an address back where it was rather than at the end, and something
dropped in one session is still recoverable in the next.

The saved addresses live in `data/locations.json`, committed alongside the
guides they came from rather than hidden in XDG state, because they are
findings: they diff, review and share like everything else here. Press `s` to
add one through a form, or edit the file directly — it carries its own schema.
It ships with the fifteen from the Euclid shortlists in guides
21 (`21.multitool-damage.md`) and 14 (`14.starships-ranked.md`)
— seven multi-tools and eight Exotic starships, read off the Portal Repository
in September 2026, all marked `shared`. From the multi-tool screen, `P` opens
the list already filtered to tools.

### Inventory

![inventory](docs/img/inventory.svg)

---

### The cheat sheet

`mise run pdf` writes `docs/pdf/nms-cheatsheet.pdf` (Latte, for print) and
`nms-cheatsheet-dark.pdf` (Mocha, for screens):

1. **Money engine** — the ×6 loops, the precious-metal engine, best profit per
   batch and per machine-hour, the six refiner rules.
2. **Nanites** — every converter with where its input drops, then the
   essentials you should stop mining, and what Tier 0 / Tier 1 reach.
3. **Kitchen** — top dishes by value, then all 19 buffs with their three best
   dishes each.
4. **Multi-tools** — the 8 types, the weapons measured, how to get the free
   ones, and the adjacency and supercharged-slot rules.
5. **Portals** — all 16 glyphs in dial order **drawn**, how to read an address,
   the conversion both ways, and every saved address in two tables: the ones
   you found and the ones you were told about. Every address carries its twelve
   symbols beside the hex, coloured by field, so at the portal you dial off the
   page without translating anything.

It is generated from `data/cheatsheet.json`, so it cannot drift from the app —
including its own prose: claims like "every row below is 5s in the Processor"
are re-checked against the rows on each build and disappear if they stop being
true. The portals page goes further: `mise run pdf` round-trips every address
and re-checks the galaxy-centre invariant, so the build fails rather than
printing a code you cannot dial.

## Where the data comes from

[NMS-Handbook](https://github.com/ApexFatality93/NMS-Handbook) parses
`NMS_REALITY_GCRECIPETABLE.MXML` straight out of the game files into JSON.
`scripts/fetch_source.py` pulls four of its tables into `.cache/` (gitignored)
and `scripts/build_data.py` flattens them into the two committed files the app
reads:

| | |
| --- | --- |
| `data/items.json` | 1,447 items — the 693 that recipes touch plus everything else that can sit in a cargo slot. Name, type, category, rarity, base value, and for cooked food the stat it buffs and how strongly |
| `data/recipes.json` | 1,680 recipes — flat, with ratio, loop multiplier, batch time, profit and rate precomputed |
| `data/cheatsheet.json` | the subset the PDF prints |
| `data/acquisition.json` | **hand-written** — where loot comes from, since the game files record what a recipe needs but never where to find it. Taken from the guides; where they say nothing, the app says "unknown" rather than guessing |
| `data/storage.json` | **hand-written** — the storage layout from guide 24, section 10: what each of the ten containers holds, as ordered rules. The guide's named items first, then their families by the game's own subtitle and type; first match wins, no match means 9 - Inbox |
| `data/multitools.json` | **hand-written** — the multi-tool reference. The game files carry nothing useful about multi-tools, so this comes wholesale from guides 05 and 21 |
| `data/locations.json` | **hand-written** — portal addresses, from the Euclid shortlists in guides 14 and 21, plus whatever you find. The `s` key on the portal screen appends to it |
| `data/glyphs.json` | the 16 symbols — outlines for the PDF and braille for the terminal, both traced from the [nmsportals](https://nmsportals.github.io/) dial art by `mise run glyphs`. Regenerated only if it is lost; the glyphs do not move |

After a game patch:

```fish
mise run refresh    # fetch → normalise → re-pick the cheat sheet → rebuild PDFs
mise run test       # 13 checks, including the numbers the written guides assert
```

The test suite is the point of that second command: it asserts the claims the
notes make — the three ×6 loops, Living Pearl → 100 Gold, Tier 0 reaching
exactly 30 materials, the 25 items no recipe produces, Larval Cores at 3,000
nanites/hour against Runaway Mould's 24 — so if upstream or the game moves a
ratio, it fails loudly instead of quietly printing a wrong sheet.

---

## Tasks

| Task | Does |
| --- | --- |
| `mise run tui` | the app |
| `mise run dev` | the app with live CSS reload, for editing `app.tcss` |
| `mise run web` | serve the TUI itself in a browser on `:8000` (textual serve) |
| `mise run web-data` | export `web/data.json` for the static site |
| `mise run site` | export, then serve the static site on `:8001` |
| `mise run test-web` | only the web checks: the export, and `web/core.js` against the Python |
| `mise run favicon` | redraw the site icon from the Atlas glyph |
| `mise run check` | what CI runs: the full suite and the web export |
| `mise run deploy` | check, push `main` over SSH, and follow the Pages deploy |
| `mise run pages-status` | DNS, Pages settings, certificate and the last deploy |
| `mise run pages-setup` | turn Pages on with the Actions source and the `nms.dlu.one` domain |
| `mise run pages-https` | enforce HTTPS once the certificate is issued |
| `mise run pdf` | both cheat-sheet PDFs into `docs/pdf/` |
| `mise run pdf-watch` | rebuild the light PDF on every save |
| `mise run refresh` | full data rebuild from upstream |
| `mise run glyphs` | re-trace the 16 portal symbols into `data/glyphs.json` |
| `mise run test` | pytest — data integrity + a headless pass over the TUI |
| `mise run screenshot` | regenerate the SVGs in this README |

---

## Layout

```
src/nms_items/
  model.py     items, recipes, the forward/reverse indexes, search
  graph.py     chain planning (Knuth's AND-OR Dijkstra), reachability, the nanite ladder
  ease.py      how gettable an item is: tier, chain depth, raw breadth, loot notes
  food.py      cooked dishes grouped by the buff they grant
  multitools.py  the hand-written multi-tool reference, loaded from data/
  portals.py   glyphs <-> galactic coordinates, and the saved addresses
  glyphart.py  the 16 symbols as braille, for drawing a code in a terminal
  inventory.py what you're carrying, persisted to XDG state
  app.py       the recipe table + detail pane
  screens.py   chain, nanites, cooking, multi-tools, portals, inventory, help
  widgets.py   the vim-keyed DataTable, Tree, scroll pane and search box
scripts/       fetch, normalise, pick cheat-sheet rows, trace glyphs, screenshots, web export
web/           the static site: index.html, app.js (views), core.js (logic), style.css, fonts/
scripts/pages.py  GitHub Pages settings for nms.dlu.one, via gh
cheatsheet.typ the PDF
```

---

## License

[GPL-3.0](LICENSE). Recipe and item data are derived from
[NMS-Handbook](https://github.com/ApexFatality93/NMS-Handbook) (GPL-3.0), which
extracts them from the game files; No Man's Sky and its data belong to Hello
Games. Portal glyphs are traced from [nmsportals](https://nmsportals.github.io/).
