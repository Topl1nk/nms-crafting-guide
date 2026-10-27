// The glow behind a picture is the item's own colour, but it must be seen on the surface it lies on: a dark item on a light panel is a dark
// smudge, a light one on a dark panel is a hole. So the glow's lightness is kept a set distance (--icon-gap, a lightness in 0..1) away from
// the lightness of the panel, to whichever side the item already is; the hue and the saturation stay the item's own. Nothing to tune per item.
const BASE = [0x5b, 0x73, 0xa7]; // what the item's colour is mixed with: the blue-grey of the game's glow
let seen = { key: "", panel: 0.1, gap: 0.3 };

const hsl = ([r, g, b]) => {
  r /= 255; g /= 255; b /= 255;
  const hi = Math.max(r, g, b), lo = Math.min(r, g, b), l = (hi + lo) / 2, d = hi - lo;
  if (!d) return [0, 0, l];
  const s = d / (1 - Math.abs(2 * l - 1));
  const h = hi === r ? ((g - b) / d + (g < b ? 6 : 0)) : hi === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h * 60, s, l];
};
const rgb = ([h, s, l]) => {
  const c = (1 - Math.abs(2 * l - 1)) * s, x = c * (1 - Math.abs(((h / 60) % 2) - 1)), m = l - c / 2;
  const [r, g, b] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
  return [r + m, g + m, b + m].map((v) => Math.round(v * 255));
};
const parse = (hex) => { const m = /^#?([0-9a-f]{6})/i.exec(hex.trim()); return m ? [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16)) : null; };

/** What the page's surface is: the lightness of --p-panel and the gap asked for, read again whenever the theme changes. */
function surface() {
  const root = document.documentElement;
  const key = root.dataset.theme + "|" + getComputedStyle(root).getPropertyValue("--p-panel");
  if (key !== seen.key) {
    const cs = getComputedStyle(root);
    const panel = parse(cs.getPropertyValue("--p-panel")) ?? [20, 29, 58];
    seen = { key, panel: hsl(panel)[2], gap: parseFloat(cs.getPropertyValue("--icon-gap")) || 0.3 };
  }
  return seen;
}

/** The glow colour for an item colour `hex` (mixed `tone` of it with the base), fitted to the surface. */
export function glow(hex, tone = 0.62) {
  const c = parse(hex || "");
  if (!c) return "#5b73a7";
  const mix = c.map((v, i) => v * tone + BASE[i] * (1 - tone));
  const [h, s, l] = hsl(mix);
  const { panel, gap } = surface();
  const fit = panel < 0.5 ? Math.max(l, Math.min(0.85, panel + gap)) : Math.min(l, Math.max(0.15, panel - gap));
  const [r, g, b] = rgb([h, fit === l ? s : Math.min(1, s * 1.08), fit]);
  return `rgb(${r} ${g} ${b})`;
}
