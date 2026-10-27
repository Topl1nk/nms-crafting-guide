<script module>
  import { N_ } from "../lib/i18n.js";

  const MT_TABS = [["types", N_("Types")], ["weapons", N_("Weapons")], ["getting", N_("Where to get")], ["tips", N_("Tips")]]; // English keys for t()
</script>

<script>
  // Multi-tools in four tabs (#/multitools?tab=): two tables, two pages of
  // cards, all from data/multitools.json.
  import List from "../components/List.svelte";
  import { D } from "../lib/data.js";
  import { t } from "../lib/i18n.js";
  import { setKeys } from "../lib/keys.js";
  import { arrival } from "../lib/router.svelte.js";

  const { params } = arrival();

  const mt = D.multitools;
  // "+15-20%" -> 15, "9-18" -> 9, "2 170" -> 2170: the first number is the sort key.
  const num = (text) => Number(String(text).replace(/\s/g, "").match(/-?\d[\d.,]*/)?.[0].replace(",", ".") ?? -1);
  const tab = MT_TABS.some(([k]) => k === params.get("tab")) ? params.get("tab") : "types";
  let cur = $state.raw(null);
  let list = $state();

  setKeys({ get list() { return list; } });
</script>

{#snippet procedure(p)}
  <section class="card"><h3>{t(p.title)}</h3>
    <ol>{#each p.steps as s}<li>{t(s)}</li>{/each}</ol>
    {#if p.note}<p class="muted">{t(p.note)}</p>{/if}
    {#if (p.after || []).length}<ul>{#each p.after as s}<li>{t(s)}</li>{/each}</ul>{/if}
  </section>
{/snippet}

<div class="fbar">
  <h1><span>{t("Multi-tools")}</span></h1>
  <nav class="tabs">
    {#each MT_TABS as [k, label] (k)}<a href="#/multitools?tab={k}" class:on={k === tab}>{t(label)}</a>{/each}
  </nav>
  <a class="btn" style="margin-left:auto" href="#/portals?kind=multi-tool">{t("Where they lie: portal addresses")}</a>
</div>
<div class="count headline">{t(mt._headline)}</div>
<div class="tab">
  {#if tab === "types"}
    <List bind:this={list} rows={mt.types} onSelect={(row) => { cur = row; }} columns={[
      { title: t("Kind"), text: (row) => t(row.type), cls: "strong", sort: (row) => row.type },
      { title: t("Damage"), text: (row) => t(row.damage), sort: (row) => num(row.damage) },
      { title: t("Mining"), text: (row) => t(row.mining), sort: (row) => num(row.mining) },
      { title: t("Scan"), text: (row) => t(row.scan), sort: (row) => num(row.scan) },
      { title: t("Slots"), text: (row) => t(row.slots), sort: (row) => num(row.slots) },
      { title: t("Notes"), text: (row) => t(row.note), cls: "wide-only muted clip" },
    ]} />
    {#if cur}
      <aside class="detail detail-below"><h2>{t(cur.type)}</h2>
        <p><span class="hl2">{t("damage")}</span> {t(cur.damage)} · <span class="hl2">{t("mining")}</span> {t(cur.mining)}
          · <span class="hl2">{t("scan")}</span> {t(cur.scan)} · <span class="hl2">{t("slots when found")}</span> {t(cur.slots)}</p>
        <p>{t(cur.note)}</p></aside>
    {/if}
  {:else if tab === "weapons"}
    <List bind:this={list} rows={mt.weapons} onSelect={(w) => { cur = w; }} columns={[
      { title: t("Weapon"), text: (w) => t(w.weapon), cls: "strong", sort: (w) => w.weapon },
      { title: t("Similar to"), text: (w) => t(w.kind), sort: (w) => w.kind },
      { title: t("Best hit"), text: (w) => t(w.best_hit), cls: "num", sort: (w) => num(w.best_hit) },
      { title: t("Pros"), text: (w) => t(w.pro), cls: "wide-only clip" },
      { title: t("Cons"), text: (w) => t(w.con), cls: "wide-only muted clip" },
    ]} />
    {#if cur}
      <aside class="detail detail-below"><h2>{t(cur.weapon)} <span class="muted small">{t(cur.kind)}, {t("best measured hit {n}", { n: t(cur.best_hit) })}</span></h2>
        <p><span class="ok">+</span> {t(cur.pro)}</p><p><span class="err">−</span> {t(cur.con)}</p></aside>
    {/if}
  {:else if tab === "getting"}
    <div class="prose">
      <section class="card"><h3>{t("Where each kind comes from")}</h3>
        <dl class="rows">
          {#each mt.getting as g}
            <dt><b>{t(g.type)}</b> <span class="muted">({t(g.cost)})</span></dt>
            <dd>{t(g.where)}<div class="muted small">{t(g.how)}</div></dd>
          {/each}
        </dl>
      </section>
      {#each [mt.sentinel_puzzle, mt.cabinet_trick, mt.hunting] as p}{@render procedure(p)}{/each}
    </div>
  {:else}
    <div class="prose">
      {#each mt.rules as r}<section class="card"><h3>{t(r.title)}</h3><p>{t(r.body)}</p></section>{/each}
      <section class="card"><h3>{t("Where to get upgrades")}</h3>
        <dl class="rows">
          {#each mt.upgrade_sources as u}
            <dt><b>{t(u.kind)}</b></dt>
            <dd>{t(u.where)} <div class="muted small">{t(u.note)}</div></dd>
          {/each}
        </dl></section>
      <section class="card"><h3>{t("The order to upgrade in")}</h3>
        <ol>{#each mt.upgrade_order as s}<li>{t(s)}</li>{/each}</ol></section>
    </div>
  {/if}
</div>

<style>
  .headline { color: var(--p-green); }
  .tab > .prose { padding: 0 0 4px; }
</style>
