// New versions of the program, from its GitHub releases, through the desktop launcher (desktop/updater.py). A page on a plain
// static host has no launcher: `available` stays false and nothing is offered.
//
// The program looks for a new version when it starts and every few hours while it is open, and only says so (a mark on the
// settings button, and a line in Settings). Installing is the player's choice, or the program's own when "update
// automatically" is on, which it is not until it is turned on.

import { local } from "./local.js";

export const update = $state({
  available: false, supported: false, current: "", latest: "", newer: false,
  state: "idle", done: 0, total: 0, error: "", auto: local.get("update-auto", false), asked: false,
});

const EVERY = 6 * 3600 * 1000;
let polling = 0;

async function look() {
  const res = await fetch("api/update", { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status}`);
  Object.assign(update, await res.json(), { available: true });
}

const post = (path) => fetch(`api/update/${path}`, { method: "POST" }).then((r) => { if (!r.ok) throw new Error(`${r.status}`); });

export function setAuto(on) {
  update.auto = on;
  local.set("update-auto", on);
  if (on) autoInstall();
}

function autoInstall() {
  if (update.auto && update.supported && update.newer && update.state === "idle") installUpdate();
}

/** Ask the launcher for what it knows, and have it ask GitHub (it keeps its own gap between two asks). */
export async function checkUpdate(force = false) {
  try {
    await look();
    if (!update.current) return; // a checkout: no version, nothing to compare
    await post(force ? "check?force=1" : "check");
    update.asked = true;
    clearInterval(polling);
    // The answer comes in the background: look until it is there (a few seconds at most).
    let n = 0;
    polling = setInterval(async () => {
      try { await look(); } catch { clearInterval(polling); return; }
      if (update.state === "idle" || ++n > 20) { clearInterval(polling); autoInstall(); }
    }, 700);
  } catch {
    update.available = false;
  }
}

/** Download the new version and install it; the program closes and starts again by itself. */
export async function installUpdate() {
  if (update.state !== "idle") return;
  try { await post("install"); } catch (exc) { update.error = `${exc.message}`; return; }
  update.state = "downloading";
  clearInterval(polling);
  polling = setInterval(async () => {
    try { await look(); } catch { return; } // the program has closed: the installer is on its way
    if (update.state === "idle") clearInterval(polling);
  }, 700);
}

/** Started once with the page; looks again every few hours while the program stays open. */
export function startUpdates() {
  checkUpdate();
  setInterval(() => checkUpdate(), EVERY);
}
