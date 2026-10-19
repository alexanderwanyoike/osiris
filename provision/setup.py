"""Turn an installed Arch + Cinnamon into Osiris.

    osiris-setup
    osiris-setup --live

The `osiris` package installs this as /usr/bin/osiris-setup, and archinstall
runs it inside the new system once everything else is in place: users exist,
packages are installed, the bootloader is on the disk. It applies what a
package cannot ship as plain files - the desktop defaults, the themes, the
boot splash, the GRUB theme - by running the same provisioning scripts, in
the same order, that a development machine runs.

It installs nothing that can stop the machine booting. GRUB was installed by
archinstall; this only themes it.

--live is the install medium's: it runs while the ISO is built, to make the
live session the same desktop. The medium boots through archiso's own menus,
so there is no GRUB to theme, and archiso builds its initramfs itself.
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import osiris  # noqa: E402
from osiris.provision import upgrade  # noqa: E402
from osiris.iso.package import KEYRING_DIR, REPOSITORY_SERVER  # noqa: E402
from osiris.provision.pacman_conf import (  # noqa: E402
    with_hosted_repository,
    without_local_repository,
)

# Order matters: themes.py composites the logo that branding.py installs into
# the wallpapers, harness.py's bar imports the package themes.py installs, and
# grub.py needs the fonts the packages brought in.
SCRIPTS = ("cinnamon.py", "apps.py", "branding.py", "themes.py", "harness.py",
           "grub.py")

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


def use_hosted_repository() -> None:
    """Trust the package signing key, then take Osiris's packages from the
    hosted repository instead of the install medium's.

    Without the keyring, which the osiris package installs, pacman would
    refuse every package from it, so the medium's repository is only removed.
    """
    if not os.path.exists(os.path.join(KEYRING_DIR, f"{REPOSITORY}.gpg")):
        forget_install_medium()
        return
    subprocess.run(["pacman-key", "--populate", REPOSITORY], check=True)
    with open(PACMAN_CONF) as fh:
        text = fh.read()
    updated = with_hosted_repository(text, REPOSITORY, REPOSITORY_SERVER)
    if updated != text:
        with open(PACMAN_CONF, "w") as fh:
            fh.write(updated)
        print(f"  pacman takes [{REPOSITORY}] from {REPOSITORY_SERVER}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true",
                        help="provision the install medium's live session")
    args = parser.parse_args()

    if os.geteuid() != 0:
        sys.exit("must run as root")

    for script in SCRIPTS:
        argv = [sys.executable, os.path.join(HERE, script)]
        if args.live and script == "grub.py":
            continue
        if args.live and script == "branding.py":
            argv.append("--no-initramfs")
        print(f"== {script} ==", flush=True)
        subprocess.run(argv, check=True)

    # The live medium's installer installs from the medium's own repository.
    if args.live:
        forget_install_medium()
    else:
        use_hosted_repository()
    # Last, so a running Osiris app that sees it restarts onto finished code.
    upgrade.MARKER.write_text(f"{osiris.__version__} {time.time_ns()}\n")
    print("OSIRIS_SETUP_DONE")


if __name__ == "__main__":
    main()
