// The game's pictures, installed from the player's own game by the local launcher (tools/launch.py -> tools/pictures.py) with one
// press. A page on a plain static host has no launcher: `available` stays false and nothing is offered.

export const pictures = $state({ available: false, game: "", have: 0, saves: 0, state: "idle", step: "", done: 0, total: 0, error: "" });

async function look() {
  const res = await fetch("api/pictures", { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status}`);
  Object.assign(pictures, await res.json(), { available: true });
}

/** Ask the launcher whether it is there, and what it has. */
export async function probePictures() {
  try { await look(); } catch { pictures.available = false; }
}

let polling = 0;

/** Begin the installation and follow it; the page reloads when the pictures are there. */
export async function installPictures() {
  if (pictures.state === "running") return;
  try {
    const res = await fetch(`api/pictures/install${pictures.have ? "?force=1" : ""}`, { method: "POST" });
    if (!res.ok) throw new Error(`${res.status}`);
  } catch (exc) {
    pictures.state = "error";
    pictures.error = `${exc.message}`;
    return;
  }
  pictures.state = "running";
  clearInterval(polling);
  polling = setInterval(async () => {
    try { await look(); } catch { return; }
    if (pictures.state === "done") { clearInterval(polling); setTimeout(() => location.reload(), 600); }
    else if (pictures.state === "error") clearInterval(polling);
  }, 700);
}
