"""Register `nms mcp` with AI clients, or print the config for any other.

    python scripts/mcp_clients.py install claude [--scope user] [--container] [--dry-run]
    python scripts/mcp_clients.py install codex|opencode|goose|pi [--container] [--dry-run]
    python scripts/mcp_clients.py uninstall claude|codex|opencode|goose|pi|all [--dry-run]
    python scripts/mcp_clients.py config [--container]

Run through the mcp:* mise tasks. Every client gets the same server: `uv run
--directory <this checkout> nms mcp`, or with --container the podman route,
`podman compose -f <this checkout>/compose.yaml run --rm -T tui nms mcp`.

Where a client has a CLI for it -- Claude Code, Codex, pi -- the CLI does the
writing, so its own config format stays its business. opencode and goose have
none that works without prompting, so their files are edited here: backed up
first, and only the nmsii entry is touched. Installing twice gives the same
result as installing once: an existing entry is replaced, not duplicated.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "nmsii"
DESCRIPTION = "NMSii: No Man's Sky recipes, refining chains, nanite routes, storage and portal addresses"
CLIENTS = ["claude", "codex", "opencode", "goose", "pi"]


class Failure(Exception):
    """A refusal with a message for the user, not a traceback."""


def server_command(container: bool) -> list[str]:
    if container:
        return ["podman", "compose", "-f", str(ROOT / "compose.yaml"),
                "run", "--rm", "-T", "tui", "nms", "mcp"]
    return ["uv", "run", "--directory", str(ROOT), "nms", "mcp"]


def require(binary: str, client: str) -> str:
    path = shutil.which(binary)
    if not path:
        raise Failure(f"{client}: `{binary}` is not on PATH - install {client} first, "
                      "or use `mise run mcp:config` for the JSON to paste by hand")
    return path


class Runner:
    """Runs commands, or with dry_run only prints them."""

    def __init__(self, dry_run: bool) -> None:
        self.dry_run = dry_run

    def show(self, cmd: list[str]) -> None:
        # Flushed, so the line lands before the command's own output.
        print(("would run: " if self.dry_run else "$ ") + shlex.join(cmd), flush=True)

    def run(self, cmd: list[str], *, check: bool = True) -> int:
        self.show(cmd)
        if self.dry_run:
            return 0
        code = subprocess.run(cmd).returncode
        if check and code:
            raise Failure(f"`{shlex.join(cmd)}` failed with exit code {code}")
        return code

    def probe(self, cmd: list[str]) -> bool:
        """True when cmd succeeds. Read-only, so it runs even in a dry run."""
        return subprocess.run(cmd, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode == 0


# -- the clients with a CLI -----------------------------------------------------------


def by_cli(run: Runner, label: str, binary: str, container: bool, remove_only: bool,
           scope: list[str]) -> None:
    """Claude Code and Codex: the same get / remove / add / get dance.

    The probe is a read, so it runs in a dry run too, and the dry run shows
    what would really happen: a remove only when there is something to remove.
    """
    require(binary, label)
    exists = run.probe([binary, "mcp", "get", NAME])
    if remove_only:
        if not exists:
            print(f"{label}: {NAME} is not registered, nothing to remove")
            return
        run.run([binary, "mcp", "remove", NAME, *scope])
        return
    if exists:
        print(f"{label}: {NAME} is already registered; replacing it")
        # Scoped, for Claude Code: an entry the user keeps in another scope stays.
        run.run([binary, "mcp", "remove", NAME, *scope], check=False)
    run.run([binary, "mcp", "add", NAME, *scope, "--", *server_command(container)])
    if not run.dry_run:
        run.run([binary, "mcp", "get", NAME], check=False)


def claude(run: Runner, container: bool, scope: str | None, remove_only: bool = False) -> None:
    # Without --scope, `claude mcp remove` removes from whichever scope has it,
    # which is what uninstall wants; install always names one.
    by_cli(run, "Claude Code", "claude", container, remove_only,
           ["--scope", scope] if scope else [])


def codex(run: Runner, container: bool, remove_only: bool = False) -> None:
    # Codex keeps one user-level list (~/.codex/config.toml), so no scope.
    by_cli(run, "Codex", "codex", container, remove_only, [])


def pi(run: Runner, container: bool, remove_only: bool = False) -> None:
    require("pi", "pi")
    # pi has no `mcp get`, and `pi mcp list` connects to every server, so the
    # remove is simply tried: it fails harmlessly when there is nothing to remove.
    run.run(["pi", "mcp", "remove", NAME], check=False)
    if remove_only:
        return
    run.run(["pi", "mcp", "add", NAME, "--", *server_command(container)])


# -- the clients whose file is edited here ----------------------------------------------


def config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def write_file(path: Path, old: str, new: str, dry_run: bool) -> None:
    """Show the diff; unless dry_run, back the file up and write it."""
    if old == new:
        print(f"{path}: nothing to change")
        return
    diff = difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                str(path), str(path))
    sys.stdout.writelines(diff)
    if dry_run:
        print(f"(dry run: {path} not written)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.name}.bak-{stamp}")
        # Two runs in one second must not overwrite the first backup.
        n = 1
        while backup.exists():
            n += 1
            backup = path.with_name(f"{path.name}.bak-{stamp}-{n}")
        shutil.copy2(path, backup)
        print(f"backed up to {backup}")
    path.write_text(new, encoding="utf-8")
    print(f"wrote {path}")


def opencode_path() -> Path:
    base = config_home() / "opencode"
    for name in ("opencode.json", "opencode.jsonc"):
        if (base / name).exists():
            return base / name
    return base / "opencode.json"


def opencode_text(old: str, container: bool | None) -> str:
    """The config with the nmsii entry set (container given) or removed (None).

    Plain JSON only: rewriting a commented .jsonc through json would drop the
    user's comments, so that is refused rather than done.
    """
    try:
        config = json.loads(old) if old.strip() else {}
    except ValueError as exc:
        raise Failure(
            "opencode: the config is not plain JSON (comments?), so it is not rewritten "
            f"here ({exc}). Add this under \"mcp\" by hand:\n"
            + json.dumps({NAME: opencode_entry(bool(container))}, indent=2)) from exc
    if not isinstance(config, dict):
        raise Failure("opencode: the config is not a JSON object")
    servers = config.get("mcp")
    if container is None:
        if not isinstance(servers, dict) or NAME not in servers:
            return old
        del servers[NAME]
    else:
        if servers is None:
            config.setdefault("$schema", "https://opencode.ai/config.json")
            servers = config["mcp"] = {}
        if not isinstance(servers, dict):
            raise Failure("opencode: \"mcp\" in the config is not an object")
        servers[NAME] = opencode_entry(container)
    return json.dumps(config, indent=2, ensure_ascii=False) + "\n"


def opencode_entry(container: bool) -> dict:
    return {"type": "local", "command": server_command(container), "enabled": True}


def opencode(run: Runner, container: bool, remove_only: bool = False) -> None:
    require("opencode", "opencode")
    path = opencode_path()
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    write_file(path, old, opencode_text(old, None if remove_only else container), run.dry_run)


def goose_path() -> Path:
    return config_home() / "goose" / "config.yaml"


def goose_entry(container: bool, indent: str) -> list[str]:
    cmd = server_command(container)
    field = indent * 2
    # Flow-style lists and JSON-quoted strings are valid YAML, and need no
    # YAML library to write; goose rewrites the file in its own style anyway.
    return [
        f"{indent}{NAME}:\n",
        f"{field}enabled: true\n",
        f"{field}type: stdio\n",
        f"{field}name: {NAME}\n",
        f"{field}description: {json.dumps(DESCRIPTION)}\n",
        f"{field}cmd: {json.dumps(cmd[0])}\n",
        f"{field}args: {json.dumps(cmd[1:])}\n",
        f"{field}envs: {{}}\n",
        f"{field}env_keys: []\n",
        f"{field}timeout: 300\n",
        f"{field}bundled: null\n",
    ]


def goose_text(old: str, container: bool | None) -> str:
    """The config with the nmsii extension set (container given) or removed (None).

    Line-based, because the standard library has no YAML: it relies on the
    block style goose itself writes -- a top-level `extensions:` key, one
    indented key per extension. Anything else is refused rather than guessed at.
    """
    lines = old.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    top = [i for i, line in enumerate(lines) if line.split("#")[0].rstrip() in
           ("extensions:", "extensions: {}")]
    if not top:
        if any(line.startswith("extensions") for line in lines):
            raise Failure("goose: `extensions` in the config is not in the block style "
                          "goose writes; add the nmsii extension with `goose configure`")
        if container is None:
            return old
        return "".join(lines + ["extensions:\n"] + goose_entry(container, "  "))
    start = top[0]
    if lines[start].rstrip().endswith("{}"):
        lines[start] = "extensions:\n"
    # The block runs until the next line that is neither blank nor indented.
    end = start + 1
    while end < len(lines) and (not lines[end].strip() or lines[end][0] in " \t"):
        end += 1
    children = [i for i in range(start + 1, end) if lines[i].strip()]
    indent = "  "
    if children:
        first = lines[children[0]]
        indent = first[: len(first) - len(first.lstrip())]
    # Find nmsii's own lines: its key, then everything indented deeper.
    ours = [i for i in children if lines[i] == f"{indent}{NAME}:\n"]
    if ours:
        a = ours[0]
        b = a + 1
        while b < end and (not lines[b].strip() or
                           len(lines[b]) - len(lines[b].lstrip()) > len(indent)):
            b += 1
        new_block = [] if container is None else goose_entry(container, indent)
        lines[a:b] = new_block
    elif container is not None:
        lines[end:end] = goose_entry(container, indent)
    return "".join(lines)


def goose(run: Runner, container: bool, remove_only: bool = False) -> None:
    require("goose", "goose")
    path = goose_path()
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    write_file(path, old, goose_text(old, None if remove_only else container), run.dry_run)


# -- entry points ----------------------------------------------------------------------


def snippet(container: bool) -> str:
    cmd = server_command(container)
    return json.dumps({"mcpServers": {NAME: {"command": cmd[0], "args": cmd[1:]}}}, indent=2)


def install(client: str, args: argparse.Namespace) -> None:
    run = Runner(args.dry_run)
    if client == "claude":
        claude(run, args.container, args.scope)
    else:
        {"codex": codex, "opencode": opencode, "goose": goose, "pi": pi}[client](
            run, args.container)


def uninstall(client: str, args: argparse.Namespace) -> None:
    run = Runner(args.dry_run)
    if client == "claude":
        claude(run, False, args.scope, remove_only=True)
    else:
        {"codex": codex, "opencode": opencode, "goose": goose, "pi": pi}[client](
            run, False, remove_only=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("install", "uninstall"):
        p = sub.add_parser(action)
        p.add_argument("client", choices=CLIENTS + (["all"] if action == "uninstall" else []))
        p.add_argument("--scope", choices=["user", "project", "local"],
                       default="user" if action == "install" else None,
                       help="Claude Code only: where the registration lives "
                       "(install: user; uninstall: whichever has it)")
        p.add_argument("--dry-run", action="store_true",
                       help="print the commands or the file diff, change nothing")
        if action == "install":
            p.add_argument("--container", action="store_true",
                           help="register the podman compose route instead of uv")
    p = sub.add_parser("config")
    p.add_argument("--container", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="accepted for symmetry; config only prints")
    args = parser.parse_args(argv)

    try:
        if args.action == "config":
            print(snippet(args.container))
        elif args.action == "install":
            install(args.client, args)
        elif args.client == "all":
            # Uninstalling everywhere skips the clients that are not installed:
            # there is nothing of ours in a client that is not there.
            for client in CLIENTS:
                print(f"-- {client}")
                try:
                    uninstall(client, args)
                except Failure as exc:
                    print(f"skipped: {exc}")
        else:
            uninstall(args.client, args)
    except Failure as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
