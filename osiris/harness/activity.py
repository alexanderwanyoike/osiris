"""Each step of an answer, as a person reads it while Osiris works and after."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


def _path(resource: str) -> str:
    """The last two parts of a path; a folder pattern loses its ``*``."""
    parts = [part for part in resource.removesuffix("*").split("/") if part]
    return "/".join(parts[-2:])


#: The most of a command, pattern or query a row shows.
LONGEST = 40


def _as_written(resource: str) -> str:
    """Whole if it fits, else cut at the last word that does."""
    if len(resource) <= LONGEST:
        return resource
    head = resource[:LONGEST]
    cut = head.rsplit(" ", 1)[0] if " " in head else head[:-1]
    return cut.rstrip() + "…"


@dataclass(frozen=True)
class Phrase:
    doing: str
    done: str
    #: What the action is always done to; empty names its resources instead.
    what: str = ""
    #: How one of its resources reads.
    shown: Callable[[str], str] = _path


#: The Engine's actions, as words.
PHRASES = {
    "read": Phrase("Reading", "Read"),
    "edit": Phrase("Editing", "Edited"),
    "list": Phrase("Listing", "Listed"),
    "glob": Phrase("Finding", "Found", shown=_as_written),
    "grep": Phrase("Searching for", "Searched for", shown=_as_written),
    "bash": Phrase("Running", "Ran", shown=_as_written),
    "shell": Phrase("Running", "Ran", shown=_as_written),
    "osiris_list_themes": Phrase("Looking at", "Looked at", "the themes"),
    "osiris_create_theme": Phrase("Making", "Made", "a theme"),
    "osiris_apply_theme": Phrase("Applying", "Applied", "a theme"),
    "osiris_list_programs": Phrase("Looking at", "Looked at", "your programs"),
    "osiris_create_program": Phrase("Starting", "Started", "a program"),
    "osiris_commit_program": Phrase("Saving", "Saved", "a change"),
    "osiris_check_program": Phrase("Checking", "Checked", "the program"),
}


@dataclass(frozen=True)
class Step:
    """One action the Harness decided on while answering."""

    action: str
    resources: tuple[str, ...]

    @property
    def doing(self) -> str:
        return f"{PHRASES[self.action].doing} {self._what}"

    @property
    def record(self) -> str:
        return f"{PHRASES[self.action].done} {self._what}"

    @property
    def _what(self) -> str:
        phrase = PHRASES[self.action]
        if phrase.what:
            return phrase.what
        first, *rest = self.resources
        shown = phrase.shown(first)
        return f"{shown} and {len(rest)} more" if rest else shown
