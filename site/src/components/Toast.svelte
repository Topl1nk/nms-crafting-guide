<script>
  import { toastState } from "../lib/toast.svelte.js";
</script>

<div class="toast" class:show={toastState.show} role="status" aria-live="polite">{toastState.text}</div>

<style>
  .toast {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translate(-50%, 20px);
    font-family: var(--p-mono);
    font-size: 0.85rem;
    background: var(--p-raised);
    border: 1px solid var(--p-outline);
    border-left: 3px solid var(--p-accent);
    padding: 8px 14px;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s, transform 0.2s;
    z-index: 10;
  }
  .toast.show { opacity: 1; transform: translate(-50%, 0); }
</style>
