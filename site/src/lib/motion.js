// Motion of the large things. A pane is never switched on or off: it slides in from the nearest edge of the screen and, when
// the page changes, the old panes slide out behind the edges they came from (a table to the left, its card to the right, the
// bars over them to the top). Only a move, no mask, no blur: whatever is drawn is what is there. Nothing moves for visitors who
// ask for less motion.
//
// Made so that nothing stutters or flashes: only transforms are animated (the compositor does them, the page is not laid out
// again); the new page is kept out of sight from the moment it is built until its first frame is ready to slide (no frame of
// it standing in its place); the old page is copied with only the rows that are in view; and every measurement is taken before
// anything is changed, so the page is laid out once, not once per pane.

import { springAt } from "./spring.js";

const OVERSHOOT = 8; // px: how far a pane may go past its place before it settles back (never into its neighbour)
const OUT = "cubic-bezier(0.55, 0, 0.9, 0.45)"; // gathers speed, gone
const still = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let busyUntil = 0; // while a whole page is arriving, the panes inside it do not slide again
let ghosts = null; // the old panes, drawn over the page while they leave
let failsafe = 0;

/**
 * The way in: the site's spring, but its overshoot is a few pixels, whatever the length of the way (the spring itself overshoots by a
 * tenth of the distance, which for a pane that crosses the screen is a hundred pixels into the pane beside it).
 */
function slideIn(el, dx, dy, o) {
  const far = Math.max(Math.abs(dx), Math.abs(dy)) || 1;
  const frames = [];
  for (let i = 0; i <= 40; i++) {
    const t = i / 40;
    let k = 1 - springAt(t);
    if (k < 0) k = -Math.min(-k, OVERSHOOT / far);
    frames.push({ offset: t, transform: `translate(${dx * k}px, ${dy * k}px)` });
  }
  return el.animate(frames, { easing: "linear", fill: "backwards", ...o });
}

/** How far `rect` must move to be behind the given edge of the screen. */
function away(rect, edge) {
  const gap = 24;
  if (edge === "left") return [-(rect.right + gap), 0];
  if (edge === "right") return [innerWidth - rect.left + gap, 0];
  if (edge === "top") return [0, -(rect.bottom + gap)];
  return [0, innerHeight - rect.top + gap];
}

/** The edge a pane belongs to: the first of a table-and-card pair to the left, the other to the right, bars to the top, the rest to the side `dir`. */
function edgeOf(el, dir) {
  const parent = el.parentElement;
  if (parent?.matches(".split, .grid3")) return parent.firstElementChild === el ? "left" : "right";
  if (el.matches(".fbar, .count")) return "top";
  return dir;
}

/** The panes of a page and where each stands (all measured at once). */
function panesOf(main) {
  const panes = [];
  for (const child of main?.children ?? []) {
    if (child.matches(".split, .grid3")) panes.push(...child.children);
    else if (!child.matches("datalist, script, style")) panes.push(child);
  }
  return panes.slice(0, 8).map((el) => ({ el, rect: el.getBoundingClientRect() })).filter(({ rect }) => rect.width > 8 && rect.height > 8);
}

const moving = (ms) => {
  document.documentElement.classList.add("nms-moving");
  setTimeout(() => document.documentElement.classList.remove("nms-moving"), ms);
};

/** A copy of a table that holds only the rows that are in view (a spacer stands for the ones above), so copying a long list is cheap. */
function trimRows(copy, el) {
  const body = copy.querySelector("tbody");
  const first = el.querySelector("tbody tr");
  if (!body || !first) return;
  const rowH = first.getBoundingClientRect().height || 48;
  const from = Math.max(0, Math.floor(el.scrollTop / rowH) - 1);
  const to = from + Math.ceil(el.clientHeight / rowH) + 3;
  [...body.children].forEach((tr, i) => { if (i < from || i > to) tr.remove(); });
  if (from) {
    const spacer = document.createElement("tr");
    spacer.innerHTML = `<td colspan="99" style="height:${from * rowH}px; padding:0; border:0"></td>`;
    body.prepend(spacer);
  }
}

/**
 * Hides the page that is about to be built: call it before it is replaced. The new panes are shown by enterView, in the
 * very frame they start to slide, so there is never a frame of them standing where they end.
 */
export function hold(main) {
  if (still() || !main) return;
  main.dataset.entering = "";
  clearTimeout(failsafe);
  failsafe = setTimeout(() => release(main), 1500); // never leave a page hidden
}
const release = (main) => { clearTimeout(failsafe); main?.removeAttribute("data-entering"); };

