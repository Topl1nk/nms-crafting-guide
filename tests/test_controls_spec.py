"""The controls of the bars: three-state flags, one fixed width and right-aligned lists, the reset button left of the search,
one canvas for every pyramid, a square glow behind every icon."""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).parent.parent / "site" / "src"


def read(*parts: str) -> str:
    return SRC.joinpath(*parts).read_text(encoding="utf-8")


def test_a_flag_has_three_states() -> None:
    check = read("components", "Check.svelte")
    assert 'value === false ? true : value === true && tri ? "not" : false' in check
    assert 'aria-checked={value === "not" ? "mixed"' in check
    facets = read("lib", "facets.js")
    assert 'export const FLAG = [[false, ""], [true, ""], ["not", ""]];' in facets
    assert "export const flag = (v, has) =>" in facets
    css = read("app.css")
    assert ".chk.not .cbx" in css and ".chk.on .cbx" in css
    for page in (("lib", "recipefacets.js"), ("views", "Wiki.svelte")):
        text = read(*page)
        assert "options: FLAG" in text and "flag(v," in text, page
    tree = read("views", "Tree.svelte")
    assert "flag(mine, heldAll(p))" in tree and "flag(cook, p.m.cooks)" in tree
    assert "tri={false}" in read("components", "ChainBar.svelte"), "a setting of the path is no filter"


def test_a_list_has_one_width_and_opens_under_its_right_edge() -> None:
    select = read("components", "Select.svelte")
    assert 'class="ghost"' in select and "visibility: hidden" in select, "every choice is stacked in the field: its widest sets the width"
    assert "seen" in select and "all" in select
    assert "left: auto; right: 0" in select
    assert not (SRC / "components" / "IconSelect.svelte").exists()
    assert "position: absolute; right: 0; top: calc(100% + 8px)" in read("app.css"), "every dropdown panel"
    assert "<select" not in read("views", "Inventory.svelte").split("</script>")[1].split("<style>")[0].replace('<select name', ""), "no native list left in a bar"
    for page in ("Recipes", "Wiki", "Tree", "Portals"):
        text = read("views", f"{page}.svelte")
        assert "all=" in text, page


def test_the_reset_button_stands_left_of_the_search() -> None:
    for page in (("views", "Recipes.svelte"), ("views", "Wiki.svelte"), ("views", "Portals.svelte"), ("views", "Tree.svelte"), ("components", "TreePicker.svelte")):
        text = read(*page)
        i = text.index("<h1>")
        assert re.search(r"</h1>\s*<Reset ", text[i:]), page
        if 'class="search"' in text:
            assert text.index("<Reset ") < text.index('class="search"'), page


def test_every_pyramid_is_on_the_one_canvas() -> None:
    pan = read("components", "PanCanvas.svelte")
    assert "user-select: none" in pan and "-webkit-user-drag: none" in pan and "ondragstart={(e) => e.preventDefault()}" in pan
    assert "onselectstart={(e) => e.preventDefault()}" in pan
    assert "<PanCanvas" in read("views", "Tree.svelte") and "<PanCanvas" in read("components", "ChainCanvas.svelte")
    assert "<ZoomBar" in read("views", "Tree.svelte") and "<ZoomBar" in read("components", "ChainBar.svelte")


def test_schemes_have_a_bold_white_plus_and_a_bold_arrow() -> None:
    assert "✚" in read("components", "Ingredients.svelte") and "color: var(--p-text); font-weight: 900" in read("components", "Ingredients.svelte")
    card = read("components", "RecipeCard.svelte")
    assert "➜" in card and "font-weight: 900" in card
    assert "{#if !r.cycle}" in card, "a loop's card has no scheme"


def test_only_loops_of_half_an_hour_are_offered() -> None:
    store = read("lib", "cycles.svelte.js")
    assert "MAX_SECONDS = 30 * 60" in store and "turnTime(data.loop) <= MAX_SECONDS" in store


def test_the_glow_behind_an_icon_is_a_soft_square() -> None:
    icon = read("components", "ItemIcon.svelte")
    assert "mask-composite: intersect" in icon and "radial-gradient" not in icon


