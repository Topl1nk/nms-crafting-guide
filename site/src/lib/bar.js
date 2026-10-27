// Motion of the filter bars (Select, Check): a filter that is not offered shrinks away instead of vanishing, and one that
// comes back grows in, while its two neighbours (app.css) stretch or give the room back at the same pace.

import { springAt } from "./spring.js";

const MS = 450;
const still = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** `in:` transition of a filter that comes back: its width grows from nothing to its own. */
/** (`skip`: the filter is there from the start, nothing comes back.) */
export function bloom(node, { skip = false } = {}) {
  if (skip || still()) return { duration: 0 };
  const w = node.getBoundingClientRect().width;
  return { duration: MS, easing: springAt, css: (t) => `width:${w * t}px; min-width:0; overflow:hidden; opacity:${t}; margin-left:${-8 * (1 - t)}px; flex-grow:0` };
}

/** The marker of a filter that is not offered: it takes the width the filter had and gives it up (the css has the transition). */
export function collapse(node, width) {
  if (still() || !width) { node.style.width = "0px"; return; }
  node.style.width = `${width}px`;
  requestAnimationFrame(() => requestAnimationFrame(() => { node.style.width = "0px"; }));
}

