"""scripts/mcp_clients.py: registering `nms mcp` with AI clients.

Nothing here touches a real client's configuration. The CLI clients (Claude
Code, Codex, pi) are stand-in shell scripts on a PATH of their own that log
how they were called; the file-edited ones (opencode, goose) write under a
temporary XDG_CONFIG_HOME.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import mcp_clients as mc  # noqa: E402

UV = ["uv", "run", "--directory", str(ROOT), "nms", "mcp"]

# A client CLI that remembers one registration in a state file: `mcp get`
# succeeds while it exists, `add` creates it, `remove` deletes it.
# Python rather than sh, because the PATH it runs on holds nothing else.
STUB = """#!{python}
import sys
from pathlib import Path
name = Path(sys.argv[0]).name
with open({log!r}, "a") as log:
    log.write(" ".join([name, *sys.argv[1:]]) + "\\n")
state = Path({state!r} + "." + name)
verb = sys.argv[2] if len(sys.argv) > 2 else ""
if verb == "get":
    sys.exit(0 if state.exists() else 1)
if verb == "add":
    state.touch()
if verb == "remove":
    if not state.exists():
        sys.exit(1)
    state.unlink()
"""


@pytest.fixture
def clients(tmp_path, monkeypatch):
    """Stub claude/codex/pi on an otherwise empty PATH; returns the call log."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    log.touch()
    for name in ("claude", "codex", "pi", "opencode", "goose"):
        path = bin_dir / name
        path.write_text(STUB.format(python=sys.executable, log=str(log),
                                    state=str(tmp_path / "state")))
        path.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    def calls() -> list[str]:
        lines = log.read_text().splitlines()
        log.write_text("")
        return lines

    return calls


# -- the CLI clients ---------------------------------------------------------------


def test_claude_install_is_idempotent(clients):
    uv = " ".join(UV)
    assert mc.main(["install", "claude"]) == 0
    assert clients() == ["claude mcp get nmsii", f"claude mcp add nmsii --scope user -- {uv}",
                         "claude mcp get nmsii"]
    # Again: replaced in its scope, not added twice.
    assert mc.main(["install", "claude", "--scope", "local"]) == 0
    assert clients() == ["claude mcp get nmsii", "claude mcp remove nmsii --scope local",
                         f"claude mcp add nmsii --scope local -- {uv}", "claude mcp get nmsii"]


def test_claude_container_route(clients):
    assert mc.main(["install", "claude", "--container"]) == 0
    add = clients()[1]
    assert add.endswith(f"-- podman compose -f {ROOT / 'compose.yaml'} run --rm -T tui nms mcp")


def test_dry_run_only_reads(clients):
    assert mc.main(["install", "codex", "--dry-run"]) == 0
    # The existence probe is a read and runs; nothing that writes does.
    assert clients() == ["codex mcp get nmsii"]
    assert mc.main(["install", "codex"]) == 0
    clients()
    assert mc.main(["uninstall", "codex", "--dry-run"]) == 0
    assert clients() == ["codex mcp get nmsii"]


def test_uninstall(clients, capsys):
    assert mc.main(["uninstall", "claude"]) == 0
    assert "not registered" in capsys.readouterr().out
    mc.main(["install", "claude"])
    clients()
    assert mc.main(["uninstall", "claude"]) == 0
    # No scope: removed from whichever scope holds it.
    assert clients() == ["claude mcp get nmsii", "claude mcp remove nmsii"]


def test_pi(clients):
    assert mc.main(["install", "pi"]) == 0
    assert clients() == ["pi mcp remove nmsii", f"pi mcp add nmsii -- {' '.join(UV)}"]


def test_missing_client(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PATH", str(tmp_path))
    assert mc.main(["install", "codex"]) == 1
    assert "`codex` is not on PATH" in capsys.readouterr().err
    # `all` skips what is not installed instead of failing.
    assert mc.main(["uninstall", "all"]) == 0
    assert capsys.readouterr().out.count("skipped:") == len(mc.CLIENTS)


def test_config_snippet():
    snippet = json.loads(mc.snippet(False))
    assert snippet == {"mcpServers": {"nmsii": {"command": "uv", "args": UV[1:]}}}
    assert json.loads(mc.snippet(True))["mcpServers"]["nmsii"]["command"] == "podman"


# -- opencode ------------------------------------------------------------------------


def test_opencode_text():
    mine = {"$schema": "https://opencode.ai/config.json", "theme": "x",
            "mcp": {"other": {"type": "local", "command": ["other"]}}}
    old = json.dumps(mine)
    new = json.loads(mc.opencode_text(old, False))
    assert new["theme"] == "x" and new["mcp"]["other"] == mine["mcp"]["other"]
    assert new["mcp"]["nmsii"] == {"type": "local", "command": UV, "enabled": True}
    again = mc.opencode_text(json.dumps(new, indent=2) + "\n", False)
    assert json.loads(again) == new
    gone = json.loads(mc.opencode_text(again, None))
    assert gone["mcp"] == mine["mcp"]
    assert json.loads(mc.opencode_text("", False))["mcp"]["nmsii"]["command"] == UV


def test_opencode_refuses_comments():
    with pytest.raises(mc.Failure, match="not plain JSON"):
        mc.opencode_text('{\n  // mine\n  "theme": "x"\n}\n', False)


def test_opencode_backs_up(clients, tmp_path):
    path = tmp_path / "config" / "opencode" / "opencode.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"theme": "x"}\n')
    assert mc.main(["install", "opencode", "--dry-run"]) == 0
    assert path.read_text() == '{"theme": "x"}\n'
    assert mc.main(["install", "opencode"]) == 0
    assert json.loads(path.read_text())["mcp"]["nmsii"]["command"] == UV
    backups = list(path.parent.glob("opencode.json.bak-*"))
    assert [b.read_text() for b in backups] == ['{"theme": "x"}\n']


# -- goose -----------------------------------------------------------------------------

GOOSE = """GOOSE_MODE: smart_approve
extensions:
  developer:
    enabled: true
    type: platform
    name: developer
    bundled: true

  memory:
    enabled: false
    type: builtin
active_provider: x
"""


def test_goose_text_adds_replaces_removes():
    added = mc.goose_text(GOOSE, False)
    assert added.startswith(GOOSE.split("active_provider")[0])
    assert added.endswith("    bundled: null\nactive_provider: x\n")
    assert "  nmsii:\n    enabled: true\n    type: stdio\n" in added
    # Re-installing with the other route replaces the entry in place.
    swapped = mc.goose_text(added, True)
    assert swapped.count("  nmsii:\n") == 1
    assert '    cmd: "podman"\n' in swapped and '"uv"' not in swapped
    assert mc.goose_text(added, False) == added
    assert mc.goose_text(swapped, None) == GOOSE
    assert mc.goose_text(GOOSE, None) == GOOSE


def test_goose_text_without_extensions():
    assert mc.goose_text("", False).startswith("extensions:\n  nmsii:\n")
    assert mc.goose_text("extensions: {}\nx: 1\n", False).startswith("extensions:\n  nmsii:\n")
    assert mc.goose_text("GOOSE_MODE: auto", False).startswith("GOOSE_MODE: auto\nextensions:\n")
    with pytest.raises(mc.Failure):
        mc.goose_text("extensions: {developer: {enabled: true}}\n", False)


def test_goose_text_keeps_other_indent():
    four = "extensions:\n    developer:\n        enabled: true\n"
    out = mc.goose_text(four, False)
    assert "    nmsii:\n        enabled: true\n" in out
    assert mc.goose_text(out, None) == four