def test_no_tag_of_the_wiki_is_a_link() -> None:
    wiki = read("views", "Wiki.svelte")
    assert "typeHref" not in wiki and "rarHref" not in wiki
    assert "goes" not in wiki.split("<style>")[1], "the place in the table is no button that sets the filter"
    assert "links={false}" in wiki and 'links ? target : ""' in read("components", "StorageNote.svelte")


def test_the_reset_button_is_always_there_and_dimmed_when_idle() -> None:
    css = read("app.css")
    assert "visibility: hidden" not in css.split(".reset.off")[1].split("}")[0]
    assert ".reset.off { color: color-mix(in srgb, var(--p-faint) 62%, var(--p-panel)); border-color: var(--p-outline);" in css, "dimmed but to be seen"
    assert ".list::-webkit-scrollbar-button:vertical:start:decrement" in css, "the head of a table runs to the edge of its pane, over the scrollbar too"
    assert "disabled={!active}" in read("components", "Reset.svelte")


def test_the_multiplier_of_a_cycle_scales_every_count_of_the_scheme() -> None:
    steps = read("components", "CycleSteps.svelte")
    assert "mult = 1" in steps and "m * mult" in steps and "* mult, ins: []" in steps
    assert "<CycleSteps {cycle} mult={qty} />" in read("components", "ChainCanvas.svelte")
    assert 'cycle ? t("Multiplier")' in read("components", "ChainBar.svelte")


def test_an_icon_stays_under_the_sticky_header_of_a_table() -> None:
    icon = read("components", "ItemIcon.svelte")
    assert "isolation: isolate" in icon and "z-index" not in icon


def test_the_sort_lists_are_long() -> None:
    picks = read("lib", "pickfacets.js")
    for key in ("color", "type", "rar", "potency", "time", "ease"):
        assert f'["{key}", ' in picks, key
    recipes = read("views", "Recipes.svelte")
    for key in ("color", "type", "rar"):
        assert f'["{key}", ' in recipes, key
    assert "export function byColor" in read("lib", "sortkeys.js")


def test_the_number_tiles_of_a_card_have_big_pictures_and_a_readable_label() -> None:
    css = read("app.css")
    assert ".stat .ic, .stat .units { width: 26px; height: 26px; }" in css
    assert ".stat small { font-size: 0.7rem; letter-spacing: 0.05em; text-transform: uppercase; color: var(--p-muted); }" in css


def test_back_closes_what_a_button_opened() -> None:
    """The side button of the mouse (Back) must show the screen the button was pressed on: a path or a loop drawn whole,
    and a list narrowed by «Найти все», each take a step of the history."""
    router = read("lib", "router.svelte.js")
    assert "export function trapBack(onclose)" in router and "history.pushState({ trap: key }" in router
    rec = read("views", "Recipes.svelte")
    assert "history.pushState(null, \"\", hash)" in rec and "history.back()" in rec and "trapBack(" in rec
    assert "replace(withRow(cur.index))" in rec, "Back comes back to the row the table stood on"
    assert 'k !== "r"' in rec, "the row alone is no link: the filters kept for the table stay"
    inv = read("views", "Inventory.svelte")
    assert "trapBack(" in inv and "onclick={clearOnly}" in inv


def test_tags_of_my_things_table_do_not_click_but_those_of_a_recipe_card_do() -> None:
    inv = read("views", "Inventory.svelte")
    snippet = inv.split("{#snippet goesTo(row)}")[1].split("{/snippet}")[0]
    assert "<button" not in snippet and "<a " not in snippet


def test_every_item_tile_is_the_one_square_tile() -> None:
    """The scheme of a card, the pyramids, the steps of a cycle and the list of things to break down: one component, one
    square size from one variable, nothing in them set by hand or by the length of a name."""
    tile = read("components", "Tile.svelte")
    assert "width: var(--tile); height: var(--tile)" in tile
    assert "--tile: 108px" in read("app.css")
    for page in ("RecipeNode", "ItemTile", "Pyramid", "CycleSteps"):
        text = read("components", f"{page}.svelte")
        assert "<Tile" in text, page
        assert ".tile {" not in text and ".nd {" not in text and ".sq {" not in text, page
    assert "max-content" not in read("components", "RecipeNode.svelte")


