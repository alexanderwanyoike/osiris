"""Removing the install medium's repository from the installed system.

The input is what archinstall itself appends, produced by its own
`repositories_config`, so a change to that format shows up here.
"""

from __future__ import annotations

from archinstall.lib.models.mirrors import (
    CustomRepository,
    MirrorConfiguration,
    SignCheck,
    SignOption,
)

from osiris.provision.pacman_conf import without_local_repository

STOCK = """[options]
HoldPkg     = pacman glibc
Architecture = auto

[core]
Include = /etc/pacman.d/mirrorlist

[extra]
Include = /etc/pacman.d/mirrorlist
"""


def appended(url: str) -> str:
    repository = CustomRepository(
        name="osiris",
        url=url,
        sign_check=SignCheck.Optional,
        sign_option=SignOption.TrustAll,
    )
    return MirrorConfiguration(custom_repositories=[repository]).repositories_config()


def test_the_install_mediums_repository_is_removed() -> None:
    text = STOCK + appended("file:///usr/share/osiris/repo")
    cleaned = without_local_repository(text, "osiris")
    assert "[osiris]" not in cleaned
    assert "file://" not in cleaned
    assert cleaned.strip() == STOCK.strip()


def test_a_hosted_repository_is_kept() -> None:
    text = STOCK + appended("https://repo.example.org/$arch")
    assert without_local_repository(text, "osiris") == text


def test_a_section_in_the_middle_leaves_the_rest_alone() -> None:
    local = "[osiris]\nSigLevel = Optional TrustAll\nServer = file:///repo\n\n"
    text = STOCK.replace("[extra]", local + "[extra]")
    cleaned = without_local_repository(text, "osiris")
    assert cleaned == STOCK


def test_nothing_to_remove() -> None:
    assert without_local_repository(STOCK, "osiris") == STOCK
