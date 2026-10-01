"""Packages for the live ISO.

Only what is needed to boot a minimal graphical session, run the installer and
install onto a disk. Everything the installed system gets comes from
provision/packages.py and is pulled by pacstrap at install time, so adding a
desktop package here would bloat the ISO without reaching the target.
"""

# Bootable Arch, plus the archiso initramfs hooks that find and mount the
# squashfs the ISO is built around.
BASE = [
    "base", "linux", "linux-firmware", "mkinitcpio", "mkinitcpio-archiso",
    "systemd", "pacman", "sudo",
    # pacstrap verifies signatures against this keyring, and against the clock.
    "archlinux-keyring", "pacman-mirrorlist",
]

# What provision/install.py actually calls: pacstrap, arch-chroot and genfstab
# come from arch-install-scripts, sgdisk from gptfdisk.
INSTALL_TOOLS = [
    "arch-install-scripts", "gptfdisk", "parted", "dosfstools", "e2fsprogs",
    "btrfs-progs", "util-linux", "efibootmgr",
]

# pacstrap needs to reach a mirror, so the live system needs networking it can
# bring up without being asked. NetworkManager also covers wifi, which
# systemd-networkd alone does not.
NETWORK = ["networkmanager", "iwd", "openssh"]

# A minimal X session to host the installer. xinit takes a client and a server
# on argv, which is how the installer service starts without a shell.
GRAPHICS = [
    "xorg-server", "xorg-xinit", "xorg-xrandr",
    "mesa", "vulkan-swrast",            # software rendering, for VMs
]

# The installer itself: GTK4 and libadwaita in Python, same as the Appearance
# app. adwaita-icon-theme supplies the symbolic icons the UI asks for.
INSTALLER = [
    "python", "python-gobject", "gtk4", "libadwaita",
    "adwaita-icon-theme", "noto-fonts", "ttf-firacode-nerd",
]

# Enough of a console to diagnose a failed install without another machine.
RESCUE = ["nano", "less", "vim", "git"]


def for_iso() -> list[str]:
    return BASE + INSTALL_TOOLS + NETWORK + GRAPHICS + INSTALLER + RESCUE
