"""Where Osiris goes on a disk, and what that destroys.

These are the tests that matter most in the project. A wrong answer here does
not produce a bad theme; it produces someone's photographs gone.
"""

from __future__ import annotations

import pytest

from osiris.model.disk import MINIMUM_BYTES, Disk, Filesystem
from osiris.model.layout import (
    DiskContents,
    FreeRegion,
    InstallMode,
    Layout,
    Partition,
)

GB = 1000**3
DISK = Disk(path="/dev/sda", size=931 * GB, label="ST1000DM010")


def windows_and_free_space() -> DiskContents:
    """A common dual-boot starting point: Windows, with room made beside it."""
    return DiskContents(
        disk=DISK,
        partitions=(
            Partition("/dev/sda1", 1, 260 * 1000**2, "vfat", "SYSTEM", esp=True),
            Partition("/dev/sda2", 2, 400 * GB, "ntfs", "Windows"),
        ),
        free=(FreeRegion(start=401 * GB, size=500 * GB),),
    )


def a_spare_partition() -> DiskContents:
    return DiskContents(
        disk=DISK,
        partitions=(
            Partition("/dev/sda1", 1, 512 * 1000**2, "vfat", "EFI", esp=True),
            Partition("/dev/sda2", 2, 400 * GB, "ext4", "Other OS"),
            Partition("/dev/sda3", 3, 300 * GB, "ext4", "spare"),
            Partition("/dev/sda4", 4, 200 * GB, "ext4", "home"),
        ),
    )


class TestWhatIsOffered:
    def test_an_empty_disk_offers_only_erasing_it(self) -> None:
        empty = DiskContents(disk=DISK)
        assert empty.modes() == [InstallMode.WHOLE_DISK]

    def test_free_space_is_offered_when_there_is_enough(self) -> None:
        assert InstallMode.FREE_SPACE in windows_and_free_space().modes()

    def test_free_space_too_small_is_not_offered(self) -> None:
        cramped = DiskContents(
            disk=DISK, free=(FreeRegion(start=0, size=MINIMUM_BYTES - 1),)
        )
        assert InstallMode.FREE_SPACE not in cramped.modes()

    def test_an_existing_partition_is_offered_when_one_is_usable(self) -> None:
        assert InstallMode.EXISTING_PARTITION in a_spare_partition().modes()

    def test_the_esp_is_never_offered_as_a_root_partition(self) -> None:
        candidates = a_spare_partition().candidates_for_root()
        assert all(not partition.esp for partition in candidates)

    def test_a_mounted_partition_is_not_offered(self) -> None:
        """It is almost always the medium being booted from."""
        contents = DiskContents(
            disk=DISK,
            partitions=(Partition("/dev/sda1", 1, 500 * GB, "ext4", mounted=True),),
        )
        assert contents.candidates_for_root() == []


class TestWhatGetsDestroyed:
    """The sentence the installer shows before it does anything."""

    def test_erasing_the_disk_names_everything_on_it(self) -> None:
        layout = Layout(windows_and_free_space(), InstallMode.WHOLE_DISK)
        assert len(layout.destroys) == 2
        assert any("Windows" in line for line in layout.destroys)
        assert layout.keeps == []

    def test_installing_into_free_space_destroys_nothing(self) -> None:
        layout = Layout(windows_and_free_space(), InstallMode.FREE_SPACE)
        assert layout.destroys == []
        assert any("Windows" in line for line in layout.keeps)

    def test_using_a_partition_destroys_only_that_partition(self) -> None:
        contents = a_spare_partition()
        spare = contents.partitions[2]
        layout = Layout(contents, InstallMode.EXISTING_PARTITION, root_partition=spare)
        assert layout.destroys == [spare.description]
        assert len(layout.keeps) == 3
        assert any("Other OS" in line for line in layout.keeps)


class TestTheEsp:
    def test_an_existing_esp_is_reused_not_reformatted(self) -> None:
        """It may hold another system's bootloader.

        Formatting it is how an install that promised to leave Windows alone
        stops Windows booting.
        """
        layout = Layout(windows_and_free_space(), InstallMode.FREE_SPACE)
        assert layout.reuses_esp
        assert "reuse" in " ".join(layout.describe())

    def test_erasing_the_disk_makes_a_new_one(self) -> None:
        layout = Layout(windows_and_free_space(), InstallMode.WHOLE_DISK)
        assert not layout.reuses_esp
        assert "new EFI system partition" in " ".join(layout.describe())

    def test_a_cramped_esp_is_not_treated_as_usable(self) -> None:
        """Filling a 32MB ESP breaks whatever else boots from it."""
        contents = DiskContents(
            disk=DISK,
            partitions=(Partition("/dev/sda1", 1, 32 * 1000**2, "vfat", esp=True),),
        )
        assert contents.existing_esp is None


class TestRefusals:
    def test_free_space_mode_refuses_when_there_is_none(self) -> None:
        layout = Layout(DiskContents(disk=DISK), InstallMode.FREE_SPACE)
        assert layout.problems

    def test_existing_partition_mode_refuses_without_a_choice(self) -> None:
        layout = Layout(a_spare_partition(), InstallMode.EXISTING_PARTITION)
        assert "no partition chosen to install into" in layout.problems

    def test_existing_partition_mode_refuses_without_an_esp(self) -> None:
        """This mode does not repartition, so it cannot create one."""
        contents = DiskContents(
            disk=DISK,
            partitions=(Partition("/dev/sda1", 1, 400 * GB, "ext4"),),
        )
        layout = Layout(
            contents,
            InstallMode.EXISTING_PARTITION,
            root_partition=contents.partitions[0],
        )
        assert any("EFI system partition" in p for p in layout.problems)

    def test_a_sound_layout_has_no_problems(self) -> None:
        contents = a_spare_partition()
        layout = Layout(
            contents,
            InstallMode.EXISTING_PARTITION,
            root_partition=contents.partitions[2],
        )
        assert layout.problems == []

    def test_erasing_a_disk_never_has_problems(self) -> None:
        assert Layout(DiskContents(disk=DISK)).problems == []


class TestKeepingHome:
    def test_a_home_partition_is_kept_and_not_formatted(self) -> None:
        contents = a_spare_partition()
        layout = Layout(
            contents,
            InstallMode.EXISTING_PARTITION,
            root_partition=contents.partitions[2],
            home_partition=contents.partitions[3],
        )
        described = " ".join(layout.describe())
        assert "not formatted" in described
        assert contents.partitions[3].description not in layout.destroys

    def test_a_mounted_home_is_refused(self) -> None:
        contents = a_spare_partition()
        busy = Partition("/dev/sda4", 4, 200 * GB, "ext4", mounted=True)
        layout = Layout(
            contents,
            InstallMode.EXISTING_PARTITION,
            root_partition=contents.partitions[2],
            home_partition=busy,
        )
        assert any("in use" in p for p in layout.problems)


class TestDescription:
    @pytest.mark.parametrize("mode", list(InstallMode))
    def test_every_mode_describes_itself(self, mode: InstallMode) -> None:
        contents = a_spare_partition()
        layout = Layout(contents, mode, root_partition=contents.partitions[2])
        assert layout.describe(), f"{mode} described itself as nothing"

    def test_btrfs_subvolumes_appear_in_every_mode(self) -> None:
        contents = a_spare_partition()
        layout = Layout(
            contents,
            InstallMode.EXISTING_PARTITION,
            filesystem=Filesystem.BTRFS,
            root_partition=contents.partitions[2],
        )
        assert "@home" in " ".join(layout.describe())
