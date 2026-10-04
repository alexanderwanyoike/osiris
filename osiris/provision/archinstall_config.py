"""The installer's answers, as an archinstall configuration.

archinstall does the install: partitioning, formatting, pacstrap, users,
microcode, graphics drivers, the bootloader, Bluetooth, swap. See ADR 0012.
This module's only job is to describe what the user chose in archinstall's own
terms.

It does that with archinstall's own objects - ArchConfig, DiskLayoutConfiguration,
Password - and lets archinstall serialise them with the same methods its own
menu uses to save a configuration. Nothing here writes the JSON format by hand,
so a change to that format between archinstall releases is archinstall's
problem rather than a silently malformed file of ours.

The disk layout is built from archinstall's own primitives too. Its
`suggest_single_disk_layout` would be the natural call, but it asks questions on
the terminal for btrfs; this does what that function does with the answers
filled in, and nothing more.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from archinstall.lib.args import ArchConfig
from archinstall.lib.disk.default_layouts import (
    _boot_partition,
    get_default_btrfs_subvols,
)
from archinstall.lib.hardware import GfxDriver
from archinstall.lib.models.application import (
    ApplicationConfiguration,
    Audio,
    AudioConfiguration,
    BluetoothConfiguration,
    ZramConfiguration,
)
from archinstall.lib.models.authentication import AuthenticationConfiguration
from archinstall.lib.models.bootloader import (
    Bootloader,
    BootloaderConfiguration,
    PlymouthTheme,
)
from archinstall.lib.models.device import (
    BDevice,
    BtrfsMountOption,
    DeviceModification,
    DiskLayoutConfiguration,
    DiskLayoutType,
    FilesystemType,
    ModificationStatus,
    PartitionFlag,
    PartitionModification,
    PartitionType,
    Size,
    Unit,
)
from archinstall.lib.models.locale import LocaleConfiguration
from archinstall.lib.models.mirrors import (
    CustomRepository,
    MirrorConfiguration,
    SignCheck,
    SignOption,
)
from archinstall.lib.models.network import NetworkConfiguration, NicType
from archinstall.lib.models.profile import ProfileConfiguration
from archinstall.lib.models.users import Password, User
from archinstall.default_profiles.profile import GreeterType
from archinstall.lib.profile.profiles_handler import profile_handler

from osiris.model.disk import Filesystem
from osiris.model.hardware import Gpu, GpuVendor
from osiris.model.layout import InstallMode, Layout
from osiris.model.request import InstallRequest

#: The package that is Osiris: the desktop, the themes, the branding, and the
#: dependencies that pull in Cinnamon, Plank and the rest.
OSIRIS_PACKAGE = "osiris"

#: Run inside the new system once archinstall has installed it. Applies the
#: things a package cannot ship as files: the default theme, the GRUB theme,
#: the Plymouth theme. One program name - archinstall wraps it in a one-line
#: script, but there is no shell logic of ours in it.
SETUP_COMMAND = "osiris-setup"

#: Where a shared EFI system partition is mounted. Not /boot: the kernels and
#: initramfs images stay on Osiris's own root, so an ESP made by Windows at
#: 100MB is not filled up, and only GRUB's few files go onto it.
SHARED_ESP = Path("/efi")

ESP_SIZE_GIB = 1


@dataclass(frozen=True)
class Target:
    """What the installer knows about the machine it is installing onto."""

    device: BDevice
    using_gpt: bool
    #: Where on the disk Osiris goes. None erases the whole disk.
    layout: Layout | None = None
    gpus: Sequence[Gpu] = ()
    bluetooth: bool = False
    repository: str = "file:///usr/share/osiris/repo"


def whole_disk_layout(
    device: BDevice, filesystem: Filesystem, using_gpt: bool
) -> DiskLayoutConfiguration:
    """Erase the disk: a boot partition and one root filesystem.

    What archinstall's own default layout produces, with its two terminal
    questions answered: btrfs gets the default subvolumes with compression,
    and there is no separate /home partition.
    """
    sector_size = device.device_info.sector_size
    available = device.device_info.total_size
    if using_gpt:
        available = available.gpt_end()
    available = available.align()

    modification = DeviceModification(device, wipe=True)
    boot = _boot_partition(sector_size, using_gpt)
    modification.add_partition(boot)

    btrfs = filesystem is Filesystem.BTRFS
    root_start = boot.start + boot.length
    root = PartitionModification(
        status=ModificationStatus.CREATE,
        type=PartitionType.PRIMARY,
        start=root_start,
        length=available - root_start,
        mountpoint=None if btrfs else Path("/"),
        fs_type=FilesystemType.BTRFS if btrfs else FilesystemType.EXT4,
        mount_options=[BtrfsMountOption.compress.value] if btrfs else [],
    )
    if btrfs:
        root.btrfs_subvols = get_default_btrfs_subvols()
    modification.add_partition(root)

    return DiskLayoutConfiguration(
        config_type=DiskLayoutType.Default,
        device_modifications=[modification],
    )


def _as_root(partition: PartitionModification, filesystem: Filesystem) -> None:
    """Make `partition` the root filesystem, as the whole-disk layout does."""
    btrfs = filesystem is Filesystem.BTRFS
    partition.fs_type = FilesystemType.BTRFS if btrfs else FilesystemType.EXT4
    partition.mountpoint = None if btrfs else Path("/")
    partition.mount_options = [BtrfsMountOption.compress.value] if btrfs else []
    partition.btrfs_subvols = get_default_btrfs_subvols() if btrfs else []
    partition.flags = []


def alongside_layout(device: BDevice, layout: Layout) -> DiskLayoutConfiguration:
    """Install beside what is already on the disk, touching only Osiris's part.

    Every existing partition is listed as it is, so archinstall knows the disk
    and leaves it alone. Only three things change: the root partition is
    created in free space or formatted in place, and an existing EFI system
    partition is mounted - never formatted - so GRUB can add itself to it.
    """
    sector_size = device.device_info.sector_size
    existing = {
        str(part.path): PartitionModification.from_existing_partition(part)
        for part in device.partition_infos
    }
    for partition in existing.values():
        partition.mountpoint = None
        partition.btrfs_subvols = []

    esp = layout.contents.existing_esp
    if esp is not None:
        existing[esp.path].mountpoint = SHARED_ESP

    created: list[PartitionModification] = []
    if layout.mode is InstallMode.FREE_SPACE:
        region = layout.contents.largest_free
        if region is None:
            raise ValueError("no free space to install into")
        start = Size(region.start, Unit.B, sector_size)
        end = Size(region.start + region.size, Unit.B, sector_size)
        if esp is None:
            boot = PartitionModification(
                status=ModificationStatus.CREATE,
                type=PartitionType.PRIMARY,
                start=start,
                length=Size(ESP_SIZE_GIB, Unit.GiB, sector_size),
                mountpoint=Path("/boot"),
                fs_type=FilesystemType.FAT32,
                flags=[PartitionFlag.BOOT, PartitionFlag.ESP],
            )
            created.append(boot)
            start = boot.start + boot.length
        root = PartitionModification(
            status=ModificationStatus.CREATE,
            type=PartitionType.PRIMARY,
            start=start,
            length=end - start,
        )
        _as_root(root, layout.filesystem)
        created.append(root)
    elif layout.mode is InstallMode.EXISTING_PARTITION:
        if layout.root_partition is None:
            raise ValueError("no partition chosen to install into")
        root = existing[layout.root_partition.path]
        root.status = ModificationStatus.MODIFY
        _as_root(root, layout.filesystem)
    else:
        raise ValueError(f"not an alongside layout: {layout.mode}")

    modification = DeviceModification(device, wipe=False)
    for partition in [*existing.values(), *created]:
        modification.add_partition(partition)
    return DiskLayoutConfiguration(
        config_type=DiskLayoutType.Manual,
        device_modifications=[modification],
    )


def disk_layout(target: Target, filesystem: Filesystem) -> DiskLayoutConfiguration:
    layout = target.layout
    if layout is None or layout.mode is InstallMode.WHOLE_DISK:
        return whole_disk_layout(target.device, filesystem, target.using_gpt)
    return alongside_layout(target.device, layout)


def graphics_driver(gpus: Sequence[Gpu]) -> GfxDriver:
    """Which of archinstall's driver sets this machine wants.

    Turing and newer NVIDIA cards take the open kernel modules; older ones get
    nouveau, because their proprietary driver is AUR-only now. Everything else
    is covered by the open-source set, which also covers hybrid laptops.
    """
    nvidia = [gpu for gpu in gpus if gpu.vendor is GpuVendor.NVIDIA]
    if nvidia:
        if all(gpu.has_open_kernel_modules for gpu in nvidia):
            return GfxDriver.NvidiaOpenKernel
        return GfxDriver.NvidiaOpenSource
    vendors = {gpu.vendor for gpu in gpus}
    if vendors == {GpuVendor.AMD}:
        return GfxDriver.AmdOpenSource
    if vendors == {GpuVendor.INTEL}:
        return GfxDriver.IntelOpenSource
    return GfxDriver.AllOpenSource


def build(request: InstallRequest, target: Target) -> ArchConfig:
    """The archinstall configuration for one install."""
    language, _, encoding = request.locale.partition(".")
    xorg = profile_handler.get_profile_by_name("Xorg")

    return ArchConfig(
        script="guided",
        hostname=request.hostname,
        timezone=request.timezone,
        locale_config=LocaleConfiguration(
            kb_layout=request.keymap,
            sys_lang=language,
            sys_enc=encoding or "UTF-8",
        ),
        disk_config=disk_layout(target, request.filesystem),
        bootloader_config=BootloaderConfiguration(
            bootloader=Bootloader.Grub,
            # Also install to /EFI/BOOT/BOOTX64.EFI, so the disk boots on a
            # machine other than the one it was installed from. Only when
            # the disk is Osiris's alone: on a shared ESP that file belongs
            # to whichever system put it there, often Windows.
            removable=target.layout is None
            or target.layout.mode is InstallMode.WHOLE_DISK,
            # The script module is what the Osiris theme is written for;
            # osiris-setup selects the theme itself.
            plymouth=PlymouthTheme.SCRIPT,
        ),
        # Xorg rather than archinstall's Cinnamon profile: it installs the
        # graphics driver and the greeter and nothing else, and the osiris
        # package decides the rest of the desktop.
        profile_config=ProfileConfiguration(
            profile=xorg,
            gfx_driver=graphics_driver(target.gpus),
            greeter=GreeterType.LightdmSlick,
        ),
        network_config=NetworkConfiguration(type=NicType.NM),
        app_config=ApplicationConfiguration(
            audio_config=AudioConfiguration(audio=Audio.PIPEWIRE),
            bluetooth_config=BluetoothConfiguration(enabled=target.bluetooth),
        ),
        swap=ZramConfiguration(enabled=True),
        mirror_config=MirrorConfiguration(
            custom_repositories=[
                CustomRepository(
                    name="osiris",
                    url=target.repository,
                    sign_check=SignCheck.Optional,
                    sign_option=SignOption.TrustAll,
                )
            ]
        ),
        auth_config=AuthenticationConfiguration(
            # No root password: root is locked and the user administers the
            # machine with sudo, as Mint and Ubuntu do.
            users=[
                User(
                    username=request.username,
                    password=Password(plaintext=request.password),
                    sudo=True,
                )
            ],
        ),
        packages=[OSIRIS_PACKAGE],
        custom_commands=[SETUP_COMMAND],
    )


def write(config: ArchConfig, directory: Path) -> tuple[Path, Path]:
    """Write the configuration and the credentials, as archinstall would.

    Credentials go in their own file, readable only by root: they carry the
    password hash.
    """
    directory.mkdir(parents=True, exist_ok=True)
    settings = directory / "config.json"
    credentials = directory / "creds.json"
    settings.write_text(config.user_config_to_json())
    credentials.touch(mode=0o600)
    credentials.chmod(0o600)
    credentials.write_text(config.user_credentials_to_json())
    return settings, credentials
