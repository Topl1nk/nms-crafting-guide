"""The brief for «Мои вещи» and the Wiki taking over «Куда класть», written as checks so it cannot be half done.

1. There is no «Куда класть» page: no route, no menu entry, no tile on the start page, no help entry, no view file, no
   link to #/storage anywhere in the site.
2. The general information on items and containers lives in the Wiki:
   - a filter «Куда деть» (the ten containers, the other places, Продать / Мусор / Использовать): #/wiki?store=KEY;
   - a column «Куда деть» whose tag filters by what it names;
   - the storage note (what to do with the item, and why) in the card of every item;
   - what linked to the old page (a recipe card, the search palette) opens the item's card in the Wiki.
3. «Мои вещи», the table «У меня есть»:
   - the name (white, not link-yellow) opens the item in the Wiki: #/wiki?item=ID;
   - the tag in the «Тип» column is a link to the Wiki with that type filtered, and the item's card open: #/wiki?type=…&item=…
   - the tag in the «Редкость» column is the same with the rarity: #/wiki?rar=…&item=…
     (each filters by the tag clicked and nothing else);
   - the right half is the card of the item the cursor is on (a click on a row, or the tag in the «Куда деть» column),
     the item's own card and nothing else: no lists «Можно сделать сейчас», «Не хватает одной вещи», no scheme.
4. The Wiki reads those links: `type`, `rar`, `store` and `item` (open that item's card, its row at the top of the table).
"""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).parent.parent / "site" / "src"


def read(*parts: str) -> str:
    return (SRC.joinpath(*parts)).read_text(encoding="utf-8")


def sources():
    return [p for p in sorted(SRC.rglob("*")) if p.suffix in {".svelte", ".js"}]


def test_there_is_no_storage_page() -> None:
    assert not (SRC / "views" / "Storage.svelte").exists()
    app = read("App.svelte")
    views = re.search(r"const VIEWS = \{(.*?)\};", app, re.S).group(1)
    assert "storage" not in views
    assert '"storage"' not in read("lib", "data.js")  # the menu
    assert '"storage"' not in read("views", "Home.svelte")
    assert '"storage"' not in read("views", "Help.svelte")


def test_nothing_links_to_the_storage_page() -> None:
    for path in sources():
        text = path.read_text(encoding="utf-8")
        assert "#/storage" not in text, f"{path.name} still links to #/storage"
        assert "Куда класть" not in text, f"{path.name} still names the page «Куда класть»"


def test_what_linked_to_storage_opens_the_item_in_the_wiki() -> None:
    assert "#/wiki?item=" in read("components", "Palette.svelte")
    card = read("components", "RecipeCard.svelte")
    assert "typeHref={wikiType(out)} rarHref={wikiRar(out)}" in card and "href={wikiStore(lineOf(p))}" in card, "the tags of a recipe card filter the Wiki"


def test_the_wiki_holds_the_storage_information() -> None:
    wiki = read("views", "Wiki.svelte")
    assert 'key: "store"' in wiki and 'label={t("Where to put it")}' in wiki, "a filter by line of the scheme"
    assert 'label={t("Where to put it")}' in wiki and "<Select hidden=" in wiki and "l.icon" in wiki, "its choices carry the game's pictures, not the numbers"
    assert '{ title: t("Where to put it"), cell: goesCell' in wiki, "a column"
    assert "f.store = lineOf(" not in wiki, "no tag of the Wiki is a link or sets a filter"
    assert "<StorageNote" in wiki, "the note is in the item's card"
    note = read("components", "StorageNote.svelte")
    for part in ("why", "Action", "home.note"):
        assert part in note, part
    lines = read("lib", "store.js")
    for label in ('t("Sell")', 't("Junk")', 't("Use it")', "act:sell"):
        assert label in lines, label


def test_the_wiki_reads_the_links() -> None:
    wiki = read("views", "Wiki.svelte")
    for key in ("type", "rar", "store", "item"):
        assert f'params.get("{key}")' in wiki, key
    assert " atTop " in wiki, "an opened item is brought to the top of the table"


