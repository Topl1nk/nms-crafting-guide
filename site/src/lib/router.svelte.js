// The hash router: `#/section/rest?query`, as the hand-written page had it, so
// every link anyone has shared still opens the same view with the same
// settings. Small enough that a routing library would be most of the code.
//
// Each hashchange bumps `route.visit`; App.svelte keys the view on it, so a
// view is built fresh per visit and its local state goes with it -- the old
// page's "a fresh element per visit". Views that keep settings in the URL
// rewrite it with replace(), which does not count as a visit.

import { resetKeys } from "./keys.js";

function parse() {
  const hash = location.hash.replace(/^#\/?/, "") || "home";
  const [path, query = ""] = hash.split("?");
  const [section, ...rest] = path.split("/");
  const params = new URLSearchParams(query);
  // Cooking is a part of Craft now; its old links (#/cooking?buff=) open there.
  if (section === "cooking") {
    params.set("domain", "cook");
    if (params.has("buff")) { params.set("effect", params.get("buff")); params.delete("buff"); }
    return { section: "recipes", arg: "", params };
  }
  // The short path is a part of Craft now (its canvas takes the table's place); #/chain/ITEM?tier=&qty=&cook= opens there.
  if (section === "chain") {
    const item = decodeURIComponent(rest.join("/"));
    params.set("path", item);
    params.set("item", item);
    return { section: "recipes", arg: "", params };
  }
  if (section === "nanites") { params.set("domain", "nanites"); return { section: "recipes", arg: "", params }; }
  return { section, arg: decodeURIComponent(rest.join("/")), params };
}

export const route = $state({ ...parse(), visit: 0 });

window.addEventListener("hashchange", () => {
  resetKeys();
  Object.assign(route, parse(), { visit: route.visit + 1 });
});

// The URL as it was when the current view was entered. A view reads it once,
// as it is built: it is rebuilt on the next visit anyway.
export const arrival = () => parse();

export const go = (hash) => { location.hash = hash; };

// Keep a view's settings in the address bar without re-entering the view.
export const replace = (hash) => history.replaceState(null, "", hash);

/**
 * A state of a view that has no address of its own (a loop drawn whole, a list narrowed to one item) takes an entry of the
 * browser's history, so Back (the mouse's side button too) closes it and shows the screen the button was pressed on.
 * `onclose` runs when Back is pressed. Returns `release()`: it closes the state from the page (the same step back).
 */
export function trapBack(onclose) {
  const key = `trap${Math.random().toString(36).slice(2)}`;
  history.pushState({ trap: key }, "", location.href);
  const off = () => { window.removeEventListener("popstate", pop); window.removeEventListener("hashchange", off); };
  function pop() {
    if (history.state?.trap === key) return;
    off();
    onclose();
  }
  window.addEventListener("popstate", pop);
  window.addEventListener("hashchange", off); // left by a link: nothing is left to close
  return () => { if (history.state?.trap === key) history.back(); else { off(); onclose(); } };
}
