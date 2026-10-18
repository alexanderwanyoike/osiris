"""What the user asked for, validated.

A frozen value object. The installer fills one in from its wizard, the command
line fills one in from argv, and the install flow is handed one. Validation
lives here rather than in either caller, so both get the same rules and neither
can skip them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from osiris.model.disk import Disk, Filesystem
from osiris.model.layout import InstallMode

MINIMUM_PASSWORD = 6

#: A disk passphrase is the only thing between a stolen laptop and its
#: contents, and unlike an account password it cannot be reset. Eight is the
#: floor, not a recommendation.
MINIMUM_PASSPHRASE = 8

# POSIX portable usernames: start with a letter or underscore, then letters,
# digits, hyphen or underscore. useradd will refuse anything else, and refusing
# it here means the user is told at the keyboard rather than forty minutes in.
_USERNAME = re.compile(r"^[a-z_][a-z0-9_-]*$")
_HOSTNAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9-]*$")


def passphrase_problem(passphrase: str) -> str | None:
    """Why `passphrase` cannot unlock a disk, or None if it can.

    A function of its own so the installer's form applies the same rule as
    the request, as the user types.
    """
    if len(passphrase) < MINIMUM_PASSPHRASE:
        return f"encryption passphrase must be at least {MINIMUM_PASSPHRASE} characters"
    if not (passphrase.isascii() and passphrase.isprintable()):
        # It is typed at boot, before any input method exists, through
        # whichever keymap the initramfs carries. Characters outside ASCII
        # are where that goes wrong, and a passphrase that cannot be typed
        # is a disk that cannot be opened.
        return (
            "encryption passphrase may only use letters, digits, spaces "
            "and the symbols on a US keyboard"
        )
    return None


class InvalidRequest(ValueError):
    """The request cannot produce a working system."""


@dataclass(frozen=True)
class InstallRequest:
    disk: Disk
    username: str
    password: str = field(repr=False)
    hostname: str = "osiris"
    timezone: str = "Europe/London"
    locale: str = "en_GB.UTF-8"
    keymap: str = "us"
    filesystem: Filesystem = Filesystem.EXT4
    software_rendering: bool = False
    mode: InstallMode = InstallMode.WHOLE_DISK
    #: The partition to install into, for InstallMode.EXISTING_PARTITION.
    root_partition: str | None = None
    #: Encrypt the root filesystem with LUKS. archinstall does the encrypting;
    #: see archinstall_config.
    encrypt: bool = False
    #: Typed at every boot to unlock the root. Kept out of the repr so it
    #: cannot reach a log or a traceback by way of the request.
    passphrase: str = field(default="", repr=False)

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
        if self.mode is InstallMode.WHOLE_DISK and not self.disk.usable:
            problems.append(f"{self.disk.path}: {self.disk.unusable_because}")
        if self.mode is InstallMode.EXISTING_PARTITION and not self.root_partition:
            problems.append("choose a partition to install into")
        if self.encrypt:
            problems += self._encryption_problems()
        return problems

    def _encryption_problems(self) -> list[str]:
        problems: list[str] = []
        if (problem := passphrase_problem(self.passphrase)) is not None:
            problems.append(problem)
        if self.mode is InstallMode.EXISTING_PARTITION:
            # This mode always shares another system's EFI partition, which
            # puts the kernels inside the encrypted root. See Layout.problems.
            problems.append(
                "encryption is not available when installing on an existing partition"
            )
        return problems

    @property
    def valid(self) -> bool:
        return not self.problems

    def validate(self) -> None:
        """Raise if this request cannot produce a working system."""
        if self.problems:
            raise InvalidRequest("; ".join(self.problems))
