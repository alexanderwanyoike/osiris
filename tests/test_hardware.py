"""Hardware detection, against real PCI device IDs.

Every identifier below is a card or processor that exists. The point of the
table is that adding a machine to it is cheaper than installing onto one.
"""

from __future__ import annotations

import pytest

from osiris.model.hardware import (
    CpuVendor,
    Gpu,
    GpuVendor,
    Hardware,
    graphics,
    microcode,
    packages_for,
    unsupported,
)
from osiris.platform.hardware import FakeProbe, HardwareProbe, SystemProbe
from osiris.platform.process import FakeRunner, Result


def nvidia(device_id: int, description: str = "") -> Gpu:
    return Gpu(GpuVendor.NVIDIA, device_id, description)


class TestNvidiaGenerations:
    """Turing and newer take the open kernel modules; nothing older can.

    The open modules need the GPU System Processor, which arrived with Turing.
    Pascal and Maxwell were dropped from Arch's repositories with driver 590
    and their proprietary driver is AUR-only, which a distribution cannot
    depend on - so those cards get nouveau.
    """

    @pytest.mark.parametrize(
        ("device_id", "name"),
        [
            (0x1E89, "RTX 2060 (TU104)"),
            (0x1E07, "RTX 2080 Ti (TU102)"),
            (0x1F82, "GTX 1650 (TU117)"),
            (0x2204, "RTX 3090 (GA102)"),
            (0x2684, "RTX 4090 (AD102)"),
        ],
    )
    def test_turing_and_newer_get_the_open_driver(
        self, device_id: int, name: str
    ) -> None:
        assert nvidia(device_id, name).has_open_kernel_modules, name
        assert "nvidia-open" in graphics((nvidia(device_id),))

    @pytest.mark.parametrize(
        ("device_id", "name"),
        [
            (0x1B06, "GTX 1080 Ti (GP102)"),
            (0x1C03, "GTX 1060 (GP106)"),
            (0x1D01, "GT 1030 (GP108)"),
            (0x1DB1, "Tesla V100 (GV100)"),
            (0x13C0, "GTX 980 (GM204)"),
        ],
    )
    def test_pascal_and_older_fall_back_to_nouveau(
        self, device_id: int, name: str
    ) -> None:
        assert not nvidia(device_id, name).has_open_kernel_modules, name
        packages = graphics((nvidia(device_id),))
        assert "nvidia-open" not in packages
        assert "mesa" in packages, "nouveau lives in mesa"

    def test_an_unsupported_card_is_explained_rather_than_silently_downgraded(
        self,
    ) -> None:
        notes = unsupported(Hardware(gpus=(nvidia(0x1B06, "GTX 1080 Ti"),)))
        assert len(notes) == 1
        assert "nouveau" in notes[0]

    def test_a_supported_card_needs_no_explanation(self) -> None:
        assert unsupported(Hardware(gpus=(nvidia(0x1E89),))) == []


class TestOtherVendors:
    def test_amd_gets_the_radeon_vulkan_driver(self) -> None:
        packages = graphics((Gpu(GpuVendor.AMD, 0x164E),))
        assert "vulkan-radeon" in packages
        assert "nvidia-open" not in packages

    def test_intel_gets_the_intel_vulkan_driver(self) -> None:
        packages = graphics((Gpu(GpuVendor.INTEL, 0x9A49),))
        assert "vulkan-intel" in packages

    def test_a_guest_gets_software_rendering(self) -> None:
        """A VM has no GPU, and a desktop that assumes one shows a black screen."""
        assert "vulkan-swrast" in graphics((), virtual=True)

    def test_bare_metal_does_not_get_software_rendering(self) -> None:
        assert "vulkan-swrast" not in graphics((Gpu(GpuVendor.AMD, 0x164E),))


class TestLaptops:
    def test_both_gpus_in_a_hybrid_machine_get_drivers(self) -> None:
        """Intel drives the panel, NVIDIA drives anything demanding.

        Picking a single "best" GPU gets this common case wrong.
        """
        packages = graphics((Gpu(GpuVendor.INTEL, 0x9A49), nvidia(0x1F82, "GTX 1650")))
        assert "vulkan-intel" in packages
        assert "nvidia-open" in packages


class TestMicrocode:
    def test_amd_and_intel_get_their_own_and_only_their_own(self) -> None:
        assert microcode(CpuVendor.AMD) == ["amd-ucode"]
        assert microcode(CpuVendor.INTEL) == ["intel-ucode"]

    def test_an_unknown_processor_gets_neither(self) -> None:
        assert microcode(CpuVendor.UNKNOWN) == []

    def test_every_real_machine_ends_up_with_microcode(self) -> None:
        """Osiris shipped none at all, on any machine, until this existed."""
        for cpu in (CpuVendor.AMD, CpuVendor.INTEL):
            assert any(
                package.endswith("-ucode")
                for package in packages_for(Hardware(cpu=cpu))
            )


class TestPeripherals:
    def test_bluetooth_packages_only_when_there_is_a_controller(self) -> None:
        assert "bluez" in packages_for(Hardware(bluetooth=True))
        assert "bluez" not in packages_for(Hardware(bluetooth=False))


class TestProbe:
    def test_both_probes_satisfy_the_port(self) -> None:
        assert isinstance(FakeProbe(), HardwareProbe)
        assert isinstance(SystemProbe(FakeRunner()), HardwareProbe)

    def test_lspci_output_is_parsed_into_gpus(self, tmp_path) -> None:
        """Numeric ids, not marketing names, which change."""
        listing = (
            '00:02.0 "0300" "8086" "9a49" -r0c "8086" "0000"\n'
            '07:00.0 "0300" "10de" "1e89" -ra1 "1458" "403b"\n'
            '00:1f.3 "0403" "8086" "a0c8" -r20 "8086" "0000"\n'
        )
        runner = FakeRunner(results={"lspci": Result(("lspci",), 0, listing)})
        (tmp_path / "proc").mkdir()
        (tmp_path / "proc" / "cpuinfo").write_text("vendor_id\t: AuthenticAMD\n")

        hardware = SystemProbe(runner, root=tmp_path).detect()

        assert [gpu.vendor for gpu in hardware.gpus] == [
            GpuVendor.INTEL,
            GpuVendor.NVIDIA,
        ], "the audio controller is not a GPU"
        assert hardware.gpus[1].device_id == 0x1E89
        assert hardware.cpu is CpuVendor.AMD

    def test_a_medium_without_lspci_degrades_rather_than_fails(self, tmp_path) -> None:
        runner = FakeRunner(results={"lspci": FileNotFoundError("no lspci")})
        hardware = SystemProbe(runner, root=tmp_path).detect()
        assert hardware.gpus == ()
        assert "mesa" in packages_for(hardware), "still a working desktop"
