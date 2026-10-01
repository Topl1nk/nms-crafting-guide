"""The storage layout against the guide it comes from.

24.storage-guide.md, section 10, names items for each of the ten containers.
These tests pin those names to the data, so a rule that shadows one of them
-- or a game patch that renames one -- fails here instead of quietly sending
Cargo Bulkheads to the inbox.
"""

from __future__ import annotations

import pytest

from nms_items.model import Book
from nms_items.storage import StorageGuide

# Section 10's table, verbatim, minus the rows' prose. Container 9 is the inbox
# and names nothing. One name is missing from row 8: Fossil Sample, a real
# item but a procedural one, absent from the game tables this app reads.
GUIDE_TABLE = {
    "0": "Ferrite Dust, Carbon, Sodium, Oxygen, Di-hydrogen, Cobalt, Chromatic Metal,"
         " Silicate Powder, Tritium",
    "1": "Star Bulb, Cactus Flesh, Frost Crystal, Solanium, Gamma Root, Fungal Mould,"
         " Pyrite, Paraffinium, Dioxite, Sulphurine, Radon, Nitrogen",
    "2": "Pure Ferrite, Magnetised Ferrite, Ionised Cobalt, Condensed Carbon, Chlorine,"
         " Gold, Silver, Platinum",
    "3": "Metal Plating, Carbon Nanotubes, Microprocessor, Hermetic Seal, Antimatter,"
         " Warp Cell, Glass",
    "4": "Stasis Device, Quantum Processor, Cryogenic Chamber, Iridesite, Living Glass,"
         " Cryo-Pump, Circuit Board, Superconductor",
    "5": "Salvaged Data, Storage Augmentation, Cargo Bulkhead, Salvaged Frigate Module,"
         " Wiring Loom, Radiant Shard, Navigation Data, Pugneum",
    "6": "Hyperdrive Module, Launch Thrusters Module, Life Support Module,"
         " Exocraft Boost Module, Sentinel Weapons Shard, Repair Kit",
    "7": "Starship AI Valves, Gravitino Ball, Vortex Cube, Albumen Pearl, Storm Crystal,"
         " Sac Venom, Neutron Microscope, Decrypted User Data",
    "8": "Larval Core, Echo Seed, Hadal Core, Fossilised Egg, Companion Egg",
}


@pytest.fixture(scope="module")
def book() -> Book:
    return Book()


@pytest.fixture(scope="module")
def guide() -> StorageGuide:
    return StorageGuide.load()


@pytest.mark.parametrize("container", sorted(GUIDE_TABLE))
def test_guide_items_land_in_their_container(
    book: Book, guide: StorageGuide, container: str
) -> None:
    for name in GUIDE_TABLE[container].split(", "):
        # Some names cover several items (four grades of Hyperdrive Module);
        # every one of them has to agree.
        items = [i for i in book.items.values() if i.name == name]
        assert items, f"{name} is not in the game data"
        for item in items:
            assert guide.place(item).home.key == container, (name, item.id)


def test_every_guide_id_is_a_real_item(book: Book, guide: StorageGuide) -> None:
    for rule in guide.rules:
        for item_id in rule.ids:
            assert item_id in book.items, item_id


def test_one_home_per_named_item(guide: StorageGuide) -> None:
    """The guide's rule: auto-routing only sorts for you if nothing has two homes."""
    seen: dict[str, str] = {}
    for rule in guide.rules:
        for item_id in rule.ids:
            assert item_id not in seen, f"{item_id} in {seen.get(item_id)} and {rule.home}"
            seen[item_id] = rule.home


def test_almost_nothing_is_left_for_the_inbox(book: Book, guide: StorageGuide) -> None:
    inbox = [i.name for i in book.items.values() if guide.place(i).home.key == "9"]
    assert len(inbox) <= 5, inbox


def test_families(book: Book, guide: StorageGuide) -> None:
    def place(item_id: str):
        return guide.place(book.items[item_id])

    assert place("F_ALL_LEG_XL").home.name == "Cold Storage"       # The Lunker
    assert place("F_TRASH_7").action == "discard"                  # Old Boot
    assert place("SPACEGUNK1").action == "discard"                 # Residual Goop
    assert place("TRA_MINERALS1").action == "sell"                 # Dirt
    assert place("SUIT_INV_TOKEN").action == "use"                 # Exosuit Expansion Unit
    assert place("AMMO").home.key == "exosuit"
    assert place("EX_YELLOW").home.key == "2"                      # Activated Copper
    # Scrapping a module pays nanites; the Trade Rocket would destroy it.
    assert place("U_SHIPGUN3").no_rocket
    assert "Trade Rocket" in place("U_SHIPGUN3").advice()


def test_search_finds_by_name_and_by_home(book: Book, guide: StorageGuide) -> None:
    first, placement = guide.search(book, "gravitino")[0]
    assert first.name == "Gravitino Ball"
    assert placement.label == "Sell - park in 7 Sellables"

    junk = guide.search(book, "junk")
    assert junk and all(p.action == "discard" for _, p in junk)

    # An exact name sorts ahead of longer ones that contain it.
    assert guide.search(book, "gold")[0][0].name == "Gold"
