"""Did the game update since our data? If so, prepare the update for review.

Compares the installed game's build (the same detection `game:version` uses,
from extract_game.py) with data/source.json, then:

  current      prints "data is current: <label>"
  blocked      newer build the pinned MBINCompiler cannot read yet: opens or
               updates ONE `game-update` issue for that build, extracts nothing
  update       newer build it reads: branch data/game-<build> from origin/main
               (or the open PR's branch), extract:all, pdf:build, the suite
               (failures are the signal, not an abort), extract:diff, commit,
               push over SSH, open or update the PR "Update data to <label>"

    uv run --extra extract python scripts/game_update.py [--check|--dry-run|--no-pr]

Exit codes: 0 current (or the issue/PR was filed), 2 no game installed or its
build unreadable, 10 update available (--check), 11 update blocked on
MBINCompiler (--check), 1 an error. Safe in CI: without a game it exits 2.

Test hooks: $NMSII_SOURCE_JSON compares against another source.json, and
NMSII_FORCE_MBIN_MISMATCH=1 makes the reader check fail without running it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_game  # noqa: E402

ROOT = extract_game.ROOT
REPO = "Topl1nk/nms-crafting-guide"
LABEL = ("game-update", "0e8a16", "The installed game is newer than data/")
BRANCH_PREFIX = "data/game-"

CURRENT, NO_GAME, UPDATE, BLOCKED, BEHIND = "current", "no-game", "update", "blocked", "behind"
EXIT = {CURRENT: 0, BEHIND: 0, NO_GAME: 2, UPDATE: 10, BLOCKED: 11}

FOLLOW_UP = """\
- [ ] Failing tests: each one is a guide claim the patch moved. Update the
      guide note and the test together (see `docs/cosmos-changes.md`)
- [ ] `docs/`: a `<update>-changes.md` like `docs/cosmos-changes.md`, from the diff above
- [ ] README: the version in "Where the data comes from" (`data/source.json` row)
- [ ] Bump the MBINCompiler pin in `mise.toml` if a newer release was needed
- [ ] Release notes / announcement once merged and deployed"""


# --- comparison (pure, unit-tested) ---------------------------------------------

def compare(installed: dict | None, recorded: dict) -> str:
    """CURRENT, NO_GAME, UPDATE (newer build) or BEHIND (data is newer).

    UPDATE here only means "different and not older"; whether MBINCompiler can
    read it (UPDATE vs BLOCKED) is decided by the reader check afterwards.
    """
    if not installed or not installed.get("build"):
        return NO_GAME
    have, want = str(installed["build"]), str(recorded.get("build") or "")
    if have == want:
        return CURRENT
    if have.isdigit() and want.isdigit() and int(have) < int(want):
        return BEHIND
    return UPDATE


def label_of(version: dict) -> str:
    return version.get("label") or f"build {version.get('build') or '?'}"


def branch_for(build: str) -> str:
    return f"{BRANCH_PREFIX}{build}"


def issue_title(version: dict) -> str:
    return f"Game updated to {label_of(version)}: waiting for MBINCompiler"


def find_numbered(items: list[dict], build: str) -> dict | None:
    """The issue/PR whose title names this build (de-dup key with the label)."""
    pattern = re.compile(rf"(?<!\d){re.escape(build)}(?!\d)")
    return next((i for i in items if pattern.search(i.get("title", ""))), None)


def collapse(markdown: str, summary: str, limit: int = 40, cap: int = 50_000) -> str:
    text = markdown.strip() or "_no changes in data/_"
    if len(text) > cap:
        text = text[:cap] + "\n\n_(truncated; run `mise run extract:diff` for all of it)_"
    if text.count("\n") < limit:
        return text
    return f"<details><summary>{summary}</summary>\n\n{text}\n\n</details>"


def failed_tests(pytest_output: str) -> list[str]:
    return sorted({m.group(1) for m in re.finditer(r"^(?:FAILED|ERROR) (\S+)", pytest_output, re.M)})


def pr_body(version: dict, recorded: dict, diff: str, tests_ok: bool, failures: list[str],
            notes: list[str], closes: int | None) -> str:
    if tests_ok:
        tests = "**Tests:** all passed. No guide number moved."
    else:
        listed = "\n".join(f"- `{f}`" for f in failures) or "- (see the run output)"
        tests = ("**Tests:** failing. Each is a guide claim this patch moved; that is "
                 f"the signal, not a broken extract.\n\n{listed}")
    parts = [
        f"The installed game is **{label_of(version)}** (build {version.get('build')}); "
        f"`data/` was **{label_of(recorded)}** (build {recorded.get('build')}). "
        "Opened by `mise run game:update`.",
        "## What changed\n\n" + collapse(diff, "extract:diff"),
        "## Tests\n\n" + tests,
        *(["## Notes\n\n" + "\n".join(f"- {n}" for n in notes)] if notes else []),
        "## Follow-up (README \"After a game patch\")\n\n" + FOLLOW_UP,
    ]
    if closes:
        parts.append(f"Closes #{closes}")
    return "\n\n".join(parts) + "\n"


def issue_body(version: dict, recorded: dict, problem: str, pinned: str, releases: str) -> str:
    return f"""\
