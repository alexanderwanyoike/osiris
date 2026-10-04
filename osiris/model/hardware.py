"""What is in the machine, and what it therefore needs installed.

Pure. Given a description of the hardware, this says which packages belong on
that machine - and nothing here opens a file or runs lspci, so every mapping
below is a table with a test rather than something you discover by installing
onto a laptop and watching it fail.

The principle is that Osiris ships drivers for the machine it is being
installed on and no others. Bundling every driver so that one image suits
everything is how distributions get to four gigabytes. Detecting is the
installer's job.
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


# --------------------------------------------------------------------------- #
# what each finding implies


def microcode(cpu: CpuVendor) -> list[str]:
    """Processor microcode updates.

    Not optional and not a preference: these carry errata and security fixes,
    and GRUB loads whichever is installed as an early initrd without being
    told. Shipping neither - which Osiris did - leaves every machine running
    whatever microcode shipped on the board.
    """
    return {
        CpuVendor.AMD: ["amd-ucode"],
        CpuVendor.INTEL: ["intel-ucode"],
        CpuVendor.UNKNOWN: [],
    }[cpu]


def graphics(gpus: tuple[Gpu, ...], virtual: bool = False) -> list[str]:
    """Drivers for every GPU present, not just the first.

    A laptop with Intel graphics and an NVIDIA card needs both: the integrated
    one drives the panel and the discrete one is what anything demanding runs
    on. Picking a single "best" GPU gets that case wrong.
    """
    packages: list[str] = ["mesa"]
    if virtual or any(gpu.vendor is GpuVendor.VIRTUAL for gpu in gpus):
        # No GPU to accelerate anything. Software rendering, or the desktop
        # comes up to a black screen.
        packages.append("vulkan-swrast")

    for gpu in gpus:
        packages.extend(_for_gpu(gpu))
    return sorted(set(packages))


def _for_gpu(gpu: Gpu) -> list[str]:
    if gpu.vendor is GpuVendor.AMD:
        return ["vulkan-radeon", "libva-mesa-driver"]
    if gpu.vendor is GpuVendor.INTEL:
        return ["vulkan-intel", "intel-media-driver"]
    if gpu.vendor is GpuVendor.NVIDIA:
        if gpu.has_open_kernel_modules:
            return ["nvidia-open", "nvidia-utils"]
        # Pascal and older were dropped from the repositories with driver 590.
        # The proprietary driver for them lives in the AUR, which a
        # distribution cannot depend on, so these cards get nouveau - which is
        # in mesa and already installed.
        return []
    return []


def peripherals(hardware: Hardware) -> list[str]:
    return ["bluez", "bluez-utils"] if hardware.bluetooth else []


def packages_for(hardware: Hardware) -> list[str]:
    """Everything this machine needs that a generic install would not."""
    return sorted(
        set(
            microcode(hardware.cpu)
            + graphics(hardware.gpus, hardware.virtual)
            + peripherals(hardware)
        )
    )


def unsupported(hardware: Hardware) -> list[str]:
    """Findings worth telling the user about before they commit.

    An installer that silently gives you nouveau on a card that had a working
    proprietary driver last week has not done you a favour.
    """
    notes: list[str] = []
    for gpu in hardware.gpus:
        if gpu.vendor is GpuVendor.NVIDIA and not gpu.has_open_kernel_modules:
            notes.append(
                f"{gpu.description or 'This NVIDIA card'} predates Turing. "
                "NVIDIA's current driver has dropped it and the legacy one is "
                "not in Arch's repositories, so Osiris will use the open "
                "nouveau driver."
            )
    return notes