def test_what_stands_in_a_bar_shares_its_width() -> None:
    css = read("app.css")
    assert ".fbar > .gone { display: block; flex: none; height: 0;" in css and "{ flex-grow: 1; }" in css and "has(+ .gone)" in css, "only the two neighbours of a hidden filter stretch"
    assert ".fbar > .fsel, .fbar > .chk" not in css, "the whole bar does not stretch"
    for part in ("Select", "Check"):
        text = read("components", f"{part}.svelte")
        assert '<i class="gone"' in text and "hidden = false" in text, part
    assert "grid-template-columns: repeat(auto-fill, minmax(var(--tile), 1fr))" in read("components", "TreePicker.svelte")


def test_reset_clears_what_a_link_set_too() -> None:
    rec = read("views", "Recipes.svelte")
    assert "|| Boolean(item) || q !== \"\"" in rec and 'if (item) go("#/recipes");' in rec
    assert "st.filters = { ...DEFAULTS };" in rec
    assert 'q = st.q = ""' in read("views", "Wiki.svelte") and 'q = st.q = ""' in read("components", "TreePicker.svelte")


def test_rows_of_a_scheme_are_far_enough_apart_for_the_count_over_a_tile() -> None:
    assert "gap: 24px 8px" in read("components", "Ingredients.svelte")
    assert "gap: 24px 12px" in read("components", "RecipeCard.svelte")


def test_nothing_in_a_bar_or_a_table_jumps() -> None:
    """A filter that goes or comes shrinks or grows while its neighbours stretch; the columns of a table move to their new
    widths instead of jumping. The arrow of a list stays at the right edge of the field however wide it grows."""
    bar = read("lib", "bar.js")
    assert "export function bloom(node, { skip = false } = {})" in bar and "export function collapse(node, width)" in bar
    for part in ("Select", "Check"):
        text = read("components", f"{part}.svelte")
        assert "use:collapse={last}" in text and "in:bloom={{ skip: !shown }}" in text, part
    css = read("app.css")
    assert "transition: width 0.45s var(--spring), flex-grow 0.45s var(--spring);" in css and "prefers-reduced-motion" in css
    select = read("components", "Select.svelte")
    assert ".cur { display: inline-grid; flex: 1;" in select and "max-width: 34ch" in select.split(".ghost")[1]
    lst = read("components", "List.svelte")
    assert "<colgroup>" not in lst and 'document.createElement("colgroup")' in lst and "requestAnimationFrame" in lst
    assert "Math.max(0, (t - t0) / MS)" in lst, "a frame older than the start must not run the widths backwards"
    assert "setTimeout(() => settle?.(), MS + 250)" in lst, "a hidden tab draws no frames: the table never stays half way"



def test_the_large_things_slide_behind_the_edges_of_the_screen() -> None:
    """Panes slide in from and out behind the edges (no mask, no drawn edge; a light motion blur smears the fast part and is gone where it stops): the table to the left, its card to the
    right, the bars to the top; the old page leaves while the new one comes."""
    motion = read("lib", "motion.js")
    for name in ("export function snapshot(", "export function enterView(", "export function swap("):
        assert name in motion, name
    assert "nms-edge" not in motion
    assert "clipPath" not in motion.split("function peelCard(")[0] and "clipPath" not in motion.split("export function swap(")[1], "a mask only in the page turn of the Wiki's card"
    assert "function drop(" in motion and "drop: true" in read("components", "RecipeCard.svelte") and "drop: true" in read("components", "StorageCard.svelte"), "the cards of Крафт fall from above"
    assert "export function capture(" in motion and "peelCard(c)" in motion and "peel: true" in read("views", "Wiki.svelte") and "capture();" in read("views", "Wiki.svelte"), "the Wiki's card is turned like a page"
    assert "function smear(" in motion and motion.count("smear(") >= 3 and "blur(0px)" in motion, "a moving pane is blurred while it moves"
    assert 'parent.firstElementChild === el ? "left" : "right"' in motion and 'el.matches(".fbar, .count")) return "top"' in motion
    assert "prefers-reduced-motion" in motion
    app = read("App.svelte")
    assert "$effect.pre(" in app and "snapshot(" in app and "enterView(document.querySelector(\"main\"), dir, old)" in app
    css = read("app.css")
    assert ".nms-ghosts {" in css and "html.nms-moving { overflow-x: hidden; }" in css and "nms-edge" not in css
    for page in (("components", "RecipeCard.svelte"), ("components", "StorageCard.svelte"), ("views", "Wiki.svelte")):
        assert "use:swap=" in read(*page), page
    assert 'use:swap={{ initial: true, edge: "left" }}' in read("components", "PanCanvas.svelte")


