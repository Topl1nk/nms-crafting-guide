"""Portal addresses: glyphs, galactic coordinates, and the places you saved.

A location in No Man's Sky has two written forms and they do not look like each
other. A **portal address** is the twelve glyphs you dial at a portal, written
as twelve hex digits. A **galactic address** is what a signal booster shows and
what people paste into spreadsheets, `XXXX:YYYY:ZZZZ:SSSS`. Converting between
them is the reason everybody ends up on nmsportals.github.io; this is that
conversion, offline, with the same constants:

    galactic X = (portal X + 2047) % 4096      portal X = (galactic X + 2049) % 4096
    galactic Y = (portal Y +  127) %  256      portal Y = (galactic Y +  129) %  256
    galactic Z = (portal Z + 2047) % 4096      portal Z = (galactic Z + 2049) % 4096

The system index is carried across unchanged, and the planet index -- the first
glyph -- is not in a galactic address at all, which is why converting that way
needs one to be chosen.

Both frames describe the same voxel grid; they only disagree about where zero
is. Portal coordinates put 0,0,0 at the centre of the galaxy, galactic ones put
it at a corner, so `voxel` below is the honest reading: signed, centre-relative,
straight out of the glyphs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path

from .model import DATA_DIR

# The sixteen glyphs, in the order they appear on the portal's dial -- which is
# the whole trick to entering an address: glyph `A` is the eleventh symbol,
# every time. The names are the community's, not the game's; Hello Games never
# gave them any.
GLYPH_NAMES = [
    "sunset",
    "bird",
    "face",
    "diplo",
    "eclipse",
    "balloon",
    "boat",
    "bug",
    "dragonfly",
    "galaxy",
    "voxel",
    "fish",
    "tent",
    "rocket",
    "tree",
    "atlas",
]

# The first ten galaxies, in order. There are 256; past Eissentam nobody has an
# agreed name worth printing, so those show as "Galaxy N".
GALAXY_NAMES = [
    "Euclid",
    "Hilbert Dimension",
    "Calypso",
    "Hesperius Dimension",
    "Hyades",
    "Ickjamatew",
    "Budullangr",
    "Kikolgallr",
    "Eltiensleen",
    "Eissentam",
]

# nmsportals rejects a system index above this. Real addresses stay well under
# it, but a mistyped one sails past unnoticed otherwise -- so it is a warning
# here rather than a parse error, and a pasted address still converts.
MAX_SYSTEM_INDEX = 0x429

KINDS = [
    "multi-tool",
    "starship",
    "freighter",
    "base",
    "planet",
    "system",
    "other",
]

# Where an address came from. Worth separating from `source`, which is free
# text: your own finds are the ones you can vouch for, and the ones off a
# catalogue carry somebody else's class claim on somebody else's save.
ORIGINS = ["mine", "shared"]


def galaxy_name(number: int) -> str:
    """Galaxy 1 is Euclid. Numbering is 1-based because the game's is."""
    if 1 <= number <= len(GALAXY_NAMES):
        return GALAXY_NAMES[number - 1]
    return f"Galaxy {number}"


class AddressError(ValueError):
    """Raised for text that is not a portal or galactic address at all."""


