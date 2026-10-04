"""Apply Osiris branding to the boot splash and login screen.

    python3 provision/branding.py [--repo PATH]

Touches four surfaces:
  * Plymouth boot splash showing the Osiris logo on the brand background
  * LightDM slick-greeter background
  * /usr/share/osiris/ as the canonical place other components read assets from
  * /etc/os-release, the system's name as other tools report it

Plymouth needs a mkinitcpio hook and a kernel command line flag, so this
regenerates the initramfs. The kernel command line that Plymouth needs
(`quiet splash`) is set by provision/grub.py, which owns the bootloader.
"""
import argparse
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run import run  # noqa: E402

from osiris.resources.loader import Resources  # noqa: E402

BRANDING_DIR = "/usr/share/osiris"
THEME_DIR = "/usr/share/plymouth/themes/osiris"
WALLPAPERS_DIR = "/usr/share/backgrounds/osiris"
# The generated per-theme wallpapers are deliberately plain gradients. The
# greeter uses the branded one, which carries the logo.
BRANDED_WALLPAPER = f"{WALLPAPERS_DIR}/osiris-default.png"
WALLPAPER = f"{WALLPAPERS_DIR}/osiris-obsidian.png"
SPLASH_LOGO = "/usr/share/osiris/logo-splash.png"
# The greeter draws its logo in a corner; the 320px splash asset clips there.
GREETER_LOGO = "/usr/share/osiris/logo-greeter.png"
MENU_ICON = "/usr/share/icons/hicolor/scalable/apps/osiris-symbolic.svg"
OS_RELEASE = "/etc/os-release"

RESOURCES = Resources()


def write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
    print(f"  wrote {path}")


def install_assets(repo: str) -> None:
    src = os.path.join(repo, "branding", "logo-dark.png")
    if not os.path.exists(src):
        sys.exit(f"missing {src}")
    os.makedirs(BRANDING_DIR, exist_ok=True)
    shutil.copy(src, os.path.join(BRANDING_DIR, "logo.png"))

    # The source is thin linework sitting in a mostly empty 1024px canvas, at
    # roughly 3% mean brightness. Dropped onto the splash unmodified it is
    # invisible. Trim the empty canvas, lift the line brightness, and scale to
    # something readable at boot resolution.
    # The splash logo is prepared at build time and committed, so the target
    # system needs no ImageMagick. Regenerate it with:
    #   magick branding/logo-dark.png -trim +repage \
    #     -channel RGB -level 0%,40% +channel -resize x320 branding/logo-splash.png
    os.makedirs(THEME_DIR, exist_ok=True)
    prepared = os.path.join(repo, "branding", "logo-splash.png")
    if not os.path.exists(prepared):
        sys.exit(f"missing {prepared}; see the comment above for how to build it")
    shutil.copy(prepared, SPLASH_LOGO)
    shutil.copy(prepared, os.path.join(THEME_DIR, "logo.png"))

    greeter_logo = os.path.join(repo, "branding", "logo-greeter.png")
    if os.path.exists(greeter_logo):
        shutil.copy(greeter_logo, GREETER_LOGO)
    print(f"  installed logo to {BRANDING_DIR}, splash logo to {THEME_DIR}")

    # The branded wallpaper carries the logo; the greeter uses it.
    os.makedirs(WALLPAPERS_DIR, exist_ok=True)
    branded = os.path.join(repo, "branding", "wallpapers", "osiris-default.png")
    if os.path.exists(branded):
        shutil.copy(branded, BRANDED_WALLPAPER)
        os.chmod(BRANDED_WALLPAPER, 0o644)
        print(f"  installed {BRANDED_WALLPAPER}")

    # The mark as a symbolic icon, for the panel's menu button. Named, so the
    # setting refers to it by name and the panel recolours it with the theme.
    icon = os.path.join(repo, "branding", "osiris-symbolic.svg")
    if os.path.exists(icon):
        os.makedirs(os.path.dirname(MENU_ICON), exist_ok=True)
        shutil.copy(icon, MENU_ICON)
        os.chmod(MENU_ICON, 0o644)
        run("gtk-update-icon-cache", "-q", "-f", "-t", "/usr/share/icons/hicolor",
            check=False)
        print(f"  installed {MENU_ICON}")

    text_logo = os.path.join(repo, "branding", "logo.txt")
    if os.path.exists(text_logo):
        shutil.copy(text_logo, os.path.join(BRANDING_DIR, "logo.txt"))
        print(f"  installed {BRANDING_DIR}/logo.txt")


def install_plymouth() -> None:
    print("installing boot splash")
    for name in ("osiris.plymouth", "osiris.script"):
        write(os.path.join(THEME_DIR, name), RESOURCES.read(f"boot/{name}"))
    run("plymouth-set-default-theme", "osiris")


def has_plymouth_hook() -> bool:
    with open("/etc/mkinitcpio.conf") as fh:
        return re.search(r"^HOOKS=.*\bplymouth\b", fh.read(), re.M) is not None


def add_mkinitcpio_hook() -> bool:
    """Insert the right plymouth hook. Returns True if changed.

    Arch's plymouth package ships exactly one hook, named `plymouth`
    (`sd-plymouth` is a Fedora/Ubuntu convention and does not exist here -
    using it makes mkinitcpio fail and leaves an incomplete initramfs).
    It goes after `systemd` on the default systemd initramfs, or after `udev`
    on a busybox one.
    """
    path = "/etc/mkinitcpio.conf"
    with open(path) as fh:
        text = fh.read()
    if re.search(r"^HOOKS=.*\bplymouth\b", text, re.M):
        print("  plymouth hook already present")
        return False

    for anchor in ("systemd", "udev"):
        new = re.sub(rf"^(HOOKS=\(.*?\b{anchor}\b)", r"\1 plymouth", text,
                     count=1, flags=re.M)
        if new != text:
            with open(path, "w") as fh:
                fh.write(new)
            print(f"  added plymouth to mkinitcpio HOOKS (after {anchor})")
            return True

    print("  no systemd or udev hook found; skipping splash hook")
    return False


def install_os_release() -> None:
    """Name the system; see osiris/resources/system/os-release for why here."""
    print("naming the system")
    if os.path.islink(OS_RELEASE):
        os.remove(OS_RELEASE)
    write(OS_RELEASE, RESOURCES.read("system/os-release"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    args = parser.parse_args()

    if os.geteuid() != 0:
        sys.exit("must run as root")

    install_assets(args.repo)
    install_os_release()
    install_plymouth()
    add_mkinitcpio_hook()

    print("configuring login screen")
    write("/etc/lightdm/slick-greeter.conf",
          RESOURCES.render("desktop/slick-greeter.conf",
                           {"wallpaper": BRANDED_WALLPAPER}))

    # The splash theme is copied into the initramfs, so choosing one means
    # rebuilding it - even when the hook was already there. On an install,
    # archinstall added the hook and built the initramfs with its own default
    # theme a minute earlier.
    if has_plymouth_hook():
        print("regenerating initramfs")
        run("mkinitcpio", "-P")

    print("BRANDING_CONFIGURED")


if __name__ == "__main__":
    main()