def test_my_things_tags_lead_to_the_wiki_and_to_the_card() -> None:
    inv = read("views", "Inventory.svelte")
    store = read("lib", "store.js")
    assert "#/wiki?type=" in store and "&item=" in store, "the type tag opens the Wiki filtered by type, on the item"
    assert "#/wiki?rar=" in store, "the rarity tag opens the Wiki filtered by rarity, on the item"
    assert "typeHref={wikiType(id)}" in inv and "rarHref={wikiRar(id)}" in inv
    assert "StorageCard" in inv, "«Куда деть» shows the item's own card in the right half"
    assert 'params.get("item")' in inv, "#/inventory?item= opens that card"


def test_my_things_is_one_table_and_one_card() -> None:
    """No lists beside the table: «Можно сделать сейчас», «Не хватает одной вещи», «Куда деть» and the scheme are gone;
    the right half is the card of the item the cursor is on, and nothing else."""
    inv = read("views", "Inventory.svelte")
    for gone in ("Можно сделать сейчас", "Не хватает одной вещи", "StorageMap", "craftableNow", "oneHopAway", "inv-cook", "inv-side"):
        assert gone not in inv, gone
    assert inv.count("<List") == 1, "one table"
    assert re.search(r'<section class="cardside">\s*<div class="cardbody">\s*\{#if current\}\s*<StorageCard id=\{current\[0\]\}', inv)
    assert "<h3>" not in inv, "no headings «У меня есть» / «Карточка»: both halves start at the top and fill the page"
    assert not (SRC / "components" / "StorageMap.svelte").exists()


def test_where_it_lies_names_and_pictures_the_places_like_the_filter() -> None:
    """The list of places the save is read from, «Где лежит» (once «Откуда»): each place with its game picture and the
    name the filter «Куда деть» gives it (a chest is its line of the scheme)."""
    inv = read("views", "Inventory.svelte")
    assert 't("Where it lies")}:' in inv and "Откуда:" not in inv
    assert "<ItemIcon id={place(c).icon}" in inv and "{place(c).name}" in inv
    assert "storeLines()" in inv, "the names and pictures are the filter's"
    assert 'class="places"' in inv and 'type="checkbox"' in inv, "a list, one row a place, its checkbox kept"
    assert "{#each places as c" in inv and "const RANK" in inv, "in the order of the Wiki's list"
    for icon in ("STORE_freighter", "STORE_ship"):
        assert icon in inv, icon
    assert "«Откуда»" not in read("views", "Help.svelte")  # (its section «Откуда всё это» is another thing)


def test_the_table_has_where_it_lies_left_of_where_to_put_it() -> None:
    """With the save on: a column «Где лежит» (the places holding the item, pictured as the filter does) stands just
    left of «Куда деть». The card on the right is as narrow as the one of the Крафт page and built like it."""
    inv = read("views", "Inventory.svelte")
    here, there = inv.index('title: t("Where it lies")'), inv.index('title: t("Where to put it")')
    assert here < there and inv.count('title: t("Where to put it")') == 1
    assert "minmax(340px, 400px)" in inv, "as narrow as the .split of the Крафт page"
    assert not re.search(r'title: t\("Where it lies"\)[^\n]*(clip|fill: true)', inv), "a column of tags is never cut"
    assert "at.map((c) => [id, c.items[id], c])" in inv, "an item in several places has a row for each: never two places in a row"
    assert "{#each whereOf(" not in inv
    assert "<PlaceTag name={place(c).name}" in inv, "a place is named by a tag, as «Куда деть» is"
    assert 'class="act act-' in read("components", "PlaceTag.svelte")
    card = read("components", "StorageCard.svelte")
    assert 'class="ic-head"' in card and 'class="stats"' in card, "built like the card of Крафт and Вики"


