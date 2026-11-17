"""The word the game puts before "Planet" (desktop/planet_word.py), against planets whose word was read in the game."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "desktop"))

import planet_word  # noqa: E402

# (seed, biome, variant) -> the key of the text the game shows. Russian texts in the game: "Зыбк. Планета", "Агрессивная Планета",
# "Заражен. Планета", "Опустошенная Планета" (Todmoni, Nasiylvan Habik, Ciusil, Odale VI). The English texts of these keys are in
# data/biomes.json. The variant is the one planet_gen.py works out for the planet (Ciusil is an infested planet).
SEEN_IN_GAME = [
    (0xE9B95D24F0349812, 12, 1, "SWAMPBIOME8"),
    (0x4DC13FD3FE0AABA8, 1, 27, "TOXIC4"),
    (0xD6A167C5B7DED3FB, 3, 24, "INFESTEDRAD1"),
    (0x557B3D1B13177D2A, 5, 21, "BARREN9"),
]


@pytest.mark.parametrize(("seed", "biome", "variant", "key"), SEEN_IN_GAME)
def test_words_match_the_game(seed: int, biome: int, variant: int, key: str) -> None:
    assert planet_word.word_key(seed, biome, variant) == key


def test_no_word_where_it_is_not_known() -> None:
    assert planet_word.word_key(0xE9B95D24F0349812, 7, 1) == ""    # a Weird planet of a variant that has no word of its own
    assert planet_word.word_key(0x4DC13FD3FE0AABA8, 0, 27) == ""   # Lush: it may be "Paradise", which needs weather and sentinels
    assert planet_word.word_key(0x4DC13FD3FE0AABA8, 99, 1) == ""   # no such biome


def test_the_prefix_follows_the_variant() -> None:
    assert planet_word.prefix(0, 25) == "SWAMPBIOME"      # a Lush planet of the Swamp variant
    assert planet_word.prefix(2, 26) == "LAVABIOME"
    assert planet_word.prefix(1, 3) == "RUINEDTOX"
    assert planet_word.prefix(8, 24) == "INFESTED"
    assert planet_word.prefix(7, 12) == "WIRECELLSBIOME"


def test_the_number_stays_within_the_texts_the_prefix_has() -> None:
    for seed in range(1, 300):
        for biome in range(1, 16):
            for variant in (1, 3, 24, 25, 26):
                key = planet_word.word_key(seed * 0x9E3779B97F4A7C15 & (2**64 - 1), biome, variant)
                name = planet_word.prefix(biome, variant)
                if not name:  # a Weird planet of a variant without a word
                    assert key == ""
                    continue
                assert key.startswith(name) and 1 <= int(key[len(name):]) <= planet_word.COUNTS[name]


def test_moons_and_giants_have_a_word_of_their_own() -> None:
    assert planet_word.class_key(1) == "PLANETCLASS1"
    assert planet_word.class_key(3) == "PLANETCLASS2"
    assert planet_word.class_key(4) == "DISC_TYPE_GIANT"
