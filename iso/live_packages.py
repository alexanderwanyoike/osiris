"""What the Osiris medium adds to archiso's releng package list.

releng is Arch's own install medium, and already carries archinstall, the
disk and filesystem tools, firmware, microcode and networking. These are only
what the graphical installer needs on top of it. Everything the installed
system gets comes from the `osiris` package and archinstall's choices, so
adding a desktop package here would make the medium bigger without reaching
the target.
"""

# A minimal X session to host the installer. xinit takes a client and a server
# on argv, which is how the installer service starts without a shell or a
# display manager. mesa renders in software where there is no driver, as in
# most virtual machines.
GRAPHICS = ["xorg-server", "xorg-xinit", "xorg-xrandr", "mesa"]

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


# The boot splash, the same one the installed system shows.
SPLASH = ["plymouth"]


def additions() -> list[str]:
    return GRAPHICS + INSTALLER + SPLASH
