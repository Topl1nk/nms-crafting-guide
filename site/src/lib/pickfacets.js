// The filters of the list of things to break down into chains (#/tree), as definitions for lib/facets.js.
// A row is an item id; what it can be made by is PRODUCED[id].

import { buffOf, D, easeOfRecipe, PRODUCED } from "./data.js";
import { collate, N_, t } from "./i18n.js";
import { owned, recipeFits, refiners, SOURCE_BANDS, sources } from "./options.js";
import { effectChoices } from "./recipefacets.js";
import { RARITIES, rarityLabel, typeLabel } from "./words.js";

export const PICK_DEFAULTS = { kind: "all", type: "any", rar: "any", effect: "any", refiner: 0, source: "any", owned: "all", ways: "any" };

const kinds = () => [["all", t("any kind")], ["refine", t("refining")], ["cook", t("cooking")], ["nanites", t("nanites")]];
const waysChoices = () => [["any", t("any number")], ["one", t("one")], ["few", "2–5"], ["many", t("more than 5")]];
const rarities = () => [["any", t("any rarity")], ["Common", t("common")], ...Object.keys(RARITIES).map((k) => [k, rarityLabel(k).toLowerCase()])];

const ways = (id) => (PRODUCED[id] || []).length;

/**
 * `makeable`: ids the bag can make right now; `held`: id -> count; `ids`: the items listed (the kinds of item to
 * offer are the kinds among them).
 */
export function pickDefs({ makeable = new Set(), held = {} } = {}, ids = []) {
  const nanites = new Set(D.nanites.map((n) => n.recipe));
  const types = [...new Set(ids.map((id) => D.items[id]?.type).filter(Boolean))]
    .map((type) => [type, typeLabel(type)]).sort((a, b) => collate(a[1], b[1]));
  return [
    { key: "kind", options: kinds(), neutral: "all", test: (id, v) => v === "all" || (PRODUCED[id] || []).some((r) => (v === "nanites" ? nanites.has(r.index) : r.domain === v)) },
    { key: "type", options: [["any", t("any kind")], ...types], neutral: "any", test: (id, v) => v === "any" || D.items[id]?.type === v },
    { key: "rar", options: rarities(), neutral: "any", test: (id, v) => v === "any" || D.items[id]?.rar === v },
    { key: "effect", options: effectChoices(), neutral: "any", test: (id, v) => v === "any" || buffOf(id)?.id === v },
    { key: "refiner", options: refiners(), neutral: 0, test: (id, v) => !v || (PRODUCED[id] || []).some((r) => recipeFits(r, v)) },
    { key: "source", options: sources(), neutral: "any", test: (id, v) => v === "any" || (PRODUCED[id] || []).some((r) => SOURCE_BANDS[v].includes(easeOfRecipe(r).band)) },
    { key: "owned", options: owned(), neutral: "all", test: (id, v) => v === "all" || (v === "can" ? makeable.has(id) : (PRODUCED[id] || []).some((r) => r.in.some(([i]) => held[i] > 0))) },
    { key: "ways", options: waysChoices(), neutral: "any", test: (id, v) => v === "any" || (v === "one" ? ways(id) === 1 : v === "few" ? ways(id) >= 2 && ways(id) <= 5 : ways(id) > 5) },
  ];
}

export const pickSorts = () => [
  ["name", t("by name")], ["color", t("by colour")], ["type", t("by kind")], ["rar", t("by rarity")], ["potency", t("by strength of effect")],
  ["ways", t("by number of ways")], ["needs", t("by where it is needed")], ["value", t("by price")], ["time", t("by time (quickest)")], ["ease", t("by how easy the raws are")],
];
