// The site's build: Svelte source in site/, everything served as-is in web/,
// the page that gets deployed in dist/.
//
// web/ is Vite's public directory, copied into dist/ untouched. It holds what
// is not code -- fonts, favicons -- and what scripts/build_web.py writes:
// data.json, the PDFs, the screenshots, and anything else it adds later. So
// the Python export keeps writing where it always has, and whatever lands in
// web/ ships, without this file having to list it.

import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";

export default defineConfig({
  root: "site",
  publicDir: "../web",
  // Relative, so dist/ works from any path: nmsii.dlu.one, the container, or
  // a subdirectory on someone's own server.
  base: "./",
  plugins: [svelte()],
  build: {
    outDir: "../dist",
    emptyOutDir: true,
  },
  // Ports clear of `mise run web` (8000) and the container (8001); loopback
  // only, as the old `mise run site` served it.
  server: { host: "127.0.0.1", port: 8790, strictPort: true },
  preview: { host: "127.0.0.1", port: 8791, strictPort: true },
});
