"""Each step of an answer, as a person reads it while Osiris works and after."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Phrase:
    doing: str
    done: str
    #: What the action is always done to; empty names its resources instead.
    what: str = ""


#: The Engine's actions, as words.
PHRASES = {
    "read": Phrase("Reading", "Read"),
    "edit": Phrase("Editing", "Edited"),
    "list": Phrase("Listing", "Listed"),
    "osiris_list_themes": Phrase("Looking at", "Looked at", "the themes"),
    "osiris_create_theme": Phrase("Making", "Made", "a theme"),
    "osiris_apply_theme": Phrase("Applying", "Applied", "a theme"),
    "osiris_list_programs": Phrase("Looking at", "Looked at", "your programs"),
    "osiris_create_program": Phrase("Starting", "Started", "a program"),
    "osiris_commit_program": Phrase("Saving", "Saved", "a change"),
    "osiris_check_program": Phrase("Checking", "Checked", "the program"),
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
        return f"{PHRASES[self.action].doing} {self._what}"

    @property
    def record(self) -> str:
        return f"{PHRASES[self.action].done} {self._what}"

    @property
    def _what(self) -> str:
        if PHRASES[self.action].what:
            return PHRASES[self.action].what
        first, *rest = self.resources
        return f"{_path(first)} and {len(rest)} more" if rest else _path(first)
