"""Configure the Cinnamon + Plank + rofi desktop.

    python3 provision/cinnamon.py [--user NAME]

Layout: one 30px panel at the TOP carrying a menu, indicators and a clock, and
nothing else. No window list in the panel - Plank at the bottom owns running and
pinned applications. rofi on Super+Space is the launcher.

Everything is written as system-wide dconf defaults under /etc/dconf/db/local.d,
not poked into a live session. That means it applies to every user, survives a
fresh login, and is the shape an `osiris-desktop` package would ship. Users can
still override anything; these are defaults, not locks.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import homes  # noqa: E402
import services  # noqa: E402
from run import run  # noqa: E402

from osiris.resources.loader import Resources  # noqa: E402

WALLPAPER = "/usr/share/backgrounds/osiris/osiris-obsidian.png"

# Applet order is "panelN:side:position:uuid:instance-id". Deliberately no
# window-list here: Plank is the task switcher.
APPLETS = [
    "panel1:left:0:menu@cinnamon.org:0",
    "panel1:right:0:systray@cinnamon.org:1",
    "panel1:right:1:xapp-status@cinnamon.org:2",
    "panel1:right:2:network@cinnamon.org:3",
    "panel1:right:3:sound@cinnamon.org:4",
    "panel1:right:4:power@cinnamon.org:5",
    "panel1:right:5:calendar@cinnamon.org:6",
]

# Plank's own defaults create several duplicate Firefox items on first run.
# Pin an explicit set instead. Names are the exact .desktop basenames present
# after a Cinnamon install - verified, not assumed.
PLANK_LAUNCHERS = [
    "com.mitchellh.ghostty.desktop",
    "nemo.desktop",
    "chromium.desktop",
    "code-oss.desktop",          # the `code` package ships code-oss.desktop
    "cinnamon-settings.desktop",
]

RESOURCES = Resources()


def dconf_defaults() -> str:
    """The dconf defaults, with the computed lists filled in."""
    return RESOURCES.render("desktop/dconf-defaults", {
        "applets": ", ".join(f"'{a}'" for a in APPLETS),
        "dock_items": ", ".join(
            f"'{n.removesuffix('.desktop')}.dockitem'" for n in PLANK_LAUNCHERS),
        "wallpaper": WALLPAPER,
    })


def write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
    print(f"  wrote {path}")


def write_plank_launchers() -> None:
    """Pin an explicit dock, in /etc/skel and for existing users."""
    for home in ["/etc/skel"] + [p.pw_dir for p in homes.desktop_users()]:
        owner = None if home == "/etc/skel" else homes.owner_of(home)
        plank = os.path.join(home, ".config", "plank")
        directory = os.path.join(plank, "dock1", "launchers")
        homes.makedirs(directory, owner)

        # Clear Plank's duplicate first-run items before pinning ours.
        for stale in os.listdir(directory):
            if stale.endswith(".dockitem"):
                os.remove(os.path.join(directory, stale))
        for name in PLANK_LAUNCHERS:
            item = os.path.join(directory,
                                name.removesuffix(".desktop") + ".dockitem")
            homes.write(item, "[PlankDockItemPreferences]\n"
                              f"Launcher=file:///usr/share/applications/{name}\n",
                        owner)
        if owner is not None:
            homes.chown_tree(plank, owner)
        print(f"  pinned {len(PLANK_LAUNCHERS)} dock items in {home}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    if os.geteuid() != 0:
        sys.exit("must run as root")

    print("configuring Cinnamon defaults")
    write("/etc/dconf/profile/user", RESOURCES.read("desktop/dconf-profile"))
    write("/etc/dconf/db/local.d/00-osiris", dconf_defaults())
    run("dconf", "update")

    print("configuring desktop defaults (gschema override)")
    write("/usr/share/glib-2.0/schemas/99-osiris.gschema.override",
          RESOURCES.render("desktop/99-osiris.gschema.override",
                           {"wallpaper": WALLPAPER}))
    run("glib-compile-schemas", "/usr/share/glib-2.0/schemas")

    print("configuring dock and launcher")
    write("/etc/xdg/autostart/plank.desktop",
          RESOURCES.read("desktop/plank.desktop"))
    write_plank_launchers()

    print("configuring display manager")
    write("/etc/lightdm/lightdm.conf.d/50-osiris.conf",
          RESOURCES.read("desktop/lightdm.conf"))
    services.enable("lightdm.service")
    run("systemctl", "set-default", "graphical.target")

    print("CINNAMON_CONFIGURED")


if __name__ == "__main__":
    main()
