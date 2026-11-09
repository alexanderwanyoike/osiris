"""The Programs' history as crediting shell commits reads it (#219): a folder
gone, or never a Program, has no commits to credit, so one such folder never
keeps the others from being credited."""
from datetime import datetime

from osiris.platform.process import CommandError
from osiris.programs.programs import ProgramError, Programs


class ProgramHistory:
    def __init__(self, programs: Programs):
        self._programs = programs

    def commits_since(self, name: str, since: datetime) -> list[tuple[str, str]]:
        try:
            return self._programs.commits_since(name, since)
        except (CommandError, ProgramError):
            return []

    def label(self, name: str) -> str:
        try:
            return self._programs.label(name)
        except ProgramError:
            return name
