"""Apply Osiris branding to the boot splash and login screen.

    python3 provision/branding.py [--repo PATH]

Touches three surfaces:
  * Plymouth boot splash showing the Osiris logo on the brand background
  * LightDM slick-greeter background
  * /usr/share/osiris/ as the canonical place other components read assets from

Plymouth needs a mkinitcpio hook and a kernel command line flag, so this
regenerates the initramfs. The kernel command line that Plymouth needs
(`quiet splash`) is set by provision/grub.py, which owns the bootloader.
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run import run  # noqa: E402

from osiris.provision import plymouth  # noqa: E402

BRANDING_DIR = "/usr/share/osiris"
WALLPAPERS_DIR = "/usr/share/backgrounds/osiris"
# The generated per-theme wallpapers are deliberately plain gradients. The
# greeter uses the branded one, which carries the logo.
BRANDED_WALLPAPER = f"{WALLPAPERS_DIR}/osiris-default.png"
WALLPAPER = f"{WALLPAPERS_DIR}/osiris-obsidian.png"
SPLASH_LOGO = "/usr/share/osiris/logo-splash.png"
# The greeter draws its logo in a corner; the 320px splash asset clips there.
GREETER_LOGO = "/usr/share/osiris/logo-greeter.png"
MENU_ICON = "/usr/share/icons/hicolor/scalable/apps/osiris-symbolic.svg"

SLICK_GREETER_CONF = f"""[Greeter]
background={BRANDED_WALLPAPER}
background-color=#0d0d10
theme-name=adw-gtk3-dark
icon-theme-name=Papirus-Dark
font-name=Noto Sans 10
show-hostname=true
show-a11y=false
show-keyboard=false
draw-user-backgrounds=false
draw-grid=false
"""


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
    os.makedirs(plymouth.THEME_DIR, exist_ok=True)
    prepared = os.path.join(repo, "branding", "logo-splash.png")
    if not os.path.exists(prepared):
        sys.exit(f"missing {prepared}; see the comment above for how to build it")
    shutil.copy(prepared, SPLASH_LOGO)
    shutil.copy(prepared, os.path.join(plymouth.THEME_DIR, "logo.png"))

    greeter_logo = os.path.join(repo, "branding", "logo-greeter.png")
    if os.path.exists(greeter_logo):
        shutil.copy(greeter_logo, GREETER_LOGO)
    print(f"  installed logo to {BRANDING_DIR}, splash logo to {plymouth.THEME_DIR}")

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
    write(os.path.join(plymouth.THEME_DIR, "osiris.plymouth"), plymouth.THEME_FILE)
    write(os.path.join(plymouth.THEME_DIR, "osiris.script"), plymouth.SCRIPT)
    run("plymouth-set-default-theme", plymouth.THEME)


def has_plymouth_hook() -> bool:
    with open("/etc/mkinitcpio.conf") as fh:
        return plymouth.has_hook(fh.read())


def add_mkinitcpio_hook() -> bool:
    """Insert the plymouth hook; see osiris/provision/plymouth.py. Returns True
    if changed."""
    path = "/etc/mkinitcpio.conf"
    with open(path) as fh:
        text = fh.read()
    if plymouth.has_hook(text):
        print("  plymouth hook already present")
        return False
    new = plymouth.with_hook(text)
    if new == text:
        print("  no systemd or udev hook found; skipping splash hook")
        return False
    with open(path, "w") as fh:
        fh.write(new)
    print("  added plymouth to mkinitcpio HOOKS")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--no-initramfs", action="store_true",
                        help="leave the initramfs to whoever builds it")
    args = parser.parse_args()

    if os.geteuid() != 0:
        sys.exit("must run as root")

    install_assets(args.repo)
    install_plymouth()
    add_mkinitcpio_hook()

    print("configuring login screen")
    write("/etc/lightdm/slick-greeter.conf", SLICK_GREETER_CONF)

    # The splash theme is copied into the initramfs, so choosing one means
    # rebuilding it - even when the hook was already there. On an install,
    # archinstall added the hook and built the initramfs with its own default
    # theme a minute earlier.
    if has_plymouth_hook() and not args.no_initramfs:
        print("regenerating initramfs")
        run("mkinitcpio", "-P")

    print("BRANDING_CONFIGURED")


if __name__ == "__main__":
    main()
