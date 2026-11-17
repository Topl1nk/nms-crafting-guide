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


import pytest  # noqa: E402

# Words and the generator state the game's own routine (NMS.exe, run on its own) left behind, for inputs where nms_namegen's
# generateName went another way: the letters after the last three are not in the table (the apostrophe cases), a run of
# consonants, a "y". (alphabet set, shortest, longest, the generator's two halves) -> (word, the generator's halves after it)
FROM_THE_GAME = [
    ((0, 5, 10, 3455889666, 1879152050), "ongzi'ihlan", (2917711707, 628206463)),
    ((0, 6, 10, 3323089296, 1076715195), "netxelwi", (1670673441, 774103384)),
    ((1, 6, 10, 576955318, 42816082), "mepfluthrell", (1204789845, 578600832)),
    ((2, 7, 12, 4088371166, 2109023089), "haefilskygugn", (3869059615, 786071663)),
    ((4, 5, 9, 471477094, 1608122770), "ialilingg", (1558564053, 938374049)),
    ((3, 7, 12, 277694675, 599185707), "poslovke'ogal", (419226268, 854640944)),
    ((7, 4, 7, 2132519730, 1067883041), "litbyocks", (1827113661, 1121821400)),
    ((7, 4, 8, 12345, 678), "kulav", (4174815804, 330053558)),
]


@pytest.mark.parametrize(("given", "word", "after"), FROM_THE_GAME)
def test_the_word_generator_gives_what_the_games_routine_gives(given, word, after) -> None:
    pytest.importorskip("numpy")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "third_party" / "nms_namegen"))
    from nms_namegen.prng import PRNG
    alphaset, shortest, longest, low, high = given
    rng = PRNG((high << 32) | low)
    assert word_filter._game_word_generator()(rng, alphaset, shortest, longest) == word
    assert (rng.seed & 0xFFFFFFFF, rng.seed >> 32) == after


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
