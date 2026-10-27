<script>
  // The books of a full cycle: what you hold before, after the turns, and the difference in things and in units,
  // then the stock after each run of the first turn, so every number can be followed by hand.
  import ItemIcon from "./ItemIcon.svelte";
  import Units from "./Units.svelte";
  import { fmtInt, fmtSigned, fmtTime } from "../lib/core.js";
  import { simulate } from "../lib/cycles.js";
  import { D, name, RECIPES } from "../lib/data.js";
  import { t } from "../lib/i18n.js";

  let { cycle, mult = 1, time = 0 } = $props();

  const sim = $derived(simulate(cycle, (i) => RECIPES[i], 1));
  const ids = $derived([...new Set([...sim.start.keys(), ...sim.end.keys()])]);
  const rows = $derived(ids.map((id) => ({ id, from: (sim.start.get(id) ?? 0) * mult, to: (sim.end.get(id) ?? 0) * mult, d: ((sim.end.get(id) ?? 0) - (sim.start.get(id) ?? 0)) * mult }))
    .sort((a, b) => b.d - a.d));
  const worth = (id, n) => n * (D.items[id]?.value ?? 0);
  const total = $derived(rows.reduce((s, r) => s + worth(r.id, r.d), 0));
  const signed = (n) => (n > 0 ? "+" : n < 0 ? "−" : "") + fmtInt(Math.abs(n));
</script>

<section class="ledger">
  <h3>{t("Profit")}{#if mult > 1}{" ×"}{mult}{/if}{#if time}{" · "}{fmtTime(time * mult)}{/if}</h3>
  <table>
    <thead><tr><th>{t("Item")}</th><th>{t("Before")}</th><th>{t("After")}</th><th>{t("Difference")}</th><th>{t("Units")}</th></tr></thead>
    <tbody>
      {#each rows as r (r.id)}
        <tr class:gain={r.d > 0} class:loss={r.d < 0}>
          <td><span class="who"><ItemIcon id={r.id} size={22} />{name(r.id)}</span></td>
          <td>{fmtInt(r.from)}</td><td>{fmtInt(r.to)}</td><td class="d">{signed(r.d)}</td>
          <td><Units size={13} />{fmtSigned(worth(r.id, r.d))}</td>
        </tr>
      {/each}
    </tbody>
    <tfoot><tr><td colspan="4">{t("Total at the items' prices")}</td><td class:gain={total > 0} class:loss={total < 0}><Units size={13} />{fmtSigned(total)}</td></tr></tfoot>
  </table>
  <p class="muted">{t("“Before” is the stock you started with. It comes back at the end of the turn, so only what you sold or threw away yourself can show a minus.")}</p>
  {#if sim.short}<p class="warn">{t("The order of runs does not add up: there is not enough stock.")}</p>{/if}

</section>

<style>
  .ledger { flex: none; width: 460px; padding: 10px 14px 14px; border-radius: 14px; background: var(--p-panel); border: 1px solid var(--p-outline); font-size: 0.88rem; }
  h3 { margin: 6px 0 8px; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--p-faint); }
  table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
  th { text-align: right; font-size: 0.72rem; color: var(--p-faint); font-weight: 600; padding: 2px 6px; }
  th:first-child, td:first-child { text-align: left; }
  td { padding: 5px 6px; text-align: right; border-top: 1px solid var(--p-outline); white-space: nowrap; }
  tfoot td { font-weight: 700; }
  tfoot td:first-child { text-align: left; }
  .who { display: inline-flex; align-items: center; gap: 6px; }
  .gain .d, td.gain, .gain td:last-child { color: var(--p-green); font-weight: 700; }
  .loss .d, td.loss, .loss td:last-child { color: var(--p-red); font-weight: 700; }
  .muted { color: var(--p-muted); font-size: 0.8rem; margin: 8px 0 0; }
  .warn { color: var(--p-red); font-weight: 700; }
  ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
  li { display: grid; gap: 2px; padding: 6px 8px; border-radius: 8px; background: var(--p-raised); }
  li .stock { color: var(--p-muted); font-size: 0.8rem; }
  li.s0 > span:first-child { font-weight: 700; }
</style>



