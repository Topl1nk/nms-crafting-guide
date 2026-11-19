// A few of the game's item texts are templates the game fills in while it plays: a companion egg is "%NAME%'s Genetic Material"
// and "... %SIZE% and %TRAIT%", a salvaged fleet unit "salvaged from %NAME%". There is nothing to fill them with here, and the
// marks are not to be shown. The subtitle loses the mark (and the "'s" of the English possessive); a description loses the part of
// a sentence it stood in: back to the last comma before it ("A living, fertile egg, %READY%" is "A living, fertile egg."), and a
// sentence with no comma before it goes whole. The same rule serves every language, which only needs commas and full stops.

const MARK = /%[A-Za-z_]+%/;
const MARKS = /%[A-Za-z_]+%(?:['’]s)?/g;
const COMMAS = [",", "，", "、"];

/** A subtitle without the game's template marks. */
export function cleanSub(text) {
  if (!text || !MARK.test(text)) return text;
  const out = text.replace(MARKS, "").replace(/^[\s:,;.\-–—]+|[\s:,;\-–—]+$/g, "").replace(/\s{2,}/g, " ");
  return out.charAt(0).toUpperCase() + out.slice(1);
}

/** A description without the sentences (or the ends of sentences) that hold the game's template marks. */
export function cleanDesc(text) {
  if (!text || !MARK.test(text)) return text;
  const lines = text.split("\n").map((line) => {
    const kept = [];
    for (const sentence of line.split(/(?<=[.!?。！？])\s*/)) {
      const at = sentence.search(MARK);
      if (at < 0) { if (sentence.trim()) kept.push(sentence.trim()); continue; }
      const cut = Math.max(...COMMAS.map((c) => sentence.lastIndexOf(c, at)));
      if (cut > 0) kept.push(`${sentence.slice(0, cut).trim()}${/[぀-ヿ㐀-鿿]/.test(sentence) ? "。" : "."}`);
    }
    return kept.join(" ");
  });
  return lines.join("\n").replace(/\n{3,}/g, "\n\n").replace(/^\n+|\n+$/g, "");
}
