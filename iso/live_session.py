#!/usr/bin/env python3
"""Make the install medium's live root the Osiris desktop.

    osiris-live-setup

Runs once, while the ISO is built: a pacman hook on the medium calls it inside
the live root as soon as the `osiris` package is installed there (see
iso/profile.py). It provisions the desktop exactly as an install does, then
adds the one thing an install does not have: an account that logs itself in.

The account has no password. LightDM's autologin only skips the password check
for members of `autologin`, a group nothing on Arch creates.

osiris-setup enables NetworkManager, and two managers on one interface fight
over it, so releng's are turned off here. systemd-networkd is masked rather
than disabled: archiso leaves /etc/machine-id uninitialized, which makes every
boot a first boot, and systemd re-enables whatever its presets list - networkd
among them - on each one. A masked unit is the one thing presets leave alone.
iwd is in no preset, so disabling it holds.
"""
import subprocess
import sys

USER = "live"
NETWORKD = (
    "systemd-networkd.service",
    "systemd-networkd.socket",
    "systemd-networkd-varlink.socket",
    "systemd-networkd-varlink-metrics.socket",
    "systemd-networkd-resolve-hook.socket",
    "systemd-networkd-wait-online.service",
)


def run(*argv: str) -> None:
    print("  $", " ".join(argv), flush=True)
    subprocess.run(argv, check=True)


def main() -> None:
    run("osiris-setup", "--live")
    run("systemctl", "disable", "iwd.service", *NETWORKD)
    run("systemctl", "mask", *NETWORKD)
    if subprocess.run(["getent", "group", "autologin"],
                      capture_output=True).returncode != 0:
        run("groupadd", "--system", "autologin")
    run("useradd", "--create-home", "--groups", "wheel,autologin",
        "--shell", "/usr/bin/zsh", "--comment", "Live session", USER)
    run("passwd", "--delete", USER)
    print("OSIRIS_LIVE_SESSION_READY")


if __name__ == "__main__":
    sys.exit(main())
