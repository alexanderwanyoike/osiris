"""Turning a request into an installed system, by handing it to archinstall.

Osiris does not install itself. archinstall partitions, formats, installs the
base system and the drivers, creates the user and installs the bootloader;
then it installs the `osiris` package and runs `osiris-setup` inside the new
system. See ADR 0012. What happens here is the hand-over: find out what the
machine has, describe the install in archinstall's terms, run it, and clean up.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from archinstall.lib.disk.device_handler import device_handler
from archinstall.lib.hardware import SysInfo
from archinstall.lib.models.device import BDevice

from osiris.model.layout import DiskContents, InstallMode, Layout
from osiris.model.request import InstallRequest, InvalidRequest
from osiris.platform.hardware import HardwareProbe, SystemProbe
from osiris.platform.process import CommandRunner
from osiris.provision import archinstall_config, disk_contents

#: fraction completed, what is starting now
Progress = Callable[[float, str], None]

#: Where the configuration is written for archinstall to read. Under /root,
#: because the credentials file carries the password hash.
CONFIG_DIR = Path("/root/osiris-install")

#: Resolves the disk the user chose to archinstall's view of it.
Devices = Callable[[str], BDevice | None]


class InstallFailed(RuntimeError):
    """archinstall did not install the system; the message says why."""


class Installer:
    """Runs one install. Everything it touches is handed to it."""

    def __init__(
        self,
        runner: CommandRunner,
        probe: HardwareProbe,
        devices: Devices,
        using_gpt: bool,
        uefi: bool = True,
        config_dir: Path = CONFIG_DIR,
    ) -> None:
        self._runner = runner
        self._probe = probe
        self._devices = devices
        self._using_gpt = using_gpt
        self._uefi = uefi
        self._config_dir = config_dir

    @classmethod
    def for_this_machine(cls, runner: CommandRunner) -> Installer:
        """The real one: this machine's disks, firmware and hardware.

        The partition table follows the firmware, as archinstall's own does:
        GPT for UEFI, MBR for a BIOS machine.
        """
        return cls(
            runner,
            SystemProbe(runner),
            devices=lambda path: device_handler.get_device(Path(path)),
            using_gpt=device_handler.partition_table.is_gpt(),
            uefi=SysInfo.has_uefi(),
        )

    def target(self, request: InstallRequest) -> archinstall_config.Target:
        """What archinstall needs to know about this machine."""
        device = self._devices(request.disk.path)
        if device is None:
            raise FileNotFoundError(f"no such disk: {request.disk.path}")
        hardware = self._probe.detect()
        return archinstall_config.Target(
            device=device,
            using_gpt=self._using_gpt,
            layout=self.layout(request, device),
            # No GPUs means archinstall's all-open-source set, whose mesa
            # renders in software where no driver works.
            gpus=() if request.software_rendering else hardware.gpus,
            bluetooth=hardware.bluetooth,
        )

    @property
    def uefi(self) -> bool:
        return self._uefi

    def contents(self, path: str) -> DiskContents | None:
        """What is on the disk at `path`, for the wizard to offer modes from."""
        device = self._devices(path)
        return disk_contents.read(device) if device is not None else None

    def layout(self, request: InstallRequest, device: BDevice) -> Layout | None:
        """Where Osiris goes, checked against what is really on the disk.

        Read again here rather than trusted from the wizard: the disk may have
        changed since it was shown - GParted is one click away - and this is
        the last moment before anything is written.
        """
        if request.mode is InstallMode.WHOLE_DISK:
            return None
        contents = disk_contents.read(device)
        if request.mode not in contents.modes(self._uefi):
            raise InvalidRequest(f"{request.mode} is not possible on {request.disk.path}")
        root = next(
            (p for p in contents.partitions if p.path == request.root_partition),
            None,
        )
        layout = Layout(
            contents,
            request.mode,
            request.filesystem,
            root_partition=root,
            encrypted=request.encrypt,
        )
        if layout.problems:
            raise InvalidRequest("; ".join(layout.problems))
        return layout

    def install(
        self, request: InstallRequest, progress: Progress | None = None
    ) -> None:
        """Run the install. Raises on failure; never calls sys.exit."""
        request.validate()
        if progress is not None:
            progress(0.0, "Installing Osiris")
        config = archinstall_config.build(request, self.target(request))
        settings, credentials = archinstall_config.write(config, self._config_dir)
        try:
            self._runner.stream(
                "archinstall",
                "--config", str(settings),
                "--creds", str(credentials),
                "--silent",
            )  # fmt: skip
        finally:
            # The hash is no use to anyone once the user exists, and the live
            # medium may be handed to someone else afterwards.
            credentials.unlink(missing_ok=True)
        if progress is not None:
            progress(1.0, "Done")
