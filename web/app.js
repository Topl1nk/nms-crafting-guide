// NMSii on the web: the TUI's screens as pages over data.json.
//
// One module, one view per hash route. Each view draws a toolbar, a list and
// a detail pane; the keyboard mirrors the TUI where it makes sense on a page
// (j/k or arrows to move, / to search, Enter to pivot, Esc to clear).

import {
  Address, AddressError, GLYPH_FIELD, craftableNow, fmtInt, fmtSigned,
  fmtTime, looksLikeAddress, machineShort, multiplierLabel, oneHopAway, ordinal,
  plan, qtyLabel, timeLabel,
} from "./core.js";

let D; // data.json

// -- small helpers ------------------------------------------------------------

const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ESC[c]);
const $ = (sel, root = document) => root.querySelector(sel);
const view = () => $("#view");

// What the data is up to date with, from data/source.json via data.json:
// "Cosmos 7.06", or "" when the build did not record a game version (data
// from the NMS-Handbook fallback, or no source.json).
const gameVersion = () => {
  const s = D?.source;
  return s?.from === "game" && s.version ? [s.game, s.version].filter(Boolean).join(" ") : "";
};
const gameBuild = () => (gameVersion() && D.source.build ? `build ${D.source.build}` : "");

const name = (id) => D.items[id]?.name ?? id;
const itemLink = (id, text = name(id)) =>
  `<a href="#/recipes?item=${encodeURIComponent(id)}">${esc(text)}</a>`;

function debounce(fn, ms = 120) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// Browser storage can be missing (private windows, blocked site data); the
// page has to work without it, it just forgets.
const local = {
  get(key, fallback) {
    try {
      const raw = localStorage.getItem(`nms-items:${key}`);
      return raw === null ? fallback : JSON.parse(raw);
    } catch { return fallback; }
  },
  set(key, value) {
    try { localStorage.setItem(`nms-items:${key}`, JSON.stringify(value)); } catch { /* forget */ }
  },
};

function toast(text) {
  const el = $("#toast");
  el.textContent = text;
  el.classList.add("show");
  clearTimeout(toast.t);
  toast.t = setTimeout(() => el.classList.remove("show"), 1800);
}

async function copy(text, what) {
  try {
    await navigator.clipboard.writeText(text);
    toast(`Copied ${what}`);
  } catch {
    toast("Copy failed - select it by hand");
  }
}

function options(list, current) {
  return list.map(([value, label]) =>
    `<option value="${esc(value)}"${value === current ? " selected" : ""}>${esc(label)}</option>`).join("");
}

// -- recipes, labelled --------------------------------------------------------

let RECIPES; // D.recipes with labels and a search key attached

function prepareRecipes() {
  RECIPES = D.recipes.map((r, index) => {
    const outName = name(r.out[0]);
    const inputs = r.in.map(([id, n]) => qtyLabel(n, name(id))).join(" + ");
    return {
      ...r,
      index,
      outName,
      outLabel: qtyLabel(r.out[1], outName),
      inputs,
      mult: multiplierLabel(r),
      timeLabel: timeLabel(r.time),
      key: `${outName} ${inputs} ${r.op}`.toLowerCase(),
    };
  });
  for (const r of RECIPES) {
    (PRODUCED[r.out[0]] ||= []).push(r);
    for (const [id] of r.in) (CONSUMED[id] ||= []).push(r);
  }
}
const PRODUCED = {};
const CONSUMED = {};

const easeOf = (id) => D.ease[id] ?? { label: "loot (unknown)", band: "hard", score: 25, describe: "", where: "", note: "" };
// The hardest ingredient is what gates a recipe.
const easeOfRecipe = (r) =>
  r.in.map(([id]) => easeOf(id)).reduce((a, b) => (b.score < a.score ? b : a));

const band = (e) => `<span class="band band-${e.band}">${esc(e.label)}</span>`;

function placement(id) {
  const item = D.items[id];
  return item ? D.storage.outcomes[item.store] : null;
}
const action = (p) => `<span class="act act-${p.action}">${esc(p.label)}</span>`;

// -- the list widget ----------------------------------------------------------

// A table with one highlighted row. Views hand it columns and rows; it owns
// the cursor, and calls `onSelect` when the cursor lands somewhere.
class List {
  constructor(el, { columns, onSelect, onEnter, empty = "Nothing matches." }) {
    Object.assign(this, { el, columns, onSelect, onEnter, empty, rows: [], sel: -1 });
    el.addEventListener("click", (event) => {
      if (event.target.closest("a, button")) return;
      const tr = event.target.closest("tr[data-i]");
      if (tr) this.select(Number(tr.dataset.i));
    });
    el.addEventListener("dblclick", (event) => {
      const tr = event.target.closest("tr[data-i]");
      if (tr && this.onEnter) this.onEnter(this.rows[Number(tr.dataset.i)]);
    });
  }

  set(rows, sel = 0) {
    this.rows = rows;
    if (!rows.length) {
      this.el.innerHTML = `<p class="muted pad">${esc(this.empty)}</p>`;
      this.sel = -1;
      return;
    }
    const head = this.columns.map((c) => `<th class="${c.cls || ""}">${esc(c.title)}</th>`).join("");
    const body = rows.map((row, i) =>
      `<tr data-i="${i}">${this.columns.map((c) => `<td class="${c.cls || ""}">${c.html(row)}</td>`).join("")}</tr>`,
    ).join("");
    this.el.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
    this.sel = -1;
    this.select(Math.min(sel, rows.length - 1), false);
  }

  select(i, scroll = true) {
    if (!this.rows.length) return;
    i = Math.max(0, Math.min(i, this.rows.length - 1));
    this.el.querySelector("tr.sel")?.classList.remove("sel");
    const tr = this.el.querySelector(`tr[data-i="${i}"]`);
    tr?.classList.add("sel");
    if (scroll) tr?.scrollIntoView({ block: "nearest" });
    this.sel = i;
    this.onSelect?.(this.rows[i], i);
  }

  move(delta) { this.select(this.sel + delta); }
  current() { return this.rows[this.sel]; }
}

// The view's keyboard targets: its main list and its search box.
let active = { list: null, search: null, enter: null, escape: null };

// -- views --------------------------------------------------------------------

const VIEWS = {};

// Recipes ----------------------------------------------------------------------

const DOMAINS = [["refine", "Refining"], ["cook", "Cooking"], ["all", "All recipes"]];
const SORTS = [
  ["mult", "multiplier"], ["time", "fastest"], ["rate", "output/hour"],
  ["profit", "units profit"], ["ease", "how gettable"], ["name", "name"],
];
const MAX_ROWS = 400;

const recipeState = { q: "", domain: "refine", sort: "mult" };

function sortRecipes(rows, mode) {
  const by = {
    mult: (a, b) => Math.max(b.loop, b.ratio) - Math.max(a.loop, a.ratio) || a.time - b.time,
    time: (a, b) => (a.time || 1e9) - (b.time || 1e9) || b.ratio - a.ratio,
    rate: (a, b) => b.rate - a.rate || a.time - b.time,
    profit: (a, b) => b.profit - a.profit || a.time - b.time,
    ease: (a, b) => easeOfRecipe(b).score - easeOfRecipe(a).score || a.time - b.time,
    name: (a, b) => a.outName.localeCompare(b.outName) || a.inputs.localeCompare(b.inputs),
  }[mode];
  return rows.sort(by);
}

function searchRecipes({ q, domain, item, role }) {
  let pool;
  if (item) {
    if (role === "output") pool = PRODUCED[item] || [];
    else if (role === "input") pool = CONSUMED[item] || [];
    else pool = [...new Set([...(PRODUCED[item] || []), ...(CONSUMED[item] || [])])];
  } else {
    pool = RECIPES;
  }
  const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
  return pool.filter((r) =>
    (domain === "all" || r.domain === domain) && terms.every((t) => r.key.includes(t)));
}

VIEWS.recipes = (params) => {
  const item = params.get("item");
  const role = params.get("role") || "any";
  const st = recipeState;
  if (params.has("domain")) st.domain = params.get("domain");

  view().innerHTML = `
    <div class="toolbar">
      <input type="search" id="q" placeholder="/  search recipes - output, ingredient or operation" value="${esc(st.q)}" autocomplete="off">
      <label>Show <select id="domain">${options(DOMAINS, st.domain)}</select></label>
      <label>Sort <select id="sort">${options(SORTS, st.sort)}</select></label>
    </div>
    <div class="note" id="note"></div>
    <div class="split">
      <div class="list" id="list"></div>
      <aside class="detail" id="detail"></aside>
    </div>`;

  const list = new List($("#list"), {
    columns: [
      { title: "Make", html: (r) => esc(r.outLabel), cls: "strong" },
      { title: "From", html: (r) => esc(r.inputs) },
      { title: "Mult", html: (r) => esc(r.mult), cls: "num" },
      { title: "Time", html: (r) => esc(r.timeLabel), cls: "num" },
      { title: "Machine", html: (r) => esc(machineShort(r.machine)), cls: "wide-only" },
    ],
    onSelect: (r) => showRecipe(r),
    onEnter: (r) => { location.hash = `#/recipes?item=${encodeURIComponent(r.out[0])}`; },
    empty: "No recipe matches.",
  });

  function refresh() {
    const matches = sortRecipes(searchRecipes({ ...st, item, role }), st.sort);
    list.set(matches.slice(0, MAX_ROWS));
    const note = [
      `<b>${esc(DOMAINS.find(([k]) => k === st.domain)[1])}</b>`,
      `sorted by <b>${esc(SORTS.find(([k]) => k === st.sort)[1])}</b>`,
    ];
    if (item) {
      const verb = { output: "produced by", input: "used in", any: "anything touching" }[role];
      note.push(`${verb} <b class="hl">${esc(name(item))}</b> <a href="#/recipes" class="chip">clear filter</a>`);
    }
    note.push(matches.length > MAX_ROWS ? `${MAX_ROWS} of ${matches.length}` : `${matches.length} recipes`);
    const inv = Object.keys(inventory()).length;
    if (inv) note.push(`<a href="#/inventory">inventory: ${inv} items</a>`);
    $("#note").innerHTML = note.join(" &nbsp;·&nbsp; ");
    if (!matches.length) $("#detail").innerHTML = `<p class="muted">No recipe matches.</p>`;
  }

  $("#q").addEventListener("input", debounce((e) => { st.q = e.target.value; refresh(); }));
  $("#domain").addEventListener("change", (e) => { st.domain = e.target.value; refresh(); });
  $("#sort").addEventListener("change", (e) => { st.sort = e.target.value; refresh(); });

  active = {
    list,
    search: $("#q"),
    enter: () => list.onEnter(list.current()),
    escape: () => {
      if (item) { location.hash = "#/recipes"; return; }
      $("#q").value = ""; st.q = ""; refresh();
    },
  };
  refresh();
};

