// No Man's Sky cheatsheet — page 1: the money engine and how a refiner behaves,
// page 2: nanites + what a refiner can reach, page 3: the kitchen (money + buffs).
// Pages 2 and 3 switch to two wide columns; page 1 keeps the dense three.
// All numbers come out of data/cheatsheet.json, which is built from the game files;
// the "where" sentences on the nanite page come from the guide notes in the repo.
// Themed with Catppuccin.
//
// Compile (see `mise run pdf`):
//   typst compile --input theme=latte cheatsheet.typ docs/pdf/nms-cheatsheet.pdf
//   typst compile --input theme=mocha cheatsheet.typ docs/pdf/nms-cheatsheet-dark.pdf

#let theme-id = sys.inputs.at("theme", default: "latte")
#let data = json("data/cheatsheet.json")

// Catppuccin Latte (light, print-friendly) and Mocha (dark, screens).
// Latte leaves the page white rather than using the palette's base: a printer
// would lay a grey wash over every sheet for nothing. The zebra stripe keeps
// Latte's own mantle, which now reads harder against white than it did against
// the base — the rows are easier to follow on paper, not fainter.
#let themes = (
  latte: (
    bg: white, text: rgb("#4c4f69"), subtext: rgb("#6c6f85"),
    card: rgb("#e6e9ef"), code: rgb("#1e66f5"), title-text: white,
    pos: rgb("#40a02b"), neg: rgb("#d20f39"),
    accents: (rgb("#40a02b"), rgb("#1e66f5"), rgb("#8839ef"), rgb("#fe640b"),
              rgb("#d20f39"), rgb("#179299"), rgb("#df8e1d"), rgb("#ea76cb")),
  ),
  mocha: (
    bg: rgb("#1e1e2e"), text: rgb("#cdd6f4"), subtext: rgb("#a6adc8"),
    card: rgb("#181825"), code: rgb("#89b4fa"), title-text: rgb("#11111b"),
    pos: rgb("#a6e3a1"), neg: rgb("#f38ba8"),
    accents: (rgb("#a6e3a1"), rgb("#89b4fa"), rgb("#cba6f7"), rgb("#fab387"),
              rgb("#f38ba8"), rgb("#94e2d5"), rgb("#f9e2af"), rgb("#f5c2e7")),
  ),
)
#let pal = themes.at(theme-id)

// How hard the input is to come by, for the nanite table.
#let bands = (
  easy: pal.accents.at(0), ok: pal.accents.at(1),
  work: pal.accents.at(3), hard: pal.accents.at(4),
)

// ─────────────────────────────── helpers ────────────────────────────────────