def test_every_where_to_put_it_tag_is_a_picture_and_a_tag() -> None:
    """The tag «Куда деть» is one component, Action, wherever it is shown (the Wiki's table and card, a recipe card, the
    table and card of «Мои вещи»): the game's picture of the place, close before the coloured tag."""
    action = read("components", "Action.svelte")
    assert "<PlaceTag" in action and "iconOf(" in action
    tag = read("components", "PlaceTag.svelte")
    assert "<ItemIcon" in tag and 'class="act act-' in tag
    for page in (("views", "Wiki.svelte"), ("views", "Inventory.svelte"), ("components", "RecipeCard.svelte"), ("components", "StorageNote.svelte")):
        assert "<Action" in read(*page), page
    for path in sources():
        if path.name not in ("Action.svelte", "PlaceTag.svelte"):
            assert 'class="act act-' not in path.read_text(encoding="utf-8"), f"{path.name} draws the tag itself"


def test_the_column_and_says_whether_it_lies_right() -> None:
    """Column «И», between «Где лежит» and «Куда деть» (with the save on): a green ✔ where the item lies in the place
    the scheme gives it, and then «Куда деть» is empty; a yellow bold ➜ where the two differ."""
    inv = read("views", "Inventory.svelte")
    assert inv.index('title: t("Where it lies")') < inv.index('title: t("Fit")') < inv.index('title: t("Where to put it")')
    assert "✔" in inv and "➜" in inv
    assert re.search(r"\.fit\.ok \{[^}]*--p-green", inv) and re.search(r"\.fit\.wrong \{[^}]*--p-yellow[^}]*font-weight: 900", inv)
    assert re.search(r"\.fit \{[^}]*border: 1px solid[^}]*border-radius", inv), "in a thin, rounded frame"
    assert 'fit(row) !== "ok"' in inv, "«Куда деть» is empty when it lies right"


def test_the_tag_shows_no_container_numbers() -> None:
    assert r'replace(/(^|«)\d\s+/g, "$1")' in read("components", "Action.svelte")


def test_the_name_opens_the_wiki_and_the_row_opens_the_card() -> None:
    """In «У меня есть»: the name is a (white, not link-yellow) link to the item in the Wiki, #/wiki?item=ID; the card
    on the right is the one of the row under the cursor (a click on the row, off the text, the tags and the buttons)."""
    inv = read("views", "Inventory.svelte")
    assert 'href="#/wiki?item={encodeURIComponent(id)}"' in inv
    assert re.search(r"\.nm \{[^}]*color: var\(--p-text\)", inv), "the name is white"
    assert "onSelect={(row, i, user) => { if (user || !pinned) showRow(row); }}" in inv


def test_a_tag_that_is_a_link_lights_up_without_underlining() -> None:
    chips = read("components", "Chips.svelte")
    hover = re.search(r"a\.chip2:hover \{([^}]*)\}", chips).group(1)
    assert "text-decoration: none" in hover and "background" in hover


def test_the_card_of_my_things_is_the_item_and_its_note() -> None:
    card = read("components", "StorageCard.svelte")
    assert "<StorageNote" in card and "<Chips" in card

# -- the last round: order of the tabs, one card for one row, concrete text, tips, clickable tags, «Найти все» --------

def test_the_tabs_run_in_the_order_asked() -> None:
    data = read("lib", "data.js")
    nav = re.search(r"export const NAV = \[(.*?)\];", data, re.S).group(1)
    keys = re.findall(r'\["(\w+)", N_\("[^"]+"\)\]', nav)
    assert keys == ["inventory", "recipes", "tree", "wiki", "multitools", "portals", "help"]


def test_each_row_has_its_own_card() -> None:
    """An item in several places is several rows, and each row's card is its own: the place, the count there, and
    whether it lies right (not the item as one whole)."""
    inv = read("views", "Inventory.svelte")
    assert "cardRow" in inv and "const at = $derived" in inv and "{at}" in inv
    note = read("components", "StorageNote.svelte")
    assert '>{t("Where it lies")}</span>' in note and '>{t("Where to put it")}</span>' in note, "where it lies, and where it goes"
    assert "шт." not in note, "the count is in the figures above; the card does not say it twice"
    assert 't("It lies in the wrong place")' in note and 't("It lies in its place")' in note and 'class="badge"' in note, "the state, in the table's frame"
    assert note.count("<Action ") == 1 and note.count("<PlaceTag ") == 1, "each tag once: where it lies, where it goes"
    assert 't("Container {n}", { n: home.key })' in note and "Положите в" not in note
    assert '<div class="about">' in note, "what the place is: a grey block"


