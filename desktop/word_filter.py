"""The game's filter for the made-up words of names (NMS.exe, the routine every generated word goes through at its end).

nms_namegen builds a word and stops there. The game then walks the word letter by letter and, wherever a position starts one
of the strings below, changes one letter of it, taking the choice from a random draw: with n letters to choose from, the
n-th part of the next number of the generator's range picks which. The draw is spent whether or not the letter changes, so a
word with such a string moves every number after it, and with it the rest of the name ("eomititu" holds "tit": the name that
follows is not the one nms_namegen gives). The table was read off the game's routine by running it on every string it reacts
to and on thousands of generator states; the filter below gives what the routine gives.

The same routine differed from nms_namegen's word generator in three more places (a rare path when no letters follow the last
three: where the count moves on, which letter is looked at, when a vowel is put in; the vowel put into a run of consonants after
a "y"; the 32-bit arithmetic of the draw), so _game_word_generator() is nms_namegen's generator with those changes, and patch()
puts it into nms_namegen's planet, system and region code, which is otherwise left as it came. scripts/check_names_against_game.py
runs the game's own routine against it (150,000 random inputs, no difference when it was written).
"""
from __future__ import annotations

# string -> (index of the letter it changes, the letters it can become, picked by the draw)
PATTERNS = {
    "ass": (0, "eo"), "cum": (0, "rgsn"), "fag": (0, "nmtz"), "nig": (0, "rvxb"), "sex": (0, "tdrp"), "tit": (2, "nmbc"),
    "wog": (0, "cslv"), "wop": (0, "csld"), "anal": (1, "tdwzx"), "anus": (1, "tdwzx"), "blow": (0, "caog"),
    "clit": (3, "cpfn"), "cock": (0, "smlth"), "cuck": (3, "aeiou"), "cunt": (1, "eio"), "dick": (2, "aeol"),
    "dong": (3, "teo"), "fuck": (0, "zlbw"), "gook": (3, "lnrb"), "homo": (1, "eiu"), "jizz": (0, "zrwl"),
    "kike": (2, "rbl"), "kunt": (3, "aeo"), "love": (2, "mpbt"), "mong": (3, "aoik"), "nazi": (0, "ryvn"),
    "negr": (0, "rvlt"), "orgy": (2, "vlos"), "paki": (2, "ntr"), "pedo": (0, "tmvs"), "piss": (2, "cokl"),
    "porn": (0, "tvbr"), "puss": (0, "brsl"), "quee": (2, "nlr"), "rape": (2, "cnys"), "shag": (3, "nml"),
    "shit": (3, "nvsl"), "slag": (3, "dnvy"), "slut": (2, "aeo"), "spaz": (3, "nlr"), "spic": (3, "nlr"),
    "tard": (0, "jcgwz"), "turd": (3, "nbtp"), "twat": (1, "ehi"), "wank": (3, "aei"), "bitch": (3, "ao"),
    "boner": (0, "lvsz"), "felch": (0, "njkmp"), "minge": (3, "amlz"), "paedo": (0, "tmvs"), "penis": (0, "klsr"),
    "prick": (0, "stbc"), "semen": (2, "tzrv"), "spunk": (1, "lh"), "whore": (0, "csa"), "hitler": (0, "vmpl"),
}
_LONGEST = max(map(len, PATTERNS))


def filter_word(word: str, rng) -> str:
    """The word as the game leaves it; `rng` is the name's generator (nms_namegen's PRNG), advanced as the game advances it."""
    letters = list(word)
    for i in range(len(letters)):
        text = "".join(letters)
        for size in range(3, _LONGEST + 1):  # the strings differ by their letters: at most one of them starts here
            hit = PATTERNS.get(text[i:i + size])
            if hit:
                at, options = hit
                rng._updateSeed()
                letters[i + at] = options[((rng.seed & 0xFFFFFFFF) * len(options)) >> 32]
                break
    return "".join(letters)


def _consecutive_consonants(name: str) -> int:
    """Where the game puts a vowel into a run of consonants, or -1: after three consonants in a row, a letter that is no vowel and
    no "y" is where it breaks. A "y" ends the run and then counts as a consonant itself (nms_namegen starts the count again)."""
    run = 0
    for i, letter in enumerate(name):
        if run == 3:
            if letter not in "aeiouy":
                return i - 3
            run = 0
        run = 0 if letter in "aeiou" else run + 1
    return -1