// 8412300 → 8 412 300, negatives with a real minus sign.
#let num(n) = {
  let v = int(calc.round(n))
  let s = str(calc.abs(v))
  let parts = ()
  let i = s.len()
  while i > 3 {
    parts.push(s.slice(i - 3, i))
    i = i - 3
  }
  parts.push(s.slice(0, i))
  let body = parts.rev().map(p => [#p]).join(h(0.22em))
  if v < 0 { [#sym.minus#body] } else { body }
}

// Profit reads green when it pays for itself, red when it burns value.
#let money(n) = text(fill: if n < 0 { pal.neg } else { pal.pos }, num(n))

// Same, with an explicit sign — for "units gained over the ingredients".
#let gain(n) = text(fill: if n < 0 { pal.neg } else { pal.pos },
  if n < 0 { num(n) } else { [+#num(n)] })

// Whole numbers stay whole, fractions keep their decimals (50 · 0.04).
#let dec(x) = if x == calc.round(x) { num(x) } else { [#x] }

// "1.5m" → 1m30s, "53m" → 53m — the raw values are floats with a unit suffix.
#let secs(s) = {
  let unit = s.slice(-1)
  let v = float(s.slice(0, -1))
  int(calc.round(
    if unit == "m" { v * 60 } else if unit == "h" { v * 3600 } else { v }))
}
#let dur(s) = {
  let n = secs(s)
  if n < 60 {
    str(n) + "s"
  } else {
    let m = int(n / 60)
    let r = calc.rem(n, 60)
    str(m) + "m" + if r > 0 { str(r) + "s" } else { "" }
  }
}

// Machine size = number of input slots.
#let mach(m) = if m.starts-with("Portable") { "P" } else if m == "Medium" { "M" } else if m == "Large" { "L" } else { "N" }

// "A + A + A" → "A ×3" — the game repeats an ingredient instead of counting it.
#let ings(s) = {
  let out = ()
  for part in s.split(" + ") {
    if out.len() > 0 and out.last().first() == part {
      out.at(-1) = (part, out.last().last() + 1)
    } else {
      out.push((part, 1))
    }
  }
  out.map(((n, c)) => if c > 1 { n + " ×" + str(c) } else { n }).join(" + ")
}

// The one value shared by every row of a column, or none if they differ.
// Everything the sheet claims about "every row" is checked against the data.
#let shared(rows, field) = {
  let vs = rows.map(r => r.at(field)).dedup()
  if vs.len() == 1 { vs.first() } else { none }
}

// Per-page header: money engine, nanites, kitchen.
#let headers = (
  ([No Man's Sky Refining],
   [self-multiplying loops · precious metals · best profit · how a refiner behaves]),
  ([No Man's Sky Nanites],
   [the second currency · where the inputs come from · essentials · what a refiner reaches]),
  ([No Man's Sky Kitchen],
   [cook once, eat one, sell the rest · top dishes by units · every buff and its best dishes]),
  ([No Man's Sky Multi-Tools],
   [types · weapons · the free S-class Sentinel tool · supercharged slots · upgrade order]),
  ([No Man's Sky Portals],
   [the 16 glyphs in dial order · glyphs ↔ galactic coordinates · addresses worth the trip]),
)
#set page(
  paper: "a4",
  flipped: true,
  margin: (x: 0.8cm, top: 1.2cm, bottom: 0.8cm),
  fill: pal.bg,
  columns: 3,
  header: context {
    let (title, sub) = headers.at(
      calc.min(counter(page).get().first(), headers.len()) - 1)
    grid(
      columns: (auto, 1fr),
      align: (left + bottom, right + bottom),
      text(size: 14pt, weight: "black", fill: pal.text,
        title + h(4pt) +
        text(size: 9pt, weight: "regular", fill: pal.subtext, "cheatsheet")),
      text(size: 7.5pt, fill: pal.subtext, sub),
    )
  },
  footer: align(center, text(size: 6.5pt, fill: pal.subtext,
    [#num(data.counts.refine) refiner recipes · #num(data.counts.cook) cook
      recipes · #num(data.counts.items) items · times read from the game files
      #if data.at("game", default: "") != "" [(#data.game)] ·
      generated #datetime.today().display() ·
      page #context counter(page).display("1 / 1", both: true)])),
)
#set columns(gutter: 16pt)
#set text(size: 8.0pt, font: "Inter", fill: pal.text)
#set par(leading: 0.4em)
#set list(indent: 0pt, body-indent: 3pt, spacing: 3pt, marker: text(fill: pal.subtext, sym.bullet))
#set enum(indent: 0pt, body-indent: 3pt, spacing: 3pt, numbering: n => text(fill: pal.subtext, weight: "bold", str(n) + "."))
#show raw: set text(font: "JetBrains Mono", size: 0.93em, fill: pal.code)

// ───────────────────────────── building blocks ──────────────────────────────

// Sections cycle through the Catppuccin accents.
#let section-count = counter("section")
#let section(title, body, breakable: false, below: 7pt) = block(breakable: breakable, below: below)[
  #section-count.step()
  #context {
    let i = section-count.get().first()
    let accent = pal.accents.at(calc.rem(i - 1, pal.accents.len()))
    block(
      fill: accent, width: 100%, radius: 2pt, inset: (x: 5pt, y: 3.2pt),
      sticky: true,
      text(fill: pal.title-text, weight: "bold", size: 1.06em, upper(title)),
    )
  }
  #body
]

// A note line directly under a section bar.
#let note(body) = block(inset: (x: 3pt, top: 1.5pt, bottom: 1.5pt), sticky: true,
  text(size: 0.88em, fill: pal.subtext, body))

// Dense striped table with a small header row.
#let dense(cols, aligns, head, ..rows, pad: 1.9pt) = table(
  columns: cols,
  align: aligns,
  stroke: none,
  inset: (x: 3pt, y: pad),
  fill: (x, y) => if y > 0 and calc.even(y) { pal.card },
  table.header(
    ..head.map(h => text(size: 0.82em, weight: "bold", fill: pal.subtext, upper(h)))),
  ..rows,
)

// Recipes whose input lists are too long for one line: headline + inputs below,
// with the in-game operation name you have to pick in the refiner menu.
// One unbreakable block each, so a recipe never straddles a column break.
#let recipes(rows, value, extra: none, show-time: true, show-mach: true) = stack(
  ..rows.enumerate().map(((i, r)) => block(
    width: 100%, breakable: false,
    fill: if calc.odd(i) { pal.card },
    inset: (x: 3pt, y: 1.5pt),
    grid(
      columns: (1fr, auto),
      align: (left, right),
      column-gutter: 4pt, row-gutter: 1pt,
      text(weight: "bold", r.make),
      value(r),
      grid.cell(colspan: 2, {
        set text(size: 0.87em, fill: pal.subtext)
        ings(r.from)
        if show-time { " · " + dur(r.time) }
        if show-mach { " · " + mach(r.machine) }
        if extra != none [ · #extra(r)]
        [ · ]
        text(style: "italic", r.operation)
        // Only on rows that need a material no source tier reaches.
        if "seed" in r [ · #text(fill: bands.work, weight: "bold", "seed:") #r.seed]
      }),
    ),
  ))
)

// Item names, alphabetical down sub-columns — a list you scan, not read.
#let names(items, cols: 2) = block(inset: (x: 3pt, y: 2pt), {
  let per = calc.ceil(items.len() / cols)
  grid(
    columns: (1fr,) * cols,
    column-gutter: 6pt,
    row-gutter: 1.6pt,
    ..range(per).map(i =>
      range(cols).map(c => {
        let j = i + c * per
        if j < items.len() { items.at(j) } else { [] }
      })).flatten()
  )
})

// ═══════════════════════ page 1 — the money engine ══════════════════════════

#let hero = data.loops.filter(r => r.mult == "x6 loop")
#let loop-time = shared(data.loops, "time")
#let loop-mach = shared(data.loops, "machine")

#block(
  width: 100%, radius: 2pt, below: 7pt,
  stroke: 0.9pt + pal.accents.at(0), inset: (x: 5pt, y: 4pt),
)[
  #text(weight: "black", size: 1.5em, fill: pal.accents.at(0))[×6 EVERY #dur(hero.first().time)]
  #h(3pt) #text(size: 0.9em, fill: pal.subtext)[the only #hero.len() sixfold loops]
  #v(2pt)
  #table(
    columns: (auto, 1fr, auto),
    align: (left, left, right),
    stroke: none, inset: (x: 0pt, y: 1.4pt), column-gutter: 5pt,
    ..hero.map(r => (
      text(weight: "bold", r.make),
      text(size: 0.9em, fill: pal.subtext, [← #ings(r.from)]),
      [#num(r.rate)#text(size: 0.85em, fill: pal.subtext)[/h]],
    )).flatten()
  )
  #v(1pt)
  #text(size: 0.87em, fill: pal.subtext)[
    Feed the output back in. A Medium refiner (2 slots) turns 1 + 2 into 6 —
    the stack pays for itself and then some.
  ]
]

#section("Self-multiplying loops", breakable: true)[
  #note[
    #if loop-mach != none and loop-time != none [
      every row: *#loop-mach* refiner, *#dur(loop-time)* a cycle,
      output feeds its own input.
    ] else [
      every row feeds its own output back in — machine and cycle time per row.
    ]
    #linebreak()
    *out/h* = items made per machine-hour · *units* = net value gained per batch
  ]
  // A notch smaller than the page: keeps every input list on one line.
  #set text(size: 0.9em)
  #if loop-mach != none and loop-time != none {
    dense(
      (auto, 1fr, auto, auto),
      (left, left, right, right),
      ("make", "from", "out/h", "units"),
      ..data.loops.map(r => (
        text(weight: "bold", r.make),
        text(fill: pal.subtext, ings(r.from)),
        num(r.rate),
        money(r.profit),
      )).flatten()
    )
  } else {
    dense(
      (auto, 1fr, auto, auto, auto),
      (left, left, right, right, right),
      ("make", "from", "time", "out/h", "units"),
      ..data.loops.map(r => (
        text(weight: "bold", r.make),
        text(fill: pal.subtext, ings(r.from)) + text(size: 0.82em, fill: pal.subtext, [ #mach(r.machine)]),
        dur(r.time),
        num(r.rate),
        money(r.profit),
      )).flatten()
    )
  }
  #note[
    the negative rows still multiply — they just cost you value per cycle;
    run them for the *material*, not the profit.
  ]
]

