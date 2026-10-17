"""An encrypted root: what archinstall is asked to encrypt, and what it is not.

Every configuration is written with archinstall's serialiser and read back
with its parser, as `archinstall --config --creds` reads it. The passphrase
travels in the credentials file only, and nothing but the root is encrypted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from archinstall.lib.args import ArchConfig, Arguments
from archinstall.lib.disk.device_handler import device_handler
from archinstall.lib.models.device import (
    BDevice,
    DiskEncryption,
    EncryptionType,
    FilesystemType,
    ModificationStatus,
    PartitionModification,
)

from osiris.model.disk import Disk, Filesystem
from osiris.model.hardware import Hardware
from osiris.model.layout import InstallMode, Layout
from osiris.model.request import InstallRequest, InvalidRequest
from osiris.platform import FakeRunner
from osiris.platform.hardware import FakeProbe
from osiris.provision import archinstall_config as config
from osiris.provision import disk_contents
from osiris.provision.installer import Installer
from tests.conftest import GIB, a_disk_with

PASSPHRASE = "correct horse battery"


def a_request(device: BDevice, **overrides: Any) -> InstallRequest:
    defaults: dict[str, Any] = {
        "disk": Disk(str(device.device_info.path), 40 * GIB),
        "username": "alex",
        "password": "osiris123",
        "encrypt": True,
        "passphrase": PASSPHRASE,
    }
    return InstallRequest(**{**defaults, **overrides})


def an_installer(device: BDevice, tmp_path: Path) -> Installer:
    return Installer(
        FakeRunner(),
        FakeProbe(Hardware()),
        devices=lambda _path: device,
        using_gpt=True,
        config_dir=tmp_path / "out",
    )


def parsed(device: BDevice, tmp_path: Path, **overrides: Any) -> ArchConfig:
    """Build as the installer would, write, and read back with credentials.

    The installer itself deletes the credentials once archinstall exits, so
    this stops one step short of running it.
    """
    request = a_request(device, **overrides)
    target = an_installer(device, tmp_path).target(request)
    settings, credentials = config.write(
        config.build(request, target), tmp_path / "out"
    )
    merged = {
        **json.loads(settings.read_text()),
        **json.loads(credentials.read_text()),
    }
    return ArchConfig.from_config(merged, Arguments())


def encryption_of(parsed: ArchConfig) -> DiskEncryption:
    assert parsed.disk_config is not None
    encryption = parsed.disk_config.disk_encryption
    assert encryption is not None, "archinstall dropped the encryption"
    return encryption


def partitions(parsed: ArchConfig) -> list[PartitionModification]:
    assert parsed.disk_config is not None
    (modification,) = parsed.disk_config.device_modifications
    return list(modification.partitions)


class TestWholeDisk:
    @pytest.mark.parametrize("filesystem", list(Filesystem))
    def test_the_root_and_only_the_root_is_luks(
        self, device: BDevice, tmp_path: Path, filesystem: Filesystem
    ) -> None:
        result = parsed(device, tmp_path, filesystem=filesystem)
        encryption = encryption_of(result)
        assert encryption.encryption_type is EncryptionType.LUKS
        (encrypted,) = encryption.partitions
        assert encrypted.is_root()
        boot, root = partitions(result)
        assert encrypted.obj_id == root.obj_id
        assert boot.obj_id != encrypted.obj_id

    @pytest.mark.parametrize("filesystem", list(Filesystem))
    def test_the_esp_holds_the_kernels_and_is_not_encrypted(
        self, device: BDevice, tmp_path: Path, filesystem: Filesystem
    ) -> None:
        result = parsed(device, tmp_path, filesystem=filesystem)
        encrypted = {p.obj_id for p in encryption_of(result).partitions}
        for partition in partitions(result):
            if partition.is_efi() or partition.mountpoint == Path("/boot"):
                assert partition.obj_id not in encrypted
                assert partition.fs_type is FilesystemType.FAT32

    def test_btrfs_keeps_its_subvolumes_inside_the_encryption(
        self, device: BDevice, tmp_path: Path
    ) -> None:
        (root,) = encryption_of(
            parsed(device, tmp_path, filesystem=Filesystem.BTRFS)
        ).partitions
        assert root.fs_type is FilesystemType.BTRFS
        assert [str(v.name) for v in root.btrfs_subvols][:2] == ["@", "@home"]

    def test_the_passphrase_reaches_archinstall(
        self, device: BDevice, tmp_path: Path
    ) -> None:
        password = encryption_of(parsed(device, tmp_path)).encryption_password
        assert password is not None
        assert password.plaintext == PASSPHRASE

    def test_an_unencrypted_install_asks_for_no_encryption(
        self, device: BDevice, tmp_path: Path
    ) -> None:
        result = parsed(device, tmp_path, encrypt=False, passphrase="")
        assert result.disk_config is not None
        assert result.disk_config.disk_encryption is None


class TestThePassphraseStaysSecret:
    def test_it_is_not_in_the_main_configuration(
        self, device: BDevice, tmp_path: Path
    ) -> None:
        settings, credentials = config.write(
            config.build(a_request(device), config.Target(device, True)),
            tmp_path / "out",
        )
        assert PASSPHRASE not in settings.read_text()
        written = json.loads(credentials.read_text())
        assert written["encryption_password"] == PASSPHRASE
        assert credentials.stat().st_mode & 0o077 == 0, "readable by root only"

    def test_the_credentials_are_deleted_after_the_install(
        self, device: BDevice, tmp_path: Path
    ) -> None:
        an_installer(device, tmp_path).install(a_request(device))
        out = tmp_path / "out"
        assert not (out / "creds.json").exists()
        assert PASSPHRASE not in (out / "config.json").read_text()

    def test_it_is_not_in_the_requests_repr(self, device: BDevice) -> None:
        request = a_request(device)
        assert PASSPHRASE not in repr(request)
        assert "osiris123" not in repr(request)


class TestAlongside:
    def test_free_space_with_a_new_boot_partition_is_encrypted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No ESP on the disk yet: Osiris makes its own, and the kernels go
        on it, exactly as on a disk of its own."""
        device = a_disk_with(tmp_path, [(1, 10240, FilesystemType.EXT4, False)])
        monkeypatch.setattr(device_handler, "get_device", lambda _path: device)
        result = parsed(device, tmp_path, mode=InstallMode.FREE_SPACE)
        (root,) = encryption_of(result).partitions
        assert root.status is ModificationStatus.CREATE
        assert root.is_root()
        existing, boot, _root = partitions(result)
        assert existing.status is ModificationStatus.EXIST
        assert boot.mountpoint == Path("/boot")
        assert boot.obj_id != root.obj_id

    def test_a_shared_esp_is_refused(
        self, shared_device: BDevice, tmp_path: Path
    ) -> None:
        """Kernels on an encrypted root, behind a GRUB that cannot unlock it."""
        runner = FakeRunner()
        installer = Installer(
            runner, FakeProbe(Hardware()), devices=lambda _path: shared_device,
            using_gpt=True, config_dir=tmp_path,
        )  # fmt: skip
        with pytest.raises(InvalidRequest, match="boot partition"):
            installer.install(a_request(shared_device, mode=InstallMode.FREE_SPACE))
        assert runner.calls == []

    def test_an_existing_partition_is_refused(self, shared_device: BDevice) -> None:
        other = str(shared_device.partition_infos[1].path)
        request = a_request(
            shared_device,
            mode=InstallMode.EXISTING_PARTITION,
            root_partition=other,
        )
        assert not request.valid
        assert any("existing partition" in p for p in request.problems)

    def test_the_config_builder_refuses_too(
        self, shared_device: BDevice, tmp_path: Path
    ) -> None:
        """Behind the model's check, in case a layout reaches it anyway."""
        layout = Layout(disk_contents.read(shared_device), InstallMode.FREE_SPACE)
        with pytest.raises(ValueError, match="boot partition"):
            config.build(
                a_request(shared_device, mode=InstallMode.FREE_SPACE),
                config.Target(shared_device, True, layout=layout),
            )
