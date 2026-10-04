"""The generated PKGBUILD.

Where makepkg is installed it is asked to read the file back, which is the
check that matters: makepkg is the only authority on what a PKGBUILD means.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from osiris.iso import package


def test_dependencies_are_unique_and_sorted() -> None:
    names = package.depends()
    assert names == sorted(set(names))


def test_nothing_archinstall_chooses_per_machine_is_a_dependency() -> None:
    """Kernel, microcode and drivers are archinstall's to pick, per machine."""
    chosen_per_machine = {
        "linux", "linux-firmware", "amd-ucode", "intel-ucode",
        "nvidia-open", "mesa", "vulkan-swrast", "efibootmgr",
    }  # fmt: skip
    assert chosen_per_machine.isdisjoint(package.depends())


@pytest.mark.parametrize("version", ["", "0.1.0-1"])
def test_an_invalid_version_is_refused(version: str) -> None:
    with pytest.raises(ValueError):
        package.pkgbuild(version)


@pytest.mark.skipif(shutil.which("makepkg") is None, reason="needs makepkg")
def test_makepkg_reads_it_back(tmp_path: Path) -> None:
    (tmp_path / "PKGBUILD").write_text(package.pkgbuild("0.1.0"))
    srcinfo = subprocess.run(
        ["makepkg", "--printsrcinfo"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    fields = [
        line.strip().split(" = ", 1) for line in srcinfo.splitlines() if " = " in line
    ]
    assert ["pkgname", package.NAME] in fields
    assert ["pkgver", "0.1.0"] in fields
    assert [value for key, value in fields if key == "depends"] == package.depends()
