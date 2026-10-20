"""Whether archinstall really installed anything, read from what it printed."""

from __future__ import annotations

import pytest

from osiris.provision.archinstall_outcome import failure

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
