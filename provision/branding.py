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
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import run  # noqa: E402

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

PLYMOUTH_THEME = """[Plymouth Theme]
Name=Osiris
Description=Osiris boot splash
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/osiris
ScriptFile=/usr/share/plymouth/themes/osiris/osiris.script
"""

# Plymouth's scripting language. Background colours are the Osiris Obsidian
# palette (#0d0d10) expressed as 0-1 floats.
PLYMOUTH_SCRIPT = """# Osiris boot splash.
#
# Modelled on plymouth's own /usr/share/plymouth/themes/script example, which is
# known to render. The earlier version set sprite positions once at load and
# used a bare refresh callback; it drew nothing. Positions are recomputed in the
# callback here because Window geometry is not final when the script loads.

Window.SetBackgroundTopColor(0.051, 0.051, 0.063);
Window.SetBackgroundBottomColor(0.051, 0.051, 0.063);

logo.image = Image("logo.png");
logo.sprite = Sprite(logo.image);
logo.opacity_angle = 0;

fun refresh_callback ()
  {
    logo.opacity_angle += ((2 * 3.14) / 60) * 0.5;
    min_opacity = 0.45;
    opacity = (Math.Cos(logo.opacity_angle) + 1) / 2;
    opacity *= 1 - min_opacity;
    opacity += min_opacity;

    logo.sprite.SetX(Window.GetX() + Window.GetWidth()  / 2
                     - logo.image.GetWidth()  / 2);
    logo.sprite.SetY(Window.GetY() + Window.GetHeight() / 2
                     - logo.image.GetHeight() / 2);
    logo.sprite.SetOpacity(opacity);
  }

Plymouth.SetRefreshFunction(refresh_callback);
"""

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

    text_logo = os.path.join(repo, "branding", "logo.txt")
    if os.path.exists(text_logo):
        shutil.copy(text_logo, os.path.join(BRANDING_DIR, "logo.txt"))
        print(f"  installed {BRANDING_DIR}/logo.txt")


def install_plymouth() -> None:
    print("installing boot splash")
    write(os.path.join(THEME_DIR, "osiris.plymouth"), PLYMOUTH_THEME)
    write(os.path.join(THEME_DIR, "osiris.script"), PLYMOUTH_SCRIPT)
    run("plymouth-set-default-theme", "osiris")


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    args = parser.parse_args()

    if os.geteuid() != 0:
        sys.exit("must run as root")

    install_assets(args.repo)
    install_plymouth()
    changed = add_mkinitcpio_hook()

    print("configuring login screen")
    write("/etc/lightdm/slick-greeter.conf", SLICK_GREETER_CONF)

    if changed:
        print("regenerating initramfs")
        run("mkinitcpio", "-P")

    print("BRANDING_CONFIGURED")


if __name__ == "__main__":
    main()
