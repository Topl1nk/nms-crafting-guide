// The logic the page runs itself, kept free of the DOM so tests/test_web.py
// can run it under node and hold it against the Python it mirrors.
//
// Everything expensive or opinionated -- ease, storage homes, the cheapest
// recipe per tier -- arrives precomputed in data.json (scripts/build_web.py).
// What is left here is formatting, the chain tree walk, inventory matching and
// the portal arithmetic.

// Python's `:g` for the numbers this app prints: six significant digits,
// trailing zeros gone.
export const g = (x) => String(Number(Number(x).toPrecision(6)));

export const fmtInt = (n) => Math.round(n).toLocaleString("en-US");
export const fmtSigned = (n) => (n >= 0 ? "+" : "-") + fmtInt(Math.abs(n));

// -- recipes (model.Recipe) ---------------------------------------------------

export function multiplierLabel(r) {
  if (r.loop > 1) return `x${g(r.loop)} loop`;
  if (r.ratio === Math.trunc(r.ratio)) return `x${g(r.ratio)}`;
  return `x${r.ratio.toFixed(2)}`;
}

export function timeLabel(seconds) {
  if (!seconds) return "-";
  if (seconds < 60) return `${g(seconds)}s`;
  if (seconds < 3600) {
    const minutes = seconds / 60;
    return minutes >= 10 ? `${minutes.toFixed(0)}m` : `${minutes.toFixed(1)}m`;
  }
  return `${(seconds / 3600).toFixed(1)}h`;
}