function showRecipe(r) {
  const out = D.items[r.out[0]];
  const have = inventory();
  const e = easeOfRecipe(r);
  const p = placement(r.out[0]);
  const ings = r.in.map(([id, n]) => {
    const ie = easeOf(id);
    const stock = have[id] ? ` <span class="ok">(have ${have[id]})</span>` : "";
    return `<li>${n} × ${itemLink(id)} <span class="muted">${fmtInt(D.items[id]?.value ?? 0)}u</span>${stock} ${band(ie)}
      <div class="muted small">${esc(ie.describe)}</div></li>`;
  }).join("");
  const others = (PRODUCED[r.out[0]] || []).filter((o) => o.index !== r.index);
  const uses = CONSUMED[r.out[0]] || [];
  const id = encodeURIComponent(r.out[0]);

  $("#detail").innerHTML = `
    <h2>${esc(r.outLabel)}</h2>
    <p class="muted">${esc(out?.sub ?? "")}</p>
    <p class="equation"><b>${esc(r.inputs)}</b><br>→ <b>${esc(r.outLabel)}</b></p>
    <dl>
      <dt>Operation</dt><dd>${esc(r.op)}</dd>
      <dt>Machine</dt><dd>${esc(r.machine)}</dd>
      <dt>Batch time</dt><dd>${esc(r.timeLabel)}</dd>
      <dt>Multiplier</dt><dd>${esc(r.mult)}</dd>
      <dt>Rate</dt><dd>${fmtInt(r.rate)}/h per machine</dd>
      <dt>Profit</dt><dd>${fmtSigned(r.profit)} units per batch</dd>
      <dt>Gettable</dt><dd>${band(e)} <span class="muted">(hardest ingredient)</span></dd>
      ${p ? `<dt>Store</dt><dd>${action(p)} <a class="muted" href="#/storage?q=${encodeURIComponent(name(r.out[0]))}">why?</a></dd>` : ""}
    </dl>
    <div class="actions">
      <a class="btn" href="#/chain/${id}">Chain plan</a>
      <a class="btn" href="#/recipes?item=${id}&role=output">Produced by</a>
      <a class="btn" href="#/recipes?item=${id}&role=input">Used in</a>
      <button class="btn" data-add="${esc(r.out[0])}">+ Inventory</button>
    </div>
    <h3>Ingredients</h3>
    <ul class="ings">${ings}</ul>
    ${others.length ? `<h3>Other ways to make it <span class="muted">(${others.length})</span></h3>
      <ul>${others.sort((a, b) => Math.max(b.loop, b.ratio) - Math.max(a.loop, a.ratio)).slice(0, 5)
        .map((o) => `<li>${esc(o.inputs)} <span class="muted">${esc(o.mult)}</span></li>`).join("")}</ul>
      <p><a href="#/recipes?item=${id}&role=output">List them all</a></p>` : ""}
    ${uses.length ? `<h3>Used in</h3><p><a href="#/recipes?item=${id}&role=input">${uses.length} recipe(s)</a></p>` : ""}`;
}

// Chain ------------------------------------------------------------------------

VIEWS.chain = (params, target) => {
  if (!D.items[target] && !PRODUCED[target]) {
    view().innerHTML = `<p class="pad">Unknown item <code>${esc(target)}</code>. <a href="#/recipes">Back to recipes</a></p>`;
    return;
  }
  let tier = Number(params.get("tier") || 0);
  let qty = Math.max(1, Number(params.get("qty") || 1));
  let cook = params.get("cook") === "1";

  view().innerHTML = `
    <div class="toolbar">
      <h1 class="view-title">Chain · ${esc(name(target))}</h1>
      <label>From <select id="tier">${options(D.tiers.map((t, i) => [String(i), t.name]), String(tier))}</select></label>
      <label>How many <input type="number" id="qty" min="1" max="9999" value="${qty}"></label>
      <label class="check"><input type="checkbox" id="cook"${cook ? " checked" : ""}> allow cooking</label>
    </div>
    <div class="chain" id="chain"></div>`;

  function refresh() {
    const t = D.tiers[tier];
    const sources = new Set(t.sources);
    const p = plan(D.recipes, t.via[cook ? "all" : "refine"], sources, target, qty);
    const head = `<p><b>${qty} × ${esc(name(target))}</b> from <b>${esc(t.name)}</b>
      <span class="muted">- ${t.sources.map(name).sort().map(esc).join(", ")}</span></p>`;

    if (!p.ok) {
      const producers = PRODUCED[target] || [];
      $("#chain").innerHTML = `${head}
        <p class="err">Not reachable from this source set.</p>
        <p class="muted">Try a wider tier${cook ? "" : ", or allow cooking recipes"}.</p>
        ${producers.length
          ? `<h3>It is made by</h3><ul>${producers.slice(0, 6).map((r) => `<li>${esc(r.inputs)} → ${esc(r.outLabel)}</li>`).join("")}</ul>`
          : `<p class="muted">No recipe produces it - this one you have to find.</p>
             <p>${esc(easeOf(target).where || "")}</p>`}`;
      return;
    }

    const gather = Object.entries(p.raw).sort((a, b) => b[1] - a[1])
      .map(([id, n]) => `<span class="pill">${n} ${esc(name(id))}</span>`).join(" ");
    $("#chain").innerHTML = `${head}
      <p><span class="ok">Gather:</span> ${gather}</p>
      <p class="muted">${p.steps} refining step(s), ${fmtTime(p.seconds)} of machine time (one refiner, unattended).
      ${cook ? "" : " Refining only."}</p>
      <ul class="tree">${node(p.root)}</ul>`;
  }

  function node(step) {
    if (step.recipe === undefined) {
      const tag = step.raw ? "gather" : "find";
      return `<li class="leaf">${step.qty} × ${itemLink(step.id)} <span class="tag tag-${tag}">${tag}</span></li>`;
    }
    const r = RECIPES[step.recipe];
    return `<li><span>${step.qty} × ${itemLink(step.id)}</span>
      <span class="muted small">${esc(r.op)} ×${step.batches}, ${fmtTime(r.time * step.batches)}, ${esc(r.machine)}</span>
      <ul>${step.children.map(node).join("")}</ul></li>`;
  }

  // Keep the settings in the URL, so a plan is a link.
  function sync() {
    const q = new URLSearchParams();
    if (tier) q.set("tier", tier);
    if (qty !== 1) q.set("qty", qty);
    if (cook) q.set("cook", "1");
    history.replaceState(null, "", `#/chain/${encodeURIComponent(target)}${q.size ? `?${q}` : ""}`);
    refresh();
  }

  $("#tier").addEventListener("change", (e) => { tier = Number(e.target.value); sync(); });
  $("#qty").addEventListener("input", debounce((e) => {
    const n = Math.floor(Number(e.target.value));
    if (n >= 1) { qty = Math.min(n, 9999); sync(); }
  }));
  $("#cook").addEventListener("change", (e) => { cook = e.target.checked; sync(); });
  active = { list: null, search: null };
  refresh();
};

// Nanites ----------------------------------------------------------------------

const NANITE_SORTS = [
  ["rate", "nanites/hour"], ["ease", "how gettable"],
  ["per_input", "nanites per item"], ["nanites", "nanites per batch"],
];
let naniteSort = "rate";

VIEWS.nanites = () => {
  view().innerHTML = `
    <div class="toolbar">
      <h1 class="view-title">Nanites</h1>
      <label>Sort <select id="sort">${options(NANITE_SORTS, naniteSort)}</select></label>
    </div>
    <div class="note" id="note"></div>
    <div class="split">
      <div class="list" id="list"></div>
      <aside class="detail" id="detail"></aside>
    </div>`;

  const rows = D.nanites.map((n) => {
    const r = RECIPES[n.recipe];
    return { ...n, r, nanites: r.out[1], perHour: r.rate, ease: easeOfRecipe(r) };
  });

  const list = new List($("#list"), {
    columns: [
      { title: "Refine", html: (n) => esc(n.r.inputs), cls: "strong" },
      { title: "Nan", html: (n) => n.nanites, cls: "num" },
      { title: "Time", html: (n) => esc(n.r.timeLabel), cls: "num" },
      { title: "Nan/h", html: (n) => fmtInt(n.perHour), cls: "num" },
      { title: "Per item", html: (n) => n.per_input.toFixed(2), cls: "num wide-only" },
      { title: "Gettable", html: (n) => band(n.ease) },
      { title: "Where it comes from", html: (n) => esc(n.ease.where || n.ease.describe), cls: "wide-only muted" },
    ],
    onSelect: (n) => {
      $("#detail").innerHTML = `
        <h2>${esc(n.r.inputs)} → ${n.nanites} Nanite Cluster</h2>
        <p class="muted">${esc(n.r.op)}, ${esc(n.r.machine)}</p>
        <dl>
          <dt>Nanites/hour</dt><dd><b>${fmtInt(n.perHour)}</b> per refiner</dd>
          <dt>Per item</dt><dd>${n.per_input.toFixed(2)} per item consumed</dd>
          <dt>Value spent</dt><dd>${fmtInt(n.units_cost)} units</dd>
          <dt>Gettable</dt><dd>${band(n.ease)}</dd>
        </dl>
        <p class="${n.ease.where ? "ok" : "muted"}">${esc(n.ease.where || n.ease.describe)}</p>
        ${n.ease.note ? `<p class="muted">${esc(n.ease.note)}</p>` : ""}
        <p>${n.r.in.map(([id]) => `<a class="btn" href="#/recipes?item=${encodeURIComponent(id)}">${esc(name(id))}</a>`).join(" ")}</p>`;
    },
  });

  function refresh() {
    const by = {
      rate: (a, b) => b.perHour - a.perHour,
      ease: (a, b) => b.ease.score - a.ease.score || b.perHour - a.perHour,
      per_input: (a, b) => b.per_input - a.per_input,
      nanites: (a, b) => b.nanites - a.nanites,
    }[naniteSort];
    list.set(rows.sort(by));
    $("#note").innerHTML = `<b>${rows.length}</b> ways to make nanites, sorted by
      <b>${esc(NANITE_SORTS.find(([k]) => k === naniteSort)[1])}</b>
      <span class="muted">· one refiner, kept fed</span>`;
  }
  $("#sort").addEventListener("change", (e) => { naniteSort = e.target.value; refresh(); });
  active = { list, search: null };
  refresh();
};

