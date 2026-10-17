// Light, dark, or the system's -- Hextra's three, "system" by default. An
// explicit choice sets data-theme; "system" removes it and the CSS media
// query decides, so an OS switch recolours an open page with no code here.
// The inline script in index.html applies the saved choice before first paint.

import { local } from "./local.js";

export const THEMES = [["light", "Light"], ["dark", "Dark"], ["system", "System"]];

export function themeChoice() {
  const t = local.get("theme", "system");
  return t === "light" || t === "dark" ? t : "system";
}

export function applyTheme(choice) {
  if (choice === "system") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = choice;
  local.set("theme", choice);
}