/** The panes of the page that is about to be replaced, copied where they stand. Call it before the page is changed. */
export function snapshot(main) {
  ghosts?.remove();
  ghosts = null;
  if (still() || !main) return null;
  const layer = document.createElement("div");
  layer.className = "nms-ghosts";
  const list = [];
  for (const { el, rect } of panesOf(main)) {
    const copy = el.cloneNode(true);
    copy.removeAttribute("id");
    if (el.matches(".list")) trimRows(copy, el);
    copy.style.cssText = `position:fixed; left:${rect.left}px; top:${rect.top}px; width:${rect.width}px; height:${rect.height}px; margin:0; pointer-events:none; will-change:transform;`;
    copy.dataset.scroll = String(el.scrollTop);
    layer.append(copy);
    list.push({ copy, rect, edge: edgeOf(el, "right") });
  }
  document.body.append(layer);
  list.forEach(({ copy }) => { copy.scrollTop = Number(copy.dataset.scroll); });
  ghosts = layer;
  return { layer, list };
}

/**
 * The page has changed: the old panes (`snap`) slide out behind their edges, then the new ones slide in from theirs.
 * `dir`: the side the new page's own panes (one that is no pair) come from.
 */
/** Motion blur: a fast thing is smeared along its way and sharp where it stops. */
function smear(el, px, o) {
  return el.animate([{ filter: `blur(${px}px)` }, { filter: "blur(0px)" }], { easing: "ease-out", fill: "backwards", ...o });
}

let soft = 0; // until when the next page change is a crossfade, not a slide
/** The next page change melts: the old panes fade, the new ones fade in where they stand (a tile is flying from one page to the other). */
export function quiet() { soft = performance.now() + 3000; }

export function enterView(main, dir, snap) {
  if (still() || !main) { snap?.layer.remove(); release(main); return; }
  if (performance.now() < soft) {
    soft = 0;
    snap?.list.forEach(({ copy }) => { copy.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 300, easing: "ease-out", fill: "forwards" }); });
    if (snap) setTimeout(() => { snap.layer.remove(); if (ghosts === snap.layer) ghosts = null; }, 340);
    panesOf(main).forEach(({ el }, i) => {
      el.style.willChange = "transform, opacity";
      const a = el.animate([{ opacity: 0, transform: "translateY(10px)" }, { opacity: 1, transform: "none" }], { duration: 420, delay: 100 + i * 40, easing: "cubic-bezier(.2, .8, .2, 1)", fill: "backwards" });
      a.onfinish = a.oncancel = () => { el.style.willChange = ""; };
    });
    moving(700);
    busyUntil = performance.now() + 700;
    release(main);
    return;
  }
  const out = 240;
  const total = out + 600;
  const fresh = panesOf(main).map(({ el, rect }) => ({ el, to: away(rect, edgeOf(el, dir)) })); // all measured, then all moved
  moving(total + 100);
  snap?.list.forEach(({ copy, rect, edge }) => {
    const [dx, dy] = away(rect, edge);
    copy.animate([{ transform: "translate(0, 0)" }, { transform: `translate(${dx}px, ${dy}px)` }], { duration: out, easing: OUT, fill: "forwards" });
    copy.animate([{ filter: "blur(0px)" }, { filter: "blur(3px)" }], { duration: out, easing: "ease-in", fill: "forwards" });
  });
  if (snap) setTimeout(() => { snap.layer.remove(); if (ghosts === snap.layer) ghosts = null; }, out + 60);
  const delay = snap ? out + 20 : 0; // the old panes are gone before the new ones start: nothing meets on the way
  fresh.forEach(({ el, to: [dx, dy] }, i) => {
    el.style.willChange = "transform";
    const a = slideIn(el, dx, dy, { duration: 520, delay: delay + i * 35 });
    smear(el, 3, { duration: 360, delay: delay + i * 35 });
    a.onfinish = a.oncancel = () => { el.style.willChange = ""; };
  });
  release(main); // the same frame: the panes are where the first keyframe puts them
  busyUntil = performance.now() + total + 100;
}

// ---- The page turn (the Wiki's card): the old card lies over the new one and is peeled off by its upper left corner, drawn toward the lower
// right. The fold is a straight line across the card that moves along the diagonal; what is behind it is the turned-over leaf (the back of
// the paper, shaded round its crease), what is before it is the old page with the shadow of the leaf on it, and under all of it the new card.
let captured = null; // the old card, copied just before the card changes

