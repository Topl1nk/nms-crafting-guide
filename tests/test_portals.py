"""Portal address conversion, and the addresses committed in data/.

The conversion is the only piece of arithmetic in this project that is not
checkable against the game files, so it is pinned three ways: the constants
match nmsportals.github.io, the two frames agree with each other over the whole
address space, and the one fact both agree on -- where the centre of the galaxy
is -- lands where it should.
"""

from __future__ import annotations

import json
import random

import pytest

from nms_items.portals import (
    GLYPH_NAMES,
    ORIGINS,
    Address,
    AddressError,
    Location,
    LocationBook,
    galaxy_name,
)
from nms_items.model import DATA_DIR


# -- the conversion -------------------------------------------------------


def test_galaxy_centre() -> None:
    """Portal 0,0,0 is the galaxy centre, which galactic coords call 07FF:007F:07FF.

    This is the anchor: get a constant wrong and this moves.
    """
    centre = Address.from_portal_code("000000000000")
    assert centre.galactic == "07FF:007F:07FF:0000"
    assert centre.voxel == (0, 0, 0)
    assert Address.from_galactic("07FF:007F:07FF:0000").voxel == (0, 0, 0)


def test_round_trip_over_the_whole_space() -> None:
    rng = random.Random(20260907)
    for _ in range(5000):
        address = Address(
            planet=rng.randrange(16),
            system=rng.randrange(0x430),
            y=rng.randrange(0x100),
            z=rng.randrange(0x1000),
            x=rng.randrange(0x1000),
        )
        back = Address.from_galactic(address.galactic, planet=address.planet)
        assert back == address, address.portal_code
        assert Address.from_portal_code(address.portal_code) == address


def test_field_layout() -> None:
    """p SSS YY ZZZ XXX -- planet, system, then height, width, length."""
    address = Address.from_portal_code("40E907FF0D6B")
    assert (address.planet, address.system) == (4, 0x0E9)
    assert (address.y, address.z, address.x) == (0x07, 0xFF0, 0xD6B)
    assert address.portal_grouped == "4 0E9 07 FF0 D6B"
    assert address.galactic == "056A:0086:07EF:00E9"


def test_voxels_are_signed_from_the_centre() -> None:
    far = Address.from_portal_code("0000FF800800")
    x, y, z = far.voxel
    assert (x, y, z) == (-2048, -1, -2048)
    assert "-2048" in far.voxel_label


def test_glyph_names_follow_the_dial() -> None:
    """The hex digit is the position on the dial, so A is the eleventh symbol."""
    assert len(GLYPH_NAMES) == 16
    assert GLYPH_NAMES[0] == "sunset"
    assert GLYPH_NAMES[0xA] == "voxel"
    assert GLYPH_NAMES[0xF] == "atlas"
    assert Address.from_portal_code("0123456789AB").glyph_names[10] == "voxel"


@pytest.mark.parametrize(
    "text",
    [
        "40E907FF0D6B",
        "40e907ff0d6b",
        "40E9 07FF 0D6B",
        "https://nmsportals.github.io/#40E907FF0D6B",
        "056A:0086:07EF:00E9",
        "056A 0086 07EF 00E9",
    ],
)
def test_parse_takes_whatever_was_pasted(text: str) -> None:
    address = Address.parse(text, planet=4)
    assert address.portal_code == "40E907FF0D6B"


@pytest.mark.parametrize(
    "text",
    ["", "not an address", "40E907FF0D6", "056A:0086:07EF", "1FFF:0086:07EF:00E9"],
)
def test_bad_input_is_refused(text: str) -> None:
    with pytest.raises(AddressError):
        Address.parse(text)


def test_planet_glyph_is_the_one_galactic_coords_lose() -> None:
    """A galactic address carries no planet, so converting back picks one."""
    assert Address.from_galactic("056A:0086:07EF:00E9").planet == 0
    assert Address.from_galactic("056A:0086:07EF:00E9", planet=4).planet == 4
    swapped = Address.parse("40E907FF0D6B").with_planet(9)
    assert swapped.portal_code == "90E907FF0D6B"
    assert swapped.galactic == Address.parse("40E907FF0D6B").galactic


