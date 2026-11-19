// Adds to README.md and every docs/readme/README.<code>.md: two pictures with captions at the end of the first screenshot table
// ("A look around"), a section of text under that table, and one bullet in "Good to know" (before the docs/pdf one).
//   node scripts/readme_add_section.mjs sections.json
// sections.json: { "README.md": { "PT": "Planets.", "PX": "caption text", "ST": "Settings.", "SX": "caption text",
//                                 "H": "### Heading", "PP": "paragraph", "B": "- **Bullet.** text" }, "README.de.md": {...}, ... }
// "{RU}" in a text becomes the Russian example name (so that its letters are not retyped). The picture names (site-planets.webp,
// site-settings.webp) are the PICTURES below: change them for another change. Refuses to run twice (looks for the first picture).
// See docs/UPDATING-README.md.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const APP = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PICTURES = ["site-planets.webp", "site-settings.webp"];
const RU = "Испорченный металл";
const tr = JSON.parse(readFileSync(process.argv[2], "utf8"));

for (const [name, t] of Object.entries(tr)) {
  const file = name === "README.md" ? `${APP}/README.md` : `${APP}/docs/readme/${name}`;
  const raw = readFileSync(file, "utf8");
  const eol = raw.includes("\r\n") ? "\r\n" : "\n";
  const lines = raw.split(/\r?\n/);
  if (raw.includes(PICTURES[0])) { console.log(name, "already done"); continue; }
  const tree = lines.findIndex((l) => l.includes("site-tree-picker.webp"));
  const end = lines.findIndex((l, i) => i > tree && l.trim() === "</table>");
  const pdf = lines.findIndex((l) => l.includes("docs/pdf"));
  if (tree < 0 || end < 0 || pdf < 0) throw new Error(`${name}: anchors`);
  const dir = /src="([^"]*\/)site-tree-picker\.webp"/.exec(lines[tree])[1]; // the folder of the pictures, as this file spells it
  const cell = (pic, title, text) => `    <td width="50%"><img src="${dir}${pic}" alt="${title.replace(/[.。]$/, "")}"><br><sub><b>${title}</b> ${text}</sub></td>`;
  const row = ["  <tr>", cell(PICTURES[0], t.PT, t.PX), cell(PICTURES[1], t.ST, t.SX), "  </tr>"];
  const fill = (s) => s.replaceAll("{RU}", RU);
  lines.splice(pdf, 0, fill(t.B));
  lines.splice(end + 1, 0, "", t.H, "", t.PP);
  lines.splice(end, 0, ...row);
  writeFileSync(file, lines.join(eol), "utf8");
  console.log(name, "ok");
}
