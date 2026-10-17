<script>
  // Who made it, as plugii's and the dotfiles' footers say it; then what it
  // stands on, as a second command -- and where the page in view is as
  // markdown (`markdown`, from lib/markdown.js).
  // `release` is lib/data.js's gameRelease(), once data.json is in.
  let { markdown = "llms.txt", release = null } = $props();

  // © 2026, or 2026-now once it is later: plugii's footer does the same.
  const year = new Date().getFullYear();
  const years = year > 2026 ? `2026–${year}` : "2026";
</script>

<footer class="foot">
  <div class="foot-in">
    <section class="whoami">
      <div class="prompt">$ whoami</div>
      <div><span class="me">Rodrigo Dlugokenski</span> <span class="dim">— Rio de Janeiro / Porto Alegre, Brazil</span></div>
      <div>
        <a href="https://r.dlu.one" target="_blank" rel="noopener me">r.dlu.one</a><span class="dim">{" · "}</span>
        <a href="https://github.com/rdlu" target="_blank" rel="noopener me">github.com/rdlu</a><span class="dim">{" · "}</span>
        <a href="https://bsky.app/profile/r.dlu.one" target="_blank" rel="noopener me">bsky @r.dlu.one</a><span class="dim">{" · "}</span>
        <a href="https://programming.dev/u/rdlu" target="_blank" rel="noopener me">programming.dev/u/rdlu</a>
      </div>
      <div class="dim">© {years} Rodrigo Dlugokenski · No Man's Sky Items Interface is <a href="https://github.com/rdlu/nms-items-interface/blob/main/LICENSE" target="_blank" rel="noopener">GPL-3.0 licensed</a></div>
    </section>
    <section class="whoami">
      <div class="prompt">$ cat CREDITS</div>
      {#if release}
        <div>Recipes and items read from the game files, {release.name}{#if release.build}{" "}(build {release.build}){/if}</div>
      {:else}
        <div>Recipes and items from the game's tables via <a href="https://github.com/ApexFatality93/NMS-Handbook" target="_blank" rel="noopener">NMS-Handbook</a></div>
      {/if}
      <div>Portal glyphs traced from <a href="https://nmsportals.github.io/" target="_blank" rel="noopener">nmsportals</a></div>
      <div>Cheat sheet for <a href="pdf/nms-cheatsheet.pdf">print</a><span class="dim">{" · "}</span><a href="pdf/nms-cheatsheet-dark.pdf">screen</a><span class="dim">{" · "}</span><a href="https://github.com/rdlu/nms-items-interface" target="_blank" rel="noopener">source</a></div>
      <div>AI friendly: <a id="md-page" href={markdown}>this page as markdown</a><span class="dim">{" · "}</span><a href="llms.txt">llms.txt</a><span class="dim">{" · "}</span><a href="md/items/index.md">every item</a></div>
      <div class="dim">No Man's Sky and its data belong to Hello Games</div>
    </section>
  </div>
</footer>

<style>
  /* plugii's `$ whoami`, and the credits as a second command, on the page's
     own grid. */
  .foot {
    border-top: 1px solid var(--p-outline);
    background: var(--p-panel);
    padding-bottom: env(safe-area-inset-bottom);
  }
  .foot-in {
    max-width: var(--wrap);
    margin: 0 auto;
    padding: 2rem var(--gutter) 2.5rem;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, max-content));
    gap: 1.5rem 4rem;
  }
  @media (max-width: 900px) { .foot-in { grid-template-columns: minmax(0, 1fr); } }
  .whoami { font-family: var(--p-mono); font-size: 0.8125rem; line-height: 1.7; color: var(--p-muted); min-width: 0; }
  .prompt { color: var(--p-accent); }
  .me { color: var(--p-text); font-weight: 700; }
  .dim { color: var(--p-faint); }
  .whoami a { white-space: nowrap; color: inherit; text-decoration: underline; text-underline-offset: 3px; text-decoration-thickness: 1px; }
  .whoami a:hover { color: var(--p-accent); }
</style>
