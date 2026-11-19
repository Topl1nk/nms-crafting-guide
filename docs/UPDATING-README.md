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
| Steam guide (outside the repository) | `NMSii/steam-guide/guide.en.txt`, `guide.ru.txt`, pictures in `images-en/`, `images-ru/` |
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
2. `pip install playwright pillow` (once; Chrome must be installed) and run `python scripts/readme_shots.py`
   (all 14 sets, about 5 minutes) or with codes: `python scripts/readme_shots.py en ru`.
3. Look at one or two pictures (`docs/img/ru/site-inventory.webp` shows the typed list in place of a save).

The script serves `dist/` itself, so no server has to be started. The pictures use no save and no launcher, so they have no
personal data, and the Planets page (which needs a save) is **not** in the README set. If it is ever to be, take it from the
desktop program with a test save, never with a real one (real planet names are the player's own).

## 3. Steam guide

`NMSii/steam-guide/guide.en.txt` and `guide.ru.txt` are written in Steam's markup (`[h1]`, `[list]`, `[url=...]`). Update the
same places as the README: the short description, "What it can do", "Is it safe?" (the privacy sentence), and the settings
section. `[IMAGE n: file]` marks where a picture goes; the files are in `images-en/` and `images-ru/` (1920 wide jpg). A new
page needs a new picture: take it with the desktop program, crop to 16:9.

## 4. Check and commit

- `git diff --stat README.md docs/readme docs/img` should list 14 READMEs and, for pictures, whole sets only.
- Open `README.md` and one translation on GitHub (or any Markdown preview) and look at the list and the emoji.
- Commit the READMEs and the pictures together: "README: <what changed>, all languages".
