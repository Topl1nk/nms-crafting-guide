<script>
  // The game's own sign for units, the currency: every price and profit on the site is in these.
  // Put it before a number, as the game does (<Units />{fmtInt(n)}).
  import { t } from "../lib/i18n.js";
  let { size = 16 } = $props();
  let missing = $state(false); // the game's picture is not there (a build without the game's files): a plain coin stands for it
</script>

{#if missing}
  <span class="units coin" role="img" aria-label={t("units")} title={t("units")} style="width:{size}px; height:{size}px"></span>
{:else}
  <img class="units" src="icons/UNITS.webp" alt={t("units")} title={t("units")} width={size} height={size} draggable="false" onerror={() => { missing = true; }}>
{/if}

<style>
  .coin { box-sizing: border-box; border: 2px solid currentColor; border-radius: 50%; opacity: 0.85; }
  .units { display: inline-block; flex: none; vertical-align: middle; margin-right: 0.2em; -webkit-user-drag: none; user-select: none; }
</style>
