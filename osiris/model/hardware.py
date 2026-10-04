"""What is in the machine.

Pure: osiris.platform.hardware does the looking. The installer passes what is
found to archinstall, which installs the microcode, drivers and Bluetooth
stack for this machine and no other - bundling every driver so one image
suits everything is how distributions reach four gigabytes. Which of
archinstall's driver sets a machine gets is decided in
osiris.provision.archinstall_config.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# PCI vendor IDs.
NVIDIA = 0x10DE
AMD = 0x1002
INTEL = 0x8086

#: NVIDIA's open kernel modules need the GPU System Processor, which arrived
#: with Turing. Device IDs are allocated in ascending order by generation and
#: Turing starts at 0x1E00 (TU102), so this one comparison separates "open
#: modules work" from "they do not" without a table of every card.
#:
#: Volta tops out at 0x1DB1 and Pascal at 0x1D81, both below the line.
TURING_MINIMUM = 0x1E00


class GpuVendor(StrEnum):
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    VIRTUAL = "virtual"
    UNKNOWN = "unknown"


class CpuVendor(StrEnum):
    AMD = "amd"
    INTEL = "intel"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Gpu:
    vendor: GpuVendor
    device_id: int = 0
    description: str = ""

    @property
    def has_open_kernel_modules(self) -> bool:
        """Turing or newer, for NVIDIA."""
        return self.vendor is GpuVendor.NVIDIA and self.device_id >= TURING_MINIMUM


@dataclass(frozen=True)
class Hardware:
    """Everything the installer needs to know about the target machine."""

    cpu: CpuVendor = CpuVendor.UNKNOWN
    gpus: tuple[Gpu, ...] = field(default_factory=tuple)
    bluetooth: bool = False
    virtual: bool = False