#section("Precious-metal engine", breakable: true)[
  #note[
    Gold · Silver · Platinum · Chromatic Metal, by units per batch ·
    the italic name is the operation to pick in the machine
  ]
  #recipes(data.engine, r => money(r.profit),
    extra: r => [#num(r.rate)/h])
  #note[
    the alloys (Aronium, Herox, Lemmium…) are *stored money*: one unit unpacks
    into 125–250 metal in a portable refiner.
  ]
]

#section("Best profit per batch", breakable: true)[
  #note[net units gained by one full run of the machine · one row per output]
  #recipes(data.profit, r => money(r.profit))
]

#section("Best units per machine-hour", breakable: true)[
  #note[profit per batch × batches an hour — what one machine actually earns]
  #recipes(data.per_hour, r => money(r.per_hour))
]

#section("Refiner rules")[
  #block(inset: (x: 3pt, y: 2pt))[
    + The output slot holds *exactly one stack* — the process auto-pauses the
      moment it fills. Empty it to keep going.
    + A lone leftover input is *consumed for nothing*, so you are never left
      holding a stack of 1.
    + Refiner contents *can vanish on quit*, and always vanish if you switch
      saves. Empty a refiner before you log off.
    + The *displayed refining time is frequently wrong* — every time on this
      sheet is read from the game files instead.
    + You can pull partial output or stop mid-run: *nothing is lost by
      interrupting* a batch.
    + Refined materials can be *refined again*, and higher tiers store more per
      slot — refine before you haul.
  ]
]

