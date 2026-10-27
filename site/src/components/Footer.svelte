<script>
  // One slim line of credit. `markdown` and `release` are kept for App.svelte's call.
  import { t } from "../lib/i18n.js";
  let { markdown = "llms.txt", release = null } = $props();
</script>

<footer class="foot">
  <span>{t("Data, names and icons come from the game files")}{#if release}: {release.name}, {t("build {build}", { build: release.build.replace("build ", "") })}{/if}. {t("No Man's Sky belongs to Hello Games.")}</span>
  <span>{t("Project")} <a href="https://github.com/rdlu/nms-items-interface" target="_blank" rel="noopener">NMSii</a> · Rodrigo Dlugokenski</span>
</footer>

<style>
  .foot {
    flex: none; display: flex; flex-wrap: nowrap; justify-content: space-between; align-items: center; gap: 24px;
    height: 36px; padding: 0 var(--gutter);
    border-top: 1px solid var(--p-outline); background: var(--p-panel);
    font-size: 0.78rem; color: var(--p-faint); white-space: nowrap; overflow: hidden;
  }
  .foot span { overflow: hidden; text-overflow: ellipsis; }
  .foot a { color: inherit; }
</style>
