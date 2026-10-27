// The lines of the storage scheme (the ten containers, the other places, and sell / junk / use) as one list, with
// which item belongs to which line. The Wiki filters by a line (`store`), "My items" lists them as links to it.
//
// A line's key is its home's key ("0".."9", "exosuit", "processor", "cold", "exocraft") or "act:sell" / "act:discard" /
// "act:use": the home of an item is a place, its action is what is done with it.

import { D } from "./data.js";
import { t } from "./i18n.js";

const actions = () => [["act:sell", t("Sell"), "act-sell"], ["act:discard", t("Junk"), "act-discard"], ["act:use", t("Use it"), "act-use"]];

// The picture of each line, icons/<id>.webp: the game's own picture of the place (Storage Container 0-9 with its number,
// the exosuit, the Nutrient Processor, the Exo-Skiff, the exocraft; tools/extract_storage_icons.py takes them out of the
// game files as STORE_*). Sell and use have no place: the units sign and an item of the game stand for them.
const ICONS = {
  0: "STORE_0", 1: "STORE_1", 2: "STORE_2", 3: "STORE_3", 4: "STORE_4", 5: "STORE_5", 6: "STORE_6", 7: "STORE_7",
  8: "STORE_8", 9: "STORE_9", exosuit: "STORE_exosuit", processor: "STORE_processor", cold: "STORE_cold",
  exocraft: "STORE_exocraft", "act:sell": "UNITS", "act:discard": "STORE_act_discard", "act:use": "F_BOTTLE",
};

/** The line an outcome (what the scheme says for an item) points at: its place, or what is done with it. */
export const lineOf = (p) => (p.home !== "none" ? p.home : `act:${p.action}`);

// The Wiki, filtered by the type or the rarity of an item, with its card open: where the tags of an item lead.
export const wikiType = (id) => (D.items[id]?.type ? `#/wiki?type=${encodeURIComponent(D.items[id].type)}&item=${encodeURIComponent(id)}` : "");
export const wikiRar = (id) => (D.items[id]?.rar ? `#/wiki?rar=${encodeURIComponent(D.items[id].rar)}&item=${encodeURIComponent(id)}` : "");
/** The Wiki, filtered by a line of the scheme (or the line an outcome points at). */
export const wikiStore = (key) => `#/wiki?store=${encodeURIComponent(key)}`;

/** The picture (icons/<id>.webp) of the line an outcome points at, or undefined. */
export const iconOf = (p) => ICONS[lineOf(p)];

/** Does the item sit on this line of the scheme? */
export function inStore(id, key) {
  const item = D.items[id];
  if (!item) return false;
  const p = D.storage.outcomes[item.store];
  return key.startsWith("act:") ? p.action === key.slice(4) : p.home === key;
}

/** [{key, label, name, icon, cls, container, n}]: the containers first, then the other places, then sell / junk / use.
 *  `name` is the label without the number of the container ("0 Raw - common" -> "Raw - common"): the picture says it. */
export function storeLines() {
  const lines = [
    ...D.storage.homes.filter((h) => h.container),
    ...D.storage.homes.filter((h) => !h.container && h.key !== "none"),
  ].map((h) => ({ key: h.key, label: h.label, cls: "", container: h.container }))
    .concat(actions().map(([key, label, cls]) => ({ key, label, cls, container: false })));
  for (const line of lines) {
    line.n = Object.keys(D.items).filter((id) => inStore(id, line.key)).length;
    line.name = line.label.replace(/^\d\s+/, "");
    line.icon = ICONS[line.key];
  }
  return lines;
}