#section("Machines & symbols")[
  #dense(
    (auto, auto, 1fr),
    (left, center, left),
    ("", "slots", "machine"),
    text(weight: "bold", "P"), [1], [Portable / Personal refiner],
    text(weight: "bold", "M"), [2], [Medium refiner],
    text(weight: "bold", "L"), [3], [Large refiner],
    text(weight: "bold", "N"), [2], [Nutrient Processor (cooking)],
  )
  #note[
    a *Medium* means two input slots, a *Large* three — the letter after an
    input list is the smallest machine that can run it.
    #linebreak()
    *out/h · nan/h* items or nanites per machine-hour ·
    *units* net value of one batch, #text(fill: pal.pos)[green] pays,
    #text(fill: pal.neg)[red] burns value ·
    _italics_ the operation to pick in the machine menu
  ]
]

// ═══════════════════ page 2 — nanites, essentials, reachability ═════════════
// Two wide columns: the nanite rows carry a sentence of prose each.
#pagebreak()
#set page(columns: 2)
#section-count.update(0)
#set text(size: 8.2pt)

#section("Nanite converters — every source, best rate first", breakable: true)[
  #note[
    nanites are the second currency: *technology upgrades*, not ships and
    freighters. Nothing sells for nanites, so every row is really a price —
    the *sale value* figure is what the batch costs you in units, not a loss.
    #linebreak()
    *nan* per batch · *nan/h* per machine-hour · *per item* nanites per item
    consumed · the coloured label is how hard the input is to come by
    (#text(fill: bands.easy, weight: "bold")[easy]
    #text(fill: bands.ok, weight: "bold")[ok]
    #text(fill: bands.work, weight: "bold")[work]
    #text(fill: bands.hard, weight: "bold")[hard]).
    The *where* line is the part the game files never tell you.
    #linebreak()
    *P* portable refiner (1 slot) · *M* medium (2) · *L* large (3) ·
    _italics_ = the operation to pick in the machine
  ]
  #stack(..data.nanites.enumerate().map(((i, r)) => block(
    width: 100%, breakable: false,
    fill: if calc.odd(i) { pal.card },
    inset: (x: 3pt, y: 2pt),
    grid(
      columns: (1fr, auto, auto, auto),
      align: (left + bottom, right + bottom, right + bottom, right + bottom),
      column-gutter: 7pt, row-gutter: 1.2pt,
      text(weight: "bold", ings(r.from)),
      [#text(weight: "bold", num(r.nanites))#text(size: 0.85em, fill: pal.subtext)[ nan]],
      [#num(r.per_hour)#text(size: 0.85em, fill: pal.subtext)[/h]],
      [#dec(r.per_input)#text(size: 0.85em, fill: pal.subtext)[/item]],
      grid.cell(colspan: 4, {
        set text(size: 0.9em)
        text(fill: bands.at(r.band), weight: "bold", r.gettable)
        text(fill: pal.subtext, [ · #r.where])
      }),
      grid.cell(colspan: 4, {
        set text(size: 0.87em, fill: pal.subtext)
        dur(r.time) + " · " + mach(r.machine) + " · "
        text(style: "italic", r.operation)
        [ · sale value #money(r.profit)]
        if r.note != "" [ · #text(style: "italic", r.note)]
      }),
    ),
  )))
]

#section("Essentials — stop mining these", breakable: true)[
  #note[
    the cheapest route to what you would otherwise go and dig up, using only
    materials the source tiers below actually reach ·
    #text(fill: bands.work, weight: "bold")[seed:] marks the one input you have
    to find yourself before the loop runs
  ]
  #dense(
    (auto, 1fr, auto, auto),
    (left, left, right, center),
    ("make", "from · operation", "time", "m"),
    ..data.essentials.map(r => (
      text(weight: "bold", r.make),
      {
        set text(fill: pal.subtext)
        ings(r.from)
        [ · ]
        text(style: "italic", r.operation)
        if "seed" in r [ · #text(fill: bands.work, weight: "bold", "seed:") #r.seed]
      },
      dur(r.time),
      mach(r.machine),
    )).flatten()
  )
]

#section("Tier 0 — from five materials", breakable: true)[
  #note[
    a refiner plus #data.sources.tier0.join(", ") makes all
    #data.tier0.len() of these:
  ]
  #names(data.tier0, cols: 3)
]

#section("Tier 1 — add asteroid mining", breakable: true)[
  #note[
    #data.sources.tier1.filter(m => m not in data.sources.tier0).join(", ")
    off asteroids unlocks #data.tier1_extra.len() more, nanites included:
  ]
  #names(data.tier1_extra, cols: 3)
]

