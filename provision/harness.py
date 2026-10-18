"""Install the Harness bar.

    python3 provision/harness.py [--repo PATH]

Lays down:
    /usr/share/osiris/harness/              the drawer (Super+A) and its Skins
    /usr/bin/osiris-harness                 launcher
    /usr/share/dbus-1/services/             D-Bus activation
    /etc/xdg/autostart/osiris-harness.desktop
    /usr/share/cinnamon/extensions/harness-drawer@osiris   placement and slide
    /usr/share/cinnamon/applets/harness@osiris             the panel button

The bar imports the osiris package that provision/themes.py installs into
/usr/share/osiris/lib, so it runs after that. The Engine, opencode, is a
package dependency (osiris/iso/package.py), not installed here.
"""
import argparse
import os
import shutil

HARNESS_DIR = "/usr/share/osiris/harness"
LAUNCHER_PATH = "/usr/bin/osiris-harness"
# Enabled in provision/cinnamon.py.
DRAWER_EXTENSION = "harness-drawer@osiris"
PANEL_BUTTON = "harness@osiris"

LAUNCHER = """#!/usr/bin/env python3
import runpy
import sys

sys.argv[0] = "osiris-harness"
runpy.run_path("/usr/share/osiris/harness/main.py", run_name="__main__")
"""

# Resident, like the theme switcher, so Super+A only has to signal it and the
# Engine connection is already open. D-Bus starts it if it is not running.
AUTOSTART = """[Desktop Entry]
Type=Application
Name=Osiris Harness
Comment=Keep the Super+A Harness bar ready
Exec=/usr/bin/osiris-harness --gapplication-service
NoDisplay=true
X-GNOME-Autostart-enabled=true
"""

SERVICE = """[D-BUS Service]
Name=dev.osiris.Harness
Exec=/usr/bin/osiris-harness --gapplication-service
"""


def write(path: str, text: str, mode: int = 0o644) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
    os.chmod(path, mode)
    print(f"  {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    args = parser.parse_args()

    print("installing the Harness bar")
    source = os.path.join(args.repo, "apps", "harness")
    os.makedirs(HARNESS_DIR, exist_ok=True)
    for name in sorted(os.listdir(source)):
        if name.endswith(".py"):
            shutil.copy(os.path.join(source, name), os.path.join(HARNESS_DIR, name))
    skins = os.path.join(HARNESS_DIR, "skins")
    shutil.rmtree(skins, ignore_errors=True)
    shutil.copytree(os.path.join(source, "skins"), skins)
    print(f"  {skins}")
    write(LAUNCHER_PATH, LAUNCHER, 0o755)
    write("/usr/share/dbus-1/services/dev.osiris.Harness.service", SERVICE)
    write("/etc/xdg/autostart/osiris-harness.desktop", AUTOSTART)
    for name, kind in ((DRAWER_EXTENSION, "extensions"), (PANEL_BUTTON, "applets")):
        target = f"/usr/share/cinnamon/{kind}/{name}"
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(os.path.join(args.repo, "apps", "harness", name), target)
        print(f"  {target}")
    print("HARNESS_INSTALLED")


if __name__ == "__main__":
    main()
