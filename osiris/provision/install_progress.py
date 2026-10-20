"""How far an install has got, read from archinstall's output as it streams.

archinstall reports no fraction complete. It does print a line as it starts
each part of the install, and pacman, which it runs to install every package,
prints counts as it goes. This turns those lines into a stage a person can
read, its number of the total, and a fraction of the whole install.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from osiris.provision.archinstall_config import OSIRIS_PACKAGE, SETUP_COMMAND


@dataclass(frozen=True)
class Stage:
    title: str
    #: Roughly how much of the install's time this stage takes, against the
    #: others. Only the ratios matter.
    weight: int
    #: The line archinstall prints as the stage begins. None for the first,
    #: which is under way before archinstall prints anything of note.
    starts: re.Pattern[str] | None = None


@dataclass(frozen=True)
class Status:
    """What the progress page shows."""

    title: str
    step: int
    steps: int
    fraction: float


#: The lines are archinstall 4.5's info() messages, in the order its guided
#: script prints them. A user is created just before the sound, graphics and
#: greeter packages go in, and that line is the last before them.
STAGES = (
    Stage("Preparing your disk", 3),
    Stage(
        "Installing the base system", 22, re.compile(r"^Installing packages: \['base'")
    ),
    Stage("Setting up the bootloader", 6, re.compile(r"^Adding bootloader ")),
    Stage("Installing drivers and sound", 10, re.compile(r"^Creating user ")),
    Stage(
        "Installing the desktop",
        45,
        re.compile("^" + re.escape(f"Installing packages: {[OSIRIS_PACKAGE]}") + "$"),
    ),
    Stage(
        "Applying Osiris",
        12,
        re.compile("^" + re.escape(f'Executing custom command "{SETUP_COMMAND}"')),
    ),
    Stage("Finishing", 2, re.compile(r"^Updating \S*/etc/fstab$")),
)

#: pacman's line as it installs each package of a transaction. archinstall
#: runs pacman on a pty, so pacman draws its progress bars, counts included.
_INSTALLING = re.compile(r"^\(\s*(\d+)/(\d+)\) installing ")
#: pacman's running total as it downloads a transaction's packages.
_DOWNLOADED = re.compile(r"^Total \(\s*(\d+)/(\d+)\)")

#: Roughly how a pacman transaction's time divides: downloading the packages,
#: installing them, and the rest running the hooks that follow. A package
#: being installed means every download has finished.
_DOWNLOADING, _INSTALLING_SHARE = 0.5, 0.4


class Tracker:
    """Follows one install's output; a new install needs a new Tracker."""

    def __init__(self, stages: tuple[Stage, ...] = STAGES) -> None:
        self._stages = stages
        self._current = 0
        #: How far through the current stage, 0.0 to 1.0.
        self._within = 0.0

    @property
    def status(self) -> Status:
        stage = self._stages[self._current]
        return Status(
            stage.title, self._current + 1, len(self._stages), self._fraction()
        )

    def feed(self, line: str) -> Status | None:
        """The new status if line moved the install on, else None."""
        text = line.strip()
        for index in range(self._current + 1, len(self._stages)):
            starts = self._stages[index].starts
            if starts is not None and starts.search(text):
                self._current = index
                self._within = 0.0
                return self.status
        if downloaded := _DOWNLOADED.match(text):
            return self._reach(_DOWNLOADING * _share(downloaded))
        if installing := _INSTALLING.match(text):
            return self._reach(_DOWNLOADING + _INSTALLING_SHARE * _share(installing))
        return None

    def _reach(self, within: float) -> Status | None:
        if within <= self._within:
            return None
        self._within = within
        return self.status

    def _fraction(self) -> float:
        before = sum(stage.weight for stage in self._stages[: self._current])
        done = before + self._stages[self._current].weight * self._within
        return done / sum(stage.weight for stage in self._stages)


def _share(counted: re.Match[str]) -> float:
    """n/N from one of pacman's (n/N) counts."""
    count, total = (int(group) for group in counted.groups())
    return count / total
