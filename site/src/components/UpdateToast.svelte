<script>
  // A new version of the page, or new data, is waiting in the service worker.
  // It stays until answered: reload onto it, or keep going on this one (the
  // next visit picks it up anyway). Never switched underneath the session.
  import { applyUpdate, dismissUpdate, pwa } from "../lib/pwa.svelte.js";
</script>

{#if pwa.update}
  <div class="update" role="status" aria-live="polite">
    <span class="msg"><span class="prompt">$</span> New data/version available</span>
    <span class="acts">
      <button type="button" class="go" onclick={applyUpdate}>reload</button>
      <button type="button" class="later" onclick={dismissUpdate} aria-label="Dismiss: update on the next visit">later</button>
    </span>
  </div>
{/if}

<style>
  .update {
    position: fixed;
    right: 20px;
    bottom: calc(20px + env(safe-area-inset-bottom));
    z-index: 11;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 14px;
    max-width: calc(100vw - 24px);
    font-family: var(--p-mono);
    font-size: 0.85rem;
    color: var(--p-text);
    background: var(--p-raised);
    border: 1px solid var(--p-outline);
    border-left: 3px solid var(--p-edge-accent);
    padding: 8px 10px 8px 14px;
    animation: rise 0.2s ease-out;
  }
  @media (max-width: 640px) { .update { left: 12px; right: 12px; bottom: calc(12px + env(safe-area-inset-bottom)); } }
  @keyframes rise { from { opacity: 0; transform: translateY(12px); } }
  @media (prefers-reduced-motion: reduce) { .update { animation: none; } }
  .prompt { color: var(--p-accent-ink); }
  .acts { display: flex; gap: 6px; margin-left: auto; }
  button { font-family: var(--p-mono); font-size: 0.85rem; border-radius: 0; padding: 2px 10px; cursor: pointer; }
  .go { background: var(--p-accent); color: var(--p-on-accent); border: 1px solid var(--p-edge-accent); font-weight: 700; }
  .go:hover { filter: brightness(1.08); }
  .later { background: none; color: var(--p-faint); border: 1px solid var(--p-outline); }
  .later:hover { color: var(--p-accent-ink); border-color: var(--p-edge-accent); }
</style>


