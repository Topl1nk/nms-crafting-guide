# Third-party work in the desktop program

## nms_namegen — the names of systems and planets

`desktop/nms_names.py` is a port to plain Python (without numpy) of the name generator of **nms_namegen**
(<https://github.com/hadsh/nms_namegen>, a fork of Stuart Coyle's nms_namegen with fixes by GoodGuysFree and had.sh),
which works out the names No Man's Sky makes up for regions, star systems and planets from an address or a planet seed.
`data/namegen.json.gz` is its table of letters (the eight letter lists of `generator.py` and `letter_map.json`), flattened
to one lookup per three letters by `scripts/build_namegen.py`, which checks every entry against the original table.
`tests/fixtures/namegen_golden.json` holds a part of its reference vectors (`test/fixtures/golden_vectors.json`).

The names are calculated, not read from the game: they were found by the community by studying the game, so after a game
update some may no longer match. The program says so wherever it shows one.

nms_namegen is distributed under the MIT licence:

```
MIT License

Copyright (c) 2026 Stuart Coyle & had.sh & GGF

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
