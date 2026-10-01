"""What the user asked for, validated.

A frozen value object. The installer fills one in from its wizard, the command
line fills one in from argv, and the install flow is handed one. Validation
lives here rather than in either caller, so both get the same rules and neither
can skip them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from osiris.model.disk import Disk, Filesystem, PartitionPlan

MINIMUM_PASSWORD = 6

# POSIX portable usernames: start with a letter or underscore, then letters,
# digits, hyphen or underscore. useradd will refuse anything else, and refusing
# it here means the user is told at the keyboard rather than forty minutes in.
_USERNAME = re.compile(r"^[a-z_][a-z0-9_-]*$")
_HOSTNAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9-]*$")


class InvalidRequest(ValueError):
    """The request cannot produce a working system."""


@dataclass(frozen=True)
class InstallRequest:
    disk: Disk
    username: str
    password: str
    hostname: str = "osiris"
    timezone: str = "Europe/London"
    locale: str = "en_GB.UTF-8"
    keymap: str = "us"
    filesystem: Filesystem = Filesystem.EXT4
    swap_megabytes: int = 0
    software_rendering: bool = False
    ssh_key: str | None = None
    virtiofs_tag: str | None = None

    #: Collected rather than raised one at a time, so a form can show every
    #: problem at once instead of playing whack-a-mole.
    problems: tuple[str, ...] = field(default_factory=tuple, init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "problems", tuple(self._find_problems()))

    def _find_problems(self) -> list[str]:
        problems: list[str] = []
        if not self.username:
            problems.append("a username is required")
        elif not _USERNAME.match(self.username):
            problems.append(
                "username must start with a letter and contain only "
                "lowercase letters, digits, - and _"
            )
        if not self.hostname:
            problems.append("a computer name is required")
        elif not _HOSTNAME.match(self.hostname):
            problems.append("computer name may only contain letters, digits and -")
        if len(self.password) < MINIMUM_PASSWORD:
            problems.append(f"password must be at least {MINIMUM_PASSWORD} characters")
        if not self.disk.usable:
            problems.append(f"{self.disk.path}: {self.disk.unusable_because}")
        if self.swap_megabytes < 0:
            problems.append("swap size cannot be negative")
        return problems

    @property
    def valid(self) -> bool:
        return not self.problems

    def validate(self) -> None:
        """Raise if this request cannot produce a working system."""
        if self.problems:
            raise InvalidRequest("; ".join(self.problems))

    @property
    def plan(self) -> PartitionPlan:
        return PartitionPlan(self.disk, self.filesystem, self.swap_megabytes)

    @property
    def extra_mounts(self) -> tuple[str, ...]:
        """fstab lines that genfstab cannot work out for itself."""
        lines: list[str] = []
        swap = self.plan.swap_file
        if swap:
            # genfstab does not see a swap file that is not switched on, and
            # switching it on inside the installer would then need switching
            # off again before the unmount.
            lines.append(f"{swap} none swap defaults 0 0")
        if self.virtiofs_tag:
            mount = f"/home/{self.username}/osiris"
            lines.append(f"{self.virtiofs_tag} {mount} virtiofs rw,nofail 0 0")
        return tuple(lines)
