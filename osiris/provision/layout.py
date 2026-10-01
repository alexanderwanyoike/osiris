"""Creating and mounting the target filesystem.

A strategy per filesystem, because ext4 and btrfs differ in four places that do
not factor into a flag: how the filesystem is made, how it is mounted, whether
subvolumes exist, and how a swap file is created. An `if filesystem == BTRFS`
in each of those would be the same branch written four times.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from osiris.model.disk import Filesystem, PartitionPlan
from osiris.platform.process import CommandRunner

TARGET = "/mnt"


class DiskLayout(ABC):
    """How one filesystem is created, mounted and given swap."""

    def __init__(self, runner: CommandRunner) -> None:
        self._run = runner

    @abstractmethod
    def format_root(self, device: str) -> None: ...

    @abstractmethod
    def mount(self, device: str, plan: PartitionPlan) -> None: ...

    @abstractmethod
    def make_swap(self, path: str, megabytes: int) -> None: ...

    def mount_esp(self, device: str) -> None:
        self._run.run("mkdir", "-p", f"{TARGET}/boot")
        self._run.run("mount", device, f"{TARGET}/boot")

    @staticmethod
    def for_filesystem(
        filesystem: Filesystem, runner: CommandRunner
    ) -> DiskLayout:
        return {
            Filesystem.EXT4: Ext4Layout,
            Filesystem.BTRFS: BtrfsLayout,
        }[filesystem](runner)


class Ext4Layout(DiskLayout):
    def format_root(self, device: str) -> None:
        self._run.run("mkfs.ext4", "-F", "-L", "osiris", device)

    def mount(self, device: str, plan: PartitionPlan) -> None:  # noqa: ARG002
        self._run.run("mount", device, TARGET)

    def make_swap(self, path: str, megabytes: int) -> None:
        target = TARGET + path
        self._run.run("fallocate", "-l", f"{megabytes}M", target)
        self._run.run("chmod", "600", target)
        self._run.run("mkswap", target)


class BtrfsLayout(DiskLayout):
    def format_root(self, device: str) -> None:
        self._run.run("mkfs.btrfs", "-f", "-L", "osiris", device)

    def mount(self, device: str, plan: PartitionPlan) -> None:
        """Create the subvolumes, then mount each where it belongs.

        The volume has to be mounted once at its top level to create them, then
        unmounted and remounted by subvolume - there is no way to create a
        subvolume on an unmounted filesystem.
        """
        self._run.run("mount", device, TARGET)
        for subvolume in plan.subvolumes:
            self._run.run(
                "btrfs", "subvolume", "create", f"{TARGET}/{subvolume.name}"
            )
        self._run.run("umount", TARGET)

        for subvolume in plan.subvolumes:
            if subvolume.mountpoint != TARGET:
                self._run.run("mkdir", "-p", subvolume.mountpoint or TARGET)
            self._run.run(
                "mount",
                "-o",
                f"subvol={subvolume.name},{subvolume.options}",
                device,
                subvolume.mountpoint or TARGET,
            )

    def make_swap(self, path: str, megabytes: int) -> None:
        """Preallocate and mark NODATACOW in one step.

        Required rather than preferred: btrfs refuses to swap on a file that is
        copy-on-write or compressed, and `mkswapfile` is the command that
        guarantees neither.
        """
        self._run.run(
            "btrfs",
            "filesystem",
            "mkswapfile",
            "--size",
            f"{megabytes}M",
            TARGET + path,
        )