#section("Must find — no recipe makes these", breakable: true)[
  #note[
    #data.must_find.len() items *no refiner recipe produces*: derelicts,
    dissonant worlds, abandoned buildings, sentinel pillars, the sea floor.
    Everything else on this sheet is downstream of them.
  ]
  #names(data.must_find, cols: 3)
]

// ═══════════════════════════ page 3 — the kitchen ═══════════════════════════
#pagebreak()
#section-count.update(0)

#let cook-time = shared(data.cooking, "time")
#let cook-mach = shared(data.cooking, "machine")

#block(
  width: 100%, radius: 2pt, below: 7pt,
  stroke: 0.9pt + pal.accents.at(0), inset: (x: 5pt, y: 4pt),
)[
  #text(weight: "black", size: 1.4em, fill: pal.accents.at(0))[
    COOK ONCE, EAT ONE, SELL THE REST]
  #h(4pt) #text(size: 0.92em, fill: pal.subtext)[
    the dish you eat is the dish you sell — there is no "eat or sell?"
  ]
  #v(1pt)
  #text(size: 0.92em, fill: pal.subtext)[
    A Nutrient Processor batch takes seconds and comes out as both the buff and
    the payday: the same cake that tops your Shield Strength sells for six
    figures. Cook a stack, eat one, sell the rest.
  ]
]

#section("Cooking for money — top dishes by value", breakable: true)[
  #note[
    #if cook-time != none and cook-mach != none [
      every row below: *#dur(cook-time)* in the #cook-mach, so units/hour =
      value × #num(3600 / secs(cook-time)) — the best row is
      #num(data.cooking.first().per_hour) an hour
    ] else [
      units gained over the ingredients for one batch — the best row is
      #num(data.cooking.first().per_hour) an hour
    ]
  ]
  #dense(
    (auto, 1fr, ..if cook-time == none { (auto, auto) } else { () }, auto),
    (left, left, ..if cook-time == none { (right, center) } else { () }, right),
    ("dish", "from · operation",
      ..if cook-time == none { ("time", "m") } else { () }, "units"),
    ..data.cooking.map(r => (
      text(weight: "bold", r.make),
      {
        set text(fill: pal.subtext)
        ings(r.from)
        [ · ]
        text(style: "italic", r.operation)
      },
      ..if cook-time == none { (dur(r.time), mach(r.machine)) } else { () },
      money(r.profit),
    )).flatten()
  )
]

#section("Cooking for buffs — the best dishes for every effect", breakable: true)[
  #note[
    #data.effects.len() stats a meal can boost, each with the three
    best-paying dishes that boost it · *pot* is the game's own 0–1 rating of
    the buff (a couple go past 1) · *units* is what the dish sells for ·
    *uplift* is what one batch gains over its ingredients ·
    ties are broken by price, so the *first dish of each effect is both the
    strongest buff and the best sale*
  ]
  #table(
    columns: (auto, 1fr, auto, auto, auto),
    align: (left, left, right, right, right),
    stroke: none,
    inset: (x: 3pt, y: 1.2pt),
    fill: (x, y) => if y > 0 and calc.rem(y - 1, 4) == 0 { pal.card },
    table.header(
      ..("dish", "from", "pot", "units", "uplift").map(h =>
        text(size: 0.82em, weight: "bold", fill: pal.subtext, upper(h)))),
    ..data.effects.map(e => (
      table.cell(colspan: 5, {
        text(weight: "bold", e.effect)
        text(size: 0.88em, fill: pal.subtext,
          " — " + e.use + " · " + str(e.count) + " dishes")
      }),
      ..e.dishes.map(d => (
        d.dish,
        text(size: 0.9em, fill: pal.subtext, ings(d.from)),
        dec(d.potency),
        num(d.value),
        gain(d.uplift),
      )).flatten(),
    )).flatten()
  )
]

// ════════════════════════ page 4 — multi-tools ══════════════════════════════
// The only page not generated from the recipe tables: it comes from the
// hand-written guides, so it is mostly prose. Two wide columns, small type.
#pagebreak()
#section-count.update(0)
#set text(size: 6.7pt)
#set list(spacing: 2pt)
#set enum(spacing: 2pt)

#let mt = data.multitools
// This page is nearly all prose: every section runs tighter than the rest.
#let msection(title, body) = section(title, body, breakable: true, below: 4pt)
#let mrow(i, body) = block(
  width: 100%, breakable: false,
  fill: if calc.odd(i) { pal.card },
  inset: (x: 3pt, y: 1.2pt), body,
)

// Highlight the claims the headline makes: a best in its column, or a zero.
#let stat(s, best) = if s == "+0%" {
  text(fill: pal.neg, weight: "bold", s)
} else if best {
  text(fill: pal.pos, weight: "bold", s)
} else { s }

