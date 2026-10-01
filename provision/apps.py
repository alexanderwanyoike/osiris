"""Configure the applications Osiris ships: shell, terminal, fetch.

    python3 provision/apps.py [--offline]

Covers the parts that are configuration rather than packages:
  * oh-my-zsh installed system-wide and zsh made the default login shell
  * ghostty: dark, translucent, FiraCode with ligatures
  * fastfetch configured to show the Osiris logo

oh-my-zsh is not packaged in any official repository, so it is cloned to
/usr/share/oh-my-zsh and owned by us - the same shape as shipping it in an
osiris-shell package later. --offline skips the clone.
"""
import argparse
import os
import pwd
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import homes  # noqa: E402
from run import run  # noqa: E402

OMZ_REPO = "https://github.com/ohmyzsh/ohmyzsh.git"
OMZ_DIR = "/usr/share/oh-my-zsh"
BRANDING_DIR = "/usr/share/osiris"

ZSHRC = """# Osiris default zsh configuration.
export ZSH="/usr/share/oh-my-zsh"
# The framework writes nothing to the shared install; per-user state lives here.
export ZSH_CUSTOM="$HOME/.config/osiris/zsh"
export ZSH_COMPDUMP="$HOME/.cache/zcompdump"

ZSH_THEME="af-magic"
plugins=(git sudo command-not-found)

mkdir -p "$ZSH_CUSTOM" "$(dirname "$ZSH_COMPDUMP")"
[ -r "$ZSH/oh-my-zsh.sh" ] && source "$ZSH/oh-my-zsh.sh"

setopt HIST_IGNORE_ALL_DUPS SHARE_HISTORY
HISTSIZE=50000
SAVEHIST=50000
HISTFILE="$HOME/.zsh_history"

alias ls='ls --color=auto'
alias grep='grep --color=auto'

command -v fastfetch >/dev/null && fastfetch
"""

# Key names verified against `ghostty +show-config --default`.
# font-feature calt/liga are FiraCode's ligature features; ghostty shapes
# through harfbuzz, so they actually take effect here.
GHOSTTY_CONF = """# Osiris terminal defaults.
font-family = FiraCode Nerd Font
font-size = 11
font-feature = calt
font-feature = liga

background = #0d0d10
foreground = #e8e8e8
cursor-color = #7c8aeb
selection-background = #2a2a2f
selection-foreground = #e8e8e8

background-opacity = 0.92
window-padding-x = 10
window-padding-y = 10
window-decoration = auto
scrollback-limit = 10000000
confirm-close-surface = false
"""

FASTFETCH_CONF = """{
    "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
    "logo": {
        "source": "/usr/share/osiris/logo.txt",
        "type": "file-raw",
        "padding": { "top": 1, "right": 3 }
    },
    "display": { "separator": "  " },
    "modules": [
        "break",
        { "type": "title", "format": "{user-name}@{host-name}" },
        "separator",
        { "type": "os", "key": "os" },
        { "type": "kernel", "key": "kernel" },
        { "type": "de", "key": "desktop" },
        { "type": "wm", "key": "wm" },
        { "type": "terminal", "key": "terminal" },
        { "type": "shell", "key": "shell" },
        { "type": "packages", "key": "packages" },
        { "type": "memory", "key": "memory" },
        { "type": "uptime", "key": "uptime" },
        "break",
        { "type": "colors", "symbol": "circle" }
    ]
}
"""


def write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
    print(f"  wrote {path}")


def desktop_users() -> list[pwd.struct_passwd]:
    return homes.desktop_users()


def install_oh_my_zsh(offline: bool) -> None:
    if offline:
        print("  skipping oh-my-zsh clone (--offline)")
        return
    if os.path.isdir(os.path.join(OMZ_DIR, ".git")):
        print(f"  {OMZ_DIR} already present")
        return
    print("installing oh-my-zsh")
    run("git", "clone", "--depth", "1", OMZ_REPO, OMZ_DIR)


def configure_shell() -> None:
    write("/etc/skel/.zshrc", ZSHRC)
    for user in desktop_users():
        target = f"{user.pw_dir}/.zshrc"
        if not os.path.exists(target):
            homes.copy("/etc/skel/.zshrc", target, user)
            print(f"  seeded {target}")
        # ZSH_CUSTOM points here, and zsh creates nothing itself.
        homes.makedirs(f"{user.pw_dir}/.config/osiris/zsh", user)
        if user.pw_shell != "/usr/bin/zsh":
            run("chsh", "-s", "/usr/bin/zsh", user.pw_name)


def configure_terminal() -> None:
    """Terminal config in /etc/skel and for existing users."""
    write("/etc/skel/.config/ghostty/config", GHOSTTY_CONF)
    for user in desktop_users():
        homes.copy("/etc/skel/.config/ghostty/config",
                   f"{user.pw_dir}/.config/ghostty/config", user)
        print(f"  configured ghostty for {user.pw_name}")


def configure_apps() -> None:
    write("/etc/skel/.config/fastfetch/config.jsonc", FASTFETCH_CONF)
    for user in desktop_users():
        for rel in (".config/fastfetch/config.jsonc",):
            homes.copy(f"/etc/skel/{rel}", f"{user.pw_dir}/{rel}", user)
        print(f"  configured terminal and fastfetch for {user.pw_name}")


def install_branding_assets(repo: str) -> None:
    """Put the logo somewhere every component can reference.

    fastfetch on Arch links no image libraries, so a PNG logo silently falls
    back to the stock Arch ASCII art. The text logo is what it actually uses;
    the PNG is kept for components that can render images.
    """
    os.makedirs(BRANDING_DIR, exist_ok=True)
    for name, dest in (("logo-dark.png", "logo.png"), ("logo.txt", "logo.txt")):
        src = os.path.join(repo, "branding", name)
        if not os.path.exists(src):
            print(f"  no {src}, skipping")
            continue
        shutil.copy(src, os.path.join(BRANDING_DIR, dest))
        print(f"  installed {BRANDING_DIR}/{dest}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true",
                        help="skip anything needing network")
    parser.add_argument("--repo", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))),
        help="path to the Osiris repo (for branding assets)")
    args = parser.parse_args()

    if os.geteuid() != 0:
        sys.exit("must run as root")

    install_branding_assets(args.repo)
    install_oh_my_zsh(args.offline)
    configure_shell()
    configure_terminal()
    configure_apps()
    print("APPS_CONFIGURED")


if __name__ == "__main__":
    main()
