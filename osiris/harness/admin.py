"""Admin password requests: sudo asking the person, through Osiris, for the
password, and the guards on who may ask (ADR 0018).

The agent's sudo runs with ``-A``, so sudo runs the askpass helper, which asks
the Harness over D-Bus; the Harness shows an admin password card in the
Conversation whose command it is. Everything here decides; the helper and the
Harness only draw and carry the answer.
"""

from __future__ import annotations

from osiris.platform.processes import Process, Processes


def _is_sudo(process: Process) -> bool:
    """The person cannot read a set-uid program's executable, so sudo is known
    by its name and by running as root; only a set-uid program can make a
    process of theirs root, and of those only sudo runs a helper before it has
    a password."""
    return process.name == "sudo" and process.euid == 0


def asking_sudo(processes: Processes, helper: int) -> Process | None:
    """The sudo that started the helper ``helper``, if it is a genuine one
    running as root for the same person; None means refuse."""
    found = processes.get(helper)
    if found is None or found.euid == 0:
        return None
    parent = processes.get(found.parent)
    if parent is None or not _is_sudo(parent) or parent.uid != found.uid:
        return None
    return parent
