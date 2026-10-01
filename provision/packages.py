"""Package sets that define an Osiris system.

Kept as plain data so the eventual pacman packages (osiris-base, osiris-desktop)
can depend on exactly these lists rather than re-deriving them.
"""

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

# COSMIC. `cosmic` is a package group pulling the whole session. Kept so the
# desktop choice stays a one-word argument rather than a rewrite.
DESKTOP_COSMIC = [
    "cosmic",
    "cosmic-icon-theme",
    "xdg-desktop-portal-cosmic",
]

DESKTOPS = {
    "cinnamon": DESKTOP_CINNAMON,
    "cosmic": DESKTOP_COSMIC,
}

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

# Only needed where there is no GPU acceleration, e.g. a QEMU guest.
SOFTWARE_RENDERING = [
    "mesa", "vulkan-swrast",
]


def for_install(desktop: str = "cinnamon",
                software_rendering: bool = False) -> list[str]:
    if desktop not in DESKTOPS:
        raise ValueError(f"unknown desktop {desktop!r}; "
                         f"one of: {', '.join(DESKTOPS)}")
    packages = BASE + DESKTOPS[desktop] + APPS + BRANDING
    if software_rendering:
        packages += SOFTWARE_RENDERING
    return packages
