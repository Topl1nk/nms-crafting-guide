// The filters of the Craft table, as definitions for lib/facets.js. Kept out of the page so they can be tested over
// every combination against the real data.

import { buffOf, D, easeOfRecipe, RECIPES } from "./data.js";
import { FLAG, flag } from "./facets.js";
import { collate, t } from "./i18n.js";
import { owned, recipeFits, refiners, SOURCE_BANDS, sources } from "./options.js";
import { shortEffect, typeLabel } from "./words.js";

export const DEFAULTS = { domain: "refine", effect: "any", refiner: 0, source: "any", owned: "all", loops: false };

/** The choices of "Kind": the kinds of recipe, then the kinds of item the recipes make, then everything. */
export function kindChoices() {
  const types = [...new Set(RECIPES.map((r) => D.items[r.out[0]]?.type).filter(Boolean))]
    .map((type) => [`type:${type}`, typeLabel(type).toLowerCase()]).sort((a, b) => collate(a[1], b[1]));
  return [["refine", t("refining")], ["cook", t("cooking")], ["nanites", t("nanites")], ...types, ["all", t("everything")]];
}

export const effectChoices = () => [["any", t("any effect")], ...[...D.cooking].sort((a, b) => collate(a.effect, b.effect)).map((g) => [g.id, shortEffect(g.effect)])];

/** `makeable`: Set of recipe indexes the bag covers; `held`: id -> count. */
export function recipeDefs({ makeable = new Set(), held = {} } = {}) {
  const nanites = new Set(D.nanites.map((n) => n.recipe));
  return [
    { key: "domain", options: kindChoices(), neutral: "all", test: (r, v) => v === "all" || (v === "nanites" ? nanites.has(r.index)
      : v.startsWith("type:") ? D.items[r.out[0]]?.type === v.slice(5) : r.domain === v) },
    { key: "effect", options: effectChoices(), neutral: "any", test: (r, v) => v === "any" || buffOf(r.out[0])?.id === v },
    { key: "refiner", options: refiners(), neutral: 0, test: (r, v) => recipeFits(r, v) },
    { key: "source", options: sources(), neutral: "any", test: (r, v) => v === "any" || SOURCE_BANDS[v].includes(easeOfRecipe(r).band) },
    { key: "owned", options: owned(), neutral: "all", test: (r, v) => v === "all" || (v === "can" ? makeable.has(r.index) : r.in.some(([id]) => held[id] > 0)) },
    { key: "loops", options: FLAG, neutral: false, test: (r, v) => flag(v, Boolean(r.cycle)) },
  ];
}
