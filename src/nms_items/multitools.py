"""Multi-tool reference: types, weapons and the tricks for getting one.

Unlike everything else in this app, none of this can be derived from the recipe
tables -- the game files carry no multi-tool stats worth reading. It is written
out of the guides into data/multitools.json and simply loaded here, so the TUI
and the PDF read the same file and cannot disagree.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .model import DATA_DIR


@dataclass(frozen=True, slots=True)
class ToolType:
    type: str
    damage: str
    mining: str
    scan: str
    slots: str
    note: str


@dataclass(frozen=True, slots=True)
class Weapon:
    weapon: str
    kind: str
    best_hit: str
    pro: str
    con: str


@dataclass(frozen=True, slots=True)
class Rule:
    title: str
    body: str


@dataclass(slots=True)
class Procedure:
    """A titled list of steps -- the camp puzzle, the cabinet trick, hunting."""

    title: str
    steps: list[str]
    after: list[str] = field(default_factory=list)
    note: str = ""


@dataclass(slots=True)
class MultiTools:
    headline: str
    types: list[ToolType]
    getting: list[dict]
    weapons: list[Weapon]
    rules: list[Rule]
    upgrade_sources: list[dict]
    upgrade_order: list[str]
    sentinel_puzzle: Procedure
    cabinet_trick: Procedure
    hunting: Procedure

    @property
    def procedures(self) -> list[Procedure]:
        return [self.sentinel_puzzle, self.cabinet_trick, self.hunting]


def load(data_dir: Path | None = None) -> MultiTools:
    path = (data_dir or DATA_DIR) / "multitools.json"
    raw = json.loads(path.read_text())

    def procedure(key: str) -> Procedure:
        row = raw[key]
        return Procedure(
            title=row["title"],
            steps=list(row.get("steps", [])),
            after=list(row.get("after", [])),
            note=row.get("note", ""),
        )

    return MultiTools(
        headline=raw["_headline"],
        types=[ToolType(**row) for row in raw["types"]],
        getting=raw["getting"],
        weapons=[Weapon(**row) for row in raw["weapons"]],
        rules=[Rule(**row) for row in raw["rules"]],
        upgrade_sources=raw["upgrade_sources"],
        upgrade_order=raw["upgrade_order"],
        sentinel_puzzle=procedure("sentinel_puzzle"),
        cabinet_trick=procedure("cabinet_trick"),
        hunting=procedure("hunting"),
    )