def _game_word_generator():
    """nms_namegen's generateName as the game runs it, with the game's filter at its end. It is nms_namegen's code with one
    change, found by running the game's routine against it on thousands of inputs: when no letters follow the last three
    (the routine then tries the next of the eight letter tables), nms_namegen starts the replacement letters from the table it
    has moved to, the game from the table the word was begun with."""
    import numpy as np
    from nms_namegen import generator as g

    def generate(rng, alphaset_index, min_length, max_length):
        first_set = alphaset_index
        alternate = False
        name = g.getCharactersFromAlphaset(rng, alphaset_index)
        if rng.randi() & 0x01:
            alternate = True
        register = rng.random(max_length - min_length + 0x01) + min_length - 0x03
        add = register
        if register > 0:
            index, tries, i = 0, 8, 0
            while i < register:
                weights = g.getStringWeights(name[-3:], alphaset_index)  # the last three letters, whatever came before
                target = np.float32(rng.randi() * g.TINY_DOUBLE)  # the game works in 32 bits here
                if weights is None:
                    tries -= 1
                    i -= 1
                    alphaset_index = (alphaset_index + 1) & 0x08000007
                    if alphaset_index < 0:
                        alphaset_index = -alphaset_index
                    if tries == 0:
                        if add < 3:
                            break
                        temp = g.getCharactersFromAlphaset(rng, first_set)
                        before = name[i + 3] in "aeiou"  # the letter the game looks at (not the last one once this has happened before)
                        if before and temp[0] in "aeiou":
                            name += "'"
                        elif not before and temp[0] not in "aeiou":
                            name += "aeiou"[rng.random(5) & 0xFF]
                        name += temp
                        tries = 1
                        i += 3
                        add -= 3
                else:
                    if alternate:
                        target = np.float32(target * np.float32(len(weights) - 1))
                        index = int(np.float32(np.sign(target) * np.float32(0.5)) + target)
                    else:
                        weight = np.float32(0.0)
                        for j in range(len(weights)):
                            weight = np.float32(weight + np.float32(weights[j]["Item2"]))
                            if weight >= target:
                                break
                        index = j
                    name += weights[index]["Item1"]
                    add -= 1
                if len(name) > 63:
                    name = name[:63]
                i += 1
        first, second = name[0], name[1]
        if first not in "aeiou" and second not in "aeiou":
            if first != "s" or second not in "hklmnprtwy":
                if not ((second == "h" and first in "ctw") or (second == "l" and first in "bcfgps")
                        or (second == "r" and first in "bcdfgkpt") or (second == "w" and first in "dgt")
                        or (second == "y" and first in "hmr")):
                    name = g.insertVowel(name, rng, 1)
        if len(name) > 1:
            ult, penult = name[-1], name[-2]
            if penult != "g" or ult in "aeiou":
                if ((ult == "b" and penult in "gn") or (ult == "d" and penult in "bdfghkmpst") or (ult == "g" and penult == "l")
                        or (ult == "p" and penult in "bdhkt") or (ult == "r" and penult in "bfg") or (ult == "t" and penult == "g")
                        or (ult == "w" and penult not in "aeiou")):
                    name = g.insertVowel(name, rng, len(name) - 1)
        consonance = _consecutive_consonants(name)
        if consonance != -1:
            consonance += rng.random(3) + 1
            name = g.insertVowel(name, rng, consonance)
        return filter_word(name, rng)

    return generate


def patch(*modules) -> None:
    """Give the modules (nms_namegen's planet, system and region) the game's word generator (once; a patched module is left alone)."""
    generate = None
    for module in modules:
        original = getattr(module, "generateName", None)
        if original is None or getattr(original, "filtered", False):
            continue
        generate = generate or _game_word_generator()
        generate.filtered = True
        generate.original = original
        module.generateName = generate


def unpatch(*modules) -> None:
    """Put the modules' own generateName back (the tests that check nms_namegen as published)."""
    for module in modules:
        current = getattr(module, "generateName", None)
        if getattr(current, "filtered", False):
            module.generateName = current.original
