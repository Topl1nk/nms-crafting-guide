// How the page looks, and what the visitor can change: light or dark, the
// accent colour, whether icons glow in the game's own item colours, whether they carry
// the chemical symbol, and the text size. Each is a data attribute or a CSS variable on <html>; the inline
// script in index.html applies the saved theme before first paint, and
// applyLook() applies the rest as soon as the page starts.

import { N_ } from "./i18n.js";
import { local } from "./local.js";

export const THEMES = [["light", N_("Light")], ["dark", N_("Dark")]];

// The game's HUD is mostly these: its gold, its cyan scanner blue, the green of
// a good scan, the purple of rare finds, and warning orange.
//
// [key, name, colour, ink, on]: the colour fills (a button, a badge); the ink is the same accent where it is drawn as text, a line or
// an icon on a dark surface (the same colour here); `on` is the text on a fill (dark, when none is given). Gold is the default.
export const ACCENTS = [
  ["gold", N_("Gold"), "#f1c265"],
  ["cyan", N_("Cyan"), "#5ccbf0"],
  ["green", N_("Green"), "#64f19f"],
  ["violet", N_("Violet"), "#c595f6"],
  ["orange", N_("Orange"), "#f09d5c"],
];

export function themeChoice() {
  return local.get("theme", "dark") === "light" ? "light" : "dark";
}

export function applyTheme(choice) {
  document.documentElement.dataset.theme = choice;
  local.set("theme", choice);
}

export const look = {
  // A saved key that is no longer in the list (the "umber" there once was) falls back to the first: gold.
  accent: () => local.get("accent", "gold"),
  glow: () => local.get("glow", true),
  // Text size in px; the old "bigger text" switch (18) still counts for a saved choice.
  fs: () => Number(local.get("fs", local.get("big", false) ? 18 : 16)),
  sym: () => local.get("sym", true),
};

export function applyLook() {
  const root = document.documentElement;
  const [, , hex, ink = hex, on = "#0b1124"] = ACCENTS.find(([k]) => k === look.accent()) ?? ACCENTS[0];
  root.style.setProperty("--accent", hex);
  root.style.setProperty("--accent-ink", ink);
  root.style.setProperty("--on-accent", on);
  root.dataset.glow = look.glow() ? "1" : "0";
  root.style.setProperty("--fs", `${look.fs()}px`);
  root.dataset.sym = look.sym() ? "1" : "0";
}

export function setLook(key, value) {
  local.set(key, value);

  applyLook();
}



