"""Configure COSMIC and Osiris defaults on an already-installed system.

Run as root on the target:

    python3 provision/desktop.py [--software-rendering]

Idempotent: safe to re-run. This is the logic an `osiris-desktop` package would
eventually own via files plus a systemd preset, which is why everything here is
either "write a file" or "enable a unit" rather than imperative fiddling.
"""
import argparse
import os
import pwd
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import services  # noqa: E402
from run import run  # noqa: E402

# COSMIC's first-run wizard enables the screen reader by default, which is a
# poor first impression on a fresh install. Suppress it per-user; revisit if we
# ship our own welcome flow.
SUPPRESS_AUTOSTART = ["com.system76.CosmicInitialSetup.desktop"]

# Osiris trims COSMIC's stock layout hard. Stock ships 12 items on the top
# panel and 5 in the dock; that reads as clutter. Keep the panel to a clock plus
# the four indicators that actually change state, and the dock to a launcher and
# the running-app list. Everything removed is still reachable from Settings or
# the app library.
COSMIC_LAYOUT = {
    "com.system76.CosmicPanel.Panel": {
        "plugins_wings": 'Some(([], [\n'
                         '    "com.system76.CosmicAppletAudio",\n'
                         '    "com.system76.CosmicAppletNetwork",\n'
                         '    "com.system76.CosmicAppletBattery",\n'
                         '    "com.system76.CosmicAppletPower",\n'
                         ']))',
        "plugins_center": 'Some([\n    "com.system76.CosmicAppletTime",\n])',
        "size": "XS",
    },
    "com.system76.CosmicPanel.Dock": {
        "plugins_center": 'Some([\n'
                          '    "com.system76.CosmicPanelLauncherButton",\n'
                          '    "com.system76.CosmicAppList",\n'
                          '])',
        "size": "S",
    },
}

GTK_SETTINGS = (
    "[Settings]\n"
    "gtk-application-prefer-dark-theme=1\n"
    "gtk-icon-theme-name=Cosmic\n"
    "gtk-font-name=JetBrainsMono Nerd Font 10\n"
)

# Only for machines with no GPU acceleration (VMs). Harmless but wasteful
# elsewhere, so it is opt-in.
SOFTWARE_RENDERING_ENV = (
    "LIBGL_ALWAYS_SOFTWARE=1\n"
    "WGPU_BACKEND=gl\n"
)


def write(path: str, text: str, owner: pwd.struct_passwd | None = None) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
    if owner is not None:
        os.chown(path, owner.pw_uid, owner.pw_gid)
        os.chown(os.path.dirname(path), owner.pw_uid, owner.pw_gid)
    print(f"  wrote {path}")


def desktop_users() -> list[pwd.struct_passwd]:
    """Ordinary login users, i.e. everyone a desktop should be set up for."""
    return [p for p in pwd.getpwall()
            if 1000 <= p.pw_uid < 60000 and os.path.isdir(p.pw_dir)]


def configure_cosmic_layout(user: pwd.struct_passwd) -> None:
    for component, keys in COSMIC_LAYOUT.items():
        for key, value in keys.items():
            write(f"{user.pw_dir}/.config/cosmic/{component}/v1/{key}",
                  value, owner=user)


def configure_user(user: pwd.struct_passwd) -> None:
    print(f"configuring {user.pw_name}")
    configure_cosmic_layout(user)
    for entry in SUPPRESS_AUTOSTART:
        write(f"{user.pw_dir}/.config/autostart/{entry}",
              "[Desktop Entry]\n"
              "Type=Application\n"
              f"Name={entry.removesuffix('.desktop')}\n"
              "Hidden=true\n",
              owner=user)
    for gtk in ("gtk-3.0", "gtk-4.0"):
        write(f"{user.pw_dir}/.config/{gtk}/settings.ini",
              GTK_SETTINGS, owner=user)


def configure_system(software_rendering: bool) -> None:
    print("configuring system")
    # cosmic-greeter is the display manager; it provides the seat session that
    # cosmic-comp needs. A tty autologin does not, and fails with
    # "Failed to acquire session".
    services.enable("cosmic-greeter.service")
    run("systemctl", "set-default", "graphical.target")

    env = "XDG_CURRENT_DESKTOP=COSMIC\nXDG_SESSION_TYPE=wayland\n"
    if software_rendering:
        env += SOFTWARE_RENDERING_ENV
    write("/etc/environment", env)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--software-rendering", action="store_true",
                        help="target has no GPU acceleration (e.g. a VM)")
    args = parser.parse_args()

    if os.geteuid() != 0:
        sys.exit("must run as root")

    configure_system(args.software_rendering)
    for user in desktop_users():
        configure_user(user)
    print("DESKTOP_CONFIGURED")


if __name__ == "__main__":
    main()
