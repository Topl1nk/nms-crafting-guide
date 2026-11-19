# Updating the README (all languages), its screenshots, and the Steam guide

Everything that has to be done when the program gains something worth telling, in the order it is done. Nothing here needs to
be rediscovered: the screenshots are taken by a script, the texts follow fixed anchors.

## What there is

| What | Where |
| --- | --- |
| English README | `README.md` |
| 13 translations | `docs/readme/README.<code>.md`: `ru`, `pt-BR`, `pt`, `es`, `fr`, `de`, `it`, `nl`, `pl`, `ja`, `ko`, `zh-CN`, `zh-TW` |
| Screenshots | `docs/img/site-*.webp` (English) and `docs/img/<code>/site-*.webp`, nine pages each, 1920x1080, dark |
| Screenshot script | `scripts/readme_shots.py` |
| Steam guide (outside the repository, English only) | `NMSii/steam-guide/00-guide-info.txt`, one text file per section in `sections/`, pictures in `images-en/` |
| Developer README | `docs/DEVELOPERS.md` (English only, not part of this routine) |

## 1. Texts

The README is a list of short bullets; a new thing is one more bullet, in the same place in every language.

- **Features list** ("What is it?"): one line `- <emoji> **Title.** text`. The order is recipes, tree, food, storage, loops, portals,
  *planets*, multi-tools, languages, privacy. New features go before multi-tools.
- **Privacy line** (🔒, last of that list): it must stay true. Today it says that the only network request is the one to GitHub
  asking whether a newer version is out. If the program ever asks for anything else, say so there, in every language.
- **"Good to know"**: the bullets between the settings/theme one and the `docs/pdf/` one. New ones go before the `docs/pdf/` line.
- Emoji per bullet are fixed: 🧪 🌳 🍲 📦 🔁 🔭 🪐 ⚔️ 🌍 🔒. Check them after a translation pass; an earlier pass once lost
  the 🌍 and put it on the privacy line in 12 languages.
- Translate in the voice each file already uses (German and French and Russian say "you" formally, Spanish and Italian informally,
  Portuguese in Portugal formally, in Brazil "você"). Do not name pages by their menu words (translations of those differ per
  language); say "the page that reads the save".
- Line ends are LF or CRLF as the file has them; keep that.

The helper is `scripts/readme_add_bullets.mjs`: `node scripts/readme_add_bullets.mjs bullets.json`. `bullets.json` holds, per
file, `P` (a bullet after the portals one), `T` (text appended to the privacy bullet), `S` and `U` (two "Good to know" bullets).
`docs/readme-bullets.example.json` is the file of 2026-11-19 (planets, the one GitHub request, the save in settings, updates), with all
14 languages: copy it, replace the texts, run. It finds the `- 🔭` line and the line holding `docs/pdf`, fixes the emoji of the
translations and inserts; it refuses to run twice on the same change (it looks for a 🪐 bullet; change that check for a new
feature). Edit single lines by hand when the change is only a rewording.

## 2. Screenshots

1. Build the site: `node node_modules/vite/bin/vite.js build` in `app/` (with `NMS_LANG=english`). `dist/lang/` must hold all
   languages (it is copied from `web/lang/`, which `scripts/build_langs.py` writes from the installed game; it is already there
   unless the game files changed).
2. `pip install playwright pillow` (once; Chrome must be installed). Set `NMS_LAUNCHER_PYTHON` to the Python that has the
   program's requirements (`desktop/requirements.txt`; the repo's `.uv\venv` has them) and `NMS_SHOTS_VERSION` to the version being
   released (Settings shows "you have the latest version" with it), then run `python scripts/readme_shots.py` (all 14 sets, about
   10 minutes), or with codes: `python scripts/readme_shots.py en ru`. `--steam` also writes the Steam guide's pictures
   (English only, `NMSii/steam-guide/images-en/NN-name.jpg`); `--no-launcher` leaves out Planets and Settings.
3. Look at one or two pictures (`site-planets.webp` and `site-settings.webp` need the game, its pictures and a save).

The script serves `dist/` itself and starts the desktop program (without its window) for the two pages that need it, Planets and
Settings. The program reads the player's real save, so it is put behind a small server that **cleans the save on its way to the
page** (`clean()` in the script): planets and systems the player named, the names of bases, ships and exocraft are dropped, and only
what the game itself names is shown. Check a Planets picture for a name that is not the game's own before committing it.

## 3. Steam guide

The Steam guide is in English only, and it is one text file **per section** (the way Steam wants it): `NMSii/steam-guide/00-guide-info.txt`
(title, the line under it, categories, what goes where) and `NMSii/steam-guide/sections/NN-name.txt`, fifteen of them, in order: What is
it, How to install, The windows, Craft (with cooking and nanites), Tree, Wiki, My items, Planets, Portals, Multi-tools, Settings, Help
and keys, Good to know, Is it safe, Links. The first lines of a file are the section's title, the text under the marked line is pasted
into the section. They are in Steam's markup (`[h2]`, `[list]`, `[url=...]`). A new window or feature gets its own file (number the
next ones after the last), and the same sentences go to 01 (the short list), 13 and 14 (the privacy sentence). `[IMAGE n: file]` marks
where a picture goes; the files are in `images-en/` (1920x1080 jpg, `NN-name.jpg`), written by
`python scripts/readme_shots.py --steam` (STEAM_ORDER in the script lists them: add a page to LAUNCHER_PAGES or PAGES and to STEAM_ORDER
for a new picture). Numbers in the text (2,292 items, 1,688 recipes) come from the data: check them against the Wiki and Craft pages
when the data changes.

## 5. The new sections of the README

`scripts/readme_add_section.mjs sections.json` adds, to the README and its 13 translations, two pictures with captions at the end of
the first screenshot table, a text section under it and one bullet in "Good to know"; `docs/readme-sections.example.json` is the
file of 2026-11-19 (the planets section and the search in any language). Like the bullets helper it refuses to run twice.

## 4. Check and commit

- `git diff --stat README.md docs/readme docs/img` should list 14 READMEs and, for pictures, whole sets only.
- Open `README.md` and one translation on GitHub (or any Markdown preview) and look at the list and the emoji.
- Commit the READMEs and the pictures together: "README: <what changed>, all languages".
