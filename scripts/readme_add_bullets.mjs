// Adds a bullet (or more) to README.md and every docs/readme/README.<code>.md, at the anchors docs/UPDATING-README.md names.
//   node scripts/readme_add_bullets.mjs bullets.json
// bullets.json: { "README.md": { "P": "- 🪐 **Title.** text"  (after the portals bullet),
//                                "T": " text"  (appended to the privacy bullet),
//                                "S": "- **...**", "U": "- **...**"  (two "Good to know" bullets, before the docs/pdf one) }, "README.de.md": {...}, ... }
// Leave out a key to add nothing there (the script skips none today: edit it if only some are wanted). It also puts the right emoji
// on the multi-tools, languages and privacy bullets of the translations. It stops if a file already has a 🪐 bullet, so run it once
// per change, from a clean tree (git diff shows what it did).import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const APP = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const tr = JSON.parse(readFileSync(process.argv[2], "utf8"));
for (const [name, t] of Object.entries(tr)) {
  const file = name === "README.md" ? `${APP}/README.md` : `${APP}/docs/readme/${name}`;
  const raw = readFileSync(file, "utf8");
  const eol = raw.includes("\r\n") ? "\r\n" : "\n";
  const lines = raw.split(/\r?\n/);
  const portals = lines.findIndex((l) => l.startsWith("- 🔭"));
  const pdf = lines.findIndex((l) => l.includes("docs/pdf"));
  if (portals < 0 || pdf < 0) throw new Error(`${name}: anchors`);
  if (lines.some((l) => l.startsWith("- 🪐"))) { console.log(name, "already done"); continue; }
  // the languages line and the privacy line sit two and three lines under the portals one; some translations lost their emoji
  const fix = (i, emoji) => { lines[i] = lines[i].replace(/^- [^*]*\*\*/, `- ${emoji} **`); };
  if (name !== "README.md" && name !== "README.ru.md") { fix(portals + 1, "⚔️"); fix(portals + 2, "🌍"); fix(portals + 3, "🔒"); }
  lines[portals + 3] += t.T;
  lines.splice(pdf, 0, t.S, t.U);
  lines.splice(portals + 1, 0, t.P);
  writeFileSync(file, lines.join(eol), "utf8");
  console.log(name, "ok", lines[portals + 4].slice(0, 40), "|", lines[portals + 5].slice(0, 40));
}
