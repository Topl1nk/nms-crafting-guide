"""Turn the letter tables of nms_namegen into data/namegen.json.gz, the data desktop/nms_names.py reads.

    python scripts/build_namegen.py --src DIR

DIR is a checkout of https://github.com/hadsh/nms_namegen (MIT, Stuart Coyle & had.sh & GGF; see THIRD_PARTY.md). Only two
things are taken from it, both data and not code: the eight letter lists (ALPHASET_0..7 in nms_namegen/generator.py) and
letter_map.json, the table that says which letter may follow which three. letter_map.json holds the table as a search tree,
5.7 MB with indentation; here it is flattened to one lookup per three letters, which is what the tree answers. Every flattened
entry is checked against a search of the original tree, so the file is the same table, only smaller.
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "namegen.json.gz"


def search(arr, text):
    """The tree search of nms_namegen/generator.py (recursiveSearch), kept as it is to check the flattened table against."""
    i = 0
    while i < len(arr):
        node = arr[i]
        if node[2] == "ja":
            if "".join(reversed(text)) > "".join(reversed(node[0])):
                found = search(node[1], text)
                if found is not None:
                    return found
        elif node[2] == "jz":
            if text == node[0]:
                return node[1]
        i += 1
    return None


def leaves(arr, into: dict, dup: list):
    for key, payload, kind in arr:
        if kind == "ja":
            leaves(payload, into, dup)
        else:
            weights = [[w["Item1"], w["Item2"]] for w in payload]
            if key in into and into[key] != weights:
                dup.append(key)
            into[key] = weights


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--src", required=True, help="a checkout of nms_namegen")
    args = ap.parse_args(argv)
    src = Path(args.src) / "nms_namegen"

    code = (src / "generator.py").read_text(encoding="utf-8")
    alphasets = [re.search(rf'^ALPHASET_{n} = "([a-z]+)"$', code, re.M).group(1) for n in range(8)]
    tree = json.loads((src / "letter_map.json").read_text(encoding="utf-8"))
    if sorted(tree, key=int) != [str(n) for n in range(8)]:
        sys.exit("letter_map.json does not hold alphasets 0..7")

    flat: dict[str, dict] = {}
    rng = random.Random(1)
    letters = "abcdefghijklmnopqrstuvwxyz"
    for a, by_first in tree.items():
        table: dict = {}
        dup: list = []
        for first, arr in by_first.items():
            leaves(arr, table, dup)
        if dup:
            sys.exit(f"alphaset {a}: the same three letters with two different answers: {dup[:5]}")
        for key, weights in table.items():
            if len(key) != 3 or search(tree[a].get(key[0], []), key) != [{"Item1": c, "Item2": w} for c, w in weights]:
                sys.exit(f"alphaset {a}: {key!r} is not what the tree search finds")
        for _ in range(20000):  # three letters the table does not hold must find nothing in the tree either
            key = "".join(rng.choice(letters) for _ in range(3))
            if key not in table and search(tree[a].get(key[0], []), key) is not None:
                sys.exit(f"alphaset {a}: the tree finds {key!r} but the flat table does not")
        flat[a] = table
        print(f"alphaset {a}: {len(table)} entries, {len(alphasets[int(a)]) // 3} letter triples")

    OUT.parent.mkdir(exist_ok=True)
    blob = json.dumps({"alphasets": alphasets, "map": flat}, separators=(",", ":")).encode("ascii")
    with open(OUT, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as gz:
        gz.write(blob)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(blob) // 1024} KB, {OUT.stat().st_size // 1024} KB gzipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
