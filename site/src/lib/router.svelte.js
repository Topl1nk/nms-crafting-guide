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
  return { section, arg: decodeURIComponent(rest.join("/")), params: new URLSearchParams(query) };
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
