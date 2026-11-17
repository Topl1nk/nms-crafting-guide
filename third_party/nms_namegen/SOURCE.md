# Where this copy comes from

A copy, unchanged, of **nms_namegen** by Stuart Coyle, had.sh and GoodGuysFree (MIT licence, see `LICENCE`):

- repository: <https://github.com/hadsh/nms_namegen> (a fork of <https://github.com/stuart/nms_namegen>)
- commit: `52ad48affaa4089c8f487a470a888dc9b7a650aa` (2026-08-27, "Merge pull request #3 from GoodGuysFree/feat/batch-mode")
- copied: `LICENCE`, `README.md`, `pyproject.toml`, `namegen.py`, the package `nms_namegen/` (with `letter_map.json`), and from `test/`
  only `test_golden_vectors.py` with `fixtures/golden_vectors.json` and `fixtures/system_names.json`. The other test files and
  fixtures (the 1.1 MB ground-truth list, `region_names.json`) are not needed to run those and were left out.

It is a copy and not a submodule so that building this program needs no other repository. To update it, copy the same files
from a newer commit and change the commit above. It needs Python 3.13 and numpy (see `pyproject.toml`); desktop/nms_save.py
uses it to work out the names of systems and planets the save does not hold.
