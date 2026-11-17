"""The game's filter for the made-up words of names (NMS.exe, the routine every generated word goes through at its end).

nms_namegen builds a word and stops there. The game then walks the word letter by letter and, wherever a position starts one
of the strings below, changes one letter of it, taking the choice from a random draw: with n letters to choose from, the
n-th part of the next number of the generator's range picks which. The draw is spent whether or not the letter changes, so a
word with such a string moves every number after it, and with it the rest of the name ("eomititu" holds "tit": the name that
follows is not the one nms_namegen gives). The table was read off the game's routine by running it on every string it reacts
to and on thousands of generator states; the filter below gives what the routine gives. patch() puts it into nms_namegen's
word generator, which is otherwise left as it came.
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


def patch(*modules) -> None:
    """Make the modules' generateName pass each word through the filter (once; a patched module is left alone)."""
    for module in modules:
        original = getattr(module, "generateName", None)
        if original is None or getattr(original, "filtered", False):
            continue

        def generate(rng, alphaset_index, min_length, max_length, _original=original):
            return filter_word(_original(rng, alphaset_index, min_length, max_length), rng)

        generate.filtered = True
        generate.original = original
        module.generateName = generate


def unpatch(*modules) -> None:
    """Put the modules' own generateName back (the tests that check nms_namegen as published)."""
    for module in modules:
        current = getattr(module, "generateName", None)
        if getattr(current, "filtered", False):
            module.generateName = current.original