def test_nothing_stalls_or_flashes_while_a_page_arrives() -> None:
    """Measured: the Wiki drew 2285 rows at once, a second on the main thread, in the very frame the page was to slide. Now a list
    draws its first rows and the rest as its end comes near; the new page is hidden until its first frame; the old page is copied
    with only the rows in view; the page is measured once, not once per pane."""
    lst = read("components", "List.svelte")
    assert "const FIRST = 80;" in lst and "view.slice(0, shown)" in lst and "use:nearEnd" in lst
    assert "if (i >= shown) shown = i + STEP / 2;" in lst, "a row the cursor is sent to is drawn first"
    assert "content-visibility: auto" in lst
    motion = read("lib", "motion.js")
    assert "export function hold(main)" in motion and "main.dataset.entering" in motion and "release(main); // the same frame" in motion
    assert "function trimRows(copy, el)" in motion and "will-change:transform" in motion
    assert "main[data-entering] > * { visibility: hidden; }" in read("app.css")
    assert "hold(main)" in read("App.svelte")
    assert 'lazy = true' in read("components", "ItemIcon.svelte")


def test_the_design_is_flat_with_dark_edges_and_the_back_lighter_than_the_front() -> None:
    """A plane with a play of static light, never a relief: the cloth at the back is the lightest, each surface in front of it
    is darker and edged by a dark line; shadows only under a pane or a button; nothing lit along an edge, nothing raised or
    sunk, no inner glow or shadow; header and footer plain. Cost: images and shadows."""
    root = SRC.parent.parent
    assert (root / "scripts" / "make_velvet.py").exists()
    for name in ("pile", "suede"):
        webp = root / "web" / f"{name}.webp"
        assert webp.exists() and webp.stat().st_size < 200_000, name
    css = read("velvet.css")
    for layer in ("var(--pile)", "var(--suede)", "--ox:", "--ts:", "--ga:", "background-position: var(--ox) var(--oy)"):
        assert layer in css, layer
    inner = re.findall(r"inset [^,;]+", css.split("*/", 1)[1])
    allowed = {"inset 0 0 22px 0 rgb(var(--v-ink) / 0.17)"}
    assert inner and all(s.strip() in allowed for s in inner), "inside a border only the one even shade, never a light, glow or bevel"
    assert css.count("var(--inner)") >= 8, "the shade is on every surface"
    assert "mix-blend-mode" not in css and "backdrop-filter" not in css and "sheen" not in css and "nms-light" not in css
    assert ".top { background-image: linear-gradient(" in css and "var(--pile)" not in css.split(".top {")[1].split("}")[0], "the header is plain"
    assert not (SRC / "lib" / "light.js").exists()
    app = read("app.css")
    bg = re.search(r"--p-bg: (#\w+);", app).group(1)
    panel = re.search(r"--p-panel: (#\w+);", app).group(1)
    outline = re.search(r"--p-outline: (#\w+);", app).group(1)
    lum = lambda h: sum(int(h[i:i + 2], 16) for i in (1, 3, 5))
    assert lum(panel) > lum(bg) and lum(panel) > lum(outline), "the panels are lighter than the cloth behind them, and their edge is darker than they are"
    main = read("main.js")
    assert 'import "./velvet.css"' in main and "startLight" not in main
    assert 'new URL(`${name}.webp`, document.baseURI).href' in main, "a relative url in a var is read against the stylesheet"
    assert "var(--suede)," in read("components", "Tile.svelte")
    assert "box-shadow: inset" not in read("components", "Tile.svelte").split("<style>")[1], "a tile has no inner light"
    index = read("..", "index.html")
    assert "pile.webp" in index and "suede.webp" in index



