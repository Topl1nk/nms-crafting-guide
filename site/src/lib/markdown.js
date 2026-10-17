// The markdown twin of each page (scripts/build_markdown.py writes them), for
// the footer link and the <link rel=alternate> a crawler or an AI reads.
//
// Plain JS on purpose: tests/test_markdown.py reads MD_PAGES out of this file
// and checks that the export writes every page it names.

import { D } from "./data.js";

export const MD_PAGES = {
  nanites: "md/nanites.md", cooking: "md/cooking.md", multitools: "md/multitools.md",
  portals: "md/portals.md", storage: "md/storage.md", inventory: "md/items/index.md",
  help: "md/guide.md", recipes: "md/recipes.md",
};

// An item's own page when the view is about one item; the section's page
// otherwise; llms.txt for the start page and anything unknown.
export function markdownFor(section, rest, params) {
  const item = section === "chain" ? rest : section === "recipes" ? params.get("item") : null;
  if (item && D?.items[item]) return `md/items/${encodeURIComponent(item)}.md`;
  return MD_PAGES[section] || "llms.txt";
}
