"""The processes port: who a running process is, read from /proc."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from osiris.platform.processes import ProcFs


@pytest.fixture
def sleeper() -> Iterator[subprocess.Popen[bytes]]:
    sleep = shutil.which("sleep")
    assert sleep is not None
    child = subprocess.Popen([sleep, "30"])
    yield child
    child.kill()
    child.wait()


def test_proc_reads_a_running_process(sleeper: subprocess.Popen[bytes]) -> None:
    found = ProcFs().get(sleeper.pid)
    assert found is not None
    assert found.pid == sleeper.pid
    assert found.parent == os.getpid()
    assert (found.uid, found.euid) == (os.getuid(), os.geteuid())
    assert found.name == "sleep"
    assert found.cmdline == (str(sleeper.args[0]), "30")
    assert found.exe == str(Path(str(sleeper.args[0])).resolve())


def test_a_process_that_is_gone_is_none() -> None:
    # Above the kernel's highest possible pid, so it never exists.
    assert ProcFs().get(2**23) is None