/** Call just before a card is to change: the card as it is now, kept for the turn. */
export function capture() {
  captured = null;
  const el = document.querySelector("main .detail");
  if (still() || !el) return;
  const rect = el.getBoundingClientRect();
  if (rect.width < 80 || rect.height < 80) return;
  const copy = el.cloneNode(true);
  copy.removeAttribute("id");
  captured = { copy, rect };
  setTimeout(() => { if (captured?.copy === copy) captured = null; }, 400);
}

/** The part of a convex polygon where `g(point) >= 0`. */
function keep(poly, g) {
  const out = [];
  poly.forEach((a, i) => {
    const b = poly[(i + 1) % poly.length];
    const ga = g(a), gb = g(b);
    if (ga >= 0) out.push(a);
    if ((ga >= 0) !== (gb >= 0)) { const k = ga / (ga - gb); out.push([a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k]); }
  });
  return out;
}
const clipOf = (poly) => (poly.length > 2 ? `polygon(${poly.map(([x, y]) => `${x.toFixed(1)}px ${y.toFixed(1)}px`).join(",")})` : "polygon(0 0, 0 0, 0 0)");

function peelCard({ copy, rect }) {
  const w = rect.width, h = rect.height, S = Math.hypot(w, h);
  const d = [w / S, h / S];
  const angle = (Math.atan2(d[0], -d[1]) * 180) / Math.PI; // the css angle of the way the page is drawn
  const box = [[0, 0], [w, 0], [w, h], [0, h]];
  const wrap = document.createElement("div");
  wrap.className = "nms-ghosts";
  wrap.style.cssText = `position:fixed; left:${rect.left}px; top:${rect.top}px; width:${w}px; height:${h}px; border-radius:var(--r-pane, 14px); overflow:hidden; pointer-events:none; z-index:12;`;
  const page = document.createElement("div"); // the old page, with the shadow of the leaf on it
  const sheet = document.createElement("div");
  copy.style.cssText = `position:absolute; left:0; top:0; width:${w}px; height:${h}px; margin:0;`;
  const shade = document.createElement("div");
  shade.style.cssText = "position:absolute; inset:0;";
  sheet.append(copy, shade);
  sheet.style.cssText = "position:absolute; inset:0;";
  page.style.cssText = "position:absolute; inset:0; filter:drop-shadow(-4px -4px 7px rgb(0 0 0 / 0.55));";
  page.append(sheet);
  const leaf = document.createElement("div"); // the turned-over leaf: the back of the paper
  const back = document.createElement("div");
  back.style.cssText = "position:absolute; inset:0; background-color:var(--p-raised);";
  leaf.style.cssText = "position:absolute; inset:0; filter:drop-shadow(-5px -5px 9px rgb(0 0 0 / 0.6));";
  leaf.append(back);
  wrap.append(page, leaf);
  document.body.append(wrap);
  const frame = (s) => {
    const f = (p) => p[0] * d[0] + p[1] * d[1] - s;
    sheet.style.clipPath = clipOf(keep(box, f));
    const W = Math.min(s, 120); // the paper rolls as it is drawn: only a band of it, the width of a roll, lies over the page
    let flap = keep(keep(box, (p) => -f(p)), (p) => f(p) + W).map((p) => { const k = 2 * f(p); return [p[0] - k * d[0], p[1] - k * d[1]]; });
    for (const g of [(p) => p[0], (p) => w - p[0], (p) => p[1], (p) => h - p[1]]) flap = keep(flap, g);
    back.style.clipPath = clipOf(flap);
    const a = (s / S) * 100, b = ((s + W) / S) * 100;
    shade.style.background = `linear-gradient(${angle}deg, transparent ${a}%, rgb(0 0 0 / 0.5) ${a}%, transparent ${a + (46 / S) * 100}%)`;
    back.style.background = `linear-gradient(${angle}deg, transparent ${a}%, rgb(0 0 0 / 0.5) ${a}%, rgb(255 255 255 / 0.1) ${a + (b - a) * 0.12}%, rgb(255 255 255 / 0.28) ${a + (b - a) * 0.34}%, rgb(255 255 255 / 0.06) ${a + (b - a) * 0.68}%, rgb(0 0 0 / 0.4) ${b}%), var(--p-raised)`;
  };
  frame(0);
  const ms = 900, t0 = performance.now();
  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2); // taken by the corner: slow, then it gives
  const done = () => wrap.remove();
  const tick = (now) => {
    if (!wrap.isConnected) return;
    const t = Math.min(1, Math.max(0, (now - t0) / ms));
    frame(S * ease(t) * 1.001);
    if (t < 1) requestAnimationFrame(tick); else done();
  };
  requestAnimationFrame(tick);
  setTimeout(done, ms + 400); // a hidden tab draws no frames: the card is never left covered
}

