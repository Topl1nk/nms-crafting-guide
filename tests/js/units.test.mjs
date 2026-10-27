// Every price and profit on the site is in units, shown with the game's own sign: no generic coin picture, no "ед." (the Russian abbreviation),
// and the picture is really there.
import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { join } from "node:path";

const ROOT = join(import.meta.dirname, "..", "..");
const SRC = join(ROOT, "site", "src");

function* sources(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) yield* sources(p);
    else if (e.name.endsWith(".svelte")) yield p; // (lang/russian.js has "ед." as a count of raw material, not money)
  }
}

test("the units picture is in the icons", () => {
  assert.ok(existsSync(join(ROOT, "web", "icons", "UNITS.webp")));
});

test("no price is drawn with the generic coin or labelled 'ед.'", () => {
  for (const file of sources(SRC)) {
    const text = readFileSync(file, "utf8");
    assert.ok(!/name="coin"/.test(text), `${file}: the generic coin icon, use <Units />`);
    assert.ok(!/ ед\.(?![а-я])/.test(text.replace(/\{[^}]*\}/g, "")), `${file}: "ед." for units, use <Units />`);
  }
});
