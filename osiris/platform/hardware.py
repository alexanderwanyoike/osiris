"""Finding out what is in the machine.

The port is deliberately thin: it answers "what hardware is this", and every
decision about what that implies lives in osiris.model.hardware, where it can
be tested against a table of real PCI IDs rather than against a laptop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from osiris.model.hardware import (
    AMD,
    INTEL,
    NVIDIA,
    CpuVendor,
    Gpu,
    GpuVendor,
    Hardware,
)
from osiris.platform.process import CommandError, CommandRunner

#: `lspci -mn` writes one quoted field per column; the two we want are the
#: class and the vendor:device pair, in hex without the 0x.
_LSPCI = re.compile(
    r'^\S+\s+"(?P<klass>[0-9a-fA-F]{4})"\s+"(?P<vendor>[0-9a-fA-F]{4})"\s+'
    r'"(?P<device>[0-9a-fA-F]{4})"'
)

#: PCI classes that mean "this draws the screen".
_DISPLAY_CLASSES = {0x0300, 0x0302, 0x0380}

#: Vendors whose display devices are emulated rather than real silicon.
_VIRTUAL_VENDORS = {
    0x1AF4,  # Red Hat / virtio
    0x1B36,  # Red Hat QXL
    0x15AD,  # VMware
    0x80EE,  # VirtualBox
    0x1234,  # QEMU standard VGA
}


@runtime_checkable
class HardwareProbe(Protocol):
    def detect(self) -> Hardware: ...


@dataclass
class FakeProbe:
    """A machine described rather than discovered."""

    hardware: Hardware = field(default_factory=Hardware)

    def detect(self) -> Hardware:
        return self.hardware


class SystemProbe:
    """The real machine, read from lspci, /proc and /sys."""

    def __init__(self, runner: CommandRunner, root: Path = Path("/")) -> None:
        self._run = runner
        self._root = root

    def detect(self) -> Hardware:
        virtual = self._is_virtual()
        return Hardware(
            cpu=self._cpu(),
            gpus=tuple(self._gpus(virtual)),
            bluetooth=self._has_bluetooth(),
            virtual=virtual,
        )

    def _cpu(self) -> CpuVendor:
        try:
            text = (self._root / "proc/cpuinfo").read_text()
        except OSError:
            return CpuVendor.UNKNOWN
        if "AuthenticAMD" in text:
            return CpuVendor.AMD
        if "GenuineIntel" in text:
            return CpuVendor.INTEL
        return CpuVendor.UNKNOWN

    def _gpus(self, virtual: bool) -> list[Gpu]:
        try:
            # -mn gives machine-readable numeric ids; parsing names is how you
            # end up matching on marketing strings that change.
            listing = self._run.capture("lspci", "-mn")
        except Exception:
            # No lspci on the medium is not fatal, only blind: the install
            # proceeds with mesa and the user gets a working, unaccelerated
            # desktop rather than no desktop.
            return []

        found: list[Gpu] = []
        for line in listing.splitlines():
            match = _LSPCI.match(line)
            if match is None:
                continue
            if int(match["klass"], 16) not in _DISPLAY_CLASSES:
                continue
            vendor_id = int(match["vendor"], 16)
            found.append(
                Gpu(
                    vendor=self._vendor(vendor_id, virtual),
                    device_id=int(match["device"], 16),
                    description=f"{vendor_id:04x}:{match['device'].lower()}",
                )
            )
        return found

    @staticmethod
    def _vendor(vendor_id: int, virtual: bool) -> GpuVendor:
        if vendor_id in _VIRTUAL_VENDORS:
            return GpuVendor.VIRTUAL
        mapping = {
            NVIDIA: GpuVendor.NVIDIA,
            AMD: GpuVendor.AMD,
            INTEL: GpuVendor.INTEL,
        }
        resolved = mapping.get(vendor_id, GpuVendor.UNKNOWN)
        # Intel's vendor id covers the emulated adapter some hypervisors
        # present, so a guest is believed over the id.
        if virtual and resolved is GpuVendor.UNKNOWN:
            return GpuVendor.VIRTUAL
        return resolved

    def _is_virtual(self) -> bool:
        result = self._run.run("systemd-detect-virt", check=False, quiet=True)
        return result.ok and result.stdout.strip() not in ("", "none")

    def _has_bluetooth(self) -> bool:
        return (self._root / "sys/class/bluetooth").is_dir() and any(
            (self._root / "sys/class/bluetooth").iterdir()
        )


#: Mesa's software renderers, for a driver that does not answer
#: GLX_MESA_query_renderer and so never says "Accelerated" either way.
_SOFTWARE = ("llvmpipe", "softpipe", "swrast", "software rasterizer")


def rendering_accelerated(runner: CommandRunner) -> bool:
    """Whether a GPU draws the desktop, as glxinfo reports it.

    Muffin counts a software renderer as accelerated, so Cinnamon cannot be
    asked. Mesa states it outright; NVIDIA's own driver does not, and is
    judged by its renderer's name. With no answer at all a GPU is assumed:
    the drift extension's own cost check is the backstop.
    """
    try:
        output = runner.run("glxinfo", "-B", quiet=True).stdout
    except OSError, CommandError:
        return True
    renderer = ""
    for line in output.splitlines():
        key, _, value = line.strip().partition(":")
        if key == "Accelerated":
            return value.strip() == "yes"
        if key == "OpenGL renderer string":
            renderer = value.lower()
    return not any(name in renderer for name in _SOFTWARE)
