"""Read a No Man's Sky save (read-only) and list what the player carries.

A save .hg file is a series of LZ4 blocks, each behind a 16-byte header
(magic 0xFEEDA1E5, compressed size, uncompressed size, padding); the joined
text is JSON whose keys are the game's 3-character obfuscated names, which
MBINCompiler's mapping.json turns back into real ones. Nothing is written.

    python tools/nms_save.py            # newest save found, as JSON
    python tools/nms_save.py --list     # every save slot with its last-played time
"""
import argparse
import glob
import json
import os
import struct
import sys
import time
from pathlib import Path

import lz4.block

import paths

MAGIC = 0xFEEDA1E5
# Where the game keeps its saves: %APPDATA% on Windows; on Linux the Proton prefix of the Steam install (App ID 275850).
PROTON = Path("steamapps/compatdata/275850/pfx/drive_c/users/steamuser/AppData/Roaming")


def save_roots() -> list[Path]:
    if os.name == "nt":
        return [Path(os.environ.get("APPDATA", "")) / "HelloGames" / "NMS"]
    home = Path.home()
    steam = [home / ".local/share/Steam", home / ".steam/steam", home / ".var/app/com.valvesoftware.Steam/.local/share/Steam"]
    return [s / PROTON / "HelloGames" / "NMS" for s in steam]


def save_files() -> list[Path]:
    files: list[Path] = []
    for root in save_roots():
        files += [Path(p) for p in glob.glob(str(root / "st_*" / "save*.hg"))]
        files += [Path(p) for p in glob.glob(str(root / "DefaultUser" / "save*.hg"))]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def decode(path: Path) -> dict:
    data = path.read_bytes()
    out, pos = [], 0
    while pos + 16 <= len(data):
        magic, csize, usize, _ = struct.unpack_from("<IIII", data, pos)
        if magic != MAGIC:
            raise ValueError(f"{path.name}: unknown save format (block magic {magic:#x})")
        pos += 16
        out.append(lz4.block.decompress(data[pos:pos + csize], uncompressed_size=usize))
        pos += csize
    return json.loads(b"".join(out).rstrip(b"\0").decode("utf-8", "replace"))


def load_mapping() -> dict[str, str]:
    raw = json.loads((paths.VENDOR / "mapping.json").read_text(encoding="utf-8"))
    return {m["Key"]: m["Value"] for m in raw["Mapping"]}


def demangle(node, mapping):
    if isinstance(node, dict):
        return {mapping.get(k, k): demangle(v, mapping) for k, v in node.items()}
    if isinstance(node, list):
        return [demangle(v, mapping) for v in node]
    return node


def read(path: Path) -> dict:
    return demangle(decode(path), load_mapping())


def _items(inv: dict) -> dict[str, int]:
    """Substances and products in one inventory, by game id. Technology (what is
    installed on the suit, ship and tools) is not stock, so it is left out."""
    out: dict[str, int] = {}
    for slot in inv.get("Slots") or []:
        # One odd slot (a field the game added or dropped) must not blank the report.
        if (slot.get("Type") or {}).get("InventoryType") not in ("Substance", "Product"):
            continue
        item = str(slot.get("Id", "")).lstrip("^").split("#")[0]  # procedural items end in #seed
        amount = slot.get("Amount") or 0
        if item and item.isascii() and amount > 0:
            out[item] = out.get(item, 0) + amount
    return out


def report(path: Path) -> dict:
    """Everything the player carries or has stored, container by container."""
    p = read(path)["BaseContext"]["PlayerStateData"]
    # The labels are English: the page words them in its language (site/src/lib/words.js placeLabel);
    # only a ship's or an exocraft's own name, which the player gave it, is carried as it is.
    found = [("suit", "Exosuit", p.get("Inventory", {})),
             ("freighter", "Freighter", p.get("FreighterInventory", {})),
             ("food", "Nutrient Processor", p.get("FoodUnitInventory", {}))]
    for i in range(10):
        found.append((f"chest{i}", f"Container {i}", p.get(f"Chest{i + 1}Inventory", {})))
    for key, label, owned in (("ship", "Ship", p.get("ShipOwnership", [])),
                              ("vehicle", "Exocraft", p.get("VehicleOwnership", []))):
        for i, entry in enumerate(owned):
            name = (entry.get("Name") or "").strip()
            found.append((f"{key}{i}", f"{label}: {name}" if name else f"{label} {i + 1}", entry.get("Inventory", {})))
    containers = [{"key": k, "label": label, "items": it}
                  for k, label, inv in found if (it := _items(inv))]
    totals: dict[str, int] = {}
    for c in containers:
        for item, n in c["items"].items():
            totals[item] = totals.get(item, 0) + n
    return {"file": path.name, "saved": path.stat().st_mtime, "containers": containers, "totals": totals}


def listing() -> list[dict]:
    return [{"file": f.name, "account": f.parent.name, "saved": f.stat().st_mtime}
            for f in save_files()]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--file")
    args = ap.parse_args()
    files = save_files()
    if args.list:
        for f in files:
            print(time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime)), f)
        sys.exit(0)
    path = Path(args.file) if args.file else (files[0] if files else None)
    if not path:
        sys.exit("no save found")
    save = read(path)
    print(json.dumps({"file": str(path), "top": list(save)[:40]}, ensure_ascii=False))
