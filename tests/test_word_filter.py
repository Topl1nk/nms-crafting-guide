"""The game's filter for made-up words (desktop/word_filter.py), whose table was read off NMS.exe."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "desktop"))

import word_filter  # noqa: E402


class Rng:
    """A generator with nms_namegen's step, so the tests need neither numpy nor the package."""

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self.steps = 0

    def _updateSeed(self) -> None:
        self.seed = ((self.seed & 0xFFFFFFFF) * 0x5A76F899) + (self.seed >> 32)
        self.steps += 1


def test_a_clean_word_is_left_alone_and_spends_nothing() -> None:
    rng = Rng(12345)
    assert word_filter.filter_word("odale", rng) == "odale" and rng.steps == 0


def test_a_word_with_a_listed_string_loses_one_letter_and_one_number() -> None:
    rng = Rng(12345)
    word = word_filter.filter_word("eomititu", rng)  # holds "tit": its third letter is changed
    assert rng.steps == 1
    assert word[:6] == "eomiti" and word[6] in "nmbc" and word[7:] == "u"  # "tit" starts at the fifth letter; its third is changed


def test_the_letter_follows_the_draw_as_the_game_takes_it() -> None:
    for start in (1, 2, 3, 99999, 0xABCDEF):
        probe = Rng(start)
        probe._updateSeed()
        wanted = "nmbc"[((probe.seed & 0xFFFFFFFF) * 4) >> 32]
        assert word_filter.filter_word("tit", Rng(start)) == "ti" + wanted
