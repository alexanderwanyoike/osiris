"""How far the install has got, read from what archinstall prints.

Every line fed in here is one archinstall 4.5 or pacman 7.1 really prints,
taken from their source or captured from pacman running under archinstall's
own pty, as the installer runs it.
"""

from __future__ import annotations

from osiris.provision.install_progress import Status, Tracker


def test_an_install_starts_by_preparing_the_disk() -> None:
    assert Tracker().status == Status("Preparing your disk", 1, 7, 0.0)
