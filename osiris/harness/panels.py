"""The Canvas's panels (#194): a group of tabs for each kind of thing it shows,
tiled side by side in the order the groups opened. GTK draws them; this
decides what is open."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Kind(Enum):
    CODE = "code"
    CHANGES = "changes"


@dataclass(frozen=True)
class Tab:
    kind: Kind
    #: What it shows, unique within its kind: a file's path, a question's message.
    key: str
    title: str


@dataclass
class Group:
    kind: Kind
    tabs: list[Tab] = field(default_factory=list)
    selected: Tab | None = None


class Panels:
    def __init__(self) -> None:
        self.groups: list[Group] = []

    def open(self, tab: Tab) -> None:
        group = next((g for g in self.groups if g.kind is tab.kind), None)
        if group is None:
            group = Group(tab.kind)
            self.groups.append(group)
        group.tabs.append(tab)
        group.selected = tab
