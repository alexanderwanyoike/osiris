"""Detecting what this machine needs, at install time.

A shim over osiris.platform.hardware and osiris.model.hardware, which is where
the detection and the package mapping actually live and are tested. See
provision/derive.py's counterpart for why the legacy entry points delegate
rather than being rewritten all at once.
"""

import os
import sys

for candidate in (
    "/usr/share/osiris/lib",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
):
    if os.path.isdir(os.path.join(candidate, "osiris")):
        sys.path.insert(0, candidate)
        break

from osiris.model.hardware import packages_for, unsupported  # noqa: E402
from osiris.platform.hardware import SystemProbe  # noqa: E402
from osiris.platform.process import SubprocessRunner  # noqa: E402

__all__ = ["describe", "detect", "packages_for", "unsupported"]


def detect():
    """What is in the machine the installer is running on."""
    return SystemProbe(SubprocessRunner(sink=lambda _line: None)).detect()


def describe(hardware) -> str:
    gpus = ", ".join(gpu.vendor.value for gpu in hardware.gpus) or "none"
    return f"cpu {hardware.cpu.value}, graphics {gpus}"
