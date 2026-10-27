// Filters that know what is left to filter.
//
// A page lists its filters as definitions; given the rows and what the visitor has chosen, `facets` says
//   * which filters are worth showing at all,
//   * which choices of each are worth offering,
//   * what is really in force once the useless ones are let go.
//
// A choice is *useful* when applying it, with every other filter as it stands, leaves some rows and fewer than the
// "no filter" choice leaves. A filter with no useful choice (cooking has nothing that multiplies itself; refining
// has no effect to pick) is not shown. A filter that is on but would leave nothing, or would change nothing, is
// not in force any more: so no combination of filters, however it came about -- a link, what was set last
// time, a click -- can leave an empty table when the rows are not empty.
//
//   def:   { key, options: [[value, label], ...], neutral: value, test(row, value) -> bool }
//   state: { key: value }

/** The choices of a yes/no flag (components/Check.svelte): no opinion, only those that have it, none of those. */
export const FLAG = [[false, ""], [true, ""], ["not", ""]];
/** `has`: does the row have what the flag is about? `v`: the flag's state. */
export const flag = (v, has) => (v === true ? has : v === "not" ? !has : true);

const PASSES = 12; // a filter let go per pass, and no page has more than a handful

export function facets(rows, defs, state) {
  const effective = { ...state };
  let result = null;
  for (let pass = 0; pass < PASSES; pass++) {
    const counts = {};
    for (const d of defs) {
      const others = defs.filter((o) => o !== d && effective[o.key] !== o.neutral);
      const base = others.length ? rows.filter((r) => others.every((o) => o.test(r, effective[o.key]))) : rows;
      counts[d.key] = new Map(d.options.map(([v]) => [v, base.reduce((n, r) => n + (d.test(r, v) ? 1 : 0), 0)]));
    }
    const show = {};
    const options = {};
    const useful = {};
    for (const d of defs) {
      const c = counts[d.key];
      const all = c.get(d.neutral) ?? 0;
      useful[d.key] = new Set(d.options.map(([v]) => v).filter((v) => v !== d.neutral && c.get(v) > 0 && c.get(v) < all));
      show[d.key] = useful[d.key].size > 0;
      options[d.key] = d.options.filter(([v]) => v === d.neutral || useful[d.key].has(v));
    }
    // One filter is let go per pass, then everything is counted again: two filters can each look unneeded only
    // because of the other (kind "a" and tag "y" on rows where every "y" is an "a"), and letting both go would lose
    // what they did together. An empty one goes before one that merely changes nothing; the last in the list first.
    const empties = [];
    const noops = [];
    for (const d of defs) {
      const v = effective[d.key];
      if (v === d.neutral || useful[d.key].has(v)) continue;
      (counts[d.key].get(v) === 0 ? empties : noops).push(d);
    }
    const drop = empties.at(-1) ?? noops.at(-1);
    if (drop) effective[drop.key] = drop.neutral;
    const changed = Boolean(drop);    result = { effective, show, options, counts, all: Object.fromEntries(defs.map((d) => [d.key, d.options])), neutral: Object.fromEntries(defs.map((d) => [d.key, d.neutral])) };
    if (!changed) break;
  }
  return result;
}

/** The rows the effective filters leave. */
export function applyFacets(rows, defs, effective) {
  const active = defs.filter((d) => effective[d.key] !== d.neutral);
  return active.length ? rows.filter((r) => active.every((d) => d.test(r, effective[d.key]))) : rows;
}


