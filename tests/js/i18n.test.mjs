// The page's words (site/src/lang/<language>.js): every text the page asks for has a translation in every language the
// game ships, with the same {placeholders} and the right number of plural forms. English is the key itself.
//
//   node --test tests/js/i18n.test.mjs
//   I18N_REPORT=1 node tests/js/i18n.test.mjs     (prints what each language still lacks)
import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const ROOT = join(import.meta.dirname, "..", "..");
const SRC = join(ROOT, "site", "src");
const LANG = join(SRC, "lang");

function* sources(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) { if (p !== LANG) yield* sources(p); } else if (/\.(js|svelte)$/.test(e.name)) yield p;
  }
}

const STRING = String.raw`"((?:[^"\\]|\\.)*)"`;
const CALLS = [
  new RegExp(String.raw`(?<![\w.$])t\(\s*${STRING}`, "g"), // t("text")
  new RegExp(String.raw`(?<![\w.$])tn\(\s*[^,()]+(?:\([^()]*\))?[^,()]*,\s*${STRING}`, "g"), // tn(n, "one|other")
  new RegExp(String.raw`(?<![\w.$])N_\(\s*${STRING}`, "g"), // N_("text")
];
const plural = new Set();

/** Every English text the code asks t() / tn() / N_() for, by its literal. */
function literalKeys() {
  const keys = new Set();
  for (const file of sources(SRC)) {
    const text = readFileSync(file, "utf8");
    CALLS.forEach((re, i) => {
      for (const m of text.matchAll(re)) {
        const key = JSON.parse(`"${m[1]}"`);
        keys.add(key);
        if (i === 1) plural.add(key);
      }
    });
  }
  return keys;
}

const hasLetters = (s) => /\p{L}/u.test(s.replace(/\b(?:x|X|Y|Z|min|s|h)\b/g, ""));

/** The texts the data carries in English (web/data.json and the hand-written data/*.json), shown through t(). */
function dataKeys() {
  const keys = new Set();
  const add = (s) => { if (typeof s === "string" && s.trim() && hasLetters(s)) keys.add(s); };
  const leaves = (v, skip = (k) => k.startsWith("_source") || k === "_note" || k === "_schema") => {
    if (typeof v === "string") add(v);
    else if (Array.isArray(v)) v.forEach((x) => leaves(x, skip));
    else if (v && typeof v === "object") for (const [k, x] of Object.entries(v)) if (!skip(k)) leaves(x, skip);
  };
  const bundle = JSON.parse(readFileSync(join(ROOT, "web", "data.json"), "utf8"));
  for (const r of bundle.recipes) add(r.machine);
  for (const t of bundle.tiers) add(t.name);
  for (const g of bundle.cooking) add(g.use);
  for (const h of bundle.storage.homes) { add(h.name); add(h.note); }
  for (const o of bundle.storage.outcomes) {
    add(o.verdict); add(o.why);
    if (/^Store it in [^.]+\. (.+)$/.test(o.advice)) add(o.advice.replace(/^Store it in [^.]+\. /, ""));
    for (const home of [o.label.replace(/^Sell - park in /, "")]) if (home !== o.label) { /* composed by words.js */ }
  }
  for (const e of Object.values(bundle.ease)) {
    add(e.where);
    if (e.describe && !/step\(s\)|^refinable once you have /.test(e.describe)) add(e.describe);
  }
  leaves(bundle.multitools);
  for (const gl of bundle.glyphs) add(gl.name);
  // (the galaxy names are proper names the game does not translate; they stay as they are)
  for (const file of ["acquisition.json"]) {
    const data = JSON.parse(readFileSync(join(ROOT, "data", file), "utf8"));
    for (const row of Object.values(data.items)) { add(row.where); add(row.note); }
  }
  return keys;
}

const holes = (s) => [...new Set([...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]))].sort().join(",");
// "{ordinal} in the system" is "3rd in the system" in English; other languages write the number: {n}.
const sameHoles = (key, value) => holes(value) === holes(key) || (key.includes("{ordinal}") && holes(value) === holes(key.replace("{ordinal}", "{n}")));

const dir = JSON.parse(readFileSync(join(ROOT, "web", "languages.json"), "utf8"));
const SAME = ["english", "usenglish", "tencentchinese"]; // English is the key; the other two share a file
const wanted = dir.list.map((l) => l.code).filter((c) => !SAME.includes(c));
const literal = literalKeys();
const required = new Set([...literal, ...dataKeys()]);

// I18N_DUMP=file.json writes the texts to translate (for a translator, human or not): [{key, plural, group}].
if (process.env.I18N_DUMP) {
  const { writeFileSync } = await import("node:fs");
  const fromData = dataKeys();
  writeFileSync(process.env.I18N_DUMP, JSON.stringify([...required].map((key) => ({ key, plural: plural.has(key), data: fromData.has(key) && !literal.has(key) })), null, 1));
}

for (const code of wanted) {
  test(`${code}: every text is translated`, async () => {
    const file = join(LANG, `${code}.js`);
    assert.ok(existsSync(file), `site/src/lang/${code}.js is missing`);
    const dict = (await import(pathToFileURL(file))).default;
    const missing = [...required].filter((k) => !(k in dict));
    if (process.env.I18N_REPORT) console.log(`${code}: ${missing.length} missing of ${required.size}`);
    if (process.env.I18N_REPORT === "list") console.log(JSON.stringify(missing, null, 1));
    assert.deepEqual(missing.slice(0, 15), [], `${missing.length} texts have no ${code} translation`);

    const locale = { brazilianportuguese: "pt-BR", portuguese: "pt-PT", simplifiedchinese: "zh-Hans", traditionalchinese: "zh-Hant",
      latinamericanspanish: "es-419" }[code] ?? { russian: "ru", french: "fr", german: "de", italian: "it", spanish: "es", polish: "pl",
      dutch: "nl", japanese: "ja", korean: "ko" }[code];
    const forms = new Intl.PluralRules(locale).resolvedOptions().pluralCategories.length;
    const bad = [];
    for (const key of required) {
      const value = dict[key];
      if (typeof value !== "string" || !value.trim()) { bad.push(`${key}: empty`); continue; }
      const parts = plural.has(key) ? value.split("|") : [value];
      const ofKey = holes(key);
      if (!parts.every((p) => sameHoles(key.includes("{ordinal}") ? key : ofKey && key, p) || holes(p) === ofKey)) bad.push(`${key}: placeholders differ -> ${value}`);
      if (plural.has(key) && value.split("|").length !== forms) bad.push(`${key}: ${value.split("|").length} plural forms, ${locale} has ${forms}`);
    }
    assert.deepEqual(bad.slice(0, 15), [], `${bad.length} problems in ${code}.js`);
  });
}

test("every dictionary key is something the page asks for", async () => {
  // A leftover key is a translation nobody sees: fine for the page, but it hides a renamed English text.
  const unused = {};
  for (const code of wanted) {
    const file = join(LANG, `${code}.js`);
    if (!existsSync(file)) continue;
    const dict = (await import(pathToFileURL(file))).default;
    unused[code] = Object.keys(dict).filter((k) => !required.has(k));
  }
  const worst = Math.max(0, ...Object.values(unused).map((v) => v.length));
  assert.ok(worst < 40, `some dictionaries hold many unused keys: ${JSON.stringify(Object.fromEntries(Object.entries(unused).map(([k, v]) => [k, v.slice(0, 5)])))}`);
});