@dataclass(frozen=True, slots=True)
class Address:
    """One location, held in the portal frame: planet, system, and a voxel.

    Field widths are the glyph counts: planet is one glyph, system three, then
    Y two and Z and X three each -- height, width, length, in that order, which
    is why the address reads `p SSS YY ZZZ XXX`.
    """

    planet: int
    system: int
    y: int
    z: int
    x: int

    def __post_init__(self) -> None:
        for name, value, limit in (
            ("planet", self.planet, 0xF),
            ("system", self.system, 0xFFF),
            ("y", self.y, 0xFF),
            ("z", self.z, 0xFFF),
            ("x", self.x, 0xFFF),
        ):
            if not 0 <= value <= limit:
                raise AddressError(f"{name} out of range: {value:#x} > {limit:#x}")

    # -- the two written forms -------------------------------------------

    @property
    def portal_code(self) -> str:
        return (
            f"{self.planet:X}{self.system:03X}"
            f"{self.y:02X}{self.z:03X}{self.x:03X}"
        )

    @property
    def portal_grouped(self) -> str:
        """The code split into its five fields, for reading aloud."""
        return (
            f"{self.planet:X} {self.system:03X} "
            f"{self.y:02X} {self.z:03X} {self.x:03X}"
        )

    @property
    def galactic(self) -> str:
        gx = (self.x + 2047) % 4096
        gy = (self.y + 127) % 256
        gz = (self.z + 2047) % 4096
        return f"{gx:04X}:{gy:04X}:{gz:04X}:{self.system:04X}"

    @property
    def share_link(self) -> str:
        return f"https://nmsportals.github.io/#{self.portal_code}"

    # -- what the numbers mean -------------------------------------------

    @property
    def voxel(self) -> tuple[int, int, int]:
        """Signed X, Y, Z from the galaxy centre, the way the glyphs store it."""
        return (
            self.x - 4096 if self.x >= 2048 else self.x,
            self.y - 256 if self.y >= 128 else self.y,
            self.z - 4096 if self.z >= 2048 else self.z,
        )

    @property
    def voxel_label(self) -> str:
        x, y, z = self.voxel
        return f"X {x:+5d}   Y {y:+4d}   Z {z:+5d}"

    @property
    def glyph_names(self) -> list[str]:
        return [GLYPH_NAMES[int(char, 16)] for char in self.portal_code]

    @property
    def warnings(self) -> list[str]:
        notes = []
        if self.system > MAX_SYSTEM_INDEX:
            notes.append(
                f"system index 0x{self.system:03X} is above the "
                f"0x{MAX_SYSTEM_INDEX:03X} "
                "nmsportals treats as the maximum - check the address"
            )
        return notes

    def with_planet(self, planet: int) -> "Address":
        return Address(planet & 0xF, self.system, self.y, self.z, self.x)

    # -- parsing ---------------------------------------------------------

    @classmethod
    def from_portal_code(cls, text: str) -> "Address":
        code = _hex_only(text)
        if len(code) != 12:
            raise AddressError(
                f"a portal code is 12 glyphs; got {len(code)}"
            )
        return cls(
            planet=int(code[0], 16),
            system=int(code[1:4], 16),
            y=int(code[4:6], 16),
            z=int(code[6:9], 16),
            x=int(code[9:12], 16),
        )

    @classmethod
    def from_galactic(cls, text: str, planet: int = 0) -> "Address":
        parts = [p for p in re.split(r"[^0-9A-Fa-f]+", text.strip()) if p]
        if len(parts) != 4 or any(len(p) > 4 for p in parts):
            raise AddressError(
                "a galactic address is four hex groups, e.g. 042F:0078:0D55:006A"
            )
        gx, gy, gz, system = (int(p, 16) for p in parts)
        if gx > 0xFFF or gz > 0xFFF:
            raise AddressError("galactic X and Z must be 0000-0FFF")
        if gy > 0xFF:
            raise AddressError("galactic Y must be 0000-00FF")
        return cls(
            planet=planet & 0xF,
            system=system % 0x1000,
            y=(gy + 129) % 256,
            z=(gz + 2049) % 4096,
            x=(gx + 2049) % 4096,
        )

    @classmethod
    def parse(cls, text: str, planet: int = 0) -> "Address":
        """Take whatever was pasted: a code, an address, or a share link.

        The two forms are told apart by shape rather than by asking, so there
        is one box to paste into instead of three: a colon anywhere means a
        galactic address (a truncated one is a mistake, not a portal code),
        and twelve bare hex digits mean a portal code.
        """
        text = text.strip()
        if not text:
            raise AddressError("nothing to convert")
        # A nmsportals share link carries the code in its fragment.
        if "#" in text:
            text = text.rsplit("#", 1)[1]
        if ":" not in text and len(_hex_only(text)) == 12:
            return cls.from_portal_code(text)
        return cls.from_galactic(text, planet)


def _hex_only(text: str) -> str:
    return re.sub(r"[^0-9A-Fa-f]", "", text).upper()


# -- saved locations ------------------------------------------------------


