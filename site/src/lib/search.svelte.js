// The state of the header's search, shared by the field in the header (Header.svelte) and the list of results under it (Palette.svelte):
// whether it is open, what is typed in it, and the keys the list takes (arrows, Enter, Esc) while the field has the focus.
export const search = $state({ open: false, q: "", keydown: null });
