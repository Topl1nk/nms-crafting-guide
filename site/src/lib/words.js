// The English strings the data export carries (machines, source tiers, how-gettable labels, the storage guide) and
// the page's shared vocabulary, put into the page's language with t() / tn() (lib/i18n.svelte.js). Names of items,
// recipes and buffs are not here: they come from the game's own language tables (lib/language.svelte.js).

import { N_, t, tn, ui } from "./i18n.js";

export const machine = (m) => t(m);

// First word only, as the narrow "Machine" column shows it.
export const machineShort = (m) => t(m.split(" ")[0]);

export const tier = (name) => t(name);

export const band = (b) => ({ easy: t("Easy"), ok: t("Fair"), work: t("Takes work"), hard: t("Hard") })[b] ?? b;

const source = (tier) => [t("from the planet"), t("from asteroids"), t("from the atmosphere")][tier];

// "T1 +6" -> "raw from asteroids, 6 steps"; the short code stays as a tooltip.
export function easeLabel(label) {
  let m;
  if ((m = /^T(\d) raw$/.exec(label))) return t("raw {source}", { source: source(m[1]) });
  if ((m = /^T(\d) \+(\d+)$/.exec(label))) {
    return t("raw {source}, {steps}", { source: source(m[1]), steps: tn(Number(m[2]), "{n} step|{n} steps") });
  }
  if (label === "needs seed") return t("needs a rare ingredient");
  if ((m = /^loot \((\w+)\)$/.exec(label))) {
    return { easy: t("loot (easy)"), medium: t("loot (medium)"), hard: t("loot (hard)"), unknown: t("loot (unknown)") }[m[1]] ?? label;
  }
  return label;
}

// What an item is, in the page's words (English keys for t(): typeLabel), with the colour its tag wears.
export const ITEM_TYPES = {
  Substance: [N_("Substance"), "#5ccbf0"],
  Tradeable: [N_("Trade good"), "#eca72a"],
  Consumable: [N_("Consumable"), "#f08f5c"],
  Component: [N_("Component"), "#c595f6"],
  Curiosity: [N_("Curiosity"), "#3adbed"],
  Fish: [N_("Fish"), "#64f19f"],
  CreatureEgg: [N_("Egg"), "#d095f6"],
  SpaceSalvage: [N_("Space salvage"), "#f484c4"],
  BuildingPart: [N_("Base part"), "#f3b878"],
  CustomisationPart: [N_("Cosmetic"), "#6a97f2"],
  Emote: [N_("Emote"), "#6a97f2"],
};
export const typeLabel = (key) => (ITEM_TYPES[key] ? t(ITEM_TYPES[key][0]) : key);

export const RARITIES = { Uncommon: [N_("Uncommon"), "#64f19f"], Rare: [N_("Rare"), "#c595f6"] };
export const rarityLabel = (key) => (key === "Common" ? t("Common") : RARITIES[key] ? t(RARITIES[key][0]) : key);
// For sorting a column: common, uncommon, rare; anything the game gives no rarity to goes first.
export const rarityRank = (r) => ({ Common: 1, Uncommon: 2, Rare: 3 })[r] ?? 0;

// -- storage layout (data/storage.json is hand-written English) ---------------

const homeLabel = (label) => {
  const m = /^(\d+ )?(.+)$/.exec(label);
  return m ? `${m[1] ?? ""}${t(m[2])}` : label;
};

function advice(text) {
  let m = /^Store it in ([^.]+)\.(.*)$/.exec(text);
  if (m) return t("Store it in {home}.", { home: homeLabel(m[1]) }) + (m[2].trim() ? ` ${t(m[2].trim())}` : "");
  m = /^Sell it\. Until you reach a terminal, park it in (.+)\.$/.exec(text);
  if (m) return t("Sell it. Until you reach a terminal, park it in {home}.", { home: homeLabel(m[1]) });
  return t(text);
}

function outcomeLabel(label) {
  const m = /^Sell - park in (.+)$/.exec(label);
  return m ? t("Sell - park in {home}", { home: homeLabel(m[1]) }) : t(label) === label ? homeLabel(label) : t(label);
}

/**
 * A place of the game save, as lib/gamesave names it in English ("Exosuit", "Container 3", "Ship: Star", "Exocraft 2"),
 * in the page's language. A name the player gave a ship or an exocraft stays as it is.
 */
export function placeLabel(label) {
  let m = /^Ship: (.+)$/.exec(label);
  if (m) return t("Ship: {name}", { name: m[1] });
  if ((m = /^Exocraft: (.+)$/.exec(label))) return t("Exocraft: {name}", { name: m[1] });
  if ((m = /^Ship (\d+)$/.exec(label))) return t("Ship {n}", { n: m[1] });
  if ((m = /^Exocraft (\d+)$/.exec(label))) return t("Exocraft {n}", { n: m[1] });
  if ((m = /^Container (\d)$/.exec(label))) return t("Container {n}", { n: m[1] });
  return { Exosuit: t("Exosuit"), Freighter: t("Freighter"), "Nutrient Processor": t("Nutrient Processor") }[label] ?? label;
}

/** Put the storage guide of data.json (`source`, the English as exported) into the page's language, into `storage`. */
export function localizeStorage(storage, source) {
  storage.homes.forEach((h, i) => {
    const s = source.homes[i];
    h.name = t(s.name);
    h.label = homeLabel(s.label);
    h.note = t(s.note);
  });
  storage.outcomes.forEach((o, i) => {
    const s = source.outcomes[i];
    o.label = outcomeLabel(s.label);
    o.verdict = t(s.verdict);
    o.advice = advice(s.advice);
    o.why = t(s.why);
  });
}

// The one pattern the export builds itself; the rest is hand-written text.
export function easeDescribe(text) {
  let m = /^(\d+) step\(s\) from (\d+) raw material\(s\), (\d+) unit\(s\) in total$/.exec(text);
  if (m) {
    return t("{steps} from {raw}, {total} in total", {
      steps: tn(Number(m[1]), "{n} step|{n} steps"),
      raw: tn(Number(m[2]), "{n} raw material|{n} raw materials"),
      total: tn(Number(m[3]), "{n} unit|{n} units"),
    });
  }
  m = /^refinable once you have (.+)$/.exec(text);
  if (m) return t("can be refined once you have {items}", { items: m[1] });
  return t(text);
}

/**
 * An effect's name as a choice of a drop-down: the long ones of the game shortened to a short phrase that says the same
 * (only where the game's own Russian wording is known to be long).
 */
export function shortEffect(text) {
  if (ui.code !== "russian") return text;
  return text
    .replace(/^Вознаграждение за анализ /, "Награда за анализ ")
    .replace(/^Баки системы жизнеобеспечения$/, "Баки жизнеобеспечения")
    .replace(/^Батарея системы защиты от вредных факторов$/, "Батарея защиты")
    .replace(/^Время восстановления ускорения$/, "Перезарядка ускорения");
}
