"""Download the two files the packaged app carries from MBINCompiler's release into desktop/vendor/:
the decompiler for the current platform (reads the game's tables) and mapping.json (reads the player's saves).

    python desktop/fetch_tools.py [--platform windows|linux]

The version is the one mise.toml pins, so the packaged app reads the same game tables the checkout does.
"""
import argparse
import os
import re
import stat
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDOR = HERE / "vendor"
TAG = re.search(r'\[tools\."github:monkeyman192/MBINCompiler"\]\s*version\s*=\s*"([^"]+)"',
                (HERE.parent / "mise.toml").read_text(encoding="utf-8")).group(1)
BASE = f"https://github.com/monkeyman192/MBINCompiler/releases/download/{TAG}"
# release asset -> name it is kept under (paths.mbincompiler)
ASSETS = {
    "windows": {"MBINCompiler.exe": "MBINCompiler.exe", "libMBIN.dll": "libMBIN.dll", "mapping.json": "mapping.json"},
    "linux": {"MBINCompiler-linux": "MBINCompiler", "mapping.json": "mapping.json"},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", choices=sorted(ASSETS), default="windows" if os.name == "nt" else "linux")
    ap.add_argument("--tag", default=TAG, help="MBINCompiler release (default: the one mise.toml pins)")
    args = ap.parse_args()
    base = BASE.replace(TAG, args.tag)
    VENDOR.mkdir(exist_ok=True)
    for asset, name in ASSETS[args.platform].items():
        target = VENDOR / name
        print(f"{base}/{asset} -> {target}", flush=True)
        try:
            urllib.request.urlretrieve(f"{base}/{asset}", target)
        except Exception as exc:  # noqa: BLE001
            if asset == "libMBIN.dll":  # only some releases ship it apart from the exe
                print(f"  (skipped: {exc})")
                continue
            sys.exit(f"could not fetch {asset}: {exc}")
        if name == "MBINCompiler":
            target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