#block(
  width: 100%, radius: 2pt, below: 7pt,
  stroke: 0.9pt + pal.accents.at(0), inset: (x: 5pt, y: 4pt),
)[
  #text(weight: "black", size: 1.3em, fill: pal.accents.at(0))[
    THE TOOL IS THE BUILD]
  #h(4pt) #text(size: 0.95em)[#mt._headline]
  #v(1pt)
  #text(size: 0.92em, fill: pal.subtext)[
    #mt.types.len() types · #mt.weapons.len() weapons · the one page not
    generated from the recipe tables — it comes from the written guides.
  ]
]

#msection("Tool types — what the class range actually buys you")[
  #note[
    ranges run C-class to S-class ·
    #text(fill: pal.pos, weight: "bold")[green] = best in column ·
    #text(fill: pal.neg, weight: "bold")[red] = no bonus at all
  ]
  #dense(
    (auto, auto, auto, auto, auto, 1fr),
    (left, right, right, right, right, left),
    ("type", "damage", "mining", "scan", "slots", ""),
    pad: 1.4pt,
    ..mt.types.map(t => (
      text(weight: "bold", t.type),
      stat(t.damage, t.damage.ends-with("50%")),
      stat(t.mining, t.mining.ends-with("50%")),
      stat(t.scan, t.scan.contains("100%")),
      t.slots,
      text(size: 0.92em, fill: pal.subtext, t.note),
    )).flatten()
  )
]

#msection("Getting the rare types")[
  #stack(..mt.getting.enumerate().map(((i, g)) => mrow(i, grid(
      columns: (auto, auto, 1fr),
      column-gutter: 5pt, row-gutter: 1pt,
      text(weight: "bold", g.type),
      text(weight: "bold",
        fill: if g.cost == "free" { pal.pos } else { bands.work }, g.cost),
      text(fill: pal.subtext, g.where),
      grid.cell(colspan: 3, text(size: 0.92em, fill: pal.subtext, g.how)),
    ))))
]

#msection(mt.sentinel_puzzle.title)[
  #block(inset: (x: 3pt, y: 2pt))[
    #enum(..mt.sentinel_puzzle.steps)
    #v(2pt)
    #text(weight: "bold")[Once it is yours]
    #list(..mt.sentinel_puzzle.after.map(a => text(fill: pal.subtext, a)))
  ]
]

#msection("Finding a specific tool")[
  #block(inset: (x: 3pt, y: 2pt))[
    #text(weight: "bold", mt.cabinet_trick.title)
    #enum(..mt.cabinet_trick.steps)
    #text(size: 0.92em, fill: pal.subtext, mt.cabinet_trick.note)
    #v(3pt)
    #text(weight: "bold", mt.hunting.title)
    #enum(..mt.hunting.steps)
  ]
]

#msection("Weapons — measured best hit")[
  #note[
    the last two are secondaries — no damage figure; they back up a primary
  ]
  #stack(..mt.weapons.enumerate().map(((i, w)) => mrow(i, grid(
      columns: (auto, 1fr, auto),
      column-gutter: 5pt, row-gutter: 1pt,
      text(weight: "bold", w.weapon),
      text(size: 0.92em, fill: pal.subtext, w.kind),
      if w.best_hit == "-" { text(fill: pal.subtext, sym.dash.em) } else {
        text(weight: "bold", w.best_hit) },
      grid.cell(colspan: 3, {
        set text(size: 0.92em, fill: pal.subtext)
        text(fill: pal.pos, weight: "bold", "+ ")
        w.pro
        linebreak()
        text(fill: pal.neg, weight: "bold", sym.minus + " ")
        w.con
      }),
    ))))
]

#msection("Rules of thumb")[
  #stack(..mt.rules.enumerate().map(((i, r)) => mrow(i, {
    text(weight: "bold", r.title)
    text(fill: pal.subtext, [ — #r.body])
  })))
]

#msection("Upgrades — where they come from, what to fit first")[
  #stack(..mt.upgrade_sources.enumerate().map(((i, u)) => mrow(i, {
    text(weight: "bold", u.kind)
    text(fill: pal.subtext, [ — #u.where · #u.note])
  })))
  #block(inset: (x: 3pt, y: 2pt), enum(..mt.upgrade_order))
]


// ════════════════════════ page 5 — portal addresses ═════════════════════════
// Also hand-written rather than generated, but the arithmetic in it is real:
// build_cheatsheet.py round-trips every address below and re-checks the
// galaxy-centre invariant, so this page cannot print a code you cannot dial.
#pagebreak()
#section-count.update(0)
#set text(size: 7.2pt)
#set list(spacing: 2.5pt)
#set enum(spacing: 2.5pt)

