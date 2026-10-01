"""The install flow, without a disk to ruin.

Every assertion here was previously only observable by running a 40-minute
install in a virtual machine and watching.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from osiris.model.disk import Disk, Filesystem
from osiris.model.request import InstallRequest, InvalidRequest
from osiris.platform import FakeFileSystem, FakeRunner
from osiris.platform.process import CommandError, Result
from osiris.provision.installer import Installer
from osiris.provision.steps import (
    Format,
    InstallPackages,
    Partition,
    Step,
    Unmount,
    WriteFstab,
)

DISK = Disk(path="/dev/vda", size=30 * 1000**3, label="Test")


def a_request(**overrides: object) -> InstallRequest:
    defaults = {"disk": DISK, "username": "alex", "password": "osiris123"}
    return InstallRequest(**{**defaults, **overrides})  # type: ignore[arg-type]


@pytest.fixture
def files() -> FakeFileSystem:
    """A filesystem where the partitions already exist.

    The Partition step waits for the device nodes to appear; in these tests
    they are there from the start so the wait returns at once.
    """
    filesystem = FakeFileSystem()
    filesystem.make_directory(Path("/dev"))
    for device in (DISK.esp, DISK.root):
        filesystem.write(Path(device), "")
    return filesystem


def an_installer(
    runner: FakeRunner, files: FakeFileSystem, steps: list[Step] | None = None
) -> Installer:
    return Installer(
        runner,
        files,
        steps
        or [
            Unmount(),
            Partition(sleep=lambda _seconds: None),
            Format(),
            InstallPackages(["base", "linux"]),
            WriteFstab(),
        ],
        cleanup=Unmount(),
    )


class TestOrdering:
    def test_the_disk_is_partitioned_before_it_is_formatted(
        self, files: FakeFileSystem
    ) -> None:
        runner = FakeRunner()
        an_installer(runner, files).install(a_request())
        commands = runner.commands
        assert commands.index("sgdisk --zap-all /dev/vda") < next(
            i for i, c in enumerate(commands) if c.startswith("mkfs.ext4")
        )

    def test_packages_are_installed_after_the_target_is_mounted(
        self, files: FakeFileSystem
    ) -> None:
        runner = FakeRunner()
        an_installer(runner, files).install(a_request())
        commands = runner.commands
        mounted = next(
            i for i, c in enumerate(commands) if c.startswith("mount /dev/vda2")
        )
        pacstrap = next(i for i, c in enumerate(commands) if c.startswith("pacstrap"))
        assert mounted < pacstrap

    def test_progress_is_reported_once_per_step_and_ends_complete(
        self, files: FakeFileSystem
    ) -> None:
        seen: list[tuple[float, str]] = []
        an_installer(FakeRunner(), files).install(
            a_request(), progress=lambda f, m: seen.append((f, m))
        )
        assert seen[0][0] == 0.0
        assert seen[-1] == (1.0, "Done")
        assert [fraction for fraction, _ in seen] == sorted(
            fraction for fraction, _ in seen
        )


class TestPartitioning:
    def test_old_filesystem_signatures_are_wiped(self, files: FakeFileSystem) -> None:
        """sgdisk clears the table, not the superblocks inside the partitions."""
        runner = FakeRunner()
        an_installer(runner, files).install(a_request())
        assert runner.ran("wipefs", "--all", "/dev/vda1")
        assert runner.ran("wipefs", "--all", "/dev/vda2")

    def test_it_waits_for_the_device_nodes(self) -> None:
        """partprobe returns before udev has created them.

        Measured at 1.7 seconds on a disk that already held a filesystem; the
        mount that followed failed intermittently.
        """
        empty = FakeFileSystem()
        runner = FakeRunner()
        with pytest.raises(FileNotFoundError) as caught:
            an_installer(runner, empty).install(a_request())
        assert "/dev/vda1" in str(caught.value)
        assert runner.ran("udevadm", "settle")

    def test_it_proceeds_once_the_nodes_appear(self, files: FakeFileSystem) -> None:
        runner = FakeRunner()
        an_installer(runner, files).install(a_request())
        assert runner.ran("mkfs.fat", "-F32", "-n", "ESP", "/dev/vda1")


class TestFilesystems:
    def test_ext4_mounts_the_partition_directly(self, files: FakeFileSystem) -> None:
        runner = FakeRunner()
        an_installer(runner, files).install(a_request(filesystem=Filesystem.EXT4))
        assert runner.ran("mkfs.ext4", "-F", "-L", "osiris", "/dev/vda2")
        assert not runner.ran("btrfs", "subvolume", "create", "/mnt/@")

    def test_btrfs_creates_subvolumes_and_remounts_by_subvolume(
        self, files: FakeFileSystem
    ) -> None:
        runner = FakeRunner()
        an_installer(runner, files).install(a_request(filesystem=Filesystem.BTRFS))
        assert runner.ran("btrfs", "subvolume", "create", "/mnt/@")
        assert runner.ran("btrfs", "subvolume", "create", "/mnt/@home")
        mounts = runner.arguments_to("mount")
        assert any("subvol=@," in " ".join(argv) for argv in mounts)

    def test_btrfs_swap_is_made_with_mkswapfile(self, files: FakeFileSystem) -> None:
        """btrfs refuses to swap on a copy-on-write or compressed file."""
        runner = FakeRunner()
        an_installer(runner, files).install(
            a_request(filesystem=Filesystem.BTRFS, swap_megabytes=2048)
        )
        assert runner.ran("btrfs", "filesystem", "mkswapfile", "--size", "2048M")

    def test_ext4_swap_is_preallocated_and_locked_down(
        self, files: FakeFileSystem
    ) -> None:
        runner = FakeRunner()
        an_installer(runner, files).install(a_request(swap_megabytes=1024))
        assert runner.ran("fallocate", "-l", "1024M", "/mnt/swapfile")
        assert runner.ran("chmod", "600", "/mnt/swapfile")
        assert runner.ran("mkswap", "/mnt/swapfile")

    def test_no_swap_means_no_swap_commands(self, files: FakeFileSystem) -> None:
        runner = FakeRunner()
        an_installer(runner, files).install(a_request())
        assert runner.count("mkswap") == 0
        assert runner.count("fallocate") == 0


class TestFstab:
    def test_the_generated_table_is_written_with_the_extra_mounts(
        self, files: FakeFileSystem
    ) -> None:
        runner = FakeRunner(
            results={
                "genfstab -U /mnt": Result(("genfstab",), 0, "UUID=abc / ext4 rw 0 1\n")
            }
        )
        an_installer(runner, files).install(a_request(swap_megabytes=512))
        written = files.read(Path("/mnt/etc/fstab"))
        assert "UUID=abc / ext4 rw 0 1" in written
        assert "/swapfile none swap defaults 0 0" in written


class TestFailure:
    def test_a_failing_step_propagates_with_the_command_named(
        self, files: FakeFileSystem
    ) -> None:
        runner = FakeRunner(results={"pacstrap": Result(("pacstrap",), 1)})
        with pytest.raises(CommandError) as caught:
            an_installer(runner, files).install(a_request())
        assert "pacstrap" in str(caught.value)

    def test_the_target_is_unmounted_even_when_a_step_fails(
        self, files: FakeFileSystem
    ) -> None:
        """So a retry starts from a known state rather than a busy mountpoint."""
        runner = FakeRunner(
            results={
                "pacstrap": Result(("pacstrap",), 1),
                "mountpoint": Result(("mountpoint",), 0),
            }
        )
        with pytest.raises(CommandError):
            an_installer(runner, files).install(a_request())
        assert runner.ran("umount", "-R", "/mnt")

    def test_a_busy_target_falls_back_to_a_lazy_detach(
        self, files: FakeFileSystem
    ) -> None:
        """A busy mountpoint at the end is not an install failure.

        arch-chroot leaves a gpg-agent holding it for a few seconds. Reporting
        a complete install as failed because of that tells the user to redo
        forty minutes of work that succeeded.
        """
        runner = FakeRunner(
            results={
                "mountpoint": Result(("mountpoint",), 0),
                "umount -R /mnt": Result(("umount",), 32),
            }
        )
        an_installer(runner, files).install(a_request())
        assert runner.ran("umount", "-R", "-l", "/mnt")

    def test_an_invalid_request_is_refused_before_anything_is_touched(
        self, files: FakeFileSystem
    ) -> None:
        runner = FakeRunner()
        with pytest.raises(InvalidRequest):
            an_installer(runner, files).install(a_request(password="x"))
        assert runner.calls == [], "nothing may run before the request validates"