The installed game moved on, but the pinned MBINCompiler cannot read its tables yet, so
`mise run game:update` extracted nothing.

| | build | label |
| --- | --- | --- |
| installed | {version.get('build')} | {label_of(version)} |
| `data/` | {recorded.get('build')} | {label_of(recorded)} |

**MBINCompiler:** pinned `{pinned}` in `mise.toml`. Latest releases (`mise run mbin:releases`):

```
{releases.strip() or '(could not list them)'}
```

<details><summary>What the reader check said</summary>

```
{problem.strip()}
```

</details>

## Next

1. Wait for an MBINCompiler release made for this patch (watch the list above).
2. Pin its tag in `mise.toml`, `mise install`, `mise run game:version`.
3. `mise run game:update`: it extracts, opens the PR, and closes this issue.
"""


# --- shell helpers --------------------------------------------------------------

def run(cmd: list[str], check: bool = True, capture: bool = True, env: dict | None = None
        ) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, cwd=ROOT, text=True, env=env,
                            capture_output=capture)
    if check and result.returncode != 0:
        out = (result.stdout or "") + (result.stderr or "") if capture else ""
        raise SystemExit(f"failed: {' '.join(cmd)}\n{out}")
    return result


def git(*args: str, check: bool = True) -> str:
    return run(["git", *args], check=check).stdout.strip()


def gh_json(*args: str) -> list[dict]:
    result = run(["gh", *args], check=False)
    if result.returncode != 0:
        return []
    return json.loads(result.stdout or "[]")


def pinned_mbincompiler() -> str:
    tools = tomllib.loads((ROOT / "mise.toml").read_text()).get("tools", {})
    return (tools.get("github:monkeyman192/MBINCompiler") or {}).get("version", "?")


def recorded_source() -> dict:
    path = Path(os.environ.get("NMSII_SOURCE_JSON") or ROOT / "data" / "source.json")
    return json.loads(path.read_text()).get("game", {})


def ensure_label(dry_run: bool) -> None:
    name, colour, about = LABEL
    cmd = ["gh", "label", "create", name, "-R", REPO, "--force",
           "--color", colour, "--description", about]
    if dry_run:
        print("would run: " + " ".join(cmd))
    else:
        run(cmd)  # --force makes it idempotent: create or update


def open_issues() -> list[dict]:
    return gh_json("issue", "list", "-R", REPO, "-l", LABEL[0], "--state", "open",
                   "--json", "number,title,url")


# --- paths ----------------------------------------------------------------------

def blocked(version: dict, recorded: dict, problem: str, dry_run: bool) -> int:
    title = issue_title(version)
    releases = run(["mise", "run", "mbin:releases"], check=False).stdout or ""
    body = issue_body(version, recorded, problem, pinned_mbincompiler(), releases)
    existing = find_numbered(open_issues(), str(version["build"]))
    if dry_run:
        verb = f"update issue #{existing['number']}" if existing else "open issue"
        print(f"--- dry run: would {verb}: {title}\n\n{body}")
        return 0
    ensure_label(False)
    tmp = ROOT / ".cache" / "game-update-issue.md"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(body)
    try:
        if existing:
            run(["gh", "issue", "edit", str(existing["number"]), "-R", REPO,
                 "--title", title, "--body-file", str(tmp)])
            print(f"updated {existing['url']}")
        else:
            out = run(["gh", "issue", "create", "-R", REPO, "--title", title,
                       "--label", LABEL[0], "--body-file", str(tmp)]).stdout
            print(f"opened {out.strip()}")
    finally:
        tmp.unlink(missing_ok=True)
    return 0


def safe_to_reset(branch: str, onto: str) -> bool:
    """A local branch may be moved only if it holds nothing `onto` lacks."""
    if run(["git", "rev-parse", "--verify", "-q", f"refs/heads/{branch}"], check=False).returncode:
        return True
    return run(["git", "merge-base", "--is-ancestor", branch, onto], check=False).returncode == 0


def update(version: dict, recorded: dict, dry_run: bool, no_pr: bool) -> int:
    build = str(version["build"])
    branch = branch_for(build)
    label = label_of(version)
    remote_url = git("remote", "get-url", "--push", "origin")
    if not dry_run and not no_pr and not re.match(r"^(git@|ssh://)", remote_url):
        raise SystemExit(f"origin pushes over {remote_url}, not SSH; refusing to push")

    git("fetch", "origin", "main")
    has_remote = run(["git", "fetch", "origin",
                      f"+refs/heads/{branch}:refs/remotes/origin/{branch}"],
                     check=False).returncode == 0
    base = f"origin/{branch}" if has_remote else "origin/main"
    start = git("rev-parse", "--abbrev-ref", "HEAD")
    start = start if start != "HEAD" else git("rev-parse", "HEAD")

    if dry_run:
        git("switch", "--detach", base)
    else:
        if not safe_to_reset(branch, base):
            raise SystemExit(f"local {branch} has commits {base} lacks; push or delete it first")
        git("switch", "-C", branch, base)
    notes: list[str] = []
    try:
        if has_remote:
            merged = run(["git", "merge", "--no-edit", "origin/main"], check=False)
            if merged.returncode:
                run(["git", "merge", "--abort"], check=False)
                raise SystemExit(f"{branch} does not merge origin/main cleanly; fix it by hand")
        print(f"== extract:all on {branch if not dry_run else base + ' (detached)'}", flush=True)
        run(["mise", "run", "extract:all"], capture=False)
        if run(["mise", "run", "pdf:build"], check=False, capture=False).returncode:
            notes.append("`pdf:build` failed, so the PDFs are not in this commit: "
                         "run `mise run pdf:build` and push them")
            run(["git", "checkout", "--", "docs/pdf"], check=False)
        print("== test", flush=True)
        tests = run(["mise", "run", "test"], check=False)
        output = (tests.stdout or "") + (tests.stderr or "")
        print(output.strip().splitlines()[-1] if output.strip() else "(no output)")
        failures = failed_tests(output)
        diff = run(["mise", "run", "extract:diff"], check=False).stdout or ""

        git("add", "data", "docs/pdf")
        if run(["git", "diff", "--cached", "--quiet"], check=False).returncode:
            msg = (f"Update data to {label}\n\n"
                   f"The installed game is build {build}, newer than the {label_of(recorded)} "
                   "the data came from, so the tables were re-extracted with game:update. "
                   + ("The suite passes, so no guide claim moved."
                      if tests.returncode == 0 else
                      f"{len(failures) or 'Some'} guide test(s) now fail: those are the "
                      "claims the patch moved, listed in the PR for review."))
            git("commit", "-q", "-m", msg)
            print(f"committed {git('rev-parse', '--short', 'HEAD')}: Update data to {label}")
        else:
            print("nothing changed in data/ or docs/pdf/ since the branch; no commit")

        issue = find_numbered(
            [i for i in open_issues() if "waiting for MBINCompiler" in i.get("title", "")], build)
        body = pr_body(version, recorded, diff, tests.returncode == 0, failures, notes,
                       issue["number"] if issue else None)
        title = f"Update data to {label}"
        prs = gh_json("pr", "list", "-R", REPO, "--head", branch, "--state", "open",
                      "--json", "number,url,title")
        if dry_run or no_pr:
            what = (f"update PR #{prs[0]['number']}" if prs else "open PR") + f" from {branch}"
            print(f"--- {'dry run' if dry_run else '--no-pr'}: would push {branch} and {what}: "
                  f"{title}\n\n{body}")
            return 0

        assert branch.startswith(BRANCH_PREFIX) and branch != "main"
        # The suite just ran above; the pre-push hook would only run it again
        # and refuse the push on the very failures this PR exists to show.
        run(["git", "push", "-u", "origin", f"{branch}:refs/heads/{branch}"],
            env={**os.environ, "NMSII_SKIP_HOOKS": "1"})
        ensure_label(False)
        tmp = ROOT / ".cache" / "game-update-pr.md"
        tmp.parent.mkdir(exist_ok=True)
        tmp.write_text(body)
        try:
            if prs:
                run(["gh", "pr", "edit", str(prs[0]["number"]), "-R", REPO, "--title", title,
                     "--body-file", str(tmp), "--add-label", LABEL[0]])
                print(f"updated {prs[0]['url']}")
            else:
                out = run(["gh", "pr", "create", "-R", REPO, "--base", "main", "--head", branch,
                           "--title", title, "--label", LABEL[0], "--body-file", str(tmp)]).stdout
                print(f"opened {out.strip()}")
        finally:
            tmp.unlink(missing_ok=True)
        return 0
    finally:
        # Back where the user was; a dry run leaves no branch behind.
        run(["git", "reset", "-q", "--hard"], check=False)
        git("switch", "-q", *(["--detach"] if re.fullmatch(r"[0-9a-f]{40}", start) else []), start)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="only compare and print; exit 0 current, 10 update, 11 blocked, 2 no game")
    mode.add_argument("--dry-run", action="store_true",
                      help="extract and commit on a detached HEAD, print the issue/PR, push nothing")
    mode.add_argument("--no-pr", action="store_true",
                      help="extract and commit on data/game-<build> locally; no push, no PR")
    parser.add_argument("--game", help="No Man's Sky install (default $NMS_GAME_DIR, else GOG)")
    args = parser.parse_args(argv)

    recorded = recorded_source()
    game = extract_game.find_game(args.game)
    version = extract_game.game_version(game) if game else None
    status = compare(version, recorded)
    if status == NO_GAME:
        where = extract_game.game_path(args.game)
        print(f"no game: nothing readable at {where} (set $NMS_GAME_DIR); "
              f"data is {label_of(recorded)}")
        return EXIT[NO_GAME]
    if status == CURRENT:
        print(f"data is current: {label_of(version)}")
        return 0
    if status == BEHIND:
        print(f"data ({label_of(recorded)}) is newer than the installed game "
              f"({label_of(version)}); nothing to do")
        return 0

    print(f"game updated: installed {label_of(version)}, data {label_of(recorded)}", flush=True)
    if os.environ.get("NMSII_FORCE_MBIN_MISMATCH") == "1":
        readable, problem = False, "forced by NMSII_FORCE_MBIN_MISMATCH=1"
    else:
        readable, problem = extract_game.compiler_reads(game)
    status = UPDATE if readable else BLOCKED
    print(f"MBINCompiler {pinned_mbincompiler()}: "
          + ("reads it" if readable else "cannot read it yet"))
    if args.check:
        return EXIT[status]

    if git("status", "--porcelain"):
        raise SystemExit("the working tree is dirty; commit or set it aside first")
    if status == BLOCKED:
        return blocked(version, recorded, problem, args.dry_run)
    return update(version, recorded, args.dry_run, args.no_pr)


if __name__ == "__main__":
    sys.exit(main())