// Cooking ----------------------------------------------------------------------

VIEWS.cooking = (params) => {
  const groups = D.cooking;
  const total = groups.reduce((n, g) => n + g.dishes.length, 0);
  view().innerHTML = `
    <div class="toolbar"><h1 class="view-title">Cooking - what it does</h1></div>
    <div class="note"><b>${total}</b> cooked dishes across <b>${groups.length}</b> buffs
      <span class="muted">· Pot = the game's own 0-1 quality for the buff · Uplift = units gained over the ingredients, one batch</span></div>
    <div class="split split-food">
      <div class="list" id="effects"></div>
      <div class="stack">
        <div class="list" id="list"></div>
        <aside class="detail detail-below" id="detail"></aside>
      </div>
    </div>`;

  const dishes = new List($("#list"), {
    columns: [
      { title: "Dish", html: (d) => esc(name(d.item)), cls: "strong" },
      { title: "Pot", html: (d) => D.items[d.item].potency.toFixed(2), cls: "num" },
      { title: "Value", html: (d) => fmtInt(D.items[d.item].value), cls: "num" },
      { title: "Uplift", html: (d) => fmtSigned(RECIPES[d.recipe].profit), cls: "num wide-only" },
      { title: "Cook from", html: (d) => esc(RECIPES[d.recipe].inputs), cls: "wide-only" },
      { title: "Time", html: (d) => esc(RECIPES[d.recipe].timeLabel), cls: "num" },
    ],
    onSelect: (d) => {
      const item = D.items[d.item];
      const r = RECIPES[d.recipe];
      const use = groups.find((g) => g.effect === item.effect)?.use;
      $("#detail").innerHTML = `
        <h2>${esc(item.name)} <span class="muted small">${esc(item.sub)}</span></h2>
        <p><span class="hl2">${esc(item.effect)}</span> at potency <b>${item.potency.toFixed(2)}</b>${use ? ` <span class="muted">- ${esc(use)}</span>` : ""}
          ${d.ways > 1 ? `<span class="muted"> · ${d.ways} recipes make it</span>` : ""}</p>
        <p><span class="ok">${esc(r.inputs)}</span> → ${esc(r.outLabel)} <span class="muted">${esc(r.op)}, ${esc(r.timeLabel)}</span></p>
        <p class="muted">Sells for ${fmtInt(item.value)} units; cooking one batch adds ${fmtInt(r.profit)} over the ingredients.</p>
        <p><a class="btn" href="#/recipes?item=${encodeURIComponent(d.item)}">All recipes for it</a></p>`;
    },
  });

  const effects = new List($("#effects"), {
    columns: [
      { title: "Boosts", html: (g) => esc(g.effect), cls: "strong" },
      { title: "N", html: (g) => g.dishes.length, cls: "num" },
      { title: "Good for", html: (g) => esc(g.use || "-"), cls: "muted wide-only" },
    ],
    onSelect: (g) => {
      dishes.set(g.dishes);
      history.replaceState(null, "", `#/cooking?buff=${encodeURIComponent(g.effect)}`);
    },
  });

  const start = Math.max(0, groups.findIndex((g) => g.effect === params.get("buff")));
  effects.set(groups, start);
  // j/k walk the dishes; the buff list is a click away.
  active = { list: dishes, search: null };
};

// Multi-tools ------------------------------------------------------------------

const MT_TABS = [["types", "Types"], ["weapons", "Weapons"], ["getting", "Getting one"], ["tips", "Tips"]];