// ---- The card of Craft is a leaf of card, with a thickness, that stands on its edge at the right edge of the screen and falls toward the
// middle, onto the card that lies there. The page is seen from above, so it is a real fall in perspective (the vanishing point is the middle
// of the screen): the card turns about its outer edge, its free edge comes down from the viewer to the table, gathering speed all the way
// (gravity, not a spring); its shadow on the table (and on the old card) grows sharp and dark as it nears; it lands and the landing is felt:
// it springs up off the table twice, less each time, and rests. `old`: the card as it was, left lying until the new one has covered it.
// A card falls only when the visitor did something to bring another one (a click, a key, the wheel): a list that reorders itself while it
// loads (the cycles are still being found) changes the card too, and that is no action to be shown twice.
let lastInput = 0;
for (const ev of ["pointerdown", "keydown", "wheel"]) addEventListener(ev, () => { lastInput = performance.now(); }, true);

let falling = null; // the leaf in the air, to be cleared if another one is dropped

function drop(node, old) {
  falling?.();
  const rect = node.getBoundingClientRect();
  const w = rect.width, h = rect.height, T = 7; // T: the thickness of the card
  const make = (css, parent) => { const el = document.createElement("div"); el.style.cssText = css; parent?.append(el); return el; };
  const lift = getComputedStyle(node).position === "static";
  const keep = { z: node.style.zIndex, o: node.style.opacity };
  const box = `position:fixed; left:${rect.left}px; top:${rect.top}px; width:${w}px; height:${h}px; pointer-events:none;`;
  const layer = make("position:fixed; inset:0; pointer-events:none; z-index:2;");
  layer.className = "nms-ghosts";
  let ghost = null;
  if (old) {
    ghost = make(`${box} position:fixed; left:${old.rect.left}px; top:${old.rect.top}px; width:${old.rect.width}px; height:${old.rect.height}px;`, layer);
    old.copy.removeAttribute("id");
    old.copy.style.cssText = `position:absolute; left:0; top:0; width:${old.rect.width}px; height:${old.rect.height}px; margin:0; transform:none;`;
    ghost.append(old.copy);
  }
  const shadow = make(`${box} border-radius:var(--r-pane, 14px); background:rgb(0 0 0); transform-origin:100% 50%;`, layer); // on the table
  const px = ((innerWidth / 2 - rect.left) / w) * 100; // the vanishing point: the middle of the screen
  const stage = make(`${box} perspective:1500px; perspective-origin:${px}% 50%;`, layer);
  const slab = make("position:absolute; inset:0; transform-style:preserve-3d; transform-origin:100% 50%;", stage);
  const edge = "background:color-mix(in srgb, var(--p-panel) 62%, black); backface-visibility:hidden;";
  const front = node.cloneNode(true);
  front.removeAttribute("id");
  front.style.cssText = `position:absolute; left:0; top:0; width:${w}px; height:${h}px; max-height:none; margin:0; overflow:hidden; transform:none; backface-visibility:hidden;`;
  slab.append(front);
  const dim = make("position:absolute; inset:0; border-radius:var(--r-pane, 14px); background:linear-gradient(90deg, rgb(0 0 0 / 0.9), rgb(0 0 0 / 0.35)); pointer-events:none; backface-visibility:hidden; opacity:0;", slab);
  make(`position:absolute; inset:0; ${edge} border-radius:var(--r-pane, 14px); transform:translateZ(${-T}px) rotateY(180deg);`, slab); // the back
  make(`position:absolute; left:0; top:0; width:${T}px; height:${h}px; ${edge} transform-origin:0 50%; transform:rotateY(90deg);`, slab);
  make(`position:absolute; right:0; top:0; width:${T}px; height:${h}px; ${edge} transform-origin:100% 50%; transform:rotateY(-90deg);`, slab);
  make(`position:absolute; left:0; top:0; width:${w}px; height:${T}px; ${edge} transform-origin:50% 0; transform:rotateX(-90deg);`, slab);
  make(`position:absolute; left:0; bottom:0; width:${w}px; height:${T}px; ${edge} filter:brightness(0.7); transform-origin:50% 100%; transform:rotateX(90deg);`, slab);
  document.body.append(layer);
  if (lift) { node.style.position = "relative"; node.style.top = "auto"; } // (a static card may still carry a `top` for when it is sticky)
  node.style.opacity = "0"; // the leaf in the air is a copy of it (the card stays drawn, only unseen, so showing it again repaints nothing)
  let over = false;
  const end = () => {
    if (over) return;
    over = true;
    falling = null;
    node.style.opacity = keep.o;
    node.style.zIndex = keep.z;
    if (lift) { node.style.position = ""; node.style.top = ""; }
    requestAnimationFrame(() => requestAnimationFrame(() => layer.remove())); // the card is up a frame before the copy of it goes: no gap, no flash
  };
  falling = end;
  // the angle of the free edge above the table (degrees) at `ms`: standing, falling, two bounces, rest
  const FALL = 520, UP1 = 210, UP2 = 150, TOTAL = FALL + UP1 + UP2 + 80;
  const angle = (ms) => {
    if (ms < FALL) return 88 * (1 - Math.pow(ms / FALL, 2.3));
    ms -= FALL;
    if (ms < UP1) { const v = ms / UP1; return 9 * 4 * v * (1 - v); }
    ms -= UP1;
    if (ms < UP2) { const v = ms / UP2; return 2.6 * 4 * v * (1 - v); }
    return 0;
  };
  const frame = (ms) => {
    const a = angle(ms), r = (a * Math.PI) / 180, s = Math.sin(r), c = Math.cos(r);
    slab.style.transform = `rotateY(${a}deg)`;
    dim.style.opacity = String(Math.min(1, 0.62 * Math.pow(s, 0.8)));
    // the shadow: the leaf's footprint on the table, soft while it is high, sharp and dark when it is down; it swells a little at the landing
    const near = 1 - s;
    const hit = ms >= FALL && ms < FALL + UP1 ? Math.sin(((ms - FALL) / UP1) * Math.PI) : 0;
    shadow.style.transform = `translate(${6 * s + 3}px, ${10 * s + 3}px) scaleX(${Math.max(0.02, c)}) scale(${1 + 0.05 * hit})`;
    shadow.style.filter = `blur(${2 + 20 * s}px)`;
    shadow.style.opacity = String(0.3 + 0.45 * near * near + 0.15 * hit);
  };
  frame(0);
  const t0 = performance.now();
  const tick = (now) => {
    if (over) return;
    const ms = now - t0;
    if (ms >= TOTAL) { end(); return; }
    frame(Math.max(0, ms));
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  setTimeout(end, TOTAL + 500); // a hidden tab draws no frames: the card is never left hidden
  ghost?.animate([{ opacity: 1 }, { opacity: 0 }], { delay: FALL, duration: 220, fill: "forwards" });
}

/**
 * An action: a pane slides in a short way from its side when `key` changes (a card whose item was swapped), or, with
 * `initial` and an `edge`, from that edge of the screen when it appears (unless a whole page is arriving: it slides it).
 */
export function swap(node, opts = {}) {
  let key = opts.key;
  let kept = null; // the card as it lies now, for the next one to fall on
  const keep = () => {
    const rect = node.isConnected ? node.getBoundingClientRect() : null;
    if (rect && rect.width > 80 && rect.height > 80) kept = { copy: node.cloneNode(true), rect };
  };
  if (opts.drop) for (const ms of [400, 1200, 2600, 5000]) setTimeout(() => { if (!kept) keep(); }, ms); // (the card may not be laid out yet)
  const slide = (o) => {
    if (still()) return;
    if (o.drop) {
      if (performance.now() - lastInput > 700) { kept = null; setTimeout(keep, 200); return; }
      drop(node, kept); kept = null; setTimeout(keep, 900); return;
    }
    if (o.peel && captured) { const c = captured; captured = null; peelCard(c); return; }
    if (o.edge) {
      const [dx, dy] = away(node.getBoundingClientRect(), o.edge);
      slideIn(node, dx, dy, { duration: 480 });
      smear(node, 2.5, { duration: 330 });
    } else {
      slideIn(node, 56, 0, { duration: 420 });
      node.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200, easing: "ease-out", fill: "backwards" });
      smear(node, 2, { duration: 300 });
    }
  };
  if (opts.initial && performance.now() > busyUntil) slide(opts);
  return {
    update(next) {
      if (next.key === key) return;
      key = next.key;
      slide(next);
    },
  };
}