// screens.fmt_time: the chain planner's machine-time total.
export function fmtTime(seconds) {
  if (seconds < 60) return `${g(seconds)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

export const machineShort = (machine) =>
  machine.split(" ")[0].replace("Nutrient", "Processor");

export function qtyLabel(n, name) {
  return n > 1 ? `${n} ${name}` : name;
}

// -- chain planning (graph.plan, with the search already done) ----------------

// `via` is {item_id: recipe index}: graph.cheapest_costs for one source tier
// and recipe set, exported by build_web.py. This is only the tree walk.
export function plan(recipes, via, sources, target, qty) {
  const raw = {};
  let steps = 0;

  function build(id, need, depth) {
    if (sources.has(id) || !(id in via) || depth > 12) {
      raw[id] = (raw[id] || 0) + need;
      return { id, qty: need, raw: sources.has(id), children: [] };
    }
    const recipe = recipes[via[id]];
    const batches = Math.ceil(need / recipe.out[1]);
    steps += 1;
    const step = { id, qty: need, recipe: via[id], batches, children: [] };
    for (const [ing, n] of recipe.in) step.children.push(build(ing, n * batches, depth + 1));
    return step;
  }

  const root = build(target, qty, 0);
  const seconds = (step) =>
    (step.recipe !== undefined ? recipes[step.recipe].time * step.batches : 0) +
    step.children.reduce((sum, child) => sum + seconds(child), 0);

  return {
    root,
    raw,
    steps,
    seconds: seconds(root),
    ok: root.recipe !== undefined || root.raw,
  };
}

// -- inventory (graph.craftable_now / one_hop_away) ---------------------------

export function craftableNow(recipes, have, domains) {
  const out = [];
  recipes.forEach((r, index) => {
    if (!domains.includes(r.domain)) return;
    let batches = Infinity;
    for (const [id, n] of r.in) {
      const stock = have[id] || 0;
      if (stock < n) { batches = 0; break; }
      batches = Math.min(batches, Math.floor(stock / n));
    }
    if (batches) out.push([index, batches]);
  });
  out.sort((a, b) =>
    recipes[b[0]].ratio - recipes[a[0]].ratio || recipes[a[0]].time - recipes[b[0]].time);
  return out;
}

export function oneHopAway(recipes, have, domains) {
  const out = [];
  recipes.forEach((r, index) => {
    if (!domains.includes(r.domain)) return;
    const missing = r.in
      .filter(([id, n]) => (have[id] || 0) < n)
      .map(([id, n]) => [id, n - (have[id] || 0)]);
    if (missing.length === 1) out.push([index, missing]);
  });
  out.sort((a, b) =>
    a[1][0][1] - b[1][0][1] || recipes[b[0]].ratio - recipes[a[0]].ratio);
  return out;
}

// -- portal addresses (portals.Address) ---------------------------------------

export class AddressError extends Error {}

const hexOnly = (text) => text.replace(/[^0-9A-Fa-f]/g, "").toUpperCase();
const hex = (n, width) => n.toString(16).toUpperCase().padStart(width, "0");

export const FIELDS = [
  ["planet", 1],
  ["system", 3],
  ["Y", 2],
  ["Z", 3],
  ["X", 3],
];
// Field index per glyph position: 0 planet, 1 system, 2 Y, 3 Z, 4 X.
export const GLYPH_FIELD = FIELDS.flatMap(([, width], i) => Array(width).fill(i));

export class Address {
  constructor(planet, system, y, z, x) {
    for (const [name, value, limit] of [
      ["planet", planet, 0xf], ["system", system, 0xfff],
      ["y", y, 0xff], ["z", z, 0xfff], ["x", x, 0xfff],
    ]) {
      if (!(value >= 0 && value <= limit)) {
        throw new AddressError(`${name} out of range: 0x${value.toString(16)} > 0x${limit.toString(16)}`);
      }
    }
    Object.assign(this, { planet, system, y, z, x });
  }

  get code() {
    return hex(this.planet, 1) + hex(this.system, 3) + hex(this.y, 2) + hex(this.z, 3) + hex(this.x, 3);
  }

  get grouped() {
    return [hex(this.planet, 1), hex(this.system, 3), hex(this.y, 2), hex(this.z, 3), hex(this.x, 3)];
  }

  get galactic() {
    const gx = (this.x + 2047) % 4096;
    const gy = (this.y + 127) % 256;
    const gz = (this.z + 2047) % 4096;
    return [gx, gy, gz, this.system].map((n) => hex(n, 4)).join(":");
  }

  get shareLink() {
    return `https://nmsportals.github.io/#${this.code}`;
  }

  // Signed X, Y, Z from the galaxy centre, the way the glyphs store it.
  get voxel() {
    return [
      this.x >= 2048 ? this.x - 4096 : this.x,
      this.y >= 128 ? this.y - 256 : this.y,
      this.z >= 2048 ? this.z - 4096 : this.z,
    ];
  }

  withPlanet(planet) {
    return new Address(planet & 0xf, this.system, this.y, this.z, this.x);
  }

  static fromCode(text) {
    const code = hexOnly(text);
    if (code.length !== 12) throw new AddressError(`a portal code is 12 glyphs; got ${code.length}`);
    const n = (a, b) => parseInt(code.slice(a, b), 16);
    return new Address(n(0, 1), n(1, 4), n(4, 6), n(6, 9), n(9, 12));
  }

  static fromGalactic(text, planet = 0) {
    const parts = text.trim().split(/[^0-9A-Fa-f]+/).filter(Boolean);
    if (parts.length !== 4 || parts.some((p) => p.length > 4)) {
      throw new AddressError("a galactic address is four hex groups, e.g. 042F:0078:0D55:006A");
    }
    const [gx, gy, gz, system] = parts.map((p) => parseInt(p, 16));
    if (gx > 0xfff || gz > 0xfff) throw new AddressError("galactic X and Z must be 0000-0FFF");
    if (gy > 0xff) throw new AddressError("galactic Y must be 0000-00FF");
    return new Address(planet & 0xf, system % 0x1000, (gy + 129) % 256, (gz + 2049) % 4096, (gx + 2049) % 4096);
  }

  // A colon means a galactic address, twelve bare hex digits a portal code,
  // and a nmsportals link carries the code in its fragment.
  static parse(text, planet = 0) {
    text = text.trim();
    if (!text) throw new AddressError("nothing to convert");
    if (text.includes("#")) text = text.slice(text.lastIndexOf("#") + 1);
    if (!text.includes(":") && hexOnly(text).length === 12) return Address.fromCode(text);
    return Address.fromGalactic(text, planet);
  }
}

// Hex and separators only: they meant an address and mistyped it.
export const looksLikeAddress = (text) => Boolean(text) && /^[0-9a-fA-F:,\-. ]+$/.test(text);

export function ordinal(n) {
  if (n % 100 >= 10 && n % 100 <= 20) return `${n}th`;
  return `${n}${{ 1: "st", 2: "nd", 3: "rd" }[n % 10] || "th"}`;
}
