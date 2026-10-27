"""Every link inside the site names a page that exists and only the settings that page reads.

A link to a table with filters is a promise about what it shows; one with a misspelt key opens the table with the
last filters instead, and that is how a link ends up on an empty table. So the pages and the keys they read are
listed here, and every `#/page?key=...` written anywhere in the site's source is checked against them.
"""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).parent.parent / "site" / "src"

# page -> the query keys it reads (the arguments after the page's name, as in #/tree/ITEM, are not keys)
PAGES = {
    "home": set(),
    "recipes": {"item", "role", "r", "domain", "effect", "path", "tier", "qty", "cook"},
    "tree": {"cook", "qty"},
    # the short path is a part of Крафт now; its old links (#/chain/ITEM?tier=&qty=&cook=) open there (lib/router.svelte.js)
    "chain": {"tier", "qty", "cook"},
    "wiki": {"q", "type", "rar", "store", "item"},
    "portals": {"kind", "code"},
    "multitools": {"tab"},
    "inventory": {"item"},
    "help": set(),
    # old links that still open (lib/router.svelte.js sends them to recipes)
    "cooking": {"buff", "domain", "effect"},
    "nanites": set(),
}
LINK = re.compile(r"#/([a-z]+)((?:/[^\s\"'`?<>]*)?)(?:\?([^\s\"'`<>]*))?")


def links() -> list[tuple[Path, int, str, set[str]]]:
    found = []
    for path in sorted(SRC.rglob("*")):
        if path.suffix not in {".svelte", ".js"}:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in LINK.finditer(line):
                page, _, query = match.groups()
                if page == "section":  # the router's own comment describing the shape, not a link
                    continue
                keys = set(re.findall(r"([A-Za-z_]+)=", query or ""))
                found.append((path, number, page, keys))
    return found


def test_every_link_names_a_page_that_exists() -> None:
    found = links()
    assert len(found) > 20, "the scan found almost no links: the pattern is broken"
    for path, number, page, _ in found:
        assert page in PAGES, f"{path.name}:{number}: no page called {page!r}"


def test_every_link_sets_only_what_its_page_reads() -> None:
    for path, number, page, keys in links():
        extra = keys - PAGES[page]
        assert not extra, f"{path.name}:{number}: #/{page} does not read {sorted(extra)}"


def test_the_pages_in_this_list_are_the_pages_of_the_site() -> None:
    app = (SRC / "App.svelte").read_text(encoding="utf-8")
    views = set(re.findall(r"(\w+): \w+", re.search(r"const VIEWS = \{(.*?)\};", app, re.S).group(1)))
    assert views | {"cooking", "nanites", "chain"} == set(PAGES)