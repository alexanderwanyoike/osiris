"""Each step of an answer, as a person reads it while Osiris works and after."""

from __future__ import annotations

from collections.abc import Callable, Sequence
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


def _site(address: str) -> str:
    return address.partition("://")[2].partition("/")[0] or address


@dataclass(frozen=True)
class Phrase:
    doing: str
    done: str
    #: The verb after "Not allowed to".
    plain: str
    #: What the action is always done to; empty names its resources instead.
    what: str = ""
    #: How one of its resources reads.
    shown: Callable[[str], str] = _path
    #: What it is done to when the Engine names nothing.
    unnamed: str = "something"


_COMMAND = Phrase("Running", "Ran", "run", shown=_as_written, unnamed="a command")

#: The Engine's actions, as words.
PHRASES = {
    "read": Phrase("Reading", "Read", "read", unnamed="a file"),
    "edit": Phrase("Editing", "Edited", "edit", unnamed="a file"),
    "list": Phrase("Listing", "Listed", "list", unnamed="a folder"),
    "external_directory": Phrase(
        "Looking in", "Looked in", "look in", unnamed="a folder"
    ),
    "glob": Phrase("Finding", "Found", "find", shown=_as_written),
    "grep": Phrase("Searching for", "Searched for", "search for", shown=_as_written),
    "webfetch": Phrase("Fetching", "Fetched", "fetch", shown=_site),
    "websearch": Phrase(
        "Searching the web for",
        "Searched the web for",
        "search the web for",
        shown=_as_written,
    ),
    "bash": _COMMAND,
    "shell": _COMMAND,
    "osiris_list_themes": Phrase(
        "Looking at", "Looked at", "look at", what="the themes"
    ),
    "osiris_create_theme": Phrase("Making", "Made", "make", what="a theme"),
    "osiris_apply_theme": Phrase("Applying", "Applied", "apply", what="a theme"),
    "osiris_list_programs": Phrase(
        "Looking at", "Looked at", "look at", what="your programs"
    ),
    "osiris_create_program": Phrase("Starting", "Started", "start", what="a program"),
    "osiris_commit_program": Phrase("Saving", "Saved", "save", what="a change"),
    "osiris_check_program": Phrase("Checking", "Checked", "check", what="the program"),
}


@dataclass(frozen=True)
class Step:
    """One action the Harness decided on while answering."""

    action: str
    resources: tuple[str, ...]
    allowed: bool = True

    @property
    def doing(self) -> str:
        return f"{self._phrase.doing} {self._what}"

    @property
    def record(self) -> str:
        if not self.allowed:
            return f"Not allowed to {self._phrase.plain} {self._what}"
        return f"{self._phrase.done} {self._what}"

    @property
    def _phrase(self) -> Phrase:
        if self.action in PHRASES:
            return PHRASES[self.action]
        name = self.action.removeprefix("osiris_").replace("_", " ")
        return Phrase("Using", "Used", "use", what=name)

    @property
    def _what(self) -> str:
        phrase = self._phrase
        if phrase.what:
            return phrase.what
        if not self.resources:
            return phrase.unnamed
        first, *rest = self.resources
        shown = phrase.shown(first)
        return f"{shown} and {len(rest)} more" if rest else shown


def summary(steps: Sequence[Step]) -> str:
    return f"Used {len(steps)} tool{'' if len(steps) == 1 else 's'}"
