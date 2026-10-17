"""Install the Osiris theme system and the Appearance app.

    python3 provision/themes.py [--repo PATH]

Lays down:
    /usr/share/osiris/lib/osiris/    the osiris package
    /usr/share/osiris/themes/        theme manifests, engine, previews
    /usr/share/osiris/logo-mask.png  the mark, composited into wallpapers
    /usr/share/osiris/appearance/    the Appearance app
    /usr/bin/osiris-appearance       launcher
    /usr/share/applications/         menu entry
    /usr/share/backgrounds/osiris/   generated wallpapers

This is what the `osiris-themes` package would own. Themes are pure data and
update independently of the desktop, which is why they are separate from
provision/cinnamon.py.
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import run  # noqa: E402

SHARE = "/usr/share/osiris"
THEMES_DIR = f"{SHARE}/themes"
APP_DIR = f"{SHARE}/appearance"
# The osiris package itself. Everything on the target that wants the tested
# code imports it from here; shell/themes/*.py are shims that put this on
# sys.path. Until the whole legacy tree has moved across, both are installed.
LIB_DIR = f"{SHARE}/lib"
WALLPAPERS = "/usr/share/backgrounds/osiris"
# Cinnamon loads system-wide extensions from here; enabled in provision/cinnamon.py.
TRANSITION = "transition@osiris"
EXTENSIONS_DIR = "/usr/share/cinnamon/extensions"

LAUNCHER = """#!/usr/bin/env python3
import runpy
import sys

sys.argv[0] = "osiris-appearance"
runpy.run_path("/usr/share/osiris/appearance/main.py", run_name="__main__")
"""


# Applies the default theme on a user's first login; see engine.first_login.
FIRST_LOGIN = """[Desktop Entry]
Type=Application
Name=Osiris theme
Comment=Apply the default Osiris theme on first login
Exec=/usr/bin/python3 /usr/share/osiris/themes/engine.py --first-login
NoDisplay=true
X-GNOME-Autostart-enabled=true
"""

# Drifts the wallpaper for the session; see shell/themes/drift.py.
DRIFT = """[Desktop Entry]
Type=Application
Name=Osiris wallpaper drift
Comment=Let the wallpaper drift slowly
Exec=/usr/bin/python3 /usr/share/osiris/themes/drift.py
NoDisplay=true
X-GNOME-Autostart-enabled=true
"""


def copy_tree(src: str, dst: str, suffixes: tuple[str, ...]) -> int:
    os.makedirs(dst, exist_ok=True)
    count = 0
    for name in sorted(os.listdir(src)):
        path = os.path.join(src, name)
        if os.path.isfile(path) and name.endswith(suffixes):
            shutil.copy(path, os.path.join(dst, name))
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    args = parser.parse_args()

    if os.geteuid() != 0:
        sys.exit("must run as root")

    src_themes = os.path.join(args.repo, "shell", "themes")
    if not os.path.isdir(src_themes):
        sys.exit(f"missing {src_themes}")

    print("installing the osiris package")
    package = os.path.join(args.repo, "osiris")
    if not os.path.isdir(package):
        sys.exit(f"missing {package}")
    target = os.path.join(LIB_DIR, "osiris")
    if os.path.isdir(target):
        shutil.rmtree(target)
    os.makedirs(LIB_DIR, exist_ok=True)
    shutil.copytree(
        package, target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print(f"  {target}")

    print("installing themes")
    n = copy_tree(src_themes, THEMES_DIR, (".json", ".py"))
    print(f"  {n} files -> {THEMES_DIR}")

    previews = os.path.join(src_themes, "previews")
    if os.path.isdir(previews):
        n = copy_tree(previews, f"{THEMES_DIR}/previews", (".png",))
        print(f"  {n} previews")
    else:
        print("  no previews; run shell/themes/preview.py first")

    print("installing the logo mask")
    # wallpaper.py composites this into every generated background, including
    # for themes written on the machine, so it has to be on the target rather
    # than only in the checkout.
    mask = os.path.join(args.repo, "branding", "logo-mask.png")
    if os.path.exists(mask):
        os.makedirs(SHARE, exist_ok=True)
        shutil.copy(mask, f"{SHARE}/logo-mask.png")
        os.chmod(f"{SHARE}/logo-mask.png", 0o644)
        print(f"  {SHARE}/logo-mask.png")
    else:
        print("  missing branding/logo-mask.png; run "
              "branding/scripts/make-logo-mask.py")

    print("installing wallpapers")
    generated = os.path.join(args.repo, "branding", "wallpapers", "generated")
    if os.path.isdir(generated):
        n = copy_tree(generated, WALLPAPERS, (".png",))
        for name in os.listdir(WALLPAPERS):
            os.chmod(os.path.join(WALLPAPERS, name), 0o644)
        print(f"  {n} wallpapers -> {WALLPAPERS}")

    print("installing the Appearance app")
    src_app = os.path.join(args.repo, "apps", "appearance")
    copy_tree(src_app, APP_DIR, (".py",))
    with open("/usr/bin/osiris-appearance", "w") as fh:
        fh.write(LAUNCHER)
    os.chmod("/usr/bin/osiris-appearance", 0o755)
    desktop = os.path.join(src_app, "dev.osiris.Appearance.desktop")
    if os.path.exists(desktop):
        shutil.copy(desktop, "/usr/share/applications/"
                             "dev.osiris.Appearance.desktop")
    run("update-desktop-database", "/usr/share/applications", check=False)
    print("  /usr/bin/osiris-appearance")

    print("installing the theme transition")
    target = os.path.join(EXTENSIONS_DIR, TRANSITION)
    n = copy_tree(os.path.join(src_themes, TRANSITION), target, (".js", ".json"))
    print(f"  {n} files -> {target}")

    print("applying the default theme on first login")
    os.makedirs("/etc/xdg/autostart", exist_ok=True)
    with open("/etc/xdg/autostart/osiris-theme.desktop", "w") as fh:
        fh.write(FIRST_LOGIN)
    print("  /etc/xdg/autostart/osiris-theme.desktop")

    print("drifting the wallpaper for each session")
    with open("/etc/xdg/autostart/osiris-drift.desktop", "w") as fh:
        fh.write(DRIFT)
    print("  /etc/xdg/autostart/osiris-drift.desktop")

    print("THEMES_INSTALLED")


if __name__ == "__main__":
    main()
