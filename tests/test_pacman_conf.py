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

from osiris.provision.pacman_conf import (
    with_hosted_repository,
    without_local_repository,
)

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


def test_both_copies_archinstall_writes_are_removed() -> None:
    """One arrives with the live pacman.conf, the other is appended after."""
    local = appended("file:///usr/share/osiris/repo")
    cleaned = without_local_repository(STOCK + local + local, "osiris")
    assert "[osiris]" not in cleaned
    assert cleaned.strip() == STOCK.strip()


HOSTED = "https://osiris-downloads.alphaneuron.net/repo/$arch"


def test_the_install_mediums_repository_is_replaced_by_the_hosted_one() -> None:
    text = STOCK + appended("file:///usr/share/osiris/repo")
    updated = with_hosted_repository(text, "osiris", HOSTED)
    assert "file://" not in updated
    assert updated == STOCK + (
        f"\n[osiris]\nSigLevel = Required DatabaseOptional\nServer = {HOSTED}\n"
    )


def test_a_system_without_the_repository_gains_it() -> None:
    """Machines whose setup only removed the medium's repository."""
    updated = with_hosted_repository(STOCK, "osiris", HOSTED)
    assert updated.count("[osiris]") == 1
    assert f"Server = {HOSTED}" in updated


def test_naming_the_hosted_repository_twice_changes_nothing() -> None:
    once = with_hosted_repository(STOCK, "osiris", HOSTED)
    assert with_hosted_repository(once, "osiris", HOSTED) == once
