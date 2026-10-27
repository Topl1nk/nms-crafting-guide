// Search boxes filter as you type, but not on every keystroke.
export function debounce(fn, ms = 120) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// A dropdown panel (<details>) that shuts when you press anywhere outside it, or Esc.
export function closeOutside(node) {
  const away = (e) => { if (node.open && !node.contains(e.target)) node.open = false; };
  const esc = (e) => { if (e.key === "Escape" && node.open) node.open = false; };
  document.addEventListener("pointerdown", away);
  document.addEventListener("keydown", esc);
  return { destroy() { document.removeEventListener("pointerdown", away); document.removeEventListener("keydown", esc); } };
}