@dataclass(slots=True)
class Location:
    """An address plus what is actually there, which is the part worth saving.

    `galaxy` matters: the same twelve glyphs point at a different star in every
    one of the 256 galaxies, so an address shared without it is ambiguous.
    """

    name: str
    code: str
    kind: str = "other"
    origin: str = "mine"
    galaxy: int = 1
    detail: str = ""
    where: str = ""
    source: str = ""
    added: str = ""

    @property
    def address(self) -> Address:
        return Address.from_portal_code(self.code)

    @property
    def origin_label(self) -> str:
        return "found by me" if self.origin == "mine" else "shared"

    @property
    def galaxy_label(self) -> str:
        return f"{self.galaxy}. {galaxy_name(self.galaxy)}"

    @property
    def search_key(self) -> str:
        return " ".join(
            (
                self.name, self.kind, self.origin, self.detail,
                self.where, self.source, self.code,
            )
        ).lower()


@dataclass(slots=True)
class LocationBook:
    """The addresses you have collected, in data/locations.json.

    This one is written by hand and by the app both -- unlike the recipe files,
    which are generated, and unlike the inventory, which is throwaway state in
    XDG. Findings belong in the repo next to the guides they came from, so they
    diff, review and share like everything else here.
    """

    path: Path
    source: str = ""
    note: str = ""
    locations: list[Location] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path | None = None) -> "LocationBook":
        path = path or (DATA_DIR / "locations.json")
        try:
            raw = json.loads(path.read_text())
        except (OSError, ValueError):
            return cls(path=path)
        rows = []
        for row in raw.get("locations", []):
            try:
                Address.from_portal_code(row["code"])
            except (AddressError, KeyError):
                continue  # a typo in the file must not take the screen down
            origin = row.get("origin", "mine")
            rows.append(
                Location(
                    name=row.get("name", "unnamed"),
                    code=_hex_only(row["code"]),
                    kind=row.get("kind", "other"),
                    origin=origin if origin in ORIGINS else "mine",
                    galaxy=int(row.get("galaxy", 1)),
                    detail=row.get("detail", ""),
                    where=row.get("where", ""),
                    source=row.get("source", ""),
                    added=row.get("added", ""),
                )
            )
        return cls(
            path=path,
            source=raw.get("_source", ""),
            note=raw.get("_note", ""),
            locations=rows,
        )

    def save(self) -> None:
        payload = {
            "_source": self.source,
            "_note": self.note
            or "Portal addresses worth keeping. Hand-editable; the TUI writes "
            "here too (portals screen, s). galaxy is 1-based: 1 is Euclid.",
            "_schema": {
                "name": "what you call it",
                "code": "12 hex digits, the portal glyphs",
                "kind": " | ".join(KINDS),
                "origin": " | ".join(ORIGINS)
                + " - your own find, or somebody else's",
                "galaxy": "1-based galaxy number, 1 = Euclid",
                "detail": "what is there - class, type, slot count",
                "where": "how to find it once you arrive",
                "source": "who shared it, or where you found it",
                "added": "YYYY-MM-DD, stamped when the TUI saves it",
            },
            "locations": [asdict(loc) for loc in self.locations],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")

    def add(self, location: Location) -> None:
        """Stamp the date if nothing set one -- a find is worth dating."""
        if not location.added:
            location.added = date.today().isoformat()
        self.locations.append(location)
        self.save()

    def remove(self, index: int) -> Location | None:
        if not 0 <= index < len(self.locations):
            return None
        gone = self.locations.pop(index)
        self.save()
        return gone

    def search(
        self,
        query: str = "",
        kind: str | None = None,
        origin: str | None = None,
    ) -> list[Location]:
        rows = self.locations
        if kind:
            rows = [loc for loc in rows if loc.kind == kind]
        if origin:
            rows = [loc for loc in rows if loc.origin == origin]
        for word in query.lower().split():
            rows = [loc for loc in rows if word in loc.search_key]
        return rows

    def count(self, origin: str) -> int:
        return sum(1 for loc in self.locations if loc.origin == origin)

    def __len__(self) -> int:
        return len(self.locations)