#let pt = data.portals
#let mono(body) = text(font: "JetBrains Mono", size: 0.95em, body)

// The glyphs themselves. data/glyphs.json carries them as outlines traced from
// the game's own symbols (scripts/build_glyphs.py) with no fill of their own,
// which is the whole reason they are paths and not the source PNGs: white line
// art is invisible on Latte's paper, and a raster cannot be recoloured. The
// fill is handed in here, so one set of shapes prints in both themes.
#let gd = json("data/glyphs.json")
#let glyph(hex, size: 1.9em, fill: pal.text) = {
  let g = gd.glyphs.find(g => g.hex == upper(hex))
  let svg = (
    "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"" + g.viewbox + "\">"
      + "<g transform=\"" + g.transform + "\" fill=\"" + fill.to-hex() + "\">"
      + g.paths.map(d => "<path d=\"" + d + "\"/>").join("")
      + "</g></svg>"
  )
  box(image(bytes(svg), format: "svg", width: size, height: size))
}
// The five fields of an address, coloured the same way the TUI colours them.
// Five accents that stay distinct in both themes -- the yellow that works on
// the TUI's dark background is unreadable on Latte's white.
#let f-planet = pal.accents.at(4)
#let f-system = pal.accents.at(1)
#let f-y = pal.accents.at(0)
#let f-z = pal.accents.at(3)
#let f-x = pal.accents.at(2)
// One colour per position in a twelve-glyph code -- planet, system, Y, Z, X --
// so the symbols, the hex and the TUI all split an address the same way.
#let field-colours = (
  (f-planet,) + (f-system,) * 3 + (f-y,) * 2 + (f-z,) * 3 + (f-x,) * 3
)

// A code drawn the way you dial it. This is the line that saves the walk back
// to the table above: twelve symbols in dial order, already in field colours.
#let glyph-code(code, size: 1.5em) = box(baseline: 20%, {
  for (i, digit) in code.clusters().enumerate() {
    // A hair of space at each field boundary: dialling is done a field at a
    // time, and twelve symbols in an unbroken row is where miscounts happen.
    if i in (1, 4, 6, 9) { std.h(2pt) }
    glyph(digit, size: size, fill: field-colours.at(i))
  }
})

#block(
  width: 100%, radius: 2pt, below: 7pt,
  stroke: 0.9pt + pal.accents.at(0), inset: (x: 5pt, y: 4pt),
)[
  #text(weight: "black", size: 1.3em, fill: pal.accents.at(0))[
    TWO NAMES FOR ONE PLACE]
  #h(4pt) #text(size: 0.95em)[
    The glyphs you dial count from the *centre* of the galaxy; the address a
    signal booster shows counts from a *corner*. Same voxel, unrecognisable
    numbers — which is the whole reason a converter exists.
  ]
  #v(1pt)
  #text(size: 0.92em, fill: pal.subtext)[
    16 glyphs · #pt.locations.len() addresses
    (#pt.counts.mine found here, #pt.counts.shared shared) ·
    press #raw("P") in the app to convert one
  ]
]

#msection("The 16 glyphs — the dial is in this order")[
  #note[
    the hex digit *is* the position, so #raw("A") is the eleventh symbol every
    time · you need all 16 unlocked, not twelve
  ]
  #dense(
    (auto, auto, auto, 1fr, auto, auto, auto, 1fr),
    (right + horizon, center + horizon, center + horizon, left + horizon,
     right + horizon, center + horizon, center + horizon, left + horizon),
    ("#", "hex", "", "glyph", "#", "hex", "", "glyph"),
    pad: 1.1pt,
    ..range(8).map(i => {
      let a = pt.glyphs.at(i)
      let b = pt.glyphs.at(i + 8)
      (
        text(fill: pal.subtext, str(a.position)),
        mono(text(weight: "bold", a.hex)), glyph(a.hex, size: 1.6em), a.name,
        text(fill: pal.subtext, str(b.position)),
        mono(text(weight: "bold", b.hex)), glyph(b.hex, size: 1.6em), b.name,
      )
    }).flatten()
  )
]

