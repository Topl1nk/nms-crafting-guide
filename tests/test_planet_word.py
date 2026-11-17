"""The word the game puts before "Planet" (desktop/planet_word.py), against planets whose word was read in the game."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "desktop"))

import planet_word  # noqa: E402

# (seed, type number) -> the key of the text the game shows. Russian text in the game: "Зыбк. Планета", "Агрессивная Планета",
# "Зараженная Планета" (Todmoni, Nasiylvan Habik, Ciusil). The English texts of these keys are in data/biomes.json.
SEEN_IN_GAME = [
    (0xE9B95D24F0349812, 12, "SWAMPBIOME8"),
    (0x4DC13FD3FE0AABA8, 1 | (1 << 16), "TOXIC4"),  # this record carries the extra bit
    (0xD6A167C5B7DED3FB, 3, "IRRADIATED3"),
]


@pytest.mark.parametrize(("seed", "vp1", "key"), SEEN_IN_GAME)
def test_words_match_the_game(seed: int, vp1: int, key: str) -> None:
    assert planet_word.word_key(seed, vp1) == key


def test_no_word_where_the_save_does_not_decide_it() -> None:
    assert planet_word.word_key(0xE9B95D24F0349812, 7) == ""            # Weird: the words depend on a variant
    assert planet_word.word_key(0x4DC13FD3FE0AABA8, 1 | (2 << 16)) == ""  # a record with more than the one extra bit seen
    assert planet_word.word_key(0x4DC13FD3FE0AABA8, 11) == ""           # the test biome has no words


def test_the_number_stays_within_the_texts_the_type_has() -> None:
    for seed in range(1, 400):
        for vp1, (prefix, count) in planet_word.WORDS.items():
            key = planet_word.word_key(seed * 0x9E3779B97F4A7C15 & (2**64 - 1), vp1)
            assert key.startswith(prefix) and 1 <= int(key[len(prefix):]) <= count
