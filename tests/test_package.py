"""The generated PKGBUILD.

Where makepkg is installed it is asked to read the file back, which is the
check that matters: makepkg is the only authority on what a PKGBUILD means.
"""

from __future__ import annotations

import configparser
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


REPOSITORY = Path(__file__).resolve().parent.parent


def test_the_dock_is_plank_reloaded() -> None:
    names = package.depends()
    assert "plank-reloaded" in names
    assert "plank" not in names


def test_the_harness_engine_comes_from_arch() -> None:
    """The Harness rents opencode (ADR 0015), which Arch packages in extra."""
    assert "opencode" in package.depends()
    assert "opencode" not in package.BUNDLED


def test_the_harness_can_render_answers() -> None:
    """Markdown is parsed by markdown-it-py and code drawn by GtkSourceView 5,
    both in Arch's extra repository."""
    names = package.depends()
    assert "python-markdown-it-py" in names
    assert "gtksourceview5" in names


def test_the_osiris_tool_server_speaks_mcp_with_the_sdk_arch_ships() -> None:
    """The tool server is built on the official MCP SDK, in Arch's extra."""
    assert "python-mcp" in package.depends()


@pytest.mark.parametrize(
    "toolchain",
    ["gcc", "meson", "cmake", "rust", "go", "nodejs-lts-krypton", "npm", "gjs"],
)
def test_the_first_class_languages_toolchains_ship(toolchain: str) -> None:
    """Python, C and C++, Rust, Go and JavaScript on Node.js's Active LTS
    (CONTEXT.md); Python is already there for Osiris itself."""
    assert toolchain in package.depends()


def test_every_bundled_package_is_built_and_depended_on() -> None:
    assert package.BUNDLED
    for name in package.BUNDLED:
        assert (REPOSITORY / "iso" / "bundled" / name / "PKGBUILD").is_file()
        assert name in package.depends()


def hook() -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str  # type: ignore[assignment,method-assign]
    parser.read_string(package.HOOK)
    return parser


def test_upgrading_osiris_reruns_setup_once_the_upgrade_is_in_place() -> None:
    parsed = hook()
    assert dict(parsed["Trigger"]) == {
        "Operation": "Upgrade",
        "Type": "Package",
        "Target": package.NAME,
    }
    assert parsed["Action"]["When"] == "PostTransaction"
    assert parsed["Action"]["Exec"] == package.SETUP


def test_the_hook_is_where_pacman_reads_hooks_shipped_by_packages() -> None:
    assert package.HOOK_PATH.startswith("/usr/share/libalpm/hooks/")
    assert package.HOOK_PATH.endswith(".hook")


def test_setup_runs_after_the_systems_own_hooks_and_before_the_last_snapshot() -> None:
    name = package.HOOK_PATH.rsplit("/", 1)[1]
    ours_first = sorted([name, "90-mkinitcpio-install.hook", "zz-snap-pac-post.hook"])
    assert ours_first.index(name) == 1
    for before in ("gtk-update-icon-cache.hook", "update-desktop-database.hook"):
        assert before < name


def test_the_hosted_repository_is_served_from_osiris_downloads() -> None:
    assert package.REPOSITORY_SERVER == (
        "https://osiris-downloads.alphaneuron.net/repo/$arch"
    )


def test_pacman_trusts_the_signing_key_fully() -> None:
    """The form pacman-key --populate reads from <keyring>-trusted."""
    assert package.trusted() == f"{package.SIGNING_KEY}:4:\n"


@pytest.mark.skipif(shutil.which("gpg") is None, reason="needs gpg")
def test_the_shipped_keyring_holds_the_signing_key() -> None:
    shown = subprocess.run(
        [
            "gpg",
            "--show-keys",
            "--with-colons",
            str(REPOSITORY / package.KEYRING_SOURCE),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    fingerprints = [
        line.split(":")[9] for line in shown.splitlines() if line.startswith("fpr")
    ]
    assert package.SIGNING_KEY in fingerprints


def test_wifi_passwords_are_kept_by_a_secrets_service() -> None:
    """Cinnamon's network menu saves passwords through libsecret, which needs
    a Secret Service; Cinnamon lists gnome-keyring only as optional. Without
    it a Wi-Fi network is saved with no password and every later connection
    fails. LightDM's PAM unlocks it at login when it is installed."""
    assert "gnome-keyring" in package.depends()