#msection("Reading an address")[
  #block(inset: (x: 3pt, y: 2pt))[
    #mono(text(size: 1.5em, weight: "bold",
      text(fill: f-planet, "p") + " " + text(fill: f-system, "SSS") + " " +
      text(fill: f-y, "YY") + " " + text(fill: f-z, "ZZZ") + " " +
      text(fill: f-x, "XXX")))
    #v(2pt)
    #grid(
      columns: (auto, 1fr), column-gutter: 5pt, row-gutter: 1.4pt,
      text(fill: f-planet, weight: "bold", "p"),
      [planet index in the system — a galactic address does *not*
        carry it, so you pick one],
      text(fill: f-system, weight: "bold", "SSS"), [star system index],
      text(fill: f-y, weight: "bold", "YY"), [voxel height],
      text(fill: f-z, weight: "bold", "ZZZ"), [voxel width],
      text(fill: f-x, weight: "bold", "XXX"), [voxel length],
    )
    #v(3pt)
    #text(weight: "bold")[Worked example]
    #v(1pt)
    #grid(
      columns: (auto, 1fr), column-gutter: 5pt, row-gutter: 1.4pt,
      text(fill: pal.subtext, "dial"), glyph-code(pt.example.code, size: 2em),
      text(fill: pal.subtext, "glyphs"),
      mono(text(weight: "bold",
        text(fill: f-planet, pt.example.planet) + " " +
        text(fill: f-system, pt.example.system) + " " +
        text(fill: f-y, pt.example.y) + " " +
        text(fill: f-z, pt.example.z) + " " +
        text(fill: f-x, pt.example.x))),
      text(fill: pal.subtext, "galactic"), mono(pt.example.galactic),
      text(fill: pal.subtext, "voxel"), mono(pt.example.voxel),
    )
  ]
]

#msection("Converting by hand")[
  #note[all arithmetic is hex; the system index crosses over unchanged]
  #block(inset: (x: 3pt, y: 2pt))[
    #dense(
      (auto, 1fr, 1fr),
      (right, left, left),
      ("", "glyphs → galactic", "galactic → glyphs"),
      pad: 1.5pt,
      text(fill: f-x, weight: "bold", "X"),
      mono("(X + 2047) % 4096"), mono("(X + 2049) % 4096"),
      text(fill: f-y, weight: "bold", "Y"),
      mono("(Y + 127) % 256"), mono("(Y + 129) % 256"),
      text(fill: f-z, weight: "bold", "Z"),
      mono("(Z + 2047) % 4096"), mono("(Z + 2049) % 4096"),
    )
    #v(2pt)
    #text(size: 0.92em, fill: pal.subtext)[
      The anchor: glyphs #mono("000000000000") are the centre of the galaxy, and
      galactic coordinates call the same place #mono("07FF:007F:07FF"). Get a
      constant wrong and that moves.
    ]
  ]
]

#msection("Before you dial")[
  #stack(
    mrow(0, {
      text(weight: "bold")[The galaxy is not in the address.]
      text(fill: pal.subtext)[ — the same twelve glyphs mean a different star in
        each of the 256 galaxies, so an address shared without its galaxy is
        ambiguous. Everything below is #text(weight: "bold")[Euclid], galaxy 1.]
    }),
    mrow(1, {
      text(weight: "bold")[Trust the address, not the label.]
      text(fill: pal.subtext)[ — the location is seeded to the coordinate and
        generally survives a patch. Class, slot count and headline damage are
        submitter metadata and rot.]
    }),
    mrow(2, {
      text(weight: "bold")[Reload location is part of the address.]
      text(fill: pal.subtext)[ — a design is seeded by where you last loaded, so
        one monolith yields several tools. An entry naming a reload planet is
        telling you which roll it saw.]
    }),
    mrow(3, {
      text(weight: "bold")[Activating a portal is not knowing glyphs.]
      text(fill: pal.subtext)[ — charging the four pillars only powers the
        machine; the glyphs are what lets you type a destination.
        #text(weight: "bold")[Artemis → The Purge] grants one per warp.]
    }),
  )
]

// The addresses themselves, split the way you actually think about them: the
// ones you stood on, and the ones you took somebody's word for.
#let address-rows(rows) = stack(..rows.enumerate().map(((i, r)) => mrow(i, grid(
  columns: (1fr, auto, auto, auto),
  column-gutter: 5pt, row-gutter: 1.2pt,
  align: (left + horizon, right + horizon, center + horizon, right + horizon),
  text(weight: "bold", r.name),
  text(size: 0.9em, fill: pal.subtext, r.kind),
  glyph-code(r.code),
  mono(text(weight: "bold", r.code)),
  grid.cell(colspan: 4, {
    set text(size: 0.9em, fill: pal.subtext)
    if r.detail != "" { r.detail }
    if r.where != "" [ · #r.where]
    linebreak()
    mono(r.galactic)
    if r.source != "" [ · #r.source]
    if r.added != "" [ · #r.added]
  }),
))))

#let mine = pt.locations.filter(r => r.origin == "mine")
#let shared-rows = pt.locations.filter(r => r.origin == "shared")

#msection("Found here — my own addresses")[
  #if mine.len() == 0 {
    note[
      nothing yet. In the app: paste or decode an address, press #raw("s"),
      set #emph[Found] to #raw("mine") — it is written to
      #raw("data/locations.json") and appears here on the next
      #raw("mise run pdf").
    ]
  } else {
    address-rows(mine)
  }
]

#msection("Shared — read off the catalogues")[
  #note[#pt.source]
  #address-rows(shared-rows)
]
