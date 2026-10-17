"""Where the boot splash's hook goes in mkinitcpio's HOOKS."""

from __future__ import annotations

from osiris.provision.plymouth import has_hook, with_hook

# Arch's stock HOOKS line, which archinstall writes on a systemd initramfs.
SYSTEMD = "HOOKS=(base systemd autodetect microcode modconf kms keyboard block filesystems fsck)\n"  # noqa: E501
# The install medium's, from archiso's releng profile.
BUSYBOX = "HOOKS=(base udev microcode modconf kms memdisk archiso block filesystems keyboard)\n"  # noqa: E501


def test_the_hook_follows_systemd() -> None:
    assert with_hook(SYSTEMD).startswith("HOOKS=(base systemd plymouth autodetect")


def test_the_hook_follows_udev_on_a_busybox_initramfs() -> None:
    assert with_hook(BUSYBOX).startswith("HOOKS=(base udev plymouth microcode")


def test_a_hook_already_present_is_not_added_again() -> None:
    once = with_hook(BUSYBOX)
    assert with_hook(once) == once


def test_hooks_with_neither_anchor_are_unchanged() -> None:
    text = "HOOKS=(base autodetect block filesystems)\n"
    assert with_hook(text) == text


def test_the_hook_is_found_only_in_hooks() -> None:
    assert has_hook(with_hook(BUSYBOX))
    assert not has_hook("MODULES=(plymouth)\n" + BUSYBOX)
