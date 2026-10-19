"""Whether Osiris was upgraded under a process that lives for the session."""

from __future__ import annotations

from pathlib import Path

from osiris.platform import FakeFileSystem
from osiris.provision.upgrade import Upgrade

MARKER = Path("/usr/share/osiris/setup-ran")


def test_nothing_has_happened_while_setup_has_not_run_again() -> None:
    files = FakeFileSystem()
    files.write(MARKER, "0.1.0 1\n")
    assert not Upgrade(files, MARKER).happened()


def test_setup_running_again_is_an_upgrade() -> None:
    files = FakeFileSystem()
    files.write(MARKER, "0.1.0 1\n")
    upgrade = Upgrade(files, MARKER)
    files.write(MARKER, "0.1.0 2\n")
    assert upgrade.happened()


def test_setup_running_for_the_first_time_since_start_is_an_upgrade() -> None:
    files = FakeFileSystem()
    upgrade = Upgrade(files, MARKER)
    files.write(MARKER, "0.1.0 1\n")
    assert upgrade.happened()


def test_an_app_in_use_restarts_only_once_it_is_put_away() -> None:
    files = FakeFileSystem()
    upgrade = Upgrade(files, MARKER)
    files.write(MARKER, "0.1.0 1\n")
    assert not upgrade.restart_due(in_use=True)
    assert upgrade.restart_due(in_use=False)


def test_an_app_not_upgraded_never_restarts() -> None:
    assert not Upgrade(FakeFileSystem(), MARKER).restart_due(in_use=False)
