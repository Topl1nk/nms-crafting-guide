// NMSii on the web: the TUI's screens as pages over data.json.
//
// App.svelte is the frame (header, view, footer); one component per view in
// views/, shared pieces in components/, and the logic that is not about
// drawing in lib/ -- lib/core.js above all, which tests/test_web.py runs under
// node against the Python it mirrors.

// The global skin first, so a component's own rules win over it.
import "./global.css";
import "./app.css"; // the friendlier skin, over the original one
import "./velvet.css"; // the cloth every surface is cut from
import { mount } from "svelte";
import App from "./App.svelte";
import { startPwa } from "./lib/pwa.svelte.js";
import { applyLook } from "./lib/theme.js";

applyLook();
// The textures of the velvet are web/pile.webp and web/suede.webp. A var holding a relative url is read against the stylesheet
// (in assets/), so the addresses are made whole here.
for (const name of ["pile", "suede"]) document.documentElement.style.setProperty(`--${name}`, `url("${new URL(`${name}.webp`, document.baseURI).href}")`);

const target = document.getElementById("app");
target.replaceChildren(); // the "Loading…" line index.html shows until now
mount(App, { target });
// The service worker (a build only), the install prompt, online/offline.
startPwa();




