"""Whether archinstall really installed anything, read from what it printed."""

from __future__ import annotations

import pytest

from osiris.provision.archinstall_outcome import NETWORK, failure

COMPLETED = (
    "Installation completed without any errors.\n"
    "Log files temporarily available at /var/log/archinstall.\n"
    "You may reboot when ready.\n"
)


def test_an_install_that_exits_cleanly_and_says_it_completed_succeeded() -> None:
    assert failure(0, "Starting installation...\n" + COMPLETED) is None


@pytest.mark.parametrize(
    ("returncode", "output"),
    [(0, "Starting installation...\n"), (1, COMPLETED), (0, "")],
    ids=["exit 0 without finishing", "non-zero exit", "nothing printed"],
)
def test_anything_else_is_a_failure_with_a_reason(returncode: int, output: str) -> None:
    reason = failure(returncode, output)
    assert reason


@pytest.mark.parametrize(
    "line",
    [
        "Failed to sync Arch Linux package database.",
        "Could not sync mirrors: pacman -Syy exited with abnormal exit code [1]",
        "error: failed to synchronize all databases (download library error)",
        "error: failed retrieving file 'core.db' from geo.mirror.pkgbuild.com : "
        "Could not resolve host: geo.mirror.pkgbuild.com",
        "error: failed retrieving file 'mesa-1.pkg.tar.zst' from fastly : "
        "Operation too slow. Less than 1 bytes/sec transferred the last 10 seconds",
        "error: failed to retrieve some files",
        "Failed to connect to fastly.mirror.pkgbuild.com port 443 after 3 ms",
    ],
)
def test_a_download_failure_is_named_as_the_network(line: str) -> None:
    output = f"Installing packages: ['base']\n{line}\nPacstrap failed.\n"
    assert failure(1, output) == NETWORK


def test_other_failures_are_not_blamed_on_the_network() -> None:
    assert failure(1, "Could not generate fstab (disk out of space?)\n") != NETWORK