def test_the_palette_is_a_warm_umber_without_green_or_yellow_and_the_edge_darkens_on_hover() -> None:
    """A navy ramp, hue 208 to 236 degrees (ink blue through slate to a cold white; no green, no violet), saturation by lightness;
    the front surfaces have a hue of their own, not just the back's, darker; a pointed-at edge is darker than at rest and is not black."""
    import colorsys

    app = read("app.css")
    names = ("bg", "panel", "raised", "outline", "outline-hover", "text", "muted", "faint", "sel")
    for name in names:
        match = re.search(rf"--p-{name}: #([0-9a-f]{{6}});", app)
        r, g, b = (int(match.group(1)[i:i + 2], 16) / 255 for i in (0, 2, 4))
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        assert 208 <= h * 360 <= 236 and s < 0.6, (name, round(h * 360), round(s, 2))
    light = lambda name: sum(int(re.search(rf"--p-{name}: #(\w{{6}});", app).group(1)[i:i + 2], 16) for i in (0, 2, 4))
    assert light("outline") > light("outline-hover") > 3 * 6, "darker on hover, and not black"
    hue = lambda name: colorsys.rgb_to_hls(*(int(re.search(rf"--p-{name}: #(\w{{6}});", app).group(1)[i:i + 2], 16) / 255 for i in (0, 2, 4)))[0] * 360
    assert abs(hue("bg") - hue("panel")) <= 12, "neighbouring surfaces are neighbours on the ramp"
    css = read("velvet.css")
    assert "border-color: var(--p-outline-hover)" in css and ":hover" in css


def test_the_accent_is_gold_unless_another_is_chosen() -> None:
    """The accent is the visitor's pick and gold by default: it fills (a button, a badge, the active tab) with dark text on it, and is the
    same colour where it is drawn as text, a line or an icon. A saved key that is no longer offered (the near-black "umber" there once was)
    falls back to gold. The CSS only has a fallback for the instant before the script sets the variable."""
    theme = read("lib", "theme.js")
    assert 'ACCENTS = [\n  ["gold", N_("Gold"), "#f1c265"],' in theme.replace("\r\n", "\n")
    assert '["umber"' not in theme, "no near-black accent: gold is the default"
    assert 'accent: () => local.get("accent", "gold")' in theme
    app = read("app.css")
    assert re.search(r"--p-accent: var\(--accent, #[0-9a-f]{6}\); --p-accent-ink: var\(--accent-ink, #[0-9a-f]{6}\);", app)
    for path in sorted(SRC.rglob("*")):
        if path.suffix in {".css", ".svelte"} and path.name != "velvet.css":
            text = path.read_text(encoding="utf-8")
            assert not re.search(r"(?<![-\w])color: var\(--p-accent\)", text), f"{path.name}: accent as a text colour must be the ink"
            assert not re.search(r"border-color: var\(--p-accent\)", text), f"{path.name}: accent as a line must be the ink"


def test_a_table_head_is_darker_than_the_table_and_the_nap_goes_with_the_content() -> None:
    app = read("app.css")
    head = re.search(r"--p-head: #(\w{6});", app).group(1)
    panel = re.search(r"--p-panel: #(\w{6});", app).group(1)
    assert sum(int(head[i:i + 2], 16) for i in (0, 2, 4)) < sum(int(panel[i:i + 2], 16) for i in (0, 2, 4))
    assert "background: var(--p-head);" in read("components", "List.svelte")
    css = read("velvet.css")
    assert ":is(.list, .detail) { background-attachment: local, scroll; }" in css
    assert "0 2px 2px -1px rgb(var(--v-ink) / 0.6), 0 12px 14px -10px" in css, "the panes lie a little above the cloth"