def test_out_of_range_system_warns_but_still_converts() -> None:
    assert not Address.from_portal_code("40E907FF0D6B").warnings
    high = Address.from_portal_code("4FFF07FF0D6B")
    assert high.warnings and "0x429" in high.warnings[0]
    assert high.galactic.endswith(":0FFF")


def test_galaxy_names() -> None:
    assert galaxy_name(1) == "Euclid"
    assert galaxy_name(10) == "Eissentam"
    assert galaxy_name(42) == "Galaxy 42"


# -- the saved-address file ------------------------------------------------


def test_committed_locations_are_all_dialable() -> None:
    """Every address in data/locations.json must survive a round trip."""
    book = LocationBook.load()
    assert len(book) >= 15
    assert book.source, "the file must say where the addresses came from"
    for loc in book.locations:
        assert loc.address.portal_code == loc.code, loc.name
        assert not loc.address.warnings, (loc.name, loc.address.warnings)
        assert loc.galaxy >= 1
        assert loc.kind in {"multi-tool", "starship", "freighter", "base",
                            "planet", "system", "other"}
        assert loc.origin in ORIGINS
        assert loc.detail or loc.where, f"{loc.name} says nothing about itself"


def test_everything_shipped_is_marked_shared() -> None:
    """None of the committed addresses were found here -- they are catalogue rows.

    The distinction is the point of the field: your own finds you can vouch
    for, and these carry somebody else's class claim on somebody else's save.
    """
    book = LocationBook.load()
    assert book.count("shared") == len(book)
    assert book.count("mine") == 0
    assert all(loc.source for loc in book.locations)


def test_the_two_for_one_addresses_are_the_ones_the_guides_name() -> None:
    """Guides 14 and 21 both point at these two systems; keep them in step."""
    book = LocationBook.load()
    by_code = {loc.code: loc for loc in book.locations}
    assert by_code["11AC008F4025"].kind == "multi-tool"   # Hamonkle VI
    assert by_code["105EFD9D4303"].kind == "starship"     # UptonicaXIX
    assert "S-class" in by_code["105EFD9D4303"].detail


def test_locations_file_is_not_hand_broken() -> None:
    raw = json.loads((DATA_DIR / "locations.json").read_text())
    assert set(raw) >= {"_source", "_note", "locations"}


def test_book_round_trips_through_disk(tmp_path) -> None:
    path = tmp_path / "locations.json"
    book = LocationBook(path=path, source="test")
    book.add(
        Location(
            name="Hamonkle VI",
            code="11AC008F4025",
            kind="multi-tool",
            galaxy=1,
            detail="Grey/white rifle",
        )
    )
    book.add(Location(name="Konslis", code="1006FD532B7E", kind="starship"))

    reloaded = LocationBook.load(path)
    assert [loc.name for loc in reloaded.locations] == ["Hamonkle VI", "Konslis"]
    assert reloaded.source == "test"
    assert reloaded.search("rifle")[0].name == "Hamonkle VI"
    assert len(reloaded.search("", kind="starship")) == 1
    assert reloaded.search("hamonkle grey")  # every word has to match
    assert not reloaded.search("hamonkle konslis")

    reloaded.remove(0)
    assert [loc.name for loc in LocationBook.load(path).locations] == ["Konslis"]


def test_dropping_moves_to_the_trash_rather_than_deleting(tmp_path) -> None:
    """`d` is one key from `s`, so a drop has to be survivable."""
    path = tmp_path / "locations.json"
    book = LocationBook(path=path)
    for name, code in (
        ("A", "11AC008F4025"), ("B", "1006FD532B7E"), ("C", "6046FFAE4450")
    ):
        book.add(Location(name=name, code=code))

    gone = book.remove(1)
    assert gone.name == "B"
    assert [loc.name for loc in book.locations] == ["A", "C"]
    assert [loc.name for loc in book.trash] == ["B"]
    assert gone.dropped  # dated on the way out

    # It has to survive the trip through disk, or the trash is a lie.
    reloaded = LocationBook.load(path)
    assert [loc.name for loc in reloaded.trash] == ["B"]

    # And come back where it was, not appended to the end.
    back = reloaded.restore()
    assert back.name == "B"
    assert [loc.name for loc in reloaded.locations] == ["A", "B", "C"]
    assert reloaded.trash == []
    assert not back.dropped and back.dropped_from == -1
    assert [loc.name for loc in LocationBook.load(path).locations] == ["A", "B", "C"]


