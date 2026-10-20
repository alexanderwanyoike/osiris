"""How far an install has got, read from archinstall's output as it streams.

archinstall reports no fraction complete. It does print a line as it starts
each part of the install, and pacman, which it runs to install every package,
prints counts as it goes. This turns those lines into a stage a person can
read, its number of the total, and a fraction of the whole install.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stage:
    title: str
    #: Roughly how much of the install's time this stage takes, against the
    #: others. Only the ratios matter.
    weight: int


@dataclass(frozen=True)
class Status:
    """What the progress page shows."""

    title: str
    step: int
    steps: int
    fraction: float


STAGES = (
    Stage("Preparing your disk", 3),
    Stage("Installing the base system", 22),
    Stage("Setting up the bootloader", 6),
    Stage("Installing drivers and sound", 10),
    Stage("Installing the desktop", 45),
    Stage("Applying Osiris", 12),
    Stage("Finishing", 2),
)


class Tracker:
    """Follows one install's output; a new install needs a new Tracker."""

    def __init__(self, stages: tuple[Stage, ...] = STAGES) -> None:
        self._stages = stages

    @property
    def status(self) -> Status:
        return Status(self._stages[0].title, 1, len(self._stages), 0.0)