def test_edges_are_one_tone_darker_than_the_surface_and_nothing_has_a_bright_line_or_colour() -> None:
    app = read("app.css")
    hexes = lambda name: [int(re.search(rf"--p-{name}: #(\w{{6}});", app).group(1)[i:i + 2], 16) for i in (0, 2, 4)]
    panel, outline, hover = hexes("panel"), hexes("outline"), hexes("outline-hover")
    ratio = sum(outline) / sum(panel)
    assert 0.74 <= ratio <= 0.95, f"the edge is one tone darker than its surface, not a black line: {ratio:.2f}"
    assert sum(hover) < sum(outline) and sum(hover) > 3 * 12, "darker on hover, and not black"
    assert "--p-edge-accent: color-mix(in srgb, var(--p-accent-ink) 20%, var(--p-outline))" in app
    for path in sorted(SRC.rglob("*")):
        if path.suffix in {".css", ".svelte"}:
            text = path.read_text(encoding="utf-8")
            assert not re.search(r"border[a-z-]*: [^;{}]*var\(--p-accent-ink\)", text), f"{path.name}: no bright accent line"
            assert not re.search(r"border[a-z-]*: [^;{}]*var\(--p-faint\)", text), f"{path.name}: no light line"
    css = read("velvet.css")
    assert "linear-gradient(180deg, rgb(var(--v-ink) / 0.46), transparent)" in css and "0 var(--top)" in css, "the top of the cloth is shaded below the header, not under it"
    assert "body { text-shadow: 0 -1px 1px rgb(var(--v-ink) / 0.45); }" in css, "every letter carries the same shade"
    assert "--inner: inset 0 0 22px 0 rgb(var(--v-ink) / 0.17);" in css and ".acts2 > button" in css, "every button: a shade from the edge in toward the middle"
    assert "box-shadow: var(--inner), 0 10px 14px -8px rgb(var(--v-ink) / 0.96)" in css, "a strong shadow under the header"
    assert "0 2px 2px -1px rgb(var(--v-ink) / 0.65), 0 7px 8px -5px rgb(var(--v-ink) / 0.88)" in css, "buttons lifted off the cloth"





