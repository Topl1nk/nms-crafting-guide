// The game's template marks (%NAME%, %SIZE% ...) in item texts are not shown: site/src/lib/placeholders.js
//   node --test tests/js/placeholders.test.mjs
import assert from "node:assert/strict";
import { test } from "node:test";
import { cleanDesc, cleanSub } from "../../site/src/lib/placeholders.js";

test("a subtitle loses the mark and the English possessive", () => {
  assert.equal(cleanSub("%NAME%'s Genetic Material"), "Genetic Material");
  assert.equal(cleanSub("%NAME%: генетический материал"), "Генетический материал");
  assert.equal(cleanSub("Lingering Soul Fragment"), "Lingering Soul Fragment");
  assert.equal(cleanSub(""), "");
});

test("a description keeps what stands before the mark's comma, and drops what has none", () => {
  const egg = "A living, fertile egg, %READY%%EXTRA%\n\n%MODIFIED%\n\nScans indicate the being within has the genetic potential to be %SIZE% and %TRAIT%.";
  assert.equal(cleanDesc(egg), "A living, fertile egg.");
  assert.equal(cleanDesc("A deployable freighter upgrade, salvaged from %NAME%.\n\nCan be re-deployed into your own capital ship."),
    "A deployable freighter upgrade.\n\nCan be re-deployed into your own capital ship.");
  assert.equal(cleanDesc("Живое оплодотворенное яйцо, %READY%%EXTRA%\n\n%MODIFIED%\n\nСканирование показывает размер %SIZE% и черту %TRAIT%."),
    "Живое оплодотворенное яйцо.");
  assert.equal(cleanDesc("Nothing to fill here."), "Nothing to fill here.");
});

test("a sentence before the one with a mark stays whole", () => {
  assert.equal(cleanDesc("The signature is intact. It will unlock the thrusters of the starship %SHIPNAME%."), "The signature is intact.");
});