def test_the_card_says_things_concretely_not_in_general() -> None:
    note = read("components", "StorageNote.svelte")
    assert "<dt>Почему</dt>" not in note, "no «Почему: Так сказано в руководстве»"
    assert '"Named in the guide"' in note and "ENGLISH.storage" in note, "that phrase is never shown by itself"


def test_a_tip_is_drawn_as_a_tip() -> None:
    note = read("components", "StorageNote.svelte")
    assert '<p class="hint">' in note and "the rest go to the same one by themselves" in note
    rule = re.search(r"\.hint \{([^}]*)\}", note, re.S).group(1)
    assert "border-left: 3px solid" in rule, "a bar and a picture: it does not compete with the grey block"


def test_every_tag_of_the_card_is_a_link() -> None:
    card = read("components", "StorageCard.svelte")
    assert "typeHref={wikiType(id)}" in card and "rarHref={wikiRar(id)}" in card
    note = read("components", "StorageNote.svelte")
    assert "href={links ? target : """"}" in note, "the «Куда деть» tag leads to the Wiki everywhere but in the Wiki"
    assert "href" in read("components", "PlaceTag.svelte")
    inv = read("views", "Inventory.svelte")
    assert "href: placeHref(c)" in inv, "the place tag"


def test_recipes_button_opens_the_item_at_the_top_of_crafting() -> None:
    """#/recipes?item=ID lists the recipes that make the item first, and its row is selected, at the top of the table."""
    rec = read("views", "Recipes.svelte")
    assert "const makes = (r) =>" in rec and ".sort((a, b) => makes(a) - makes(b))" in rec
    assert re.search(r"<List [^>]*\{start\} atTop", rec)


def test_find_all_shows_every_place_of_the_item() -> None:
    inv = read("views", "Inventory.svelte")
    assert "others > 1 && only !== current[0]" in inv, "only a card of an item with other places has the button"
    assert 'let only = $state("")' in inv and "shown.filter(([id]) => id === only)" in inv
    assert 't("Find all")' in read("components", "StorageNote.svelte")

# -- the design review (docs/inventory-card-review.md) --------------------------------------------------------------

def test_the_narrow_page_still_has_its_table() -> None:
    """Under 1000px the grid is one column and the table has a height of its own (it had none, and the page was empty)."""
    inv = read("views", "Inventory.svelte")
    media = re.search(r"@media \(max-width: 1000px\) \{(.*?)\n  \}", inv, re.S).group(1)
    assert "grid-template-rows: none" in media and re.search(r":global\(\.list\) \{[^}]*height: 60vh", media)


def test_a_long_tag_is_never_cut_by_the_card() -> None:
    note = read("components", "StorageNote.svelte")
    assert re.search(r"\.row \{[^}]*display: grid", note), "label above the tag: the card's whole width is the tag's"
    assert "text-overflow: ellipsis" in read("components", "PlaceTag.svelte"), "a name too long ends in an ellipsis inside its tag"


def test_the_card_buttons_stay_in_view() -> None:
    note = read("components", "StorageNote.svelte")
    assert re.search(r"\.btns \{[^}]*position: sticky[^}]*bottom: 0", note)


def test_the_reason_is_worded_in_the_pages_language() -> None:
    """The reasons of the storage guide are English in the data; lib/words.js puts them into the page's language, and the card
    shows the worded one (only the empty "Named in the guide" is left out, found out from the English source)."""
    note = read("components", "StorageNote.svelte")
    assert "ENGLISH.storage" in note and "p.why" in note
    assert "localizeStorage" in read("lib", "language.svelte.js")





