"""Where an item goes: the storage layout from the guide, as lookups.

The guide (24.storage-guide.md, section 10) splits storage into ten numbered
containers plus the single-purpose stores, and gives every item one home -- the
game's auto-routing sends a deposit to whichever container already holds that
item, so one home per item is what makes "send everything to storage" sort
itself.

data/storage.json holds the layout as an ordered rule list: the items the guide
names first, then the families they belong to, matched on the game's subtitle
and type. The first rule that matches wins; nothing matching means 9 - Inbox.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .model import DATA_DIR, Book, Item

# What to do with the item, as opposed to where it lives. "store" is the
# default; the others are the answers the guide gives besides a container.
ACTIONS = {
    "keep": "Keep on you",
    "store": "Store",
    "sell": "Sell",
    "discard": "Junk",
    "use": "Use it",
}

CONTAINERS = [str(n) for n in range(10)]
INBOX = "9"


@dataclass(frozen=True, slots=True)
class Home:
    key: str
    name: str
    note: str

    @property
    def is_container(self) -> bool:
        return self.key in CONTAINERS

    @property
    def label(self) -> str:
        """`3 Components` for a container, the plain name for anything else."""
        return f"{self.key} {self.name}" if self.is_container else self.name


@dataclass(frozen=True, slots=True)
class Rule:
    home: str
    action: str
    why: str
    ids: frozenset[str] = frozenset()
    ids_prefix: tuple[str, ...] = ()
    subtitles: frozenset[str] = frozenset()
    subtitle_has: tuple[str, ...] = ()
    types: frozenset[str] = frozenset()
    categories: frozenset[str] = frozenset()
    # Scrapping it pays nanites, and the Trade Rocket pays units only.
    no_rocket: bool = False

    def matches(self, item: Item) -> bool:
        """Every condition the rule sets has to hold; unset ones are ignored."""
        if self.ids and item.id not in self.ids:
            return False
        if self.ids_prefix and not item.id.startswith(self.ids_prefix):
            return False
        if self.subtitles and item.subtitle not in self.subtitles:
            return False
        if self.subtitle_has and not any(s in item.subtitle for s in self.subtitle_has):
            return False
        if self.types and item.type not in self.types:
            return False
        if self.categories and item.category not in self.categories:
            return False
        return True


@dataclass(frozen=True, slots=True)
class Placement:
    home: Home
    action: str
    why: str
    no_rocket: bool = False

    @property
    def verdict(self) -> str:
        return ACTIONS[self.action]

    @property
    def label(self) -> str:
        """One line for a table cell: what to do and where."""
        if self.action == "discard":
            return "Junk - drop it"
        if self.action == "use":
            return "Use it, don't store"
        if self.action == "sell":
            return f"Sell - park in {self.home.label}"
        return self.home.label

    def advice(self) -> str:
        """The longer form, for a detail pane."""
        if self.action == "discard":
            return "Drop it when you need the slot. Sell it if you are at a terminal anyway."
        if self.action == "use":
            return "Don't store it: use it, open it or read it, and the slot is free again."
        if self.action == "sell":
            text = f"Sell it. Until you reach a terminal, park it in {self.home.label}."
        elif self.home.key == "exosuit":
            text = "Keep it in the exosuit."
        else:
            text = f"Store it in {self.home.label}."
        if self.no_rocket:
            text += (
                " Scrap it at a terminal for nanites if you have no use for it --"
                " never send it with the Trade Rocket, which pays units only."
            )
        return text


class StorageGuide:
    def __init__(self, homes: dict[str, Home], rules: list[Rule]) -> None:
        self.homes = homes
        self.rules = rules

    @classmethod
    def load(cls, path: Path | None = None) -> StorageGuide:
        raw = json.loads((path or DATA_DIR / "storage.json").read_text())
        homes = {
            key: Home(key, row["name"], row.get("note", ""))
            for key, row in raw["homes"].items()
        }
        rules = []
        for row in raw["rules"]:
            home = row["home"]
            if home not in homes:
                raise ValueError(f"storage.json: rule points at unknown home {home!r}")
            action = row.get("action") or ("keep" if home == "exosuit" else "store")
            if action not in ACTIONS:
                raise ValueError(f"storage.json: unknown action {action!r}")
            rules.append(
                Rule(
                    home=home,
                    action=action,
                    why=row.get("why", ""),
                    ids=frozenset(row.get("ids", ())),
                    ids_prefix=tuple(row.get("ids_prefix", ())),
                    subtitles=frozenset(row.get("subtitles", ())),
                    subtitle_has=tuple(row.get("subtitle_has", ())),
                    types=frozenset(row.get("types", ())),
                    categories=frozenset(row.get("categories", ())),
                    no_rocket=row.get("no_rocket", False),
                )
            )
        return cls(homes, rules)

    def place(self, item: Item) -> Placement:
        for rule in self.rules:
            if rule.matches(item):
                return Placement(self.homes[rule.home], rule.action, rule.why, rule.no_rocket)
        return Placement(self.homes[INBOX], "store", "No rule yet - sort it by hand")

    def search(self, book: Book, query: str) -> list[tuple[Item, Placement]]:
        """Items whose name, subtitle or home matches every word typed.

        Matching the home too means "sell" lists everything to sell and
        "cold" everything for Cold Storage, not only items with those words
        in their names.
        """
        terms = query.lower().split()
        rows = []
        for item in book.items.values():
            placement = self.place(item)
            key = f"{item.name} {item.subtitle} {placement.label} {placement.verdict}".lower()
            if all(term in key for term in terms):
                rows.append((item, placement))
        # Exact name first, then names that start with it: "gold" lands on
        # Gold, not on whatever alphabetises first among the names containing it.
        q = query.strip().lower()
        rows.sort(key=lambda r: (
            r[0].name.lower() != q,
            not r[0].name.lower().startswith(q),
            r[0].name.lower(),
        ))
        return rows
