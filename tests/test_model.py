"""The domain model. No ports, no fakes - it has no dependencies to invert."""

from __future__ import annotations

import pytest

from osiris.model.disk import (
    MINIMUM_BYTES,
    Disk,
    Filesystem,
    PartitionPlan,
    human,
)
from osiris.model.request import InstallRequest, InvalidRequest


def a_disk(**overrides: object) -> Disk:
    defaults = {"path": "/dev/vda", "size": 30 * 1000**3, "label": "Test"}
    return Disk(**{**defaults, **overrides})  # type: ignore[arg-type]


class TestPartitionNaming:
    def test_a_plain_device_takes_a_bare_number(self) -> None:
        assert a_disk(path="/dev/sda").esp == "/dev/sda1"
        assert a_disk(path="/dev/sda").root == "/dev/sda2"

    def test_a_device_ending_in_a_digit_takes_a_p_separator(self) -> None:
        """/dev/nvme0n12 would be ambiguous otherwise."""
        disk = a_disk(path="/dev/nvme0n1")
        assert disk.esp == "/dev/nvme0n1p1"
        assert disk.root == "/dev/nvme0n1p2"

    def test_mmc_devices_too(self) -> None:
        assert a_disk(path="/dev/mmcblk0").root == "/dev/mmcblk0p2"


class TestUsability:
    def test_a_disk_below_the_minimum_is_refused_with_a_reason(self) -> None:
        disk = a_disk(size=MINIMUM_BYTES - 1)
        assert not disk.usable
        assert "too small" in (disk.unusable_because or "")

    def test_a_mounted_disk_is_refused(self) -> None:
        """Almost always the medium being booted from."""
        disk = a_disk(mounted=True)
        assert not disk.usable
        assert "in use" in (disk.unusable_because or "")

    def test_a_large_idle_disk_is_usable(self) -> None:
        assert a_disk().usable
        assert a_disk().unusable_because is None


class TestHumanSizes:
    @pytest.mark.parametrize(
        ("size", "expected"),
        [
            (512, "512 B"),
            (30 * 1000**3, "30.0 GB"),
            (1000**4, "1.0 TB"),
        ],
    )
    def test_reported_in_the_units_on_the_box(self, size: int, expected: str) -> None:
        assert human(size) == expected


class TestPartitionPlan:
    def test_ext4_has_no_subvolumes_and_a_root_swapfile(self) -> None:
        plan = PartitionPlan(a_disk(), Filesystem.EXT4, swap_megabytes=2048)
        assert plan.subvolumes == ()
        assert plan.swap_file == "/swapfile"
        assert plan.root_flags == ""

    def test_btrfs_puts_the_system_on_a_subvolume(self) -> None:
        plan = PartitionPlan(a_disk(), Filesystem.BTRFS)
        assert [v.name for v in plan.subvolumes] == ["@", "@home"]
        assert plan.root_flags == "rootflags=subvol=@"

    def test_btrfs_swap_gets_its_own_subvolume(self) -> None:
        """A subvolume holding an active swap file cannot be snapshotted.

        Keeping it off @ keeps that limitation off the root.
        """
        plan = PartitionPlan(a_disk(), Filesystem.BTRFS, swap_megabytes=4096)
        assert [v.name for v in plan.subvolumes] == ["@", "@home", "@swap"]
        assert plan.swap_file == "/swap/swapfile"

    def test_the_swap_subvolume_is_never_compressed(self) -> None:
        """btrfs refuses to swap on a compressed or copy-on-write file."""
        plan = PartitionPlan(a_disk(), Filesystem.BTRFS, swap_megabytes=1024)
        swap = next(v for v in plan.subvolumes if v.name == "@swap")
        assert "compress" not in swap.options

    def test_no_swap_means_no_swap_file(self) -> None:
        assert PartitionPlan(a_disk(), Filesystem.EXT4).swap_file is None

    def test_the_plan_describes_itself(self) -> None:
        described = "\n".join(
            PartitionPlan(a_disk(), Filesystem.BTRFS, 2048).describe()
        )
        assert "btrfs" in described
        assert "@swap" in described
        assert "2048 MB" in described


class TestValidation:
    def a_request(self, **overrides: object) -> InstallRequest:
        defaults = {
            "disk": a_disk(),
            "username": "alex",
            "password": "osiris123",
        }
        return InstallRequest(**{**defaults, **overrides})  # type: ignore[arg-type]

    def test_a_sound_request_is_valid(self) -> None:
        assert self.a_request().valid

    @pytest.mark.parametrize(
        "username", ["", "1alex", "Alex", "al ex", "al;ex", "-alex"]
    )
    def test_usernames_useradd_would_refuse(self, username: str) -> None:
        assert not self.a_request(username=username).valid

    @pytest.mark.parametrize("username", ["alex", "_system", "a-b_c9"])
    def test_usernames_useradd_accepts(self, username: str) -> None:
        assert self.a_request(username=username).valid

    def test_a_short_password_is_refused(self) -> None:
        assert not self.a_request(password="short").valid

    def test_an_unusable_disk_is_refused(self) -> None:
        assert not self.a_request(disk=a_disk(mounted=True)).valid

    def test_every_problem_is_reported_at_once(self) -> None:
        """A form should show all of them, not one per attempt."""
        request = self.a_request(username="", password="x", hostname="bad name")
        assert len(request.problems) == 3

    def test_validate_raises_with_every_problem_named(self) -> None:
        with pytest.raises(InvalidRequest) as caught:
            self.a_request(username="", password="x").validate()
        assert "username" in str(caught.value)
        assert "password" in str(caught.value)


class TestExtraMounts:
    def test_nothing_extra_by_default(self) -> None:
        request = InstallRequest(a_disk(), "alex", "osiris123")
        assert request.extra_mounts == ()

    def test_a_swap_file_is_written_rather_than_detected(self) -> None:
        """genfstab cannot see a swap file that is not switched on."""
        request = InstallRequest(a_disk(), "alex", "osiris123", swap_megabytes=2048)
        assert request.extra_mounts == ("/swapfile none swap defaults 0 0",)

    def test_a_virtiofs_share_mounts_under_the_users_home(self) -> None:
        request = InstallRequest(a_disk(), "alex", "osiris123", virtiofs_tag="osiris")
        assert "/home/alex/osiris virtiofs" in request.extra_mounts[0]
