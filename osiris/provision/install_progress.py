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

#: pacman's running total as it downloads a transaction's packages.
#: archinstall runs pacman on a pty, so pacman draws its progress bars,
#: counts included.
_DOWNLOADED = re.compile(r"^Total \(\s*(\d+)/(\d+)\)")
#: pacman's line as it installs each package of a transaction.
_INSTALLING = re.compile(r"^\(\s*(\d+)/(\d+)\) installing ")
#: After this, pacman's (n/N) counts are its hooks. Before it they are its
#: checks: keys, integrity, conflicts, disk space.
_RUNNING_HOOKS = ":: Running post-transaction hooks..."
_COUNTED = re.compile(r"^\(\s*(\d+)/(\d+)\) ")

#: Roughly how a pacman transaction's time divides: downloads up to the
#: first mark, installs up to the second, hooks for the rest. A package
#: being installed means every download has finished.
_DOWNLOADS_END, _INSTALLS_END = 0.5, 0.9


class Tracker:
    """Follows one install's output; a new install needs a new Tracker."""

    def __init__(self, stages: tuple[Stage, ...] = STAGES) -> None:
        self._stages = stages
        self._current = 0
        #: How far through the current stage, 0.0 to 1.0.
        self._within = 0.0
        self._transaction = _Transaction()

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
                self._transaction = _Transaction()
                return self.status
        within = self._transaction.read(text)
        if within is None or within <= self._within:
            return None
        self._within = within
        return self.status

    def _fraction(self) -> float:
        before = sum(stage.weight for stage in self._stages[: self._current])
        done = before + self._stages[self._current].weight * self._within
        return done / sum(stage.weight for stage in self._stages)


class _Transaction:
    """How far pacman has got through one transaction, from what it prints."""

    def __init__(self) -> None:
        self._hooks = False

    def read(self, text: str) -> float | None:
        """How far through, 0.0 to 1.0, if text says; None if it does not."""
        if text == _RUNNING_HOOKS:
            self._hooks = True
            return None
        if self._hooks:
            return _between(_INSTALLS_END, 1.0, _COUNTED.match(text))
        if downloaded := _DOWNLOADED.match(text):
            return _between(0.0, _DOWNLOADS_END, downloaded)
        return _between(_DOWNLOADS_END, _INSTALLS_END, _INSTALLING.match(text))


def _between(low: float, high: float, counted: re.Match[str] | None) -> float | None:
    """Where pacman's n/N count puts a phase that runs from low to high."""
    if counted is None:
        return None
    count, total = (int(group) for group in counted.groups())
    return low + (high - low) * count / total