VIEWS.multitools = (params) => {
  const mt = D.multitools;
  const tab = MT_TABS.some(([k]) => k === params.get("tab")) ? params.get("tab") : "types";
  view().innerHTML = `
    <div class="toolbar">
      <h1 class="view-title">Multi-tools</h1>
      <a class="btn" href="#/portals?kind=multi-tool">Portal addresses for these tools</a>
    </div>
    <p class="headline">${esc(mt._headline)}</p>
    <nav class="tabs">${MT_TABS.map(([k, label]) =>
      `<a href="#/multitools?tab=${k}" class="${k === tab ? "on" : ""}">${esc(label)}</a>`).join("")}</nav>
    <div id="tab"></div>`;

  const el = $("#tab");
  active = { list: null, search: null };

  if (tab === "types" || tab === "weapons") {
    el.innerHTML = `<div class="list" id="list"></div><aside class="detail detail-below" id="detail"></aside>`;
    const list = tab === "types"
      ? new List($("#list"), {
        columns: [
          { title: "Type", html: (t) => esc(t.type), cls: "strong" },
          { title: "Damage", html: (t) => esc(t.damage) },
          { title: "Mining", html: (t) => esc(t.mining) },
          { title: "Scan", html: (t) => esc(t.scan) },
          { title: "Slots", html: (t) => esc(t.slots) },
          { title: "Notes", html: (t) => esc(t.note), cls: "wide-only muted" },
        ],
        onSelect: (t) => {
          $("#detail").innerHTML = `<h2>${esc(t.type)}</h2>
            <p><span class="hl2">damage</span> ${esc(t.damage)} · <span class="hl2">mining</span> ${esc(t.mining)}
            · <span class="hl2">scan</span> ${esc(t.scan)} · <span class="hl2">slots at spawn</span> ${esc(t.slots)}</p>
            <p>${esc(t.note)}</p>`;
        },
      })
      : new List($("#list"), {
        columns: [
          { title: "Weapon", html: (w) => esc(w.weapon), cls: "strong" },
          { title: "Like a", html: (w) => esc(w.kind) },
          { title: "Best hit", html: (w) => esc(w.best_hit), cls: "num" },
          { title: "Good", html: (w) => esc(w.pro), cls: "wide-only" },
          { title: "Bad", html: (w) => esc(w.con), cls: "wide-only muted" },
        ],
        onSelect: (w) => {
          $("#detail").innerHTML = `<h2>${esc(w.weapon)} <span class="muted small">${esc(w.kind)}, best measured hit ${esc(w.best_hit)}</span></h2>
            <p><span class="ok">+</span> ${esc(w.pro)}</p><p><span class="err">−</span> ${esc(w.con)}</p>`;
        },
      });
    list.set(tab === "types" ? mt.types : mt.weapons);
    active.list = list;
  } else if (tab === "getting") {
    const procedure = (p) => `
      <section class="card"><h3>${esc(p.title)}</h3>
        <ol>${p.steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ol>
        ${p.note ? `<p class="muted">${esc(p.note)}</p>` : ""}
        ${(p.after || []).length ? `<ul>${p.after.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>` : ""}
      </section>`;
    el.innerHTML = `<div class="prose">
      <section class="card"><h3>Where each type comes from</h3>
        <dl class="rows">${mt.getting.map((g) => `<dt><b>${esc(g.type)}</b> <span class="muted">(${esc(g.cost)})</span></dt>
          <dd>${esc(g.where)}<div class="muted small">${esc(g.how)}</div></dd>`).join("")}</dl>
      </section>
      ${[mt.sentinel_puzzle, mt.cabinet_trick, mt.hunting].map(procedure).join("")}
    </div>`;
  } else {
    el.innerHTML = `<div class="prose">
      ${mt.rules.map((r) => `<section class="card"><h3>${esc(r.title)}</h3><p>${esc(r.body)}</p></section>`).join("")}
      <section class="card"><h3>Where upgrades come from</h3>
        <dl class="rows">${mt.upgrade_sources.map((u) => `<dt><b>${esc(u.kind)}</b></dt>
          <dd>${esc(u.where)} <div class="muted small">${esc(u.note)}</div></dd>`).join("")}</dl></section>
      <section class="card"><h3>Upgrade order</h3>
        <ol>${mt.upgrade_order.map((s) => `<li>${esc(s)}</li>`).join("")}</ol></section>
    </div>`;
  }
};

// Storage ----------------------------------------------------------------------

VIEWS.storage = (params) => {
  let q = params.get("q") || "";
  view().innerHTML = `
    <div class="toolbar">
      <h1 class="view-title">Where does it go?</h1>
      <input type="search" id="q" placeholder="/  item name, or a home: sell, junk, cold, components…" value="${esc(q)}" autocomplete="off">
    </div>
    <div class="split">
      <div class="list" id="list"></div>
      <aside class="detail" id="detail"></aside>
    </div>`;

  const homes = Object.fromEntries(D.storage.homes.map((h) => [h.key, h]));
  const all = Object.entries(D.items).map(([id, item]) => {
    const p = D.storage.outcomes[item.store];
    return { id, item, p, key: `${item.name} ${item.sub} ${p.label} ${p.verdict}`.toLowerCase() };
  });

  // With nothing typed the pane shows the layout, until you move into the
  // list to look at something.
  let quiet = false;
  const list = new List($("#list"), {
    columns: [
      { title: "Item", html: (r) => esc(r.item.name), cls: "strong" },
      { title: "What it is", html: (r) => esc(r.item.sub), cls: "muted wide-only" },
      { title: "Goes to", html: (r) => action(r.p) },
    ],
    onSelect: (r) => { if (!quiet) showItem(r); },
    empty: "Nothing matches.",
  });

  function showItem({ id, item, p }) {
    const home = homes[p.home];
    const have = inventory()[id];
    $("#detail").innerHTML = `
      <h2>${esc(item.name)}</h2>
      <p class="muted">${esc(item.sub)} · ${fmtInt(item.value)}u</p>
      <p class="big">${action(p)}</p>
      <p>${esc(p.advice)}</p>
      <dl><dt>Why</dt><dd>${esc(p.why)}</dd>
      ${home && home.key !== "none" ? `<dt>${esc(home.label)}</dt><dd class="muted">${esc(home.note)}</dd>` : ""}</dl>
      ${have ? `<p class="ok">You are carrying ${have}.</p>` : ""}
      ${home?.container ? `<p class="muted">Once one is in its container, sending more to storage routes them there by itself.</p>` : ""}
      ${PRODUCED[id] || CONSUMED[id] ? `<p><a class="btn" href="#/recipes?item=${encodeURIComponent(id)}">Recipes</a></p>` : ""}`;
  }

  function showLayout(total) {
    const byHome = {};
    const byAction = {};
    for (const r of all) {
      byHome[r.p.home] = (byHome[r.p.home] || 0) + 1;
      byAction[r.p.action] = (byAction[r.p.action] || 0) + 1;
    }
    const row = (label, n, cls = "") =>
      `<li><a href="#/storage?q=${encodeURIComponent(label)}"><b class="${cls}">${esc(label)}</b></a> <span class="muted">${n} items</span></li>`;
    $("#detail").innerHTML = `
      <h3>The ten containers</h3>
      <ul class="plain">${D.storage.homes.filter((h) => h.container).map((h) => row(h.label, byHome[h.key] || 0)).join("")}</ul>
      <h3>Everything else</h3>
      <ul class="plain">${D.storage.homes.filter((h) => !h.container && h.key !== "none").map((h) => row(h.label, byHome[h.key] || 0)).join("")}
        ${row("Sell", byAction.sell || 0, "act-sell")}
        ${row("Junk", byAction.discard || 0, "act-discard")}
        ${row("Use it", byAction.use || 0, "act-use")}</ul>
      <p class="muted">From the storage guide, section 10.</p>
      <p class="muted">${q.trim() ? `${total} items match.` : "Type a name - or sell, junk, use."}</p>`;
  }

  function refresh() {
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    const exact = q.trim().toLowerCase();
    const rows = all.filter((r) => terms.every((t) => r.key.includes(t)));
    // Exact name first, then names that start with it.
    rows.sort((a, b) => {
      const an = a.item.name.toLowerCase();
      const bn = b.item.name.toLowerCase();
      return (an !== exact) - (bn !== exact) || !an.startsWith(exact) - !bn.startsWith(exact) || an.localeCompare(bn);
    });
    quiet = !q.trim();
    list.set(rows.slice(0, 300));
    quiet = false;
    if (!q.trim() || !rows.length) showLayout(rows.length);
  }

  $("#q").addEventListener("input", debounce((e) => {
    q = e.target.value;
    history.replaceState(null, "", q ? `#/storage?q=${encodeURIComponent(q)}` : "#/storage");
    refresh();
  }));
  active = {
    list,
    search: $("#q"),
    escape: () => { $("#q").value = ""; q = ""; refresh(); },
  };
  refresh();
};

// Inventory --------------------------------------------------------------------

const inventory = () => local.get("inventory", {});
const setInventory = (inv) => local.set("inventory", inv);

VIEWS.inventory = () => {
  let cook = local.get("inv-cook", true);
  view().innerHTML = `
    <div class="toolbar">
      <h1 class="view-title">Inventory</h1>
      <form id="add" class="inline">
        <input id="q" list="item-names" placeholder="/  add an item - type its name" autocomplete="off">
        <input id="n" type="number" min="1" value="1" aria-label="how many">
        <button class="btn">Add</button>
      </form>
      <label class="check"><input type="checkbox" id="cook"${cook ? " checked" : ""}> include cooking</label>
      <button class="btn danger" id="clear">Clear all</button>
    </div>
    <p class="muted small pad-x">Kept in this browser only.</p>
    <div class="grid3">
      <section><h3>Carrying</h3><div class="list" id="have"></div></section>
      <section><h3>Can make now</h3><div class="list" id="can"></div></section>
      <section><h3>One ingredient short</h3><div class="list" id="near"></div></section>
    </div>`;

  const byName = Object.fromEntries(Object.entries(D.items).map(([id, i]) => [i.name.toLowerCase(), id]));

  const have = new List($("#have"), {
    columns: [
      { title: "Item", html: ([id]) => itemLink(id), cls: "strong" },
      { title: "Count", html: ([id, n]) => `<input type="number" class="count" min="0" value="${n}" data-id="${esc(id)}" aria-label="count">`, cls: "num" },
      { title: "Value", html: ([id, n]) => fmtInt((D.items[id]?.value ?? 0) * n), cls: "num" },
      { title: "Goes to", html: ([id]) => (placement(id) ? action(placement(id)) : ""), cls: "wide-only" },
      { title: "", html: ([id]) => `<button class="x" data-drop="${esc(id)}" title="drop">×</button>` },
    ],
    empty: "Nothing yet. Add what you are carrying above.",
  });
  const can = new List($("#can"), {
    columns: [
      { title: "Make", html: ([i]) => esc(RECIPES[i].outLabel), cls: "strong" },
      { title: "From", html: ([i]) => esc(RECIPES[i].inputs) },
      { title: "Mult", html: ([i]) => esc(RECIPES[i].mult), cls: "num" },
      { title: "Batches", html: ([, b]) => b, cls: "num" },
    ],
    onEnter: ([i]) => { location.hash = `#/recipes?item=${encodeURIComponent(RECIPES[i].out[0])}`; },
    empty: "Nothing your inventory makes yet.",
  });
  const near = new List($("#near"), {
    columns: [
      { title: "Make", html: ([i]) => esc(RECIPES[i].outLabel), cls: "strong" },
      { title: "From", html: ([i]) => esc(RECIPES[i].inputs), cls: "wide-only" },
      { title: "Missing", html: ([, m]) => m.map(([id, n]) => `${n} ${itemLink(id)}`).join(", ") },
    ],
    onEnter: ([i]) => { location.hash = `#/recipes?item=${encodeURIComponent(RECIPES[i].out[0])}`; },
    empty: "-",
  });

  function refresh() {
    const inv = inventory();
    const domains = cook ? ["refine", "cook"] : ["refine"];
    have.set(Object.entries(inv).sort((a, b) => name(a[0]).localeCompare(name(b[0]))));
    can.set(craftableNow(D.recipes, inv, domains).slice(0, 200));
    // With nothing carried, every one-input recipe is "one short": noise.
    near.set(Object.keys(inv).length ? oneHopAway(D.recipes, inv, domains).slice(0, 200) : []);
  }

  $("#add").addEventListener("submit", (e) => {
    e.preventDefault();
    const id = byName[$("#q").value.trim().toLowerCase()];
    if (!id) { toast("No item by that name - pick one from the list"); return; }
    const inv = inventory();
    inv[id] = Math.max(0, (inv[id] || 0) + Math.max(1, Number($("#n").value) || 1));
    setInventory(inv);
    $("#q").value = "";
    $("#n").value = 1;
    toast(`${name(id)}: ${inv[id]}`);
    refresh();
  });
  $("#have").addEventListener("change", (e) => {
    const el = e.target.closest("input.count");
    if (!el) return;
    const inv = inventory();
    const n = Math.floor(Number(el.value));
    if (n > 0) inv[el.dataset.id] = n; else delete inv[el.dataset.id];
    setInventory(inv);
    refresh();
  });
  $("#have").addEventListener("click", (e) => {
    const id = e.target.closest("[data-drop]")?.dataset.drop;
    if (!id) return;
    const inv = inventory();
    delete inv[id];
    setInventory(inv);
    refresh();
  });
  $("#clear").addEventListener("click", () => {
    if (Object.keys(inventory()).length && confirm("Clear the whole inventory?")) {
      setInventory({});
      refresh();
    }
  });
  $("#cook").addEventListener("change", (e) => { cook = e.target.checked; local.set("inv-cook", cook); refresh(); });
  active = { list: can, search: $("#q"), enter: () => can.onEnter(can.current()) };
  refresh();
};

// Portals ----------------------------------------------------------------------

const FIELD_NAMES = ["planet", "system", "height (Y)", "width (Z)", "length (X)"];

function glyphSvg(digit, cls = "") {
  const gl = D.glyphs[parseInt(digit, 16)];
  return `<svg class="glyph ${cls}" viewBox="${gl.viewbox}" role="img" aria-label="${esc(gl.name)}">
    <g transform="${gl.transform}">${gl.paths.map((d) => `<path d="${d}"/>`).join("")}</g></svg>`;
}

function glyphStrip(code, { names = false } = {}) {
  return `<div class="glyphs">${[...code].map((digit, i) => `
    <figure class="f${GLYPH_FIELD[i]}">${glyphSvg(digit)}
      <figcaption><b>${digit}</b>${names ? ` <span>${esc(D.glyphs[parseInt(digit, 16)].name)}</span>` : ""}</figcaption>
    </figure>`).join("")}</div>`;
}

const groupedCode = (a) =>
  a.grouped.map((part, i) => `<b class="f${i}">${part}</b>`).join(" ");

const galaxyName = (n) => D.portals.galaxies[n - 1] ?? `Galaxy ${n}`;

// Shipped addresses come from data/locations.json; the ones saved here live in
// this browser, and Export hands them over in the same shape for the file.
const myLocations = () => local.get("locations", []);
const setMyLocations = (rows) => local.set("locations", rows);

function allLocations() {
  const clean = (l) => ({ kind: "other", origin: "mine", galaxy: 1, ...l, code: l.code.replace(/[^0-9A-Fa-f]/g, "").toUpperCase() });
  const shipped = D.portals.locations.map((l) => ({ ...clean(l), local: false }));
  const mine = myLocations().map((l, i) => ({ ...clean(l), local: true, localIndex: i }));
  return [...shipped, ...mine];
}

const portalState = { text: "", planet: 0, kind: "", origin: "" };

// A GitHub issue on the "Share a portal address" form, pre-filled. The form's
// field ids are the query keys (.github/ISSUE_TEMPLATE/portal-address.yml); a
// bot checks what arrives with the same rules as this page and the TUI.
const REPO_URL = "https://github.com/rdlu/nms-items-interface";
function shareIssueUrl(l = {}) {
  const q = new URLSearchParams({ template: "portal-address.yml", title: `Portal: ${l.name || ""}`.trim() });
  for (const key of ["name", "code", "galaxy", "kind", "detail", "where"]) {
    if (l[key]) q.set(key, String(l[key]));
  }
  return `${REPO_URL}/issues/new?${q}`;
}

VIEWS.portals = (params) => {
  const st = portalState;
  if (params.has("kind")) st.kind = params.get("kind");
  if (params.has("code")) st.text = params.get("code");
  const kinds = [["", "everything"], ...D.portals.kinds.map((k) => [k, k])];
  const origins = [["", "mine and shared"], ["mine", "my finds"], ["shared", "shared"]];

  view().innerHTML = `
    <div class="toolbar">
      <h1 class="view-title">Portal addresses</h1>
      <input type="search" id="q" placeholder="/  portal code, galactic address, nmsportals link - or search saved" value="${esc(st.text)}" autocomplete="off" spellcheck="false">
      <label>Planet <select id="planet">${options([...Array(16).keys()].map((i) => [String(i), `${i.toString(16).toUpperCase()} - ${ordinal(i + 1)}`]), String(st.planet))}</select></label>
      <button class="btn" id="dial-open">Dial by glyph</button>
    </div>
    <div id="dial" class="card dial" hidden></div>
    <div class="split split-portals">
      <section class="readout" id="readout"></section>
      <section>
        <div class="toolbar sub">
          <label>Kind <select id="kind">${options(kinds, st.kind)}</select></label>
          <label>Found <select id="origin">${options(origins, st.origin)}</select></label>
          <button class="btn" id="export" title="Download the addresses saved in this browser, in data/locations.json's shape">Export mine</button>
        </div>
        <div class="list short" id="list"></div>
        <p class="invite">Found somewhere worth the trip? <a href="${shareIssueUrl()}" target="_blank" rel="noopener">Share it on GitHub</a>:
          a bot checks the address and replies, and accepted ones join this list for everyone.
          Or edit <a href="${REPO_URL}/blob/main/data/locations.json" target="_blank" rel="noopener">data/locations.json</a> in a pull request.</p>
        <aside class="detail detail-below" id="detail"></aside>
      </section>
    </div>`;

  let current = null;
  let error = "";
  let search = "";

  const list = new List($("#list"), {
    columns: [
      { title: "Name", html: (l) => esc(l.name), cls: "strong" },
      { title: "Kind", html: (l) => esc(l.kind) },
      { title: "Found", html: (l) => (l.origin === "mine" ? `<span class="ok">mine</span>` : "shared") + (l.local ? ` <span class="tag">here</span>` : "") },
      { title: "Address", html: (l) => `<code>${esc(l.code)}</code>`, cls: "wide-only" },
      { title: "What is there", html: (l) => esc(l.detail), cls: "muted wide-only" },
    ],
    onSelect: (l) => showLocation(l),
    onEnter: (l) => load(l.code),
    empty: "No saved address matches.",
  });

  function showLocation(l) {
    let a;
    try { a = Address.fromCode(l.code); } catch { return; }
    $("#detail").innerHTML = `
      <h2>${esc(l.name)} <span class="muted small">${esc(l.kind)}</span>
        ${l.origin === "mine" ? `<span class="ok small">found by me</span>` : `<span class="hl2 small">shared</span>`}</h2>
      <p><code>${groupedCode(a)}</code> <span class="muted">${a.galactic}</span></p>
      <p><span class="hl2">Galaxy</span> ${l.galaxy || 1}. ${esc(galaxyName(l.galaxy || 1))}</p>
      ${glyphStrip(a.code)}
      ${l.detail ? `<p><span class="hl2">There</span> ${esc(l.detail)}</p>` : ""}
      ${l.where ? `<p><span class="hl2">Finding it</span> ${esc(l.where)}</p>` : ""}
      <p class="muted small">${esc([l.source, l.added].filter(Boolean).join(" · "))}</p>
      <div class="actions">
        <button class="btn" data-load="${esc(l.code)}">Open in converter</button>
        <button class="btn" data-copy="${esc(l.code)}">Copy code</button>
        ${l.local ? `<a class="btn" href="${esc(shareIssueUrl(l))}" target="_blank" rel="noopener">Share on GitHub</a>` : ""}
        ${l.local ? `<button class="btn danger" data-del="${l.localIndex}">Delete</button>` : ""}
      </div>`;
  }

  function refreshList() {
    const terms = search.toLowerCase().split(/\s+/).filter(Boolean);
    const rows = allLocations().filter((l) =>
      (!st.kind || l.kind === st.kind) &&
      (!st.origin || l.origin === st.origin) &&
      terms.every((t) => [l.name, l.kind, l.origin, l.detail, l.where, l.source, l.code].join(" ").toLowerCase().includes(t)));
    list.set(rows, list.sel > 0 ? list.sel : 0);
  }

  function refreshReadout() {
    const el = $("#readout");
    if (!current) {
      el.innerHTML = `${error ? `<p class="err">${esc(error)}</p>` : ""}${PRIMER}`;
      return;
    }
    const a = current;
    const [x, y, z] = a.voxel;
    const saved = allLocations().filter((l) => l.code === a.code);
    el.innerHTML = `
      <p class="code-big">${groupedCode(a)}</p>
      ${glyphStrip(a.code, { names: true })}
      <dl>
        <dt>Portal code</dt><dd><b>${a.code}</b> <button class="link" data-copy="${a.code}">copy</button></dd>
        <dt>Galactic</dt><dd><b>${a.galactic}</b> <button class="link" data-copy="${a.galactic}">copy</button></dd>
        <dt>Voxel</dt><dd>X ${x >= 0 ? "+" : ""}${x} · Y ${y >= 0 ? "+" : ""}${y} · Z ${z >= 0 ? "+" : ""}${z} <span class="muted">from centre</span></dd>
        <dt>Planet</dt><dd>${ordinal(a.planet + 1)} of the system <span class="muted">(glyph ${a.planet.toString(16).toUpperCase()})</span></dd>
        <dt>System</dt><dd>0x${a.grouped[1]} <span class="muted">(${a.system})</span></dd>
        <dt>Share link</dt><dd><a href="${a.shareLink}" target="_blank" rel="noopener">${a.shareLink}</a></dd>
      </dl>
      ${a.system > D.portals.max_system ? `<p class="warn">! system index 0x${a.grouped[1]} is above the 0x${D.portals.max_system.toString(16).toUpperCase()} nmsportals treats as the maximum - check the address</p>` : ""}
      ${saved.length
        ? `<h3 class="ok">Saved</h3><ul>${saved.map((l) => `<li>${esc(l.name)} <span class="muted">${esc(l.kind)}, ${esc(l.origin)}, ${l.galaxy || 1}. ${esc(galaxyName(l.galaxy || 1))}</span></li>`).join("")}</ul>`
        : ""}
      <details class="save"${saved.length ? "" : " open"}>
        <summary>Save this address</summary>
        <form id="save" class="form">
          <label>Name <input name="name" required placeholder="what you call it"></label>
          <label>Kind <select name="kind">${options(D.portals.kinds.map((k) => [k, k]), "other")}</select></label>
          <label>Found <select name="origin">${options([["mine", "mine - I stood there"], ["shared", "shared - off a catalogue or a friend"]], "mine")}</select></label>
          <label>Galaxy <input name="galaxy" type="number" min="1" max="256" value="1"></label>
          <label class="wide">What is there <input name="detail" placeholder="class, type, slot count"></label>
          <label class="wide">Finding it <input name="where" placeholder="how to find it once you arrive"></label>
          <label class="wide">Source <input name="source" placeholder="who shared it, or where you found it"></label>
          <div class="wide form-actions">
            <button class="btn">Save in this browser</button>
            <button class="btn" type="button" id="share-gh" title="Open a GitHub issue with these fields filled in">Share on GitHub</button>
          </div>
        </form>
      </details>`;
    $("#share-gh").addEventListener("click", () => {
      const f = new FormData($("#save"));
      const row = Object.fromEntries([...f].map(([k, v]) => [k, String(v).trim()]));
      window.open(shareIssueUrl({ ...row, code: a.code }), "_blank", "noopener");
    });
    $("#save").addEventListener("submit", (e) => {
      e.preventDefault();
      const f = new FormData(e.target);
      const row = {
        name: f.get("name").trim() || "unnamed",
        code: a.code,
        kind: f.get("kind"),
        origin: f.get("origin"),
        galaxy: Math.min(256, Math.max(1, Number(f.get("galaxy")) || 1)),
        detail: f.get("detail").trim(),
        where: f.get("where").trim(),
        source: f.get("source").trim(),
        added: new Date().toISOString().slice(0, 10),
      };
      setMyLocations([...myLocations(), row]);
      toast(`Saved ${row.name}`);
      refreshList();
      refreshReadout();
    });
  }

  function convert() {
    const text = st.text.trim();
    current = null; error = ""; search = "";
    if (text) {
      try {
        current = Address.parse(text, st.planet);
        st.planet = current.planet;
        $("#planet").value = String(st.planet);
      } catch (exc) {
        if (!(exc instanceof AddressError)) throw exc;
        if (looksLikeAddress(text)) error = exc.message; else search = text;
      }
    }
    refreshList();
    refreshReadout();
  }

  function load(code) {
    st.text = code;
    $("#q").value = code;
    convert();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // The dial: sixteen symbols in dial order, two rows of eight, so picking
  // here is the same motion as dialling at the portal.
  let dialled = "";
  function drawDial() {
    const next = dialled.length < 12 ? FIELD_NAMES[GLYPH_FIELD[dialled.length]] : "";
    $("#dial").innerHTML = `
      <div class="dial-head">
        <b>Dial an address</b>
        <span class="muted small">Click the symbols in order, or type the hex digit. Backspace undoes.</span>
        <button class="link" id="dial-close">close</button>
      </div>
      <div class="dial-code">${[...Array(12).keys()].map((i) => i < dialled.length
        ? `<span class="slot f${GLYPH_FIELD[i]}">${glyphSvg(dialled[i])}</span>`
        : `<span class="slot empty f${GLYPH_FIELD[i]}"></span>`).join("")}</div>
      <p class="small">${next ? `<span class="muted">glyph ${dialled.length + 1} of 12 - ${next}</span>` : `<span class="ok">all twelve</span> <button class="btn" id="dial-use">Use it</button>`}
        ${dialled ? `<button class="link" id="dial-undo">undo</button>` : ""}</p>
      <div class="dial-grid">${D.glyphs.map((gl) =>
        `<button class="dial-key" data-digit="${gl.hex}" title="${esc(gl.name)}">${glyphSvg(gl.hex)}<span><b>${gl.hex}</b> ${esc(gl.name)}</span></button>`).join("")}</div>`;
  }
  function dialPick(digit) {
    if (dialled.length < 12) dialled += digit.toUpperCase();
    drawDial();
  }
  $("#dial-open").addEventListener("click", () => {
    const el = $("#dial");
    el.hidden = !el.hidden;
    if (!el.hidden) { dialled = ""; drawDial(); }
  });
  $("#dial").addEventListener("click", (e) => {
    const key = e.target.closest("[data-digit]");
    if (key) return dialPick(key.dataset.digit);
    if (e.target.closest("#dial-undo")) { dialled = dialled.slice(0, -1); drawDial(); }
    if (e.target.closest("#dial-close")) $("#dial").hidden = true;
    if (e.target.closest("#dial-use")) { load(dialled); $("#dial").hidden = true; }
  });

  $("#q").addEventListener("input", debounce((e) => { st.text = e.target.value; convert(); }));
  $("#planet").addEventListener("change", (e) => {
    st.planet = Number(e.target.value);
    if (current) { st.text = current.withPlanet(st.planet).code; $("#q").value = st.text; }
    convert();
  });
  $("#kind").addEventListener("change", (e) => { st.kind = e.target.value; refreshList(); });
  $("#origin").addEventListener("change", (e) => { st.origin = e.target.value; refreshList(); });
  $("#export").addEventListener("click", () => {
    const rows = myLocations();
    if (!rows.length) { toast("Nothing saved in this browser yet"); return; }
    const blob = new Blob([`${JSON.stringify(rows, null, 1)}\n`], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "nms-locations.json";
    a.click();
    URL.revokeObjectURL(a.href);
  });
  view().addEventListener("click", (e) => {
    const c = e.target.closest("[data-copy]");
    if (c) copy(c.dataset.copy, c.dataset.copy.includes(":") ? "the galactic address" : "the portal code");
    const l = e.target.closest("[data-load]");
    if (l) load(l.dataset.load);
    const d = e.target.closest("[data-del]");
    if (d && confirm("Delete this saved address from this browser?")) {
      const rows = myLocations();
      rows.splice(Number(d.dataset.del), 1);
      setMyLocations(rows);
      refreshList();
      refreshReadout();
    }
  });

  active = {
    list,
    search: $("#q"),
    enter: () => list.current() && load(list.current().code),
    escape: () => { $("#q").value = ""; st.text = ""; convert(); },
    key: (e) => {
      if ($("#dial").hidden) return false;
      if (/^[0-9a-fA-F]$/.test(e.key)) { dialPick(e.key); return true; }
      if (e.key === "Backspace") { dialled = dialled.slice(0, -1); drawDial(); return true; }
      return false;
    },
  };
  convert();
};

const PRIMER = `
  <h3>Paste either form above</h3>
  <p>It converts as you type.</p>
  <dl>
    <dt>portal code</dt><dd><code>40E907FF0D6B</code><div class="muted small">12 hex digits, one per glyph</div></dd>
    <dt>galactic address</dt><dd><code>056A:0086:07EF:00E9</code><div class="muted small">what a signal booster shows</div></dd>
    <dt>share link</dt><dd><span class="muted">a nmsportals.github.io URL</span></dd>
  </dl>
  <p class="muted">Type anything else and it searches the saved addresses.</p>
  <h3>What the twelve glyphs are</h3>
  <p class="code-big"><b class="f0">p</b> <b class="f1">SSS</b> <b class="f2">YY</b> <b class="f3">ZZZ</b> <b class="f4">XXX</b></p>
  <p><span class="f0">planet</span>, <span class="f1">system index</span>, then the voxel as
  <span class="f2">height</span>, <span class="f3">width</span>, <span class="f4">length</span>. Portal coordinates put
  0,0,0 at the centre of the galaxy; a galactic address counts from a corner, which is the whole reason the two do not look alike.</p>
  <h3>Dialling one</h3>
  <p>The 16 glyphs sit on the portal dial in a fixed order, 0-9 then A-F, so the hex digit <i>is</i> the position:
  <b>A</b> is the 11th symbol, every time. You need all 16 unlocked, not twelve.</p>
  <h3>Sharing one</h3>
  <p>The same twelve glyphs point at a different star in each of the 256 galaxies, so an address alone is ambiguous. Saved ones carry their galaxy.</p>
  <h3>Adding yours to the list</h3>
  <p>Convert it here, fill in the form, and press <b>Share on GitHub</b>: it opens an issue with the fields filled in.
  A bot converts the address the same way this page does and replies with the glyphs it read, or what to fix.
  Once accepted it is added to the shared list, credited to you.</p>`;

// Home -------------------------------------------------------------------------

// Line icons for the section cards, in the 24px / 1.5-stroke outline style of
// the plugii and dotfiles start pages. Drawn here, not taken from a set.
const ICONS = {
  recipes: '<path d="M9 3h6M10 3v6l-5.2 9.2A1.9 1.9 0 0 0 6.5 21h11a1.9 1.9 0 0 0 1.7-2.8L14 9V3"/><path d="M7.4 15h9.2"/>',
  chain: '<rect x="9" y="3" width="6" height="4"/><rect x="3" y="17" width="6" height="4"/><rect x="15" y="17" width="6" height="4"/><path d="M12 7v7.5M6 17v-2.5h12V17"/>',
  nanites: '<path d="M12 3l7.8 4.5v9L12 21l-7.8-4.5v-9z"/><path d="M4.2 7.5L12 12l7.8-4.5M12 12v9"/>',
  cooking: '<path d="M4 11h16v2.5A6.5 6.5 0 0 1 13.5 20h-3A6.5 6.5 0 0 1 4 13.5z"/><path d="M2 11h20M9 7.5c0-1.6 1.2-1.6 1.2-3.5M14 7.5c0-1.6 1.2-1.6 1.2-3.5"/>',
  multitools: '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="1.5"/><path d="M12 2v5M12 17v5M2 12h5M17 12h5"/>',
  portals: '<path d="M5 21V11a7 7 0 0 1 14 0v10"/><path d="M8.5 21v-9.5a3.5 3.5 0 0 1 7 0V21M3 21h18"/>',
  storage: '<rect x="3" y="4" width="18" height="5"/><path d="M5 9v11h14V9M10 13h4"/>',
  inventory: '<path d="M6 10a6 6 0 0 1 12 0v10H6z"/><path d="M9.5 5V3h5v2M9 14h6v3H9z"/>',
  sheet: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
  data: '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/>',
  keys: '<rect x="2.5" y="6" width="19" height="12" rx="1"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7.5 14h9"/>',
  terminal: '<rect x="3" y="4" width="18" height="16"/><path d="M7 9l3 3-3 3M12.5 15h4.5"/>',
};

// Three ways to run the terminal app, from the least installed to the most.
// Shown on the start page and in Help; the README says the same at more length.
const INSTALL = `
  <div class="install">
    <section class="pane">
      <h3><span>podman / docker</span><em>nothing else to install</em></h3>
      <p>The app and its Python live in a container. Saved addresses still land in the checkout.</p>
      <pre><code>git clone https://github.com/rdlu/nms-items-interface
cd nms-items-interface
podman compose run --rm tui</code></pre>
      <p class="muted small">This site, offline: <code>podman compose up site</code>, then <code>localhost:8001</code>. Docker reads the same <code>compose.yaml</code>.</p>
    </section>
    <section class="pane">
      <h3><span>uv</span><em>one tool, it fetches Python</em></h3>
      <p><a href="https://docs.astral.sh/uv/">uv</a> downloads the right Python and the one dependency, Textual, on the first run.</p>
      <pre><code>git clone https://github.com/rdlu/nms-items-interface
cd nms-items-interface
uv run nms</code></pre>
      <p class="muted small">Python 3.11 or newer. Any terminal with 256 colours; truecolor looks best.</p>
    </section>
    <section class="pane">
      <h3><span>mise</span><em>to work on it</em></h3>
      <p><a href="https://mise.jdx.dev/">mise</a> pins uv and Typst and carries every task: tests, the PDF, this site, a data refresh.</p>
      <pre><code>mise install
mise run sync
mise run tui</code></pre>
      <p class="muted small"><code>mise tasks</code> lists them all; the <a href="${REPO_URL}#tasks">README</a> explains each.</p>
    </section>
  </div>`;

// What the project is, and a card per section -- the same shape as the plugii
// and dotfiles start pages. Every count on it is read off data.json, so the
// page cannot claim a number the data no longer has.
VIEWS.home = () => {
  active = { list: null, search: null };
  const count = (domain) => D.recipes.filter((r) => r.domain === domain).length;
  const dishes = D.cooking.reduce((n, g) => n + g.dishes.length, 0);
  const containers = D.storage.homes.filter((h) => h.container).length;
  const bestNanite = D.nanites.map((n) => RECIPES[n.recipe]).sort((a, b) => b.rate - a.rate)[0];
  const loops = RECIPES.filter((r) => r.loop > 1).length;
  // The chain card shows off a real plan: the most valuable thing Tier 0 reaches.
  const showcase = Object.keys(D.tiers[0].via.refine)
    .sort((a, b) => (D.items[b]?.value ?? 0) - (D.items[a]?.value ?? 0))[0];
  const n = (x) => `<b>${fmtInt(x)}</b>`;

  const card = (key, href, title, body, icon) => `
    <a class="feature" href="${href}">
      <h3>${ICONS[icon] ? `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">${ICONS[icon]}</svg>` : ""}<span>${esc(title)}</span>${key ? `<kbd>${key}</kbd>` : ""}</h3>
      <p>${body}</p>
    </a>`;

  view().innerHTML = `
    <section class="home">
      <a class="badge" href="https://github.com/rdlu/nms-items-interface"><i></i>No Man's Sky Items Interface (NMSii)<em> · Python TUI · GPL-3.0</em> <span>→</span></a>
      <h1 class="hero">The numbers No Man's Sky doesn't show you</h1>
      <p class="lede">
        What refines into what, the cheapest way to make it from what you can pick up,
        which dish buffs what, where every item belongs in storage, and every portal
        address drawn in glyphs. All of it computed from the game's own recipe tables,
        not copied from a wiki.
      </p>
      ${gameVersion() ? `<p><a class="badge" href="${REPO_URL}/blob/main/docs/cosmos-changes.md"><i></i>Up to date with ${esc(gameVersion())}<em> · ${esc(gameBuild())} · read from the game files</em> <span>→</span></a></p>` : ""}
      <p class="lede muted">
        This is the web version of a terminal app. It runs entirely in your browser,
        and works on a phone propped up next to the game.
      </p>
      <div class="hero-actions">
        <a class="primary" href="#/recipes">Open the recipes</a>
        <a href="#/home" id="to-install">Run it locally</a>
        <a href="pdf/nms-cheatsheet-dark.pdf">Cheat sheet (PDF)</a>
        <a href="https://github.com/rdlu/nms-items-interface">GitHub</a>
      </div>

      <figure class="demo">
        <div class="bar"><span>mise run tui</span><b>the terminal app</b></div>
        <img src="img/recipes.svg" alt="The NMSii terminal app: the recipe list searched for cobalt, with the detail pane showing the selected recipe, its ingredients and how gettable each one is." loading="lazy">
      </figure>

      <h2 class="section">What's inside</h2>
      <div class="features">
        ${card("1", "#/recipes", "Recipes", `${n(count("refine"))} refining and ${n(count("cook"))} cooking recipes, searchable by output, ingredient or operation. Sort by multiplier, speed, profit or how gettable the inputs are; ${loops} recipes are loops that grow a stack from a seed.`, "recipes")}
        ${card("c", `#/chain/${encodeURIComponent(showcase)}`, "Chain planner", `Works backwards from any item to what you can pick up on any planet, off asteroids, or from an atmosphere harvester, minimising refiner time. Try it on ${esc(name(showcase))}, the most valuable thing the bare planet surface refines into.`, "chain")}
        ${card("2", "#/nanites", "Nanite ladder", `All ${n(D.nanites.length)} routes to nanites, ranked by nanites per hour per refiner, with where each input drops. The best is ${esc(bestNanite?.inputs ?? "")} at ${n(bestNanite?.rate ?? 0)}/h.`, "nanites")}
        ${card("3", "#/cooking", "Cooking buffs", `${n(dishes)} dishes across ${n(D.cooking.length)} buffs: what each one does when you eat it, how strongly, and what it sells for. Cook the batch, eat one, sell the rest.`, "cooking")}
        ${card("4", "#/multitools", "Multi-tools", `The ${n(D.multitools.types.length)} types side by side, the weapons measured, where the free S-class ones come from, and the adjacency and supercharged-slot rules.`, "multitools")}
        ${card("5", "#/portals", "Portal addresses", `Convert between portal glyphs and galactic coordinates as you type, dial an address symbol by symbol, and browse ${n(D.portals.locations.length)} saved places worth going.`, "portals")}
        ${card("6", "#/storage", "Where does it go?", `Every one of ${n(Object.keys(D.items).length)} items gets a home: one of the ${containers} storage containers, Cold Storage, or sell, junk, use it now. Type "sell" to list everything to sell.`, "storage")}
        ${card("7", "#/inventory", "Inventory", "Type what you are carrying, and see what you can make right now and what you are one ingredient short of. Kept in this browser.", "inventory")}
        ${card("", "pdf/nms-cheatsheet.pdf", "Cheat sheet", "The recipes worth memorising on six landscape A4 pages, for print. The dark version for screens is linked at the bottom of every page.", "sheet")}
      </div>

      <h2 class="section" id="install">Run it on your machine</h2>
      <p class="lede muted">The terminal app has the same screens with vim keys, a command palette and themes, and
        saves portal addresses to a file you can share. It works offline once installed.</p>
      ${INSTALL}

      <h2 class="section">Good to know</h2>
      <div class="features">
        ${card("", `${REPO_URL}#where-the-data-comes-from`, "Straight from the game files", `Recipes, batch times and values are read from the game's own files${gameVersion() ? `, currently ${esc(gameVersion())} (${esc(gameBuild())})` : ""}, re-extracted after each patch. NMS-Handbook, the original source, is the fallback. A test suite checks the claims the written guides make.`, "data")}
        ${card("?", "#/help", "Keys and columns", "<kbd>j</kbd> <kbd>k</kbd> move, <kbd>/</kbd> searches, <kbd>Enter</kbd> pivots, <kbd>1</kbd>-<kbd>7</kbd> jump between sections. What Mult, Gettable and the rest mean.", "keys")}
        ${card("", "#/portals", "Share an address", "Found a ship, a tool or a base worth the trip? Convert it on the portals page and share it as a GitHub issue; a bot checks the glyphs, and accepted ones join the list.", "portals")}
      </div>
    </section>`;
  // A scroll, not a #fragment: the hash is the router's.
  $("#to-install").addEventListener("click", (e) => {
    e.preventDefault();
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    $("#install").scrollIntoView({ behavior: still ? "auto" : "smooth" });
  });
};

// Help -------------------------------------------------------------------------

VIEWS.help = () => {
  active = { list: null, search: null };
  view().innerHTML = `<div class="prose">
    <section class="card"><h3>Keys</h3>
      <dl class="rows keys">
        <dt><kbd>j</kbd> <kbd>k</kbd> / <kbd>↓</kbd> <kbd>↑</kbd></dt><dd>move through the list</dd>
        <dt><kbd>/</kbd></dt><dd>search - <kbd>Esc</kbd> or <kbd>Enter</kbd> leaves the box</dd>
        <dt><kbd>Enter</kbd></dt><dd>recipes: everything touching the item · portals: load the address</dd>
        <dt><kbd>Esc</kbd></dt><dd>clear the search or the item filter</dd>
        <dt><kbd>p</kbd> <kbd>r</kbd></dt><dd>recipes that produce / consume the highlighted item</dd>
        <dt><kbd>c</kbd></dt><dd>chain plan for the highlighted item</dd>
        <dt><kbd>1</kbd>-<kbd>7</kbd></dt><dd>jump to a section</dd>
      </dl></section>
    <section class="card"><h3>Reading the columns</h3>
      <dl class="rows">
        <dt>Mult</dt><dd>Units out per unit in. <code>x6 loop</code> means the recipe feeds itself:
          1 Chlorine + 2 Oxygen → 6 Chlorine multiplies the seed six times.</dd>
        <dt>Time</dt><dd>One batch, from the game files. The in-game display is often wrong.</dd>
        <dt>Machine</dt><dd>Portable/Personal (1 input), Medium (2), Large (3).</dd>
        <dt>Rate / Profit</dt><dd>Units per hour with one machine kept fed, and the base-value difference across one batch.
          Profit is in units and says nothing about nanites; those get their own page.</dd>
        <dt>Gettable</dt><dd><code>T0/T1/T2 +n</code>: refinable from surface materials / asteroids / an atmosphere harvester,
          n refining steps away. <code>needs seed</code>: refinable, but wanting a material none of those tiers contain.
          <code>loot (…)</code>: no recipe makes it.</dd>
      </dl></section>
    <section class="card"><h3>The chain planner</h3>
      <p>It works backwards to a source set - by default the five things you can pick up on any planet - and minimises
      <b>refiner-seconds per unit</b>, so the plan is the one that ties up a machine for the least time.</p></section>
    <section class="card span"><h3>Running it locally</h3>
      <p>This site is the web front end of a terminal app. Both read the same data, and the app adds vim keys,
      a command palette, themes, and saving portal addresses to <code>data/locations.json</code>.</p>
      ${INSTALL}
      <p class="muted small">On Windows, use WSL or the podman route. The app is a Textual program: any modern terminal draws it.</p></section>
    <section class="card"><h3>Sharing a portal address</h3>
      <p>Convert it on the <a href="#/portals">portals page</a>, fill in the form there, and press <b>Share on GitHub</b>.
      It opens an issue on the <i>Share a portal address</i> form with the fields filled in.</p>
      <p>A bot reads it within a minute, converts the address the same way this page does, and replies with the glyphs
      and coordinates it got, or a list of what to fix. Edit the issue and it checks again. When a maintainer accepts it,
      the bot opens the pull request that adds it, crediting you.</p>
      <p>Comfortable with git? Edit <a href="${REPO_URL}/blob/main/data/locations.json">data/locations.json</a> in a pull
      request instead; the same checks run on it. Locally, <code>mise run validate-locations</code>.</p></section>
    <section class="card"><h3>Where this comes from</h3>
      <p>Every number is read from the game's own files${gameVersion()
        ? `: ${esc(gameVersion())} (${esc(gameBuild())}), extracted ${esc(D.source.extracted)}` : ""}.
      Earlier builds read the same tables via
      <a href="https://github.com/ApexFatality93/NMS-Handbook">NMS-Handbook</a>, still the fallback source. This page is the web front end of a
      terminal app; the source, the cheat-sheet PDFs and the full README are on
      <a href="https://github.com/rdlu/nms-items-interface">GitHub</a>. Portal glyphs are traced from
      <a href="https://nmsportals.github.io/">nmsportals</a>. No Man's Sky and its data belong to Hello Games.</p></section>
  </div>`;
};

// -- routing and keys ---------------------------------------------------------

const NAV = [
  ["recipes", "Recipes"], ["nanites", "Nanites"], ["cooking", "Cooking"],
  ["multitools", "Multi-tools"], ["portals", "Portals"], ["storage", "Storage"],
  ["inventory", "Inventory"], ["help", "Help"],
];

// The markdown twin of each page (scripts/build_markdown.py writes them), for
// the footer link and the <link rel=alternate> a crawler or an AI reads.
const MD_PAGES = {
  nanites: "md/nanites.md", cooking: "md/cooking.md", multitools: "md/multitools.md",
  portals: "md/portals.md", storage: "md/storage.md", inventory: "md/items/index.md",
  help: "md/guide.md", recipes: "md/recipes.md",
};
function markdownFor(section, rest, params) {
  const item = section === "chain" ? rest : section === "recipes" ? params.get("item") : null;
  if (item && D.items[item]) return `md/items/${encodeURIComponent(item)}.md`;
  return MD_PAGES[section] || "llms.txt";
}

function route() {
  const hash = location.hash.replace(/^#\/?/, "") || "home";
  const [path, query = ""] = hash.split("?");
  const [section, ...rest] = path.split("/");
  const params = new URLSearchParams(query);
  const render = VIEWS[section] || VIEWS.home;
  document.querySelectorAll("#nav a").forEach((a) => {
    const on = a.dataset.view === section || (section === "chain" && a.dataset.view === "recipes");
    a.classList.toggle("on", on);
    if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  // A fresh element per visit, so listeners a view hangs on it leave with it.
  const fresh = view().cloneNode(false);
  view().replaceWith(fresh);
  active = { list: null, search: null };
  window.scrollTo(0, 0);
  const target = decodeURIComponent(rest.join("/"));
  render(params, target);
  const md = markdownFor(section, target, params);
  $("#md-page").href = md;
  document.querySelector('link[rel="alternate"][type="text/markdown"]')?.setAttribute("href", md);
  document.title = section === "home" || !VIEWS[section]
    ? "NMSii - No Man's Sky recipes, nanites, portals"
    : `${NAV.find(([k]) => k === section)?.[1] ?? "Chain"} · NMSii`;
}

function onKey(e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    openPalette();
    return;
  }
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const typing = e.target.closest("input, select, textarea");
  if (typing) {
    if (e.key === "Escape") e.target.blur();
    if (e.key === "Enter" && e.target === active.search && active.list) {
      e.target.blur();
      e.preventDefault();
    }
    return;
  }
  if (active.key?.(e)) { e.preventDefault(); return; }
  const list = active.list;
  const id = location.hash.startsWith("#/recipes") ? list?.current()?.out?.[0] : null;
  const go = (hash) => { location.hash = hash; };
  switch (e.key) {
    case "j": case "ArrowDown": list?.move(1); break;
    case "k": case "ArrowUp": list?.move(-1); break;
    case "PageDown": list?.move(10); break;
    case "PageUp": list?.move(-10); break;
    case "G": case "End": list?.select(list.rows.length - 1); break;
    case "Home": list?.select(0); break;
    case "/": active.search?.focus(); active.search?.select(); break;
    case "Enter": active.enter?.(); break;
    case "Escape": active.escape?.(); break;
    case "p": if (id) go(`#/recipes?item=${encodeURIComponent(id)}&role=output`); break;
    case "r": if (id) go(`#/recipes?item=${encodeURIComponent(id)}&role=input`); break;
    case "c": if (id) go(`#/chain/${encodeURIComponent(id)}`); break;
    case "?": go("#/help"); break;
    default:
      if (/^[1-7]$/.test(e.key)) go(`#/${NAV[Number(e.key) - 1][0]}`);
      else return;
  }
  e.preventDefault();
}

// -- header: theme, menu, search palette --------------------------------------

// Light, dark, or the system's -- Hextra's three, "system" by default. An
// explicit choice sets data-theme; "system" removes it and the CSS media
// query decides, so an OS switch recolours an open page with no code here.
const themeChoice = () => {
  const t = local.get("theme", "system");
  return t === "light" || t === "dark" ? t : "system";
};

function applyTheme(choice) {
  if (choice === "system") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = choice;
  local.set("theme", choice);
  document.querySelectorAll("[data-theme-choice]").forEach((b) =>
    b.setAttribute("aria-checked", String(b.dataset.themeChoice === choice)));
}

function setupHeader() {
  const themeBtn = $("#theme");
  const themeMenu = $("#theme-menu");
  const closeTheme = () => { themeMenu.hidden = true; themeBtn.setAttribute("aria-expanded", "false"); };
  applyTheme(themeChoice());
  themeBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    themeMenu.hidden = !themeMenu.hidden;
    themeBtn.setAttribute("aria-expanded", String(!themeMenu.hidden));
    if (!themeMenu.hidden) themeMenu.querySelector('[aria-checked="true"]')?.focus();
  });
  themeMenu.addEventListener("click", (e) => {
    const b = e.target.closest("[data-theme-choice]");
    if (!b) return;
    applyTheme(b.dataset.themeChoice);
    closeTheme();
    themeBtn.focus();
  });
  themeMenu.addEventListener("keydown", (e) => {
    const items = [...themeMenu.querySelectorAll("button")];
    const i = items.indexOf(document.activeElement);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      items[(i + (e.key === "ArrowDown" ? 1 : items.length - 1)) % items.length].focus();
    } else if (e.key === "Escape") {
      e.stopPropagation();
      closeTheme();
      themeBtn.focus();
    }
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".theme-wrap")) closeTheme(); });
  const menu = $("#menu");
  const closeMenu = () => { document.body.classList.remove("menu-open"); menu.setAttribute("aria-expanded", "false"); };
  menu.addEventListener("click", () => {
    const open = document.body.classList.toggle("menu-open");
    menu.setAttribute("aria-expanded", String(open));
  });
  $("#nav").addEventListener("click", closeMenu);
  window.addEventListener("hashchange", closeMenu);
  $("#search-open").addEventListener("click", openPalette);
  $("#palette").addEventListener("click", (e) => { if (e.target.id === "palette") closePalette(); });
  $("#palette-q").addEventListener("input", () => { palette.sel = 0; drawPalette(); });
  $("#palette-q").addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      palette.sel = Math.max(0, Math.min(palette.rows.length - 1, palette.sel + (e.key === "ArrowDown" ? 1 : -1)));
      drawPalette(false);
    } else if (e.key === "Enter") {
      e.preventDefault();
      choose(palette.rows[palette.sel]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      closePalette();
    }
  });
  $("#palette-list").addEventListener("click", (e) => {
    const li = e.target.closest("li[data-i]");
    if (li) choose(palette.rows[Number(li.dataset.i)]);
  });
}

