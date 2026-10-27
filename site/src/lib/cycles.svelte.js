// The real loops of the recipe book, found in the background and kept as rows that sit in the Craft table beside the recipes.
// A row is made like a recipe (so the table, its filters and sorts need nothing special) with `cycle` on it: the loop itself.
// Their index is below zero: they are not in D.recipes.

import { qtyLabel, timeLabel } from "./core.js";
import { D, name, RECIPES } from "./data.js";
import { t } from "./i18n.js";

export const MAX_SECONDS = 30 * 60; // a turn longer than half an hour is too much to run: such loops are not offered
export const cycles = $state({ rows: [], done: false });
let started = false;
const found = []; // the loops themselves, so the rows can be worded again when the language changes

const turnTime = (loop) => loop.parts.reduce((s, p) => s + (RECIPES[p.recipe].time || 0) * p.runs, 0);

function rowOf(loop, k) {
  const top = loop.net[0];
  const seed = loop.seed.length ? loop.seed : loop.parts.flatMap((p) => RECIPES[p.recipe].in.slice(0, 1));
  const time = turnTime(loop);
  const inputs = seed.map(([id, n]) => qtyLabel(n, name(id))).join(" + ");
  const outName = name(top[0]);
  const steps = loop.parts.map((p) => RECIPES[p.recipe]);
  return {
    index: -1 - k, domain: "refine", cycle: loop,
    in: seed, out: [top[0], top[1]], time, machine: steps[0].machine, op: t("Loop"),
    ratio: 0, loop: 0, rate: 0, profit: 0,
    outName, outLabel: t("{item} per turn", { item: qtyLabel(top[1], outName) }), inputs: t("start with {items}", { items: inputs }),
    mult: `+${top[1]}`, timeLabel: timeLabel(time),
    key: `${t("loop")} ${outName} ${inputs} ${steps.map((r) => `${r.outName} ${r.inputs}`).join(" ")}`.toLowerCase(),
  };
}

/** Word the rows again, in the language now chosen. */
export function rewordLoops() {
  cycles.rows = found.map(rowOf);
}

/** Starts the search once; the rows appear in `cycles.rows` as they are found. */
export function findLoopsInBackground() {
  if (started || typeof Worker === "undefined") return;
  started = true;
  const worker = new Worker(new URL("./cycles.worker.js", import.meta.url), { type: "module" });
  worker.onmessage = ({ data }) => {
    if (data.loop && turnTime(data.loop) <= MAX_SECONDS) {
      found.push(data.loop);
      cycles.rows = [...cycles.rows, rowOf(data.loop, cycles.rows.length)];
    }
    if (data.done) { cycles.done = true; worker.terminate(); }
  };
  worker.onerror = () => { cycles.done = true; };
  const recipes = D.recipes.map((r, index) => ({ index, in: r.in, out: r.out, time: r.time, domain: r.domain })).filter((r) => r.domain === "refine");
  worker.postMessage({ recipes, maxSize: 8 });
}

