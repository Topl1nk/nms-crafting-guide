#!/usr/bin/env node
// Checks that a built dist/ is an installable, offline-capable app, so a build
// that would quietly stop installing, or a worker that would fail its install
// over a missing file, never deploys. Runs after every `npm run build` (the
// package.json postbuild): CI, the Pages workflow, the pre-push hook and
// `mise run web:build` all build that way. tests/test_web.py runs it too.
//
//   node scripts/check_pwa.mjs [dist]
//
// The manifest: the fields an install needs, every icon and screenshot there
// at the size it states, start_url and the shortcuts inside the scope. The
// worker: sw.js at the root, and its precache list naming files that exist,
// covering the page and everything the page loads first, and nothing that
// sw.js is meant to cache on demand instead.

import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

const dist = process.argv[2] ?? "dist";
const errors = [];
const fail = (msg) => errors.push(msg);
const ORIGIN = "https://nmsii.invalid/"; // a stand-in root to resolve URLs against
const file = (url) => {
  const u = new URL(url);
  return u.origin === new URL(ORIGIN).origin ? decodeURIComponent(u.pathname.slice(1)) : null;
};

// [width, height] of a PNG or WebP, from its header.
function dimensions(path) {
  const b = readFileSync(path);
  if (b.subarray(1, 4).toString() === "PNG") return [b.readUInt32BE(16), b.readUInt32BE(20)];
  if (b.subarray(0, 4).toString() === "RIFF" && b.subarray(8, 12).toString() === "WEBP") {
    const chunk = b.subarray(12, 16).toString();
    if (chunk === "VP8X") return [b.readUIntLE(24, 3) + 1, b.readUIntLE(27, 3) + 1];
    if (chunk === "VP8 ") return [b.readUInt16LE(26) & 0x3fff, b.readUInt16LE(28) & 0x3fff];
    if (chunk === "VP8L") {
      const bits = b.readUInt32LE(21);
      return [(bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1];
    }
  }
  return null;
}

function* walk(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(path);
    else yield relative(dist, path).split(sep).join("/");
  }
}

if (!existsSync(join(dist, "index.html"))) {
  console.error(`check_pwa: no ${dist}/index.html; build first (npm run build)`);
  process.exit(1);
}
const html = readFileSync(join(dist, "index.html"), "utf-8");

// -- the manifest

const link = html.match(/<link rel="manifest" href="([^"]+)"/);
let manifest = {};
let manifestUrl = ORIGIN;
if (!link) fail("index.html has no <link rel=\"manifest\">");
else {
  manifestUrl = new URL(link[1], ORIGIN).href;
  const path = join(dist, file(manifestUrl) ?? "");
  if (!existsSync(path)) fail(`the manifest ${link[1]} is not in ${dist}/`);
  else {
    try {
      manifest = JSON.parse(readFileSync(path, "utf-8"));
    } catch (exc) {
      fail(`the manifest is not JSON: ${exc.message}`);
    }
  }
}

for (const key of ["name", "short_name", "description", "start_url", "scope", "display", "theme_color", "background_color"]) {
  if (typeof manifest[key] !== "string" || !manifest[key]) fail(`manifest: no ${key}`);
}
if (manifest.short_name && manifest.short_name.length > 12) fail(`manifest: short_name "${manifest.short_name}" is over 12 characters, launchers cut it`);
if (manifest.display && !["standalone", "fullscreen", "minimal-ui"].includes(manifest.display)) {
  fail(`manifest: display "${manifest.display}" does not install as an app`);
}
const scope = new URL(manifest.scope ?? ".", manifestUrl).href;
// The site is served from the domain root, and the worker's scope is too.
if (scope !== ORIGIN) fail(`manifest: scope resolves to ${scope}, not the site root`);
const inScope = (url, what) => {
  const abs = new URL(url, manifestUrl).href;
  if (!abs.startsWith(scope)) fail(`manifest: ${what} ${url} is outside the scope ${manifest.scope}`);
};
if (manifest.start_url) inScope(manifest.start_url, "start_url");

