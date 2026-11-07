"""Where the desktop app finds what ships with it and where it keeps what the player makes.

Installed (PyInstaller) the program folder is read-only (Program Files, an AppImage), so
everything written goes to a per-user data folder; from a checkout it is the same folder,
so a source run and an installed one behave alike. NMSII_HOME moves it.
"""
import os
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))
# Frozen: the bundle (PyInstaller's _internal folder). From source: app/.
RES = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
THIS = Path(__file__).resolve().parent


def data_home() -> Path:
    if os.environ.get("NMSII_HOME"):
        return Path(os.environ["NMSII_HOME"])
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "NMSii"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "nmsii"


HOME = data_home()
DIST = Path(os.environ.get("NMS_DIST") or RES / "dist")
PROFILE = HOME / "browser-profile"  # window size, theme and saved items live here
PICTURES = HOME / "pictures"
ICONS = PICTURES / "icons"
CACHE = HOME / "cache"  # what is unpacked from the game; NMS_CACHE for scripts/extract_game.py
VENDOR = RES / "vendor"  # MBINCompiler and its mapping.json, fetched at build time (desktop/fetch_tools.py)
EXTRACT_SCRIPT = RES / "scripts" / "extract_game.py"


def self_command(tool: str) -> list[str]:
    """Run one of this program's own helper tools in a child process (see nmsii.py --tool)."""
    if FROZEN:
        return [sys.executable, "--tool", tool]
    return [sys.executable, str(THIS / "nmsii.py"), "--tool", tool]


def mbincompiler() -> Path:
    return VENDOR / ("MBINCompiler.exe" if os.name == "nt" else "MBINCompiler")
