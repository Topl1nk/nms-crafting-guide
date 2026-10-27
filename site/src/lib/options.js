// The choices that more than one page offers, in one place, so a filter is
// worded, ordered and sized the same wherever it shows up. Each is a function: the words follow the page's language.

import { refinerLevel } from "./data.js";
import { t } from "./i18n.js";

/** "Refiner": the biggest one you have (a recipe needing a bigger one is out). */
export const refiners = () => [[0, t("any refiner")], [1, t("portable only")], [2, t("portable and medium")]];
export const fitsRefiner = (level, max) => !max || level <= max;
export const recipeFits = (recipe, max) => fitsRefiner(refinerLevel(recipe), max);

/** "Source": how hard the hardest ingredient of a recipe is to get. */
export const sources = () => [["any", t("any source")], ["easy", t("easy only")], ["ok", t("easy and fair")], ["nohard", t("all but the hard ones")]];
export const SOURCE_BANDS = { easy: ["easy"], ok: ["easy", "ok"], nohard: ["easy", "ok", "work"] };

/** "My items": how much of a recipe you already have. */
export const owned = () => [["all", t("ignore")], ["can", t("enough for the recipe")], ["some", t("have some of what it needs")]];
