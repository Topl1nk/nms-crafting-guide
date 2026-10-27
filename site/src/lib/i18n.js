// The page's own words (labels, buttons, help, messages), in the language chosen with the game's texts
// (lib/language.svelte.js). The English text is the key: t("Search") is "Search" in English and whatever
// site/src/lang/<code>.js maps "Search" to in any other language, so a string nobody has translated yet
// shows in English instead of a key or a blank.
//
// Plain JavaScript, no runes, so the logic that uses it runs under node in the tests. App.svelte draws
// everything again when the language changes, so a t() call needs nothing reactive of its own.

import { setNumberLocale, setUnits } from "./core.js";

export const ui = { code: "english", locale: "en", dict: {} };

// BCP 47 for each language the game ships (number grouping, plural rules, sorting).
export const LOCALES = {
  english: "en", usenglish: "en-US", russian: "ru", french: "fr", german: "de", italian: "it", spanish: "es",
  latinamericanspanish: "es-419", portuguese: "pt-PT", brazilianportuguese: "pt-BR", polish: "pl", dutch: "nl",
  japanese: "ja", korean: "ko", simplifiedchinese: "zh-Hans", traditionalchinese: "zh-Hant", tencentchinese: "zh-Hans",
};
/** Languages that share the page's words with another one. */
export const SAME = { usenglish: "english", tencentchinese: "simplifiedchinese" };

/** Use `dict` (English text -> text, {} for English) as the page's words for the game language `code`. */
export function setWords(code, dict = {}) {
  const locale = LOCALES[code] ?? "en";
  setNumberLocale(locale);
  ui.dict = dict;
  setUnits({ s: t("s"), min: t("min"), h: t("h") });
  ui.locale = locale;
  ui.code = code;
  if (typeof document !== "undefined") document.documentElement.lang = locale;
}

/** The code of the game language that best matches the browser's (English when none does). */
export function browserLanguage(list) {
  const want = (typeof navigator === "undefined" ? [] : navigator.languages ?? [navigator.language]).filter(Boolean);
  const real = Object.entries(LOCALES).filter(([code]) => list.includes(code));
  for (const tag of want) {
    const lower = normal(tag.toLowerCase());
    const hit = real.find(([, loc]) => loc.toLowerCase() === lower)
      ?? real.find(([code, loc]) => !SAME[code] && code !== "usenglish" && loc.split("-")[0].toLowerCase() === lower.split("-")[0]);
    if (hit) return hit[0];
  }
  return "english";
}

// The browser's tag as one of LOCALES: Spanish outside Spain is Latin American, Chinese is written two ways, Portuguese two.
function normal(tag) {
  if (tag.startsWith("es-") && tag !== "es-es") return "es-419";
  if (tag.startsWith("zh")) return /hant|-tw|-hk|-mo/.test(tag) ? "zh-hant" : "zh-hans";
  if (tag === "pt") return "pt-pt";
  return tag;
}

const fill = (text, params) => (params ? text.replace(/\{(\w+)\}/g, (m, k) => (k in params ? String(params[k]) : m)) : text);

/** `text` in the page's language; `{name}` marks a place for params[name]. */
export function t(text, params = null) {
  return fill(ui.dict[text] ?? text, params);
}

const ORDER = ["zero", "one", "two", "few", "many", "other"];
const rules = {};

/**
 * A count with its noun: `forms` is the English "one|other" ("{n} step|{n} steps"); a language gives its own forms in
 * the order of its plural categories (Russian: one|few|many|other), which Intl.PluralRules names.
 */
export function tn(n, forms, params = null) {
  const own = ui.dict[forms];
  const all = { n, ...params };
  if (!own) {
    const [one, other = one] = forms.split("|");
    return fill(n === 1 ? one : other, all);
  }
  const rule = (rules[ui.locale] ||= new Intl.PluralRules(ui.locale));
  const cats = ORDER.filter((c) => rule.resolvedOptions().pluralCategories.includes(c));
  const parts = own.split("|");
  return fill(parts[cats.indexOf(rule.select(n))] ?? parts[parts.length - 1], all);
}

/** The ordinal of `n` in English ("1st", "22nd"), for the English wording of "{ordinal} in the system"; other languages use {n}. */
export function ordinal(n) {
  const kind = new Intl.PluralRules("en", { type: "ordinal" }).select(n);
  return `${n}${{ one: "st", two: "nd", few: "rd" }[kind] ?? "th"}`;
}

/** "a, b and c" in the page's language. */
export const list = (items) => new Intl.ListFormat(ui.locale, { style: "long", type: "conjunction" }).format(items);

/** Sort order of the page's language (not of the browser's). */
export const collate = (a, b) => a.localeCompare(b, ui.locale);

/** Marks an English text to be translated later, where t() cannot be called yet (the text is kept as it is). */
export const N_ = (text) => text;
