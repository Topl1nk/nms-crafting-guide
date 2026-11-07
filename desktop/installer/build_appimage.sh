#!/usr/bin/env bash
# Linux package for NMS Crafting Guide: one AppImage file, which runs where it is (chmod +x, double-click), no install step and no root.
# Run from app/ after desktop/build.py:  desktop/installer/build_appimage.sh 1.2.3
set -euo pipefail

version="${1:?usage: build_appimage.sh VERSION}"
out=desktop/out
appdir="$out/nms-crafting-guide.AppDir"

rm -rf "$appdir"
mkdir -p "$appdir/usr/lib"
cp -r "$out/nms-crafting-guide" "$appdir/usr/lib/nms-crafting-guide"
cp web/icon-512.png "$appdir/nms-crafting-guide.png"

cat >"$appdir/nms-crafting-guide.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=NMS Crafting Guide
Comment=No Man's Sky refining, cooking and crafting from the game's own tables
Exec=nms-crafting-guide
Icon=nms-crafting-guide
Categories=Game;Utility;
Terminal=false
EOF

cat >"$appdir/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/nms-crafting-guide/nms-crafting-guide" "$@"
EOF
chmod +x "$appdir/AppRun" "$appdir/usr/lib/nms-crafting-guide/nms-crafting-guide"

tool="$out/appimagetool"
if [ ! -x "$tool" ]; then
  curl -fsSL -o "$tool" https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$tool"
fi
# The runner has no FUSE: let the tool unpack itself instead of mounting.
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$tool" "$appdir" "$out/nms-crafting-guide-$version-x86_64.AppImage"
