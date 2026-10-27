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

// The languages the page's words come in, for a build that has no languages.json (one without the game's files): the page is translated
// into each, while the game's own texts (item names, descriptions) stay English there, as they have no pack to be read from.
const BUILT_IN = [
  ["english", "English"], ["brazilianportuguese", "Português (Brasil)"], ["dutch", "Nederlands"], ["french", "Français"], ["german", "Deutsch"],
  ["italian", "Italiano"], ["japanese", "日本語"], ["korean", "한국어"], ["latinamericanspanish", "Español (Latinoamérica)"], ["polish", "Polski"],
  ["portuguese", "Português"], ["russian", "Русский"], ["simplifiedchinese", "简体中文"], ["spanish", "Español"], ["tencentchinese", "简体中文 (Tencent)"],
  ["traditionalchinese", "繁體中文"], ["usenglish", "English (US)"],
].map(([code, name]) => ({ code, name }));

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
    let base = "english", list = BUILT_IN;
    try {
      const res = await fetch("languages.json");
      if (res.ok) ({ base, list } = await res.json());
    } catch { /* none: the built-in list */ }
    language.base = base;
    language.list = list;
    const codes = list.map((l) => l.code);
    const saved = local.get("lang", null);
    await setLanguage(codes.includes(saved) ? saved : browserLanguage(codes));
  } catch {
    // a language that cannot be applied leaves the page as it is
  }
}

export async function setLanguage(code) {
  if (code !== language.base && !(code in packs)) {
    // The game's texts of the language; a build without them keeps them in English (the page's words are still the language's).
    const res = await fetch(`lang/${code}.json`).catch(() => null);
    packs[code] = res?.ok ? await res.json().catch(() => null) : null;
  }
  setWords(code, await wordsOf(code));
  localizeStorage(D.storage, ENGLISH.storage);
  D.cooking.forEach((g, i) => { g.use = t(ENGLISH.use[i]); });
  retext(code === language.base ? null : packs[code] ?? null);
  rewordLoops();
  language.code = code;
  local.set("lang", code);
}
