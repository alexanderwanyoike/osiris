"""The configuration handed to archinstall.

The strongest available check is used throughout: archinstall's own parser.
Every configuration built here is written with archinstall's serialiser and
read back with `ArchConfig.from_config`, the code path `archinstall --config`
takes. If archinstall accepts it, the format is right by definition.

The disk is a sparse image file, never a real device: see the `device`
fixture in conftest.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from archinstall.lib.args import ArchConfig, Arguments
from archinstall.lib.hardware import GfxDriver
from archinstall.lib.models.device import BDevice, FilesystemType

from osiris.model.disk import Disk, Filesystem
from osiris.model.hardware import Gpu, GpuVendor
from osiris.model.request import InstallRequest
from osiris.provision import archinstall_config as config

GIB = 1024**3


def a_request(device: BDevice, **overrides: Any) -> InstallRequest:
    defaults: dict[str, Any] = {
        "disk": Disk(str(device.device_info.path), 40 * GIB),
        "username": "alex",
        "password": "osiris123",
    }
    return InstallRequest(**{**defaults, **overrides})


def round_trip(built: ArchConfig, tmp_path: Path) -> tuple[ArchConfig, dict[str, Any]]:
    settings, credentials = config.write(built, tmp_path / "out")
    written = json.loads(settings.read_text())
    secrets = json.loads(credentials.read_text())
    return ArchConfig.from_config({**written, **secrets}, Arguments()), written


class TestTheWholeConfigIsAcceptedByArchinstall:
    @pytest.mark.parametrize("filesystem", list(Filesystem))
    def test_round_trips(
        self, device: BDevice, tmp_path: Path, filesystem: Filesystem
    ) -> None:
        built = config.build(
            a_request(device, filesystem=filesystem), config.Target(device, True)
        )
        parsed, _ = round_trip(built, tmp_path)
        assert parsed.disk_config is not None
        assert parsed.hostname == "osiris"
        assert parsed.packages == [config.OSIRIS_PACKAGE]
        assert parsed.custom_commands == [config.SETUP_COMMAND]


class TestDiskLayout:
    def test_ext4_is_a_boot_partition_and_a_root(
        self, device: BDevice, tmp_path: Path
    ) -> None:
        parsed, _ = round_trip(
            config.build(a_request(device), config.Target(device, True)), tmp_path
        )
        assert parsed.disk_config is not None
        modification = parsed.disk_config.device_modifications[0]
        boot, root = modification.partitions
        assert modification.wipe
        assert boot.fs_type is FilesystemType.FAT32
        assert str(boot.mountpoint) == "/boot"
        assert root.fs_type is FilesystemType.EXT4
        assert str(root.mountpoint) == "/"

    def test_the_root_fills_the_disk_short_of_the_gpt_backup(
        self, device: BDevice
    ) -> None:
        """GPT keeps a backup header at the end; nothing may overlap it."""
        layout = config.whole_disk_layout(device, Filesystem.EXT4, using_gpt=True)
        root = layout.device_modifications[0].partitions[1]
        end = (root.start + root.length).convert(root.length.unit.__class__.B)
        assert 0 < 40 * GIB - end.value <= 2 * 1024**2

    def test_btrfs_uses_archinstalls_default_subvolumes(
        self, device: BDevice, tmp_path: Path
    ) -> None:
        parsed, _ = round_trip(
            config.build(
                a_request(device, filesystem=Filesystem.BTRFS),
                config.Target(device, True),
            ),
            tmp_path,
        )
        assert parsed.disk_config is not None
        root = parsed.disk_config.device_modifications[0].partitions[1]
        names = [str(volume.name) for volume in root.btrfs_subvols]
        assert names[:2] == ["@", "@home"]
        assert "compress" in " ".join(root.mount_options)


class TestGraphics:
    @pytest.mark.parametrize(
        ("gpus", "expected"),
        [
            ((Gpu(GpuVendor.NVIDIA, 0x1E89),), GfxDriver.NvidiaOpenKernel),
            ((Gpu(GpuVendor.NVIDIA, 0x1B06),), GfxDriver.NvidiaOpenSource),
            ((Gpu(GpuVendor.AMD, 0x164E),), GfxDriver.AmdOpenSource),
            ((Gpu(GpuVendor.INTEL, 0x9A49),), GfxDriver.IntelOpenSource),
            (
                (Gpu(GpuVendor.INTEL, 0x9A49), Gpu(GpuVendor.AMD, 0x164E)),
                GfxDriver.AllOpenSource,
            ),
            ((), GfxDriver.AllOpenSource),
        ],
        ids=["rtx-2060", "gtx-1080ti", "amd", "intel", "hybrid", "unknown"],
    )
    def test_the_right_driver_set(
        self, gpus: tuple[Gpu, ...], expected: GfxDriver
    ) -> None:
        assert config.graphics_driver(gpus) is expected


class TestAccounts:
    def test_the_user_is_a_sudoer_and_root_is_locked(
        self, device: BDevice, tmp_path: Path
    ) -> None:
        parsed, _ = round_trip(
            config.build(a_request(device), config.Target(device, True)), tmp_path
        )
        assert parsed.auth_config is not None
        (user,) = parsed.auth_config.users
        assert user.username == "alex"
        assert user.sudo
        assert parsed.auth_config.root_enc_password is None

    def test_the_password_is_hashed_and_kept_out_of_the_main_file(
        self, device: BDevice, tmp_path: Path
    ) -> None:
        settings, credentials = config.write(
            config.build(a_request(device), config.Target(device, True)),
            tmp_path / "out",
        )
        assert "osiris123" not in settings.read_text()
        assert "osiris123" not in credentials.read_text()
        assert credentials.stat().st_mode & 0o077 == 0, "readable by root only"


class TestBoot:
    def test_grub_also_installs_the_removable_fallback(
        self, device: BDevice, tmp_path: Path
    ) -> None:
        """Without it the disk only boots on the machine it was installed from."""
        parsed, _ = round_trip(
            config.build(a_request(device), config.Target(device, True)), tmp_path
        )
        assert parsed.bootloader_config is not None
        assert parsed.bootloader_config.removable
