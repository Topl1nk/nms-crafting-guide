// The language of the page: the game's own texts (item names, descriptions, what a recipe and a buff are
// called) and the page's words (labels, help, messages), both in the one language chosen here.
// web/languages.json lists the ones the game ships, written by scripts/build_langs.py from the game's files;
// web/lang/<code>.json holds the game's texts, site/src/lang/<code>.js the page's words (lib/i18n.svelte.js).

import { rewordLoops } from "./cycles.svelte.js";
import { D, ENGLISH, retext } from "./data.js";
import { browserLanguage, SAME, setWords, t } from "./i18n.js";
import { local } from "./local.js";
import { localizeStorage } from "./words.js";

export const language = $state({ code: "", base: "", list: [] });

const packs = {};
const loaders = import.meta.glob("../lang/*.js");
const words = {};

/** The page's words for a game language: English needs no file, a language without one shows English. */
async function wordsOf(code) {
  const file = SAME[code] ?? code;
  if (file === "english") return {};
  if (!words[file]) {
    const load = loaders[`../lang/${file}.js`];
    words[file] = load ? (await load()).default : {};
  }
  return words[file];
}

/** Read the list and apply the saved choice, else the browser's language, else English. */
export async function startLanguage() {
  try {
    const res = await fetch("languages.json");
    if (!res.ok) return;
    const { base, list } = await res.json();
    language.base = base;
    language.list = list;
    const codes = list.map((l) => l.code);
    const saved = local.get("lang", null);
    await setLanguage(codes.includes(saved) ? saved : browserLanguage(codes));
  } catch {
    // no languages.json: nothing to switch between
  }
}

export async function setLanguage(code) {
  if (code !== language.base && !packs[code]) {
    const res = await fetch(`lang/${code}.json`);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    packs[code] = await res.json();
  }
  setWords(code, await wordsOf(code));
  localizeStorage(D.storage, ENGLISH.storage);
  D.cooking.forEach((g, i) => { g.use = t(ENGLISH.use[i]); });
  retext(code === language.base ? null : packs[code]);
  rewordLoops();
  language.code = code;
  local.set("lang", code);
}