def test_no_colour_of_the_source_is_louder_than_the_ceiling() -> None:
    """scripts/tone_colors.py brings every loud colour of the source down to one saturation ceiling (and only those: it changes
    nothing the second time); the glow of an item keeps only part of its own colour, the rest a warm grey."""
    import subprocess
    import sys

    script = SRC.parent.parent / "scripts" / "tone_colors.py"
    done = subprocess.run([sys.executable, str(script), "--check"], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout[-600:]
    assert "--item-tone: 62%;" in read("app.css")
    # what means something keeps its colour (muted, not loud): the tags of type and rarity, the branches, the accents, the signals
    ru = read("lib", "words.js")
    import colorsys

    def lively(text: str, at_least: int) -> bool:
        """At least `at_least` colours of the text are real colours (saturation over 0.5) and none is louder than the ceiling."""
        sats = []
        for h in re.findall(r"#([0-9a-fA-F]{6})", text):
            r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
            sats.append(colorsys.rgb_to_hls(r, g, b)[2])
        return sum(s > 0.5 for s in sats) >= at_least and all(s <= 0.86 for s in sats)

    assert lively(ru, 8), "the tags are coloured, lively and not shouting"
    assert lively(read("components", "Pyramid.svelte"), 6), "the branches of a pyramid"
    glob = read("global.css").split("\n")[:60]
    assert lively("\n".join(l for l in glob if re.search(r"--p-(green|red|orange|purple|pink):", l)), 4), "the signal colours"
    assert lively("\n".join(l for l in read("lib", "theme.js").split("\n") if re.search(r"\[\"(gold|cyan|green|violet|orange)\"", l)), 4), "the accents"
    assert "glow(color)" in read("components", "ItemIcon.svelte") and "--icon-gap:" in read("app.css"), "the glow of a picture is fitted to the surface it lies on"
    assert "panel + gap" in read("lib", "icontone.js")
    assert re.search(r"var\(--item-tone\), #\w{6}\)", read("components", "Tile.svelte"))




def test_a_tile_is_a_pane_of_glass_that_lifts_with_its_picture() -> None:
    """The glass is the tile: one straight, not strong glare on it, and pointed at, the whole piece (glass and picture) lifts with a
    soft shadow under it. A picture alone (in a table) is a small piece of glass of its own."""
    tile = read("components", "Tile.svelte")
    assert ".itile::after" in tile and "linear-gradient(128deg, rgb(255 255 255 / 0.13) 0%" in tile, "the glare is on the tile"
    assert ".itile:hover { transform: translateY(-3px);" in tile and "prefers-reduced-motion" in tile
    assert ".itile:hover { box-shadow: var(--inner), 0 11px 12px -8px" in read("velvet.css")
    icon = read("components", "ItemIcon.svelte")
    assert ".ico:not(.none)::after" in icon and ".ico:hover" not in icon, "a picture alone (in a table) does not move"
    assert ":global(.itile) .ico::after { display: none; }" in icon and ":global(.itile) .ico:hover { transform: none; filter: none; }", "in a tile only the tile lifts"


def test_what_has_a_colour_is_glass() -> None:
    css = read("velvet.css")
    assert ":is(.chip2, .band, .act, .stat)" in css and "linear-gradient(128deg, rgb(255 255 255 / 0.24) 0%" in css, "a tag, a badge, a figure: gradient, dark edge of its colour, one glare"
    assert "a.chip2:hover { transform: translateY(-2px)" in css
    for n, colour in ((1, "cyan"), (2, "green"), (3, "purple"), (4, "orange")):
        assert f"--sc: var(--p-{colour});" in css, colour
    assert "--p-cyan:" in read("app.css")



def test_all_motion_is_one_soft_spring_that_overshoots_a_little() -> None:
    """One damped spring (scripts/make_spring.py): in css as --spring, in script as lib/spring.js; every entry, lift, bloom and
    column move uses it; exits use a plain ease-in."""
    import math

    spring = read("lib", "spring.js")
    points = [float(x) for x in re.search(r"SPRING_POINTS = \[([^\]]+)\]", spring).group(1).split(",")]
    assert 1.05 < max(points) < 1.2 and points[0] == 0 and points[-1] == 1 and abs(points[-2] - 1) < 0.03, "overshoots a little, then rests"
    linear = re.search(r'SPRING = "(linear\([^"]+\))"', spring).group(1)
    assert f"--spring: {linear};" in read("app.css"), "the same curve in css"
    motion = read("lib", "motion.js")
    assert "springAt(t)" in motion and "OVERSHOOT" in motion, "the same spring on the long way in, its overshoot a few pixels (a pane must not go into its neighbour)"
    assert "const delay = snap ? out + 20 : 0;" in motion, "the old panes are gone before the new ones start"
    assert "easing: springAt" in read("lib", "bar.js") and "springAt(p)" in read("components", "List.svelte")
    for rel in (("components", "Tile.svelte"), ("velvet.css",), ("app.css",)):
        assert "var(--spring)" in read(*rel), rel
    assert "cubic-bezier(0.22, 1, 0.36, 1)" not in read("lib", "motion.js")


def test_the_text_has_a_scale_of_its_own() -> None:
    import colorsys

    app = read("app.css")
    light = {}
    for name in ("text-strong", "text", "muted", "faint", "dim"):
        h = re.search(rf"--p-{name}: #(\w{{6}});", app).group(1)
        light[name] = colorsys.rgb_to_hls(*(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)))[1]
    steps = [light[n] for n in ("text-strong", "text", "muted", "faint", "dim")]
    assert all(a - b >= 0.07 for a, b in zip(steps, steps[1:])), f"each step of the scale is a step you can see: {steps}"
    css = read("velvet.css")
    assert "color: var(--p-text-strong)" in css and ".list td.strong" in css
