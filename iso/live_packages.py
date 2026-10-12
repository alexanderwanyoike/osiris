"""What the Osiris medium adds to archiso's releng package list.

releng is Arch's own install medium, and already carries archinstall, the
disk and filesystem tools, firmware, microcode and networking. On top of it
the medium carries the `osiris` package itself, so the live session is the
desktop an install produces, and what the installer needs to run without it.
"""

# The live session: the installed desktop, from the same package archinstall
# installs. It brings Cinnamon, LightDM and the boot splash with it.
DESKTOP = ["osiris"]

# A bare X session to host the installer when the medium is booted without the
# live desktop. xinit takes a client and a server on argv, which is how the
# installer service starts without a shell or a display manager. mesa renders
# in software where there is no driver, as in most virtual machines.
# xsetroot gives that bare screen a pointer rather than X's default X shape.
GRAPHICS = ["xorg-server", "xorg-xinit", "xorg-xrandr", "xorg-xsetroot", "mesa"]

# The installer itself: GTK4 and libadwaita in Python, same as the Appearance
# app. adwaita-icon-theme supplies the symbolic icons the UI asks for.
INSTALLER = [
    "python", "python-gobject", "gtk4", "libadwaita",
    "adwaita-icon-theme", "noto-fonts", "ttf-firacode-nerd",
    # lspci, which is how the installer works out which graphics driver the
    # machine needs.
    "pciutils",
    # Making room to install beside another system: the installer opens it
    # rather than shrinking anything itself.
    "gparted",
]

# The installed system's network manager, in place of releng's; see
# iso/live_session.py.
NETWORK = ["networkmanager"]


def additions() -> list[str]:
    return DESKTOP + GRAPHICS + INSTALLER + NETWORK
