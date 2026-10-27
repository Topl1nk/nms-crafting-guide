"""Runs the node:test files in tests/js/ (the craft-tree planner and the Russian
helpers) as part of pytest, so one command covers the Python and the site."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path(__file__).parent / "js"
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="needs node")
@pytest.mark.parametrize("path", sorted(JS.glob("*.test.mjs")), ids=lambda p: p.name)
def test_node_suite(path: Path) -> None:
    result = subprocess.run([NODE, "--test", str(path)], capture_output=True, text=True, timeout=900)
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-1000:]
