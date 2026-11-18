// Dates and times as the person's system writes them (the desktop program reads Windows' short date and time patterns,
// /api/formats): 18.11.26, 11/18/26, 26-11-18 - the order and the separators are the system's, never a month's name. The
// day and the month have two digits, the year two. Where the system says nothing (a plain browser) the browser's own locale
// orders the same numbers.

let pattern = { date: "", time: "" };

/** Ask the desktop program for the system's patterns; a page without it keeps the browser's. */
export async function loadFormats() {
  try {
    const res = await fetch("api/formats", { cache: "no-store" });
    if (res.ok) pattern = await res.json();
  } catch { /* no desktop program: the browser's locale */ }
}

const two = (n) => String(n).padStart(2, "0");

// The letters of a Windows pattern (d, M, y, h, H, m, s, t) swapped for the parts of the date; everything else is a separator.
function paint(format, d) {
  return format.replace(/d+|M+|y+|h+|H+|m+|s+|t+/g, (tok) => {
    switch (tok[0]) {
      case "d": return two(d.getDate());
      case "M": return two(d.getMonth() + 1);
      case "y": return two(d.getFullYear() % 100);
      case "H": return two(d.getHours());
      case "h": return two(d.getHours() % 12 || 12);
      case "m": return two(d.getMinutes());
      case "s": return two(d.getSeconds());
      default: return d.getHours() < 12 ? "AM" : "PM";
    }
  });
}

const own = (d, time) => {
  const f = new Intl.DateTimeFormat(undefined, time ? { hour: "2-digit", minute: "2-digit" } : { day: "2-digit", month: "2-digit", year: "2-digit" });
  return f.format(d);
};

/** 11/18/26 for a time in milliseconds ("" for none). */
export const fmtDate = (ms) => (ms ? (pattern.date ? paint(pattern.date, new Date(ms)) : own(new Date(ms), false)) : "");
/** 6:03 PM for a time in milliseconds. */
export const fmtTime = (ms) => (ms ? (pattern.time ? paint(pattern.time, new Date(ms)) : own(new Date(ms), true)) : "");
/** 11/18/26 6:03 PM. */
export const fmtStamp = (ms) => (ms ? `${fmtDate(ms)} ${fmtTime(ms)}` : "");
/** A date kept as 2026-11-18 (the saved portal addresses), as the system writes it. */
export const fmtIso = (iso) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso ?? "");
  return m ? fmtDate(new Date(+m[1], +m[2] - 1, +m[3]).getTime()) : iso ?? "";
};