def test_restoring_an_empty_trash_is_a_no_op(tmp_path) -> None:
    book = LocationBook(path=tmp_path / "locations.json")
    assert book.restore() is None
    assert book.purge(0) is None
    assert book.empty_trash() == 0


def test_the_trash_can_be_emptied_and_picked_through(tmp_path) -> None:
    path = tmp_path / "locations.json"
    book = LocationBook(path=path)
    for name, code in (
        ("Sunset", "11AC008F4025"),
        ("Balloon", "1006FD532B7E"),
        ("Dragonfly", "6046FFAE4450"),
    ):
        book.add(Location(name=name, code=code))
    book.remove(0)
    book.remove(0)
    assert [loc.name for loc in book.trash] == ["Sunset", "Balloon"]

    # searchable while it is in there, and gone from the live list
    assert [loc.name for loc in book.search("sunset", trash=True)] == ["Sunset"]
    assert not book.search("sunset")

    assert book.purge(0).name == "Sunset"
    assert [loc.name for loc in book.trash] == ["Balloon"]
    assert book.empty_trash() == 1
    assert LocationBook.load(path).trash == []


def test_trash_only_fields_stay_out_of_the_live_list(tmp_path) -> None:
    """A record that is not in the trash should not carry drop bookkeeping."""
    path = tmp_path / "locations.json"
    book = LocationBook(path=path)
    book.add(Location(name="A", code="11AC008F4025"))
    book.add(Location(name="B", code="1006FD532B7E"))
    book.remove(1)

    raw = json.loads(path.read_text())
    assert "dropped" not in raw["locations"][0]
    assert "dropped_from" not in raw["locations"][0]
    assert raw["_trash"][0]["dropped_from"] == 1


def test_the_committed_file_has_nothing_in_the_trash() -> None:
    """A dropped address should not ship; it means somebody forgot to look."""
    assert LocationBook.load().trash == []


def test_origin_splits_the_two_kinds_of_find(tmp_path) -> None:
    path = tmp_path / "locations.json"
    book = LocationBook(path=path)
    book.add(Location(name="Mine", code="11AC008F4025", origin="mine"))
    book.add(Location(name="Theirs", code="1006FD532B7E", origin="shared"))

    back = LocationBook.load(path)
    assert back.count("mine") == 1 and back.count("shared") == 1
    assert [loc.name for loc in back.search(origin="mine")] == ["Mine"]
    assert [loc.name for loc in back.search(origin="shared")] == ["Theirs"]
    assert len(back.search()) == 2
    # kind and origin narrow independently
    assert not back.search(kind="starship", origin="mine")
    assert back.search("mine")[0].name == "Mine"  # origin is searchable text


def test_saving_stamps_a_date_unless_one_is_given(tmp_path) -> None:
    from datetime import date

    book = LocationBook(path=tmp_path / "locations.json")
    book.add(Location(name="Fresh", code="11AC008F4025"))
    book.add(Location(name="Dated", code="1006FD532B7E", added="2026-09-07"))
    assert book.locations[0].added == date.today().isoformat()
    assert book.locations[1].added == "2026-09-07"


def test_an_unknown_origin_falls_back_rather_than_vanishing(tmp_path) -> None:
    path = tmp_path / "locations.json"
    path.write_text(
        json.dumps({"locations": [
            {"name": "odd", "code": "11AC008F4025", "origin": "borrowed"},
            {"name": "bare", "code": "1006FD532B7E"},
        ]})
    )
    book = LocationBook.load(path)
    assert [loc.origin for loc in book.locations] == ["mine", "mine"]


def test_a_typo_in_the_file_does_not_take_the_screen_down(tmp_path) -> None:
    path = tmp_path / "locations.json"
    path.write_text(
        json.dumps(
            {
                "locations": [
                    {"name": "fine", "code": "11AC008F4025"},
                    {"name": "eleven glyphs", "code": "11AC008F402"},
                    {"name": "no code at all"},
                ]
            }
        )
    )
    book = LocationBook.load(path)
    assert [loc.name for loc in book.locations] == ["fine"]
