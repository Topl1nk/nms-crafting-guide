// lib/i18n.js and lib/words.js: the page's words in English (the keys) and in another language.
import assert from "node:assert/strict";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

const LIB = join(import.meta.dirname, "..", "..", "site", "src", "lib");
const LANG = join(import.meta.dirname, "..", "..", "site", "src", "lang");
const i18n = await import(pathToFileURL(join(LIB, "i18n.js")));
const words = await import(pathToFileURL(join(LIB, "words.js")));
const core = await import(pathToFileURL(join(LIB, "core.js")));
const russian = (await import(pathToFileURL(join(LANG, "russian.js")))).default;

const { t, tn, setWords } = i18n;
const { easeDescribe, easeLabel, machine, machineShort, localizeStorage, band } = words;

test("English is the key: nothing is translated, {holes} are filled", () => {
  setWords("english", {});
  assert.equal(t("Search…"), "Search…");
  assert.equal(t("Saved: {name}", { name: "Base" }), "Saved: Base");
  assert.equal(t("not a known text {x}", { x: 1 }), "not a known text 1");
  assert.equal(t("{a}, {b}", { a: 1 }), "1, {b}"); // a hole without a value stays
});

test("plural forms follow the language", () => {
  setWords("english", {});
  assert.equal(tn(1, "{n} step|{n} steps"), "1 step");
  assert.equal(tn(0, "{n} step|{n} steps"), "0 steps");
  assert.equal(tn(5, "{n} step|{n} steps", { n: "5!" }), "5! steps");
  setWords("russian", russian);
  const f = (n) => tn(n, "{n} step|{n} steps");
  const expect = { 0: "шагов", 1: "шаг", 2: "шага", 4: "шага", 5: "шагов", 11: "шагов", 12: "шагов", 14: "шагов",
    21: "шаг", 22: "шага", 25: "шагов", 101: "шаг", 111: "шагов", 112: "шагов", 1002: "шага" };
  for (const [n, word] of Object.entries(expect)) assert.equal(f(Number(n)), `${n} ${word}`, n);
});

test("ease labels become words, unknown ones pass through", () => {
  setWords("english", {});
  assert.equal(easeLabel("T0 raw"), "raw from the planet");
  assert.equal(easeLabel("T1 raw"), "raw from asteroids");
  assert.equal(easeLabel("T2 +1"), "raw from the atmosphere, 1 step");
  assert.equal(easeLabel("T1 +6"), "raw from asteroids, 6 steps");
  assert.equal(easeLabel("loot (hard)"), "loot (hard)");
  assert.equal(easeLabel("loot (zzz)"), "loot (zzz)");
  assert.equal(easeLabel("something else"), "something else");
  setWords("russian", russian);
  assert.equal(easeLabel("T0 raw"), "сырьё с планеты");
  assert.equal(easeLabel("T2 +1"), "сырьё из атмосферы, 1 шаг");
  assert.equal(easeLabel("T1 +6"), "сырьё с астероидов, 6 шагов");
  assert.equal(easeLabel("loot (hard)"), "добыча (трудно)");
  assert.equal(band("work"), "Придётся потрудиться");
});

test("ease descriptions: the generated sentence is translated, others kept or looked up", () => {
  setWords("english", {});
  assert.equal(easeDescribe("2 step(s) from 3 raw material(s), 7 unit(s) in total"), "2 steps from 3 raw materials, 7 units in total");
  assert.equal(easeDescribe("1 step(s) from 1 raw material(s), 1 unit(s) in total"), "1 step from 1 raw material, 1 unit in total");
  assert.equal(easeDescribe("hand written"), "hand written");
  setWords("russian", russian);
  assert.equal(easeDescribe("2 step(s) from 3 raw material(s), 7 unit(s) in total"), "2 шага из 3 вида сырья, всего 7 ед.");
});

test("machines", () => {
  setWords("russian", russian);
  assert.equal(machine("Large Refiner"), "Большой очиститель");
  assert.equal(machine("Unknown"), "Unknown");
  assert.equal(machineShort("Nutrient Processor"), "Процессор");
  assert.equal(machineShort("Weird thing"), "Weird");
  setWords("english", {});
  assert.equal(machineShort("Large Refiner"), "Large");
});

test("localizeStorage words the exported English guide in place, from the English source, in any language", () => {
  const source = {
    homes: [{ key: "0", name: "Raw - common", label: "0 Raw - common", note: "x" }, { key: "zz", name: "Mystery", label: "Mystery", note: "kept" }],
    outcomes: [{ label: "Sell - park in 7 Sellables", verdict: "Sell", advice: "Keep it in the exosuit.", why: "Named in the guide" },
      { label: "5 Progression", verdict: "Store", advice: "Store it in 5 Progression.", why: "A companion egg" },
      { label: "6 Upgrades & tech", verdict: "Store", why: "x",
        advice: "Store it in 6 Upgrades & tech. Scrap it at a terminal for nanites if you have no use for it -- never send it with the Trade Rocket, which pays units only." }],
  };
  const storage = structuredClone(source);
  setWords("russian", russian);
  localizeStorage(storage, source);
  assert.equal(storage.homes[0].name, "Сырьё — обычное");
  assert.equal(storage.homes[0].label, "0 Сырьё — обычное");
  assert.equal(storage.homes[1].name, "Mystery");
  assert.equal(storage.homes[1].note, "kept");
  assert.equal(storage.outcomes[0].label, "Продать — до тех пор в «7 На продажу»");
  assert.equal(storage.outcomes[0].verdict, "Продать");
  assert.equal(storage.outcomes[0].advice, "Держите в экзокостюме.");
  assert.equal(storage.outcomes[1].advice, "Положите в «5 Прогресс».");
  assert.match(storage.outcomes[2].advice, /^Положите в «6 Улучшения и технологии»\. Если не пригодится/);
  setWords("english", {});
  localizeStorage(storage, source); // back to English, from the same source
  assert.equal(storage.homes[0].name, "Raw - common");
  assert.equal(storage.outcomes[0].label, "Sell - park in 7 Sellables");
  assert.equal(storage.outcomes[1].advice, "Store it in 5 Progression.");
  assert.equal(storage.outcomes[2].advice, source.outcomes[2].advice);
});

test("numbers and the short time units follow the language", () => {
  setWords("english", {});
  assert.equal(core.fmtInt(1234567), "1,234,567");
  assert.equal(core.timeLabel(90), "1.5 min");
  assert.equal(core.timeLabel(30), "30 s");
  setWords("russian", russian);
  assert.equal(core.timeLabel(90), "1.5 мин");
  assert.equal(core.timeLabel(7200), "2.0 ч");
  assert.match(core.fmtInt(1234567), /^1\s234\s567$/u);
  setWords("english", {});
});

test("the browser's language picks the game language, English when none fits", () => {
  const list = ["english", "usenglish", "russian", "latinamericanspanish", "spanish", "brazilianportuguese", "portuguese", "simplifiedchinese", "tencentchinese"];
  const pick = (langs) => { Object.defineProperty(globalThis, "navigator", { value: { languages: langs }, configurable: true }); return i18n.browserLanguage(list); };
  assert.equal(pick(["ru-RU", "en"]), "russian");
  assert.equal(pick(["es-MX"]), "latinamericanspanish");
  assert.equal(pick(["es-ES"]), "spanish");
  assert.equal(pick(["pt-BR"]), "brazilianportuguese");
  assert.equal(pick(["zh-CN"]), "simplifiedchinese");
  assert.equal(pick(["fr-FR"]), "english"); // not in this list
  assert.equal(pick([]), "english");
});
