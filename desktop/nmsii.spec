# PyInstaller spec for the desktop app: `pyinstaller desktop/nmsii.spec` from app/ (build.py does it).
# One folder, not one file: a onefile program unpacks itself into a temp folder on every start, which is slow and what virus
# scanners dislike. The installers (Inno Setup, AppImage) are what make the folder one thing for the user.
import sys
from pathlib import Path

app = Path(SPECPATH).parent
windows = sys.platform == "win32"

a = Analysis(
    [str(app / "desktop" / "nmsii.py")],
    pathex=[str(app / "desktop")],
    datas=[
        (str(app / "dist"), "dist"),  # the built site (npm run build)
        (str(app / "scripts" / "extract_game.py"), "scripts"),
        (str(app / "desktop" / "vendor"), "vendor"),  # fetch_tools.py
    ],
    hiddenimports=["hgpaktool.cli", "lz4.block", "PIL.Image", "PIL.WebPImagePlugin"],
    excludes=["tkinter", "textual", "mcp", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    # UTF-8 as the default text encoding, as the source run has with PYTHONUTF8 (the bootloader ignores that variable): the
    # game's tables hold characters cp1252 cannot write.
    a.scripts + [("X utf8", None, "OPTION")],
    [],
    exclude_binaries=True,
    name="NMSii",
    console=False,  # a window app: no black console behind it (the tools it starts are run hidden, see nmsii.py)
    icon=str(app / "desktop" / "icon.ico") if windows else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="NMSii")
