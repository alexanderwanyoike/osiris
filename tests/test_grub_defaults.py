"""Osiris's GRUB settings, merged without disturbing archinstall's."""

from __future__ import annotations

from osiris.provision.grub_defaults import SETTINGS, grub_dir, merged, settings

# The shape of Arch's stock /etc/default/grub after archinstall has filled in
# the kernel command line for an encrypted btrfs root.
COMMAND_LINE = (
    "cryptdevice=PARTUUID=abc:root root=/dev/mapper/root zswap.enabled=0 "
    "rootflags=subvol=@ rw rootfstype=btrfs quiet splash"
)
ARCHINSTALL = f"""# GRUB boot loader configuration

GRUB_DEFAULT=0
GRUB_TIMEOUT=5
GRUB_DISTRIBUTOR="Arch"
GRUB_CMDLINE_LINUX_DEFAULT="loglevel=3 quiet"
GRUB_CMDLINE_LINUX="{COMMAND_LINE}"

# Uncomment to enable a theme
#GRUB_THEME="/path/to/gfxtheme"

#GRUB_DISABLE_OS_PROBER=false
"""


def values(text: str) -> dict[str, str]:
    return dict(
        line.split("=", 1)
        for line in text.splitlines()
        if "=" in line and not line.startswith("#")
    )


def test_archinstalls_kernel_command_line_survives() -> None:
    assert values(merged(ARCHINSTALL))["GRUB_CMDLINE_LINUX"] == f'"{COMMAND_LINE}"'


def test_every_setting_is_applied_exactly_once() -> None:
    text = merged(ARCHINSTALL)
    for key, value in SETTINGS.items():
        assert values(text)[key] == value
        assert sum(line.startswith(f"{key}=") for line in text.splitlines()) == 1


def test_commented_keys_are_replaced_in_place() -> None:
    text = merged(ARCHINSTALL).splitlines()
    original = ARCHINSTALL.splitlines()
    assert text.index(f"GRUB_THEME={SETTINGS['GRUB_THEME']}") == original.index(
        '#GRUB_THEME="/path/to/gfxtheme"'
    )


def test_merging_twice_changes_nothing() -> None:
    once = merged(ARCHINSTALL)
    assert merged(once) == once


def test_a_shared_esp_points_the_theme_at_efi() -> None:
    directory = grub_dir(lambda path: path == "/efi/grub/grub.cfg")
    assert directory == "/efi/grub"
    text = merged(ARCHINSTALL, settings(directory))
    assert 'GRUB_THEME="/efi/grub/themes/osiris/theme.txt"' in text


def test_a_disk_of_its_own_uses_boot() -> None:
    assert grub_dir(lambda path: path == "/boot/grub/grub.cfg") == "/boot/grub"
