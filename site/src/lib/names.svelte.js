// Names of the items in every language the program has built, for searches that should find "Испорченный металл" while the page
// is in English (or "Tainted Metal" while it is in Russian). The page itself shows one language at a time; the launcher
// (desktop/languages.py names()) reads the rest from the language packs it has built, /api/names. Where there is no launcher,
// or only one language, there is nothing more to match and the searches work as they did.

import { baseName, D } from "./data.js";

export const names = $state({ available: false, languages: 0, total: 0, n: 0 });

let table = {};   // item id -> its names in the other languages, lower case, one per line
let reverse = {}; // a name (lower case) -> item id

/** Read the names of every built language; again after more have been built. */
export async function loadNames() {
  try {
    const res = await fetch("api/names", { cache: "no-store" });
    if (!res.ok) throw new Error(`${res.status}`);
    const data = await res.json();
    const next = {}, back = {};
    for (const [id, list] of Object.entries(data.names)) {
      const all = new Set([baseName(id), ...list].filter(Boolean).map((s) => s.toLowerCase()));
      next[id] = [...all].join("\n");
      for (const s of all) back[s] ??= id;
    }
    table = next;
    reverse = back;
    Object.assign(names, { available: true, languages: data.languages, total: data.total });
    names.n++; // searches that read otherNames() are made again
  } catch {
    names.available = false;
  }
}

/** The item's names in the other languages (lower case, one per line), "" when there are none. Read in a $derived, it is made again when more arrive. */
export const otherNames = (id) => { names.n; return table[id] ?? ""; };

/** The names, in the other languages, of what a recipe makes and is made of (a loop of recipes: of each step), one per line. */
export const recipeNames = (r) => {
  if (r.out && r.in) return [r.out[0], ...r.in.map(([id]) => id)].map(otherNames).join("\n");
  return (r.steps ?? []).map((s) => recipeNames(s)).join("\n");
};

/** The item a name belongs to in any language ("" if none): for adding an item to My items by typing it. */
export const idByAnyName = (text) => { names.n; return reverse[text.trim().toLowerCase()] ?? ""; };

/** Does the item's name (in the page's language) or any of its names in other languages contain every term? Terms are lower case. */
export const nameMatches = (id, terms) => {
  const hay = `${(D.items[id]?.name ?? "").toLowerCase()}\n${otherNames(id)}`;
  return terms.every((w) => hay.includes(w));
};

/**
 * Started once with the page. The launcher builds the languages that are missing by itself, in the background, a minute after it
 * starts (desktop/languages.py auto()), so there is nothing to switch on: the names are read now and again whenever the number of
 * built languages has grown.
 */
export function startNames() {
  loadNames();
  setInterval(async () => {
    if (!names.available || names.languages >= names.total) return;
    try {
      const s = await (await fetch("api/lang/all", { cache: "no-store" })).json();
      if (s.languages !== names.languages) await loadNames();
    } catch { /* the program has closed */ }
  }, 60000);
}
