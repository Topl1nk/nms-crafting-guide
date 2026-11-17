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
import planet_word

MAGIC = 0xFEEDA1E5


def _namegen():
    """The names the game makes up for planets and systems come from nms_namegen (third_party/, MIT, Stuart Coyle & had.sh & GGF),
    which needs numpy. Without it the names the save does not hold are simply left out. Installed, the package is in the bundle;
    from a checkout it is the copy under third_party/."""
    if not paths.FROZEN:
        path = str(paths.RES / "third_party" / "nms_namegen")
        if path not in sys.path:
            sys.path.insert(0, path)
    try:
        from nms_namegen import planet, system
    except ImportError:
        return None
    return planet, system
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


def _ua(value) -> int:
    """A universe address as the save writes it: a number, or a "0x..." string."""
    return int(value, 16) if isinstance(value, str) else int(value or 0)


def _place(ua: int) -> dict:
    """The fields of a universe address, low bits first: x 12 bits, z 12, y 8, galaxy 8 (0-based), system 12, planet 4.
    The portal code is the same fields in the order planet, system, y, z, x, each as hex. (Checked against the save's own
    current address: x -343 and z -1500 read back as 0xEA9 and 0xA24.)"""
    planet, system, galaxy = (ua >> 52) & 0xF, (ua >> 40) & 0xFFF, (ua >> 32) & 0xFF
    y, z, x = (ua >> 24) & 0xFF, (ua >> 12) & 0xFFF, ua & 0xFFF
    return {"galaxy": galaxy + 1, "planet": planet, "system": system,
            "code": f"{planet:X}{system:03X}{y:02X}{z:03X}{x:03X}"}


# The planet type a discovery record holds: the low 16 bits of its second value (DD.VP[1]) are the game's biome number, in the order
# of GcBiomeType (11 is the test biome, left out). Read off a real save, where all 125 planets fall in 0..13 and the rarest types
# (swamp, lava) are the rarest here too; the higher bits are not understood and not used. Not checked against the game itself.
BIOMES = {0: "Lush", 1: "Toxic", 2: "Scorched", 3: "Radioactive", 4: "Frozen", 5: "Barren", 6: "Dead", 7: "Weird", 8: "Red",
          9: "Green", 10: "Blue", 12: "Swamp", 13: "Lava", 14: "Waterworld", 15: "GasGiant"}


def planets(save: dict, account: str = "") -> list[dict]:
    """The planets the player has been to, as far as the save shows it: those with a discovery of theirs (the planet itself,
    or an animal, plant or mineral found on it) or with a base of theirs. The save does not keep a planet's resources, and
    its name only if one was given (or uploaded with the discovery). Where there is none, the name is worked out from the
    planet's seed and address the way the game makes it up (nms_namegen, see _namegen) and marked "generated" in name_source and
    system_name_source; a name taken from the save is marked "save"."""
    records = ((save.get("DiscoveryManagerData") or {}).get("DiscoveryData-v1") or {}).get("Store", {}).get("Record") or []
    state = save["BaseContext"]["PlayerStateData"]
    mask = (1 << 56) - 1
    if not account:  # a save outside a Steam folder: the account whose own discoveries (local id = user id) are most
        own = [r["OWS"].get("UID") for r in records if r["OWS"].get("UID") and r["OWS"].get("LID") == r["OWS"].get("UID")]
        account = max(set(own), key=own.count) if own else ""

    def mine(owner: dict) -> bool:
        return bool(account) and owner.get("UID") == account

    found: dict[int, dict] = {}

    def planet(key: int) -> dict:
        return found.setdefault(key, {**_place(key), "name": "", "system_name": "", "name_source": "", "system_name_source": "",
                                      "biome": "", "word_key": "", "found": 0, "seen": 0, "flora": 0, "fauna": 0, "minerals": 0, "bases": []})

    count = {"Flora": "flora", "Animal": "fauna", "Mineral": "minerals"}
    seeds: dict[int, int] = {}  # a planet's seed, from anyone's discovery record of it (it is the planet's, not the finder's)
    types: dict[int, str] = {}  # and its type, from the same record
    words: dict[int, str] = {}  # and the loc key of the word the game puts before "Planet" (planet_word.py)
    for r in records:
        kind, key, owner = r["DD"]["DT"], _ua(r["DD"]["UA"]) & mask, r.get("OWS", {})
        if kind == "Planet" and r["DD"].get("VP"):
            seeds[key] = _ua(r["DD"]["VP"][0])
            if len(r["DD"]["VP"]) > 1:
                types[key] = BIOMES.get(_ua(r["DD"]["VP"][1]) & 0xFFFF, "")
                words[key] = planet_word.word_key(seeds[key], _ua(r["DD"]["VP"][1]))
        if kind in count and mine(owner):
            p = planet(key)
            p[count[kind]] += 1
            p["seen"] = max(p["seen"], owner.get("TS", 0))
        elif kind == "Planet" and mine(owner):
            p = planet(key)
            p["found"] = owner.get("TS", 0)
            p["seen"] = max(p["seen"], p["found"])
    for b in state.get("PersistentPlayerBases", []):
        if mine(b.get("Owner") or {}) and _ua(b.get("GalacticAddress")):
            p = planet(_ua(b["GalacticAddress"]) & mask)
            p["bases"].append((b.get("Name") or "").strip())
            p["seen"] = max(p["seen"], b.get("LastUpdateTimestamp", 0))
    # Names the player gave: the planet's own record, and its system's (the system is the planet without its index).
    for r in records:
        name = (r.get("DM") or {}).get("CN")
        if not name:
            continue
        key = _ua(r["DD"]["UA"]) & mask
        if r["DD"]["DT"] == "Planet" and key in found:
            found[key]["name"] = name
        elif r["DD"]["DT"] == "SolarSystem":
            for p in found.values():
                if (p["galaxy"], p["system"]) == (_place(key)["galaxy"], _place(key)["system"]):
                    p["system_name"] = name
    for key, p in found.items():
        p["biome"] = types.get(key, "")
        p["word_key"] = words.get(key, "") if p["planet"] else ""
    namegen = _namegen() if any(not p["name"] or not p["system_name"] for p in found.values()) else None
    for key, p in found.items():
        p["name_source"], p["system_name_source"] = ("save" if p["name"] else ""), ("save" if p["system_name"] else "")
        if not namegen:
            continue
        planet_mod, system_mod = namegen
        code, galaxy = int(p["code"], 16), p["galaxy"] - 1
        try:
            if not p["name"] and p["planet"] > 0:  # planet 0 is no body of the system (nms_namegen would read it as the last one)
                seed = seeds[key] if key in seeds else planet_mod.planetSeed(code, galaxy)
                p["name"], p["name_source"] = planet_mod.planetName(seed), "generated"
            if not p["system_name"]:
                p["system_name"], p["system_name_source"] = system_mod.systemName(code, galaxy), "generated"
        except (KeyError, IndexError, ValueError):
            pass  # no name rather than a wrong one: e.g. a planet number the system has no body for
    # Planet 0 of an address is the system itself (a base can be recorded there), not one of its planets: not listed.
    return sorted((p for p in found.values() if p["planet"] > 0), key=lambda p: p["seen"], reverse=True)


def report(path: Path) -> dict:
    """Everything the player carries or has stored, container by container."""
    save = read(path)
    p = save["BaseContext"]["PlayerStateData"]
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
    account = path.parent.name.removeprefix("st_") if path.parent.name.startswith("st_") else ""
    return {"file": path.name, "saved": path.stat().st_mtime, "containers": containers, "totals": totals,
            "planets": planets(save, account)}


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
