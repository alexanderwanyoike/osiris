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


@dataclass(frozen=True)
class Step:
    """One action the Harness decided on while answering."""

    action: str
    resources: tuple[str, ...]

    @property
    def doing(self) -> str:
        return f"{VERBS[self.action].doing} {self.resources[0]}"

    @property
    def record(self) -> str:
        return f"{VERBS[self.action].done} {self.resources[0]}"
