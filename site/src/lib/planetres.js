// What a planet has on it, as desktop/planet_data.py worked it out from its seed (a planet's `resources`): first the hints
// (a plant, bones, salvage, bugs, a swarm), then the rare, the uncommon and the common substance. Shared by the Planets page
// and by the Wiki card, which says on which planets of the save an item is to be found.

/** The rare, uncommon and common substance: the last three of the list. */
export const subOf = (p, i) => (p.resources?.length >= 3 ? p.resources[p.resources.length - 3 + i] : "");

/** The plant comes first (its hint is an item's id, the others' are the game's UI texts), then the rest in the game's order. */
export const hintsOf = (p) => {
  const hints = p.resources?.length >= 3 ? p.resources.slice(0, -3) : [];
  return [...hints.filter((id) => !id.startsWith("UI_")), ...hints.filter((id) => id.startsWith("UI_"))];
};

/** Everything the planet has, in the order the card shows it. */
export const resOf = (p) => [...hintsOf(p), ...(p.resources?.length >= 3 ? p.resources.slice(-3) : p.resources ?? [])];

/** The planets of a save that have the item. */
export const planetsWith = (planets, id) => (planets ?? []).filter((p) => resOf(p).includes(id));
