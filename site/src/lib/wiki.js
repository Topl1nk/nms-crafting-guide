// Every item the game has -- not only what recipes touch: the build menu, the
// cosmetics and the emotes too -- from wiki.json, fetched the first time the
// Wiki page opens. Each row: id -> [name, subtitle, type, category, rarity,
// value, colour, description], turned here into plain objects.

import { CONSUMED, PACK, PRODUCED } from "./data.js";

let raw = null;
let rows = null;
let rowsIn = null; // the language pack `rows` was made with

// Names, subtitles and descriptions follow the game language in use (data.js).
export async function loadWiki() {
  if (!raw) {
    const res = await fetch("wiki.json");
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    raw = await res.json();
  }
  if (rows && rowsIn === PACK) return rows;
  rowsIn = PACK;
  rows = Object.entries(raw).map(([id, v]) => {
    const t = PACK?.items[id];
    return {
      id, name: t?.[0] || v[0], sub: t?.[1] || v[1], type: v[2], cat: v[3], rar: v[4], value: v[5], color: v[6],
      desc: t?.[2] || v[7],
      makes: (PRODUCED[id] || []).length,
      needs: (CONSUMED[id] || []).length,
    };
  });
  return rows;
}
