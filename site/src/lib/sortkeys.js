// Orders of items for the sort lists of the pages (Tree, Craft): each compares two item ids, so a page that sorts
// recipes passes the id of what a recipe makes.

import { D } from "./data.js";
import { collate } from "./i18n.js";
import { rarityRank, typeLabel } from "./words.js";

/** [hue 0-360, saturation 0-1, lightness 0-1] of "#rrggbb"; null when the item has no colour. */
function hsl(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex ?? "");
  if (!m) return null;
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16) / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  if (!d) return [0, 0, l];
  const s = d / (1 - Math.abs(2 * l - 1));
  const h = max === r ? ((g - b) / d + (g < b ? 6 : 0)) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h * 60, s, l];
}

/** By the colour of the item's glow: the colours round the wheel, then the greys from light to dark; no colour last. */
export function byColor(a, b) {
  const x = hsl(D.items[a]?.color);
  const y = hsl(D.items[b]?.color);
  if (!x || !y) return (x ? 0 : 1) - (y ? 0 : 1);
  const gx = x[1] < 0.15;
  const gy = y[1] < 0.15;
  if (gx !== gy) return gx - gy;
  return gx ? y[2] - x[2] : Math.round(x[0] / 12) - Math.round(y[0] / 12) || y[1] - x[1];
}
/** By the kind of thing it is, in the words the page shows. */
export const byType = (a, b) => collate(typeLabel(D.items[a]?.type) || "￿", typeLabel(D.items[b]?.type) || "￿");
/** The rarest first. */
export const byRarity = (a, b) => rarityRank(D.items[b]?.rar) - rarityRank(D.items[a]?.rar);
/** The strongest effect first. */
export const byPotency = (a, b) => (D.items[b]?.potency ?? 0) - (D.items[a]?.potency ?? 0);
