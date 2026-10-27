<script>
  // Three ways to run the terminal app, from the least installed to the most.
  // Shown on the start page and in Help; the README says the same at more
  // length.
  import { REPO_URL } from "../lib/data.js";
  import PaneHeading from "./PaneHeading.svelte";
</script>

<div class="install">
  <section class="pane">
    <PaneHeading title="podman / docker" note="nothing else to install" />
    <p>The app and its Python live in a container. Saved addresses still land in the checkout.</p>
    <pre><code>git clone https://github.com/rdlu/nms-items-interface
cd nms-items-interface
podman compose run --rm tui</code></pre>
    <p class="muted small">This site, offline: <code>podman compose up site</code>, then <code>localhost:8001</code>. Docker reads the same <code>compose.yaml</code>.</p>
  </section>
  <section class="pane">
    <PaneHeading title="uv" note="one tool, it fetches Python" />
    <p><a href="https://docs.astral.sh/uv/">uv</a> downloads the right Python and the one dependency, Textual, on the first run.</p>
    <pre><code>git clone https://github.com/rdlu/nms-items-interface
cd nms-items-interface
uv run nms</code></pre>
    <p class="muted small">Python 3.11 or newer. Any terminal with 256 colours; truecolor looks best.</p>
  </section>
  <section class="pane">
    <PaneHeading title="mise" note="to work on it" />
    <p><a href="https://mise.jdx.dev/">mise</a> pins uv and Typst and carries every task: tests, the PDF, this site, a data refresh.</p>
    <pre><code>mise install
mise run sync
mise run tui</code></pre>
    <p class="muted small"><code>mise tasks</code> lists them all; the <a href="{REPO_URL}#tasks">README</a> explains each.</p>
  </section>
</div>

<style>
  .install { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }
  @media (max-width: 1000px) { .install { grid-template-columns: minmax(0, 1fr); } }
  .pane { background: var(--p-panel); border: 1px solid var(--p-outline); padding: 4px 18px 14px; min-width: 0; }
  .pane p { font-size: 0.92rem; line-height: 1.6; color: var(--p-muted); }
  pre {
    margin: 10px 0;
    padding: 10px 12px;
    overflow-x: auto;
    background: var(--p-bg);
    border: 1px solid var(--p-outline);
    border-left: 2px solid var(--p-edge-accent);
    font-family: var(--p-mono);
    font-size: 0.85rem;
    line-height: 1.6;
    color: var(--p-text);
  }
  pre code { font-size: inherit; }
  /* Inside Help's card the panes invert, so they still stand out. */
  :global(.card) .pane { background: var(--p-bg); }
  :global(.card) .pane pre { background: var(--p-panel); }
</style>


