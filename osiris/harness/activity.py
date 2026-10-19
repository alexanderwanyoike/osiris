"""Each step of an answer, as a person reads it while Osiris works and after."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Verb:
    doing: str
    done: str


#: The Engine's actions, as words.
VERBS = {
    "read": Verb("Reading", "Read"),
    "edit": Verb("Editing", "Edited"),
    "list": Verb("Listing", "Listed"),
}


def _path(resource: str) -> str:
    """The last two parts of a path; a folder pattern loses its ``*``."""
    parts = [part for part in resource.removesuffix("*").split("/") if part]
    return "/".join(parts[-2:])


@dataclass(frozen=True)
class Step:
    """One action the Harness decided on while answering."""

    action: str
    resources: tuple[str, ...]

    @property
    def doing(self) -> str:
        return f"{VERBS[self.action].doing} {self._what}"

    @property
    def record(self) -> str:
        return f"{VERBS[self.action].done} {self._what}"

    @property
    def _what(self) -> str:
        first, *rest = self.resources
        return f"{_path(first)} and {len(rest)} more" if rest else _path(first)
