#!/usr/bin/env python3
"""Make the install medium's live root the Osiris desktop.

    osiris-live-setup

Runs once, while the ISO is built: a pacman hook on the medium calls it inside
the live root as soon as the `osiris` package is installed there (see
iso/profile.py). It provisions the desktop exactly as an install does, then
adds the one thing an install does not have: an account that logs itself in.

The account has no password. LightDM's autologin only skips the password check
for members of `autologin`, a group nothing on Arch creates.
"""
import subprocess
import sys

USER = "live"


def run(*argv: str) -> None:
    print("  $", " ".join(argv), flush=True)
    subprocess.run(argv, check=True)


def main() -> None:
    run("osiris-setup", "--live")
    if subprocess.run(["getent", "group", "autologin"],
                      capture_output=True).returncode != 0:
        run("groupadd", "--system", "autologin")
    run("useradd", "--create-home", "--groups", "wheel,autologin",
        "--shell", "/usr/bin/zsh", "--comment", "Live session", USER)
    run("passwd", "--delete", USER)
    print("OSIRIS_LIVE_SESSION_READY")


if __name__ == "__main__":
    sys.exit(main())
