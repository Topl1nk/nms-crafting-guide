// One line of feedback at the bottom of the page: copied, saved, added.
// Toast.svelte draws it; anything can call toast().

export const toastState = $state({ text: "", show: false });

let timer;
export function toast(text) {
  toastState.text = text;
  toastState.show = true;
  clearTimeout(timer);
  timer = setTimeout(() => { toastState.show = false; }, 1800);
}

export async function copy(text, what) {
  try {
    await navigator.clipboard.writeText(text);
    toast(`Copied ${what}`);
  } catch {
    toast("Copy failed - select it by hand");
  }
}
