"""Theme the GRUB boot menu.

    python3 provision/grub.py [--repo PATH]

GRUB itself is installed by archinstall, for UEFI or BIOS, before this runs.
This puts the Osiris theme beside it, merges Osiris's settings into
/etc/default/grub (see osiris/provision/grub_defaults.py for why it merges
rather than overwrites) and regenerates the menu. It never runs grub-install:
a theme that fails to apply leaves a plain menu, and a plain menu still boots.

The theme lives under /boot/grub/themes/osiris, which GRUB reads at boot,
before any filesystem but the one holding /boot is mounted.
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run import run  # noqa: E402

from osiris.provision.grub_defaults import merged  # noqa: E402

THEME_DIR = "/boot/grub/themes/osiris"
DEFAULTS = "/etc/default/grub"

# Fonts have to be GRUB's own .pf2 format. The family name set here is what
# theme.txt refers to; if the two disagree GRUB falls back to a bitmap font
# without saying so.
FONTS = (
    ("Osiris Sans", 18, "/usr/share/fonts/noto/NotoSans-Regular.ttf"),
    ("Osiris Sans", 28, "/usr/share/fonts/noto/NotoSans-Regular.ttf"),
    ("Osiris Sans", 14, "/usr/share/fonts/noto/NotoSans-Regular.ttf"),
    ("Osiris Mono", 16,
     "/usr/share/fonts/TTF/FiraCodeNerdFont-Regular.ttf"),
)

def find_font(candidates: str) -> str | None:
    if os.path.exists(candidates):
        return candidates
    return None


def install_fonts() -> None:
    """Convert the UI fonts to .pf2 beside the theme."""
    made = set()
    for name, size, source in FONTS:
        if (name, size) in made:
            continue
        if find_font(source) is None:
            print(f"  missing {source}; GRUB will fall back for {name} {size}")
            continue
        target = os.path.join(THEME_DIR, f"{name.replace(' ', '-')}-{size}.pf2")
        run("grub-mkfont", "-n", name, "-s", str(size), "-o", target, source,
            check=False)
        made.add((name, size))
        print(f"  {os.path.basename(target)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    args = parser.parse_args()

    if os.geteuid() != 0:
        sys.exit("must run as root")

    source = os.path.join(args.repo, "branding", "grub")
    if not os.path.isdir(source):
        sys.exit(f"missing {source}; run branding/scripts/make-grub-theme.py")

    print("installing the boot menu theme")
    if os.path.isdir(THEME_DIR):
        shutil.rmtree(THEME_DIR)
    os.makedirs(THEME_DIR, exist_ok=True)
    for name in sorted(os.listdir(source)):
        if name.endswith((".png", ".txt")):
            shutil.copy(os.path.join(source, name),
                        os.path.join(THEME_DIR, name))
    print(f"  {THEME_DIR}")
    install_fonts()

    print("configuring the boot menu")
    with open(DEFAULTS) as fh:
        current = fh.read()
    with open(DEFAULTS, "w") as fh:
        fh.write(merged(current))
    run("grub-mkconfig", "-o", "/boot/grub/grub.cfg")

    print("GRUB_CONFIGURED")


if __name__ == "__main__":
    main()