// The TUI's Ctrl+P palette, as the site's search: sections by name, items by
// name (exact, then prefix, then substring, like Book.search_items), and a
// pasted portal address straight into the converter.
const palette = { rows: [], sel: 0 };

function openPalette() {
  if (!D) return;
  $("#palette").hidden = false;
  $("#palette-q").value = "";
  palette.sel = 0;
  drawPalette();
  $("#palette-q").focus();
}

function closePalette() { $("#palette").hidden = true; }

function choose(row) {
  if (!row) return;
  closePalette();
  location.hash = row.href;
}

function paletteRows(q) {
  const text = q.trim();
  const lower = text.toLowerCase();
  const rows = [];
  const sections = [["home", "Home"], ...NAV];
  for (const [key, label] of sections) {
    if (!lower || label.toLowerCase().includes(lower)) {
      rows.push({ kind: "section", label, href: `#/${key === "home" ? "" : key}` });
    }
  }
  if (!lower) return rows;
  try {
    const a = Address.parse(text);
    rows.unshift({ kind: "portal", label: a.code, note: a.galactic, href: `#/portals?code=${a.code}` });
  } catch { /* not an address */ }
  const starts = [];
  const contains = [];
  for (const [id, item] of Object.entries(D.items)) {
    const n = item.name.toLowerCase();
    if (n.startsWith(lower)) starts.push(id);
    else if (n.includes(lower)) contains.push(id);
  }
  const byName = (a, b) =>
    (name(a).toLowerCase() !== lower) - (name(b).toLowerCase() !== lower) || name(a).localeCompare(name(b));
  for (const id of [...starts.sort(byName), ...contains.sort(byName)].slice(0, 30)) {
    const recipes = PRODUCED[id] || CONSUMED[id];
    rows.push({
      kind: recipes ? "item" : "store",
      label: name(id),
      note: D.items[id].sub,
      // Items no recipe touches still have a storage answer.
      href: recipes ? `#/recipes?item=${encodeURIComponent(id)}` : `#/storage?q=${encodeURIComponent(name(id))}`,
    });
  }
  return rows;
}

