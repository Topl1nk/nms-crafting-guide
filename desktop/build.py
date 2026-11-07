"""Build the desktop app's program folder (desktop/out/nms-crafting-guide/), which the installers then wrap.

    npm run build && python desktop/fetch_tools.py && python desktop/build.py

Needs the environment of desktop/requirements.txt, the built site (dist/) and the fetched tools (desktop/vendor/).
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
APP = HERE.parent


def main() -> int:
    for need in (APP / "dist" / "index.html", HERE / "vendor" / "mapping.json"):
        if not need.exists():
            sys.exit(f"missing {need}: build the site (npm run build) and run desktop/fetch_tools.py first")
    # The Windows installer and executable want an .ico; the site already has the app's mark at 512 px.
    with Image.open(APP / "web" / "icon-512.png") as im:
        im.save(HERE / "icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                    "--distpath", str(HERE / "out"), "--workpath", str(HERE / "build"),
                    str(HERE / "nms-crafting-guide.spec")], check=True, cwd=APP)
    return 0


if __name__ == "__main__":
    sys.exit(main())
