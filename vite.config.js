// The site's build: Svelte source in site/, everything served as-is in web/,
// the page that gets deployed in dist/.
//
// web/ is Vite's public directory, copied into dist/ untouched. It holds what
// is not code -- fonts, favicons -- and what scripts/build_web.py writes:
// data.json, the PDFs, the screenshots, and anything else it adds later. So
// the Python export keeps writing where it always has, and whatever lands in
// web/ ships, without this file having to list it.

import { createHash } from "node:crypto";
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, relative, resolve, sep } from "node:path";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";

// What the service worker stores at install, so the installed app opens with
// no signal: the page, its hashed bundle, data.json, the fonts it preloads or
// draws with, and the icons. Not md/, pdf/ or img/ (megabytes, most of it
// never opened): site/sw.js keeps those as they are visited.
const PRECACHE = [
  /^index\.html$/,
  /^assets\//,
  /^data\.json$/,
  /^(pile|suede)\.webp$/,
  /^fonts\/.*\.woff2$/,
  /^(favicon\.(svg|ico)|apple-touch-icon\.png|icon-[\w-]+\.png|manifest\.webmanifest)$/,
];

function* walk(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(path);
    else yield path;
  }
}

// Writes dist/sw.js once the build is out: site/sw.js with the precache list
// and a version above it. The version hashes every precached file, so a new
// bundle or new data makes a new worker, and nothing else does. Build only:
// `vite dev` never registers a worker (site/src/lib/pwa.svelte.js).
function serviceWorker() {
  let outDir;
  return {
    name: "nmsii-service-worker",
    apply: "build",
    configResolved(config) { outDir = resolve(config.root, config.build.outDir); },
    closeBundle() {
      const files = [...walk(outDir)]
        .map((path) => relative(outDir, path).split(sep).join("/"))
        .filter((path) => PRECACHE.some((re) => re.test(path)))
        .sort();
      const hash = createHash("sha256");
      for (const path of files) hash.update(path).update("\0").update(readFileSync(join(outDir, path)));
      const version = hash.digest("hex").slice(0, 12);
      const worker = readFileSync(new URL("site/sw.js", import.meta.url), "utf-8");
      writeFileSync(join(outDir, "sw.js"),
        `const VERSION = ${JSON.stringify(version)};\nconst PRECACHE = ${JSON.stringify(files, null, 1)};\n\n${worker}`);
      this.info?.(`sw.js: ${files.length} files precached, version ${version}`);
    },
  };
}

export default defineConfig({
  root: "site",
  publicDir: "../web",
  // Relative, so dist/ works from any path: nmsii.dlu.one, the container, or
  // a subdirectory on someone's own server.
  base: "./",
  plugins: [svelte(), serviceWorker()],
  build: {
    outDir: "../dist",
    emptyOutDir: true,
  },
  // Ports clear of `mise run web` (8000) and the container (8001); loopback
  // only, as the old `mise run site` served it.
  server: { host: "127.0.0.1", port: 8790, strictPort: true },
  preview: { host: "127.0.0.1", port: 8791, strictPort: true },
});


