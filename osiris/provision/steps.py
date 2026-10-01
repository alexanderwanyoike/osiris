"""The install, as a sequence of steps.

Each step is an object with a label, a weight and a `run`. That buys three
things over one long function: a step can be tested on its own, the progress
bar gets an honest denominator without anything counting lines, and the
sequence is visible in one place as a list rather than inferred by reading
three hundred lines from the top.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from osiris.model.request import InstallRequest
from osiris.platform.filesystem import FileSystem
from osiris.platform.process import CommandRunner
from osiris.provision.layout import TARGET, DiskLayout

ESP_SIZE = "+1024M"
SETTLE_TIMEOUT = 15.0


@dataclass
class Context:
    """Everything a step is allowed to touch."""

    request: InstallRequest
    runner: CommandRunner
    files: FileSystem
    layout: DiskLayout

    def target(self, path: str) -> Path:
        """A path inside the system being installed."""
        return Path(TARGET + path)


class Step(ABC):
    """One stage of the install."""

    #: Rough share of wall-clock. pacstrap dominates; a bar that spends most of
    #: its life on one step is not lying, and pretending otherwise only makes
    #: the remainder feel broken.
    weight: float = 0.01
    label: str = ""

    @abstractmethod
    def run(self, context: Context) -> None: ...

    @property
    def name(self) -> str:
        return type(self).__name__


class Unmount(Step):
    """Leave the target free, whatever state it is in.

    Runs first as well as last. A failed attempt leaves the target mounted, and
    without this the next one fails at `mount` with a message about /mnt being
    busy that says nothing about what went wrong the first time.
    """

    label = "Preparing"

    def run(self, context: Context) -> None:
        run = context.runner
        run.run("sync", check=False, quiet=True)
        if not run.run("mountpoint", "-q", TARGET, check=False).ok:
            return
        if run.run("umount", "-R", TARGET, check=False).ok:
            return
        # A busy target is not a failure at the end of an install: everything
        # is written by then, and arch-chroot routinely leaves a gpg-agent
        # holding the mountpoint for a few seconds after it returns. Reporting
        # a finished install as failed is worse than detaching lazily.
        run.run("umount", "-R", "-l", TARGET, check=False)


class Partition(Step):
    label = "Partitioning the disk"
    weight = 0.02

    def __init__(self, sleep: Callable[[float], None] = time.sleep) -> None:
        self._sleep = sleep

    def run(self, context: Context) -> None:
        disk = context.request.disk
        run = context.runner
        run.run("sgdisk", "--zap-all", disk.path)
        run.run(
            "sgdisk", "-n", f"1:0:{ESP_SIZE}", "-t", "1:ef00", "-c", "1:EFI", disk.path
        )
        run.run("sgdisk", "-n", "2:0:0", "-t", "2:8300", "-c", "2:root", disk.path)
        run.run("partprobe", disk.path)
        self._settle(context, disk.esp, disk.root)
        # Zapping the partition table leaves any old filesystem superblock
        # inside the new partition, where blkid will still report it.
        for device in (disk.esp, disk.root):
            run.run("wipefs", "--all", device, check=False, quiet=True)

    def _settle(self, context: Context, *devices: str) -> None:
        """Block until the kernel and udev have published the device nodes.

        `partprobe` asks the kernel to re-read the partition table and returns
        immediately; the nodes appear when udev gets round to it. On a disk
        that already held a filesystem that took 1.7 seconds here, and the
        `mount` that followed failed against a device that did not exist yet -
        intermittently, which is the worst way for an installer to fail.
        """
        context.runner.run("udevadm", "settle", check=False, quiet=True)
        deadline = SETTLE_TIMEOUT
        while deadline > 0:
            if all(context.files.exists(Path(device)) for device in devices):
                return
            self._sleep(0.2)
            deadline -= 0.2
        missing = [d for d in devices if not context.files.exists(Path(d))]
        raise FileNotFoundError(
            f"partitions did not appear after {SETTLE_TIMEOUT:.0f}s: "
            f"{', '.join(missing)}"
        )


class Format(Step):
    label = "Creating filesystems"
    weight = 0.03

    def run(self, context: Context) -> None:
        disk = context.request.disk
        context.runner.run("mkfs.fat", "-F32", "-n", "ESP", disk.esp)
        context.layout.format_root(disk.root)
        context.layout.mount(disk.root, context.request.plan)
        context.layout.mount_esp(disk.esp)


class InstallPackages(Step):
    label = "Installing packages"
    weight = 0.62

    def __init__(self, packages: list[str]) -> None:
        self._packages = packages

    def run(self, context: Context) -> None:
        context.runner.stream("pacstrap", "-K", TARGET, *self._packages)


class WriteFstab(Step):
    label = "Writing fstab"

    def run(self, context: Context) -> None:
        plan = context.request.plan
        if plan.swap_file:
            context.layout.make_swap(
                plan.swap_file, context.request.swap_megabytes
            )
        # genfstab writes to stdout; captured here rather than redirected by a
        # shell, because there is no shell.
        generated = context.runner.capture("genfstab", "-U", TARGET)
        lines = [generated, *context.request.extra_mounts, ""]
        context.files.write(context.target("/etc/fstab"), "\n".join(lines))