// An image the manifest names, there at the size it says.
function image(entry, what) {
  const path = file(new URL(entry.src, manifestUrl).href);
  if (!path || !existsSync(join(dist, path))) return fail(`manifest: ${what} ${entry.src} is not in ${dist}/`);
  if (entry.sizes === "any") return path;
  const got = dimensions(join(dist, path));
  if (!got) return fail(`manifest: ${what} ${entry.src} is neither PNG nor WebP`);
  if (!entry.sizes?.split(" ").includes(`${got[0]}x${got[1]}`)) {
    fail(`manifest: ${what} ${entry.src} says ${entry.sizes} but is ${got[0]}x${got[1]}`);
  }
  return path;
}

const icons = manifest.icons ?? [];
const iconFiles = icons.map((icon) => image(icon, "icon")).filter(Boolean);
const purposes = (icon) => (icon.purpose ?? "any").split(" ");
for (const size of ["192x192", "512x512"]) {
  if (!icons.some((i) => i.sizes === size && i.type === "image/png" && purposes(i).includes("any"))) {
    fail(`manifest: no ${size} PNG icon for purpose "any"`);
  }
}
if (!icons.some((i) => i.sizes === "512x512" && purposes(i).includes("maskable"))) fail("manifest: no 512x512 maskable icon");

for (const shortcut of manifest.shortcuts ?? []) {
  if (!shortcut.name || !shortcut.url) fail(`manifest: a shortcut without a name or url: ${JSON.stringify(shortcut)}`);
  else inScope(shortcut.url, `shortcut ${shortcut.name}`);
  for (const icon of shortcut.icons ?? []) image(icon, `shortcut ${shortcut.name} icon`);
}
for (const shot of manifest.screenshots ?? []) image(shot, "screenshot");

// -- the service worker

const worker = join(dist, "sw.js");
let precache = [];
if (!existsSync(worker)) fail(`no ${dist}/sw.js, so nothing works offline`);
else {
  const sw = readFileSync(worker, "utf-8");
  if (!/^const VERSION = "[0-9a-f]{12}";$/m.test(sw)) fail("sw.js: no VERSION line");
  const list = sw.match(/^const PRECACHE = (\[[\s\S]*?\]);$/m);
  if (!list) fail("sw.js: no PRECACHE list");
  else precache = JSON.parse(list[1]);
}
const bundles = readdirSync(join(dist, "assets")).filter((f) => f.endsWith(".js"));
if (!bundles.some((f) => /serviceWorker\.register\(\s*["'`]\.\/sw\.js/.test(readFileSync(join(dist, "assets", f), "utf-8")))) {
  fail("no bundle registers ./sw.js");
}

if (new Set(precache).size !== precache.length) fail("sw.js: PRECACHE lists a file twice");
for (const path of precache) {
  if (!existsSync(join(dist, path)) || !statSync(join(dist, path)).isFile()) fail(`sw.js: precaches ${path}, which is not in ${dist}/`);
  if (/^(md|pdf|img|screenshots)\//.test(path)) fail(`sw.js: precaches ${path}, which it should cache on demand`);
}
const cached = new Set(precache);
const must = new Set(["index.html", "data.json", file(manifestUrl), ...iconFiles]);
for (const path of walk(dist)) if (path.startsWith("assets/")) must.add(path);
// Everything index.html loads by itself: the bundle, the preloaded fonts, the icons.
for (const [, href] of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
  const path = file(new URL(href, ORIGIN).href);
  if (path && !/\.(txt|md)$/.test(path)) must.add(path);
}
for (const path of must) if (path && !cached.has(path)) fail(`sw.js: does not precache ${path}`);

if (errors.length) {
  console.error(`check_pwa: ${dist}/ is not an installable offline app:\n${errors.map((e) => `  - ${e}`).join("\n")}`);
  process.exit(1);
}
console.log(`check_pwa: manifest ok (${icons.length} icons, ${manifest.shortcuts?.length ?? 0} shortcuts, ${manifest.screenshots?.length ?? 0} screenshots), sw.js precaches ${precache.length} files`);
