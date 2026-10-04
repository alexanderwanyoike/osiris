"""Package sets that define an Osiris system.

Kept as plain data so the eventual pacman packages (osiris-base, osiris-desktop)
can depend on exactly these lists rather than re-deriving them.

What is *not* here is drivers. Osiris ships the drivers the target machine
actually has, worked out at install time by osiris.model.hardware - bundling
every driver so one image suits every machine is how a distribution reaches
four gigabytes.
"""

from collections.abc import Sequence

# Bootable Arch with networking, audio and a login shell. No desktop.
BASE = [
    "base", "linux", "linux-firmware", "mkinitcpio",
    # The provisioning scripts run inside the new system during install, so the
    # target needs python before any of them can configure anything. It would
    # otherwise arrive only as a dependency of the desktop packages, which
    # makes a desktop-less install silently unprovisionable.
    "python",
    "sudo", "openssh", "git", "vim", "nano", "which", "man-db",
    # The root may be btrfs; the tools have to be on the installed system, not
    # only on the installer.
    "btrfs-progs",
    # GRUB draws the boot menu; efibootmgr writes the UEFI boot entry and
    # os-prober finds other installed systems.
    "grub", "efibootmgr", "os-prober",
    "networkmanager", "polkit",
    "pipewire", "pipewire-pulse", "wireplumber",
    "upower", "brightnessctl",
    "xdg-user-dirs",
]

# Cinnamon plus the pieces Osiris layers on top: Plank as the dock, rofi as the
# launcher, LightDM with Mint's slick-greeter as the login screen. Cinnamon's
# own panel is trimmed to a single top bar by provision/cinnamon.py.
DESKTOP_CINNAMON = [
    "cinnamon", "cinnamon-translations", "nemo",
    "plank", "rofi",
    "lightdm", "lightdm-slick-greeter",
    "xdg-desktop-portal-gtk",
    "xed", "gnome-screenshot",
    "adw-gtk-theme", "papirus-icon-theme",
]

# Applications Osiris ships by default.
#
# ghostty: GTK4/libadwaita native, and shapes text through harfbuzz, so it is
# the only conventional terminal in Arch's repos that does BOTH font ligatures
# and background transparency. VTE terminals (gnome-terminal, xfce4-terminal)
# implement no ligatures at all, and gnome-terminal has no transparency setting.
#
# chromium and code are the builds that exist in Arch's repositories.
# google-chrome and visual-studio-code-bin are AUR-only; a distribution cannot
# depend on the AUR, so shipping those means building them into an Osiris repo.
APPS = [
    "ghostty",
    "chromium",
    "code",
    "zsh", "zsh-completions",
    "git",
    "fastfetch",
    "ttf-firacode-nerd", "ttf-jetbrains-mono-nerd",
    "noto-fonts", "noto-fonts-emoji",
    "wl-clipboard", "xclip",
    # Appearance app: GTK4/libadwaita in Python. Pillow and numpy render the
    # theme previews and generate wallpapers, including for themes the user
    # writes on the machine, so both are needed at runtime and not just at
    # build time.
    "python-gobject", "gtk4", "libadwaita", "python-pillow", "python-numpy",
]

# Boot splash.
BRANDING = [
    "plymouth",
]

# Forced when the user ticks "software rendering", for a machine whose GPU
# driver is broken rather than absent. Hardware detection adds these by itself
# for a guest; this is the override.
SOFTWARE_RENDERING = [
    "mesa", "vulkan-swrast",
]


def for_install(
    software_rendering: bool = False,
    detected: Sequence[str] = (),
) -> list[str]:
    """The package set for one machine.

    `detected` is what osiris.model.hardware decided this particular machine
    needs - its microcode, its GPU drivers - and is the reason Osiris does not
    ship every driver to every target. See provision/hardware.py.
    """
    packages = BASE + DESKTOP_CINNAMON + APPS + BRANDING + list(detected)
    if software_rendering:
        packages += SOFTWARE_RENDERING
    # Order is irrelevant to pacman but a stable one makes the install log
    # diffable between runs.
    return sorted(set(packages))
