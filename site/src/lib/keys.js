// The keyboard, as the TUI has it: j/k or arrows move, / searches, Enter
// pivots, Esc clears, p/r/c jump from the highlighted recipe, 1-7 between
// sections. One listener for the page; each view says what its keys act on
// by calling setKeys() with getters, since its list exists only once mounted.
//
//   list    a List component (move, select, current, count)
//   search  the view's search box
//   enter   / escape   what those keys do when no box has focus
//   key     first refusal on any key (the portal dial takes hex digits)

import { NAV } from "./data.js";
import { go } from "./router.svelte.js";

let active = {};

export const setKeys = (targets) => { active = targets; };
export const resetKeys = () => { active = {}; };

export function onKey(e, openPalette) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    openPalette();
    return;
  }
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const typing = e.target.closest?.("input, select, textarea");
  if (typing) {
    if (e.key === "Escape") e.target.blur();
    if (e.key === "Enter" && e.target === active.search && active.list) {
      e.target.blur();
      e.preventDefault();
    }
    return;
  }
  if (active.key?.(e)) { e.preventDefault(); return; }
  const list = active.list;
  const id = location.hash.startsWith("#/recipes") ? list?.current()?.out?.[0] : null;
  switch (e.key) {
    case "j": case "ArrowDown": list?.move(1); break;
    case "k": case "ArrowUp": list?.move(-1); break;
    case "PageDown": list?.move(10); break;
    case "PageUp": list?.move(-10); break;
    case "G": case "End": list?.select(list.count() - 1); break;
    case "Home": list?.select(0); break;
    case "/": active.search?.focus(); active.search?.select(); break;
    case "Enter": active.enter?.(); break;
    case "Escape": active.escape?.(); break;
    case "p": if (id) go(`#/recipes?item=${encodeURIComponent(id)}&role=output`); break;
    case "r": if (id) go(`#/recipes?item=${encodeURIComponent(id)}&role=input`); break;
    case "c": if (id) go(`#/chain/${encodeURIComponent(id)}`); break;
    case "?": go("#/help"); break;
    default:
      if (/^[1-7]$/.test(e.key)) go(`#/${NAV[Number(e.key) - 1][0]}`);
      else return;
  }
  e.preventDefault();
}