function drawPalette(rebuild = true) {
  if (rebuild) palette.rows = paletteRows($("#palette-q").value);
  const tag = { section: "go", item: "recipes", store: "storage", portal: "portal" };
  $("#palette-list").innerHTML = palette.rows.length
    ? palette.rows.map((r, i) => `<li data-i="${i}" role="option"${i === palette.sel ? ' class="sel" aria-selected="true"' : ""}>
        <span class="pl">${esc(r.label)}</span>${r.note ? `<span class="pn">${esc(r.note)}</span>` : ""}<span class="pt">${tag[r.kind]}</span></li>`).join("")
    : `<li class="empty">Nothing by that name.</li>`;
  $("#palette-list .sel")?.scrollIntoView({ block: "nearest" });
}

async function main() {
  // © 2026, or 2026-now once it is later: plugii's footer does the same.
  const year = new Date().getFullYear();
  if (year > 2026) $("#years").textContent = `2026–${year}`;
  $("#nav").innerHTML = NAV.map(([k, label], i) =>
    `<a href="#/${k}" data-view="${k}" title="${i < 7 ? `key ${i + 1}` : "key ?"}">${esc(label)}</a>`).join("");
  setupHeader();
  try {
    const res = await fetch("data.json");
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    D = await res.json();
  } catch (exc) {
    view().innerHTML = `<p class="pad err">Could not load data.json (${esc(exc.message)}). Run <code>mise run web-data</code>.</p>`;
    return;
  }
  prepareRecipes();
  // The footer credit names the game version from the data, so a patch
  // needs no HTML edit; index.html carries the version-less fallback.
  if (gameVersion()) $("#data-version").textContent = `, ${gameVersion()} (${gameBuild()})`;
  // One shared datalist for every "type an item" box.
  const dl = document.createElement("datalist");
  dl.id = "item-names";
  dl.innerHTML = Object.values(D.items).map((i) => i.name).sort()
    .map((n) => `<option value="${esc(n)}">`).join("");
  document.body.append(dl);

  document.addEventListener("click", (e) => {
    const add = e.target.closest("[data-add]");
    if (!add) return;
    const inv = inventory();
    inv[add.dataset.add] = (inv[add.dataset.add] || 0) + 1;
    setInventory(inv);
    toast(`${name(add.dataset.add)}: ${inv[add.dataset.add]} in inventory`);
  });
  document.addEventListener("keydown", onKey);
  window.addEventListener("hashchange", route);
  route();
}

main();
