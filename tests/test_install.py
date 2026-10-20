"""The hand-over to archinstall, without a disk to ruin."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from archinstall.lib.args import ArchConfig, Arguments
from archinstall.lib.models.device import BDevice

from osiris.model.disk import Disk
from osiris.model.hardware import Gpu, GpuVendor, Hardware
from osiris.model.request import InstallRequest, InvalidRequest
from osiris.platform import FakeRunner
from osiris.platform.hardware import FakeProbe
from osiris.platform.process import CommandError, Result
from osiris.provision.archinstall_outcome import NETWORK
from osiris.provision.installer import Installer, InstallFailed
from tests.conftest import an_archinstall_that_completes

GIB = 1024**3
RTX_2060 = Gpu(GpuVendor.NVIDIA, 0x1E89)


def a_request(device: BDevice, **overrides: object) -> InstallRequest:
    defaults = {
        "disk": Disk(str(device.device_info.path), 40 * GIB),
        "username": "alex",
        "password": "osiris123",
    }
    return InstallRequest(**{**defaults, **overrides})  # type: ignore[arg-type]


def an_installer(
    runner: FakeRunner,
    device: BDevice,
    config_dir: Path,
    hardware: Hardware | None = None,
) -> Installer:
    return Installer(
        runner,
        FakeProbe(hardware or Hardware()),
        devices=lambda path: device if path == str(device.device_info.path) else None,
        using_gpt=True,
        config_dir=config_dir,
    )


def test_archinstall_is_run_once_silently_with_the_written_files(
    device: BDevice, tmp_path: Path
) -> None:
    runner = an_archinstall_that_completes()
    an_installer(runner, device, tmp_path).install(a_request(device))
    (argv,) = runner.arguments_to("archinstall")
    assert argv == (
        "archinstall",
        "--config", str(tmp_path / "config.json"),
        "--creds", str(tmp_path / "creds.json"),
        "--silent",
    )  # fmt: skip


def test_the_written_configuration_is_one_archinstall_accepts(
    device: BDevice, tmp_path: Path
) -> None:
    an_installer(an_archinstall_that_completes(), device, tmp_path).install(
        a_request(device)
    )
    written = json.loads((tmp_path / "config.json").read_text())
    parsed = ArchConfig.from_config(written, Arguments())
    assert parsed.disk_config is not None


@pytest.mark.parametrize("succeeds", [True, False], ids=["success", "failure"])
def test_the_credentials_do_not_outlive_the_install(
    device: BDevice, tmp_path: Path, succeeds: bool
) -> None:
    runner = an_archinstall_that_completes()
    if not succeeds:
        runner.results["archinstall"] = CommandError(["archinstall"], 1)
    installer = an_installer(runner, device, tmp_path)
    if succeeds:
        installer.install(a_request(device))
    else:
        with pytest.raises(CommandError):
            installer.install(a_request(device))
    assert not (tmp_path / "creds.json").exists()


@pytest.mark.parametrize(
    ("returncode", "output", "reason"),
    [
        (0, "", "archinstall stopped without installing anything."),
        (1, "error: failed to retrieve some files\n", NETWORK),
    ],
    ids=["exit 0 without finishing", "a dropped connection"],
)
def test_an_install_archinstall_did_not_finish_fails_with_the_reason(
    device: BDevice, tmp_path: Path, returncode: int, output: str, reason: str
) -> None:
    runner = FakeRunner(
        results={"archinstall": Result(("archinstall",), returncode, output)}
    )
    with pytest.raises(InstallFailed) as caught:
        an_installer(runner, device, tmp_path).install(a_request(device))
    assert str(caught.value) == reason


def test_an_invalid_request_is_refused_before_anything_runs(
    device: BDevice, tmp_path: Path
) -> None:
    runner = FakeRunner()
    with pytest.raises(InvalidRequest):
        an_installer(runner, device, tmp_path).install(a_request(device, password="x"))
    assert runner.calls == []


def test_an_unknown_disk_is_refused(device: BDevice, tmp_path: Path) -> None:
    request = InstallRequest(
        disk=Disk("/dev/nope", 40 * GIB), username="alex", password="osiris123"
    )
    with pytest.raises(FileNotFoundError):
        an_installer(FakeRunner(), device, tmp_path).install(request)


class TestWhatTheMachineHas:
    def test_detected_gpus_and_bluetooth_are_passed_on(
        self, device: BDevice, tmp_path: Path
    ) -> None:
        hardware = Hardware(gpus=(RTX_2060,), bluetooth=True)
        target = an_installer(FakeRunner(), device, tmp_path, hardware).target(
            a_request(device)
        )
        assert target.gpus == (RTX_2060,)
        assert target.bluetooth

    def test_software_rendering_ignores_the_gpus(
        self, device: BDevice, tmp_path: Path
    ) -> None:
        hardware = Hardware(gpus=(RTX_2060,))
        target = an_installer(FakeRunner(), device, tmp_path, hardware).target(
            a_request(device, software_rendering=True)
        )
        assert target.gpus == ()
