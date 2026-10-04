"""Turn an installed Arch + Cinnamon into Osiris.

    osiris-setup

The `osiris` package installs this as /usr/bin/osiris-setup, and archinstall
runs it inside the new system once everything else is in place: users exist,
packages are installed, the bootloader is on the disk. It applies what a
package cannot ship as plain files - the desktop defaults, the themes, the
boot splash, the GRUB theme - by running the same provisioning scripts, in
the same order, that a development machine runs.

It installs nothing that can stop the machine booting. GRUB was installed by
archinstall; this only themes it.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from osiris.provision.pacman_conf import without_local_repository  # noqa: E402

# Order matters: themes.py composites the logo that branding.py installs into
# the wallpapers, and grub.py needs the fonts the packages brought in.
SCRIPTS = ("cinnamon.py", "apps.py", "branding.py", "themes.py", "grub.py")

PACMAN_CONF = "/etc/pacman.conf"
REPOSITORY = "osiris"


def forget_install_medium() -> None:
    """Drop the install medium's repository from pacman.conf.

    See osiris/provision/pacman_conf.py: left in, every update fails.
    """
    with open(PACMAN_CONF) as fh:
        text = fh.read()
    cleaned = without_local_repository(text, REPOSITORY)
    if cleaned != text:
        with open(PACMAN_CONF, "w") as fh:
            fh.write(cleaned)
        print(f"  removed the install medium's [{REPOSITORY}] repository")


def main() -> None:
    if os.geteuid() != 0:
        sys.exit("must run as root")

    for script in SCRIPTS:
        print(f"== {script} ==", flush=True)
        subprocess.run([sys.executable, os.path.join(HERE, script)], check=True)

    forget_install_medium()
    print("OSIRIS_SETUP_DONE")


if __name__ == "__main__":
    main()
