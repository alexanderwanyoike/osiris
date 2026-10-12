"""Build the Osiris live ISO.

    python3 iso/repo.py                         # first, as a normal user
    sudo python3 iso/profile.py                 # generate the profile and build
    python3 iso/profile.py --generate-only      # just write build/iso-profile

The medium is archiso's releng profile - the official Arch install medium -
with Osiris added on top. releng is maintained by Arch, boots on BIOS and UEFI,
and already carries archinstall, which does the install (ADR 0012). This copies
it and adds: the `osiris` package, provisioned at build time into a live
desktop that logs itself in; the installer, launched from that desktop or, from
a second boot entry, on bare X; and the local repository holding the package,
which archinstall installs from. Everything else is upstream's, unchanged.

Must run as root - mkarchiso mounts and chroots - and needs the `archiso`
package. The repository comes from iso/repo.py, which runs first and as a
normal user, because makepkg refuses root.

Why archiso and not mkosi: mkosi has no ISO output format.
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "provision"))
sys.path.insert(0, HERE)
sys.path.insert(0, REPO)

import apps  # noqa: E402
import grub  # noqa: E402
import live_packages  # noqa: E402
from osiris.iso import boot_menu, package  # noqa: E402
from osiris.provision import plymouth  # noqa: E402
from run import run, stream  # noqa: E402

RELENG = "/usr/share/archiso/configs/releng"

# Where things go on the medium.
REPOSITORY_DIR = "/usr/share/osiris/repo"
MEDIUM_GRUB_THEME = "/boot/grub/themes/osiris"
LAUNCHER_PATH = "/usr/local/bin/osiris-installer"
LIVE_SETUP_PATH = "/usr/local/bin/osiris-live-setup"
INSTALLER_TARGET = "osiris-installer.target"
SUDOERS_PATH = "/etc/sudoers.d/osiris-live"


def profiledef_overrides(version: str) -> str:
    """Assignments appended to releng's profiledef.sh.

    Appended rather than rewritten, so every setting Osiris does not care
    about - compression, permissions on upstream's own files -
    keeps tracking upstream. The later assignment wins in bash. These are
    assignments only, no logic: the project authors no bash.
    """
    return (
        "\n"
        "# Osiris, appended by iso/profile.py.\n"
        'iso_name="osiris"\n'
        f'iso_label="OSIRIS_{version.replace(".", "")}"\n'
        'iso_publisher="Osiris"\n'
        'iso_application="Osiris install medium"\n'
        f'iso_version="{version}"\n'
        'install_dir="osiris"\n'
        # GRUB rather than releng's systemd-boot on UEFI, because only GRUB
        # draws a theme. BIOS stays on syslinux: archiso has no BIOS GRUB mode.
        "bootmodes=('bios.syslinux' 'uefi.grub')\n"
        f'kernel_params_x86_64="quiet splash {plymouth.QUIET}"\n'
        f'file_permissions+=(["{LAUNCHER_PATH}"]="0:0:755")\n'
        f'file_permissions+=(["{LIVE_SETUP_PATH}"]="0:0:755")\n'
        'file_permissions+=(["/etc/sudoers.d"]="0:0:750")\n'
        f'file_permissions+=(["{SUDOERS_PATH}"]="0:0:440")\n'
    )


# xinit takes the client and then the server on argv, so a graphical session
# starts here without a shell or a display manager. Conflicts with getty@tty1
# so the two do not fight over the console; the other consoles keep releng's
# root login for rescue work. After plymouth-quit, as LightDM's own unit is, so
# X does not race the splash for the display.
INSTALLER_SERVICE = f"""[Unit]
Description=Osiris installer
After=systemd-user-sessions.service plymouth-quit.service
Conflicts=getty@tty1.service
After=getty@tty1.service

[Service]
Type=simple
ExecStart=/usr/bin/xinit {LAUNCHER_PATH} -- /usr/bin/X :0 vt1 -keeptty -nolisten tcp
Restart=on-failure
RestartSec=2
TTYPath=/dev/tty1
StandardInput=tty
StandardOutput=journal
StandardError=journal

[Install]
WantedBy={INSTALLER_TARGET}
"""

# What the installer-only boot entry starts in place of the live desktop.
INSTALLER_TARGET_UNIT = """[Unit]
Description=Osiris installer, without the live desktop
Requires=multi-user.target
After=multi-user.target
AllowIsolate=yes
"""

# "remove from airootfs" is what releng's own last hook looks for: it deletes
# every hook so marked once the build's package installation is done, so this
# one does not run again inside the live system.
LIVE_HOOK = f"""# remove from airootfs!
[Trigger]
Operation = Install
Type = Package
Target = {package.NAME}

[Action]
Description = Provisioning the Osiris live session...
When = PostTransaction
Exec = {LIVE_SETUP_PATH}
"""

LIVE_AUTOLOGIN = """[Seat:*]
autologin-user=live
autologin-session=cinnamon
"""

# A live medium has nothing to protect and nobody to protect it from; the same
# reasoning that runs the installer as root.
LIVE_SUDOERS = "live ALL=(ALL:ALL) NOPASSWD: ALL\n"

LAUNCHER = f"""#!/usr/bin/env python3
import runpy
import sys

sys.argv[0] = "osiris-installer"
runpy.run_path("{package.SOURCE_DIR}/apps/installer/main.py", run_name="__main__")
"""


def write(path: str, text: str, mode: int | None = None) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
    if mode is not None:
        os.chmod(path, mode)


def rebrand(out: str) -> None:
    """Apply osiris/iso/boot_menu.py to each of releng's menu files."""
    for directory in boot_menu.CONFIG_DIRS:
        for parent, _dirs, files in os.walk(os.path.join(out, directory)):
            for name in files:
                if not name.endswith(boot_menu.CONFIG_SUFFIXES):
                    continue
                path = os.path.join(parent, name)
                with open(path) as fh:
                    text = fh.read()
                branded = boot_menu.rebranded(text)
                if branded != text:
                    write(path, branded)


def theme_boot_menu(out: str) -> None:
    """The installed system's GRUB theme on the UEFI menu, its backdrop on BIOS.

    mkarchiso copies everything in the profile's grub/ that is not a .cfg to
    /boot/grub on the medium.
    """
    theme = os.path.join(out, "grub", "themes", "osiris")
    grub.install_theme(os.path.join(REPO, "branding", "grub"), theme)
    fonts = sorted({grub.font_file(name, size) for name, size, _ in grub.FONTS})
    missing = [name for name in fonts
               if not os.path.exists(os.path.join(theme, name))]
    if missing:
        sys.exit(f"grub-mkfont made no {', '.join(missing)}; the build host "
                 "needs grub, freetype2, noto-fonts and ttf-firacode-nerd")
    config = os.path.join(out, "grub", "grub.cfg")
    with open(config) as fh:
        text = fh.read()
    write(config, boot_menu.themed(text, MEDIUM_GRUB_THEME, fonts))

    shutil.copy(os.path.join(REPO, "branding", "syslinux", "splash.png"),
                os.path.join(out, "syslinux", "splash.png"))


def install_splash(out: str) -> None:
    """The installed system's boot splash, in the medium's initramfs.

    mkarchiso lays airootfs down before it installs packages, so these are in
    place when the kernel's install hook first builds the initramfs. That build
    reads the theme from plymouthd.conf, which plymouth-set-default-theme would
    write on an installed system.
    """
    root = os.path.join(out, "airootfs")
    theme = os.path.join(root, plymouth.THEME_DIR.lstrip("/"))
    write(os.path.join(theme, f"{plymouth.THEME}.plymouth"), plymouth.THEME_FILE)
    write(os.path.join(theme, f"{plymouth.THEME}.script"), plymouth.SCRIPT)
    shutil.copy(os.path.join(REPO, "branding", "logo-splash.png"),
                os.path.join(theme, "logo.png"))
    write(os.path.join(root, "etc/plymouth/plymouthd.conf"),
          f"[Daemon]\nTheme={plymouth.THEME}\n")

    hooks = os.path.join(root, "etc/mkinitcpio.conf.d/archiso.conf")
    with open(hooks) as fh:
        text = fh.read()
    with_splash = plymouth.with_hook(text)
    if not plymouth.has_hook(with_splash):
        sys.exit(f"no udev hook in {hooks} to put the splash after")
    write(hooks, with_splash)


# releng manages the network with systemd-networkd and iwd. The installed
# system, its Cinnamon network applet and osiris-setup all expect
# NetworkManager, and two managers on one interface fight over it.
NETWORKD_LINKS = (
    "multi-user.target.wants/systemd-networkd.service",
    "multi-user.target.wants/iwd.service",
    "sockets.target.wants/systemd-networkd.socket",
    "network-online.target.wants/systemd-networkd-wait-online.service",
    "dbus-org.freedesktop.network1.service",
)
NETWORKMANAGER_LINKS = {
    "multi-user.target.wants/NetworkManager.service": "NetworkManager.service",
    "network-online.target.wants/NetworkManager-wait-online.service":
        "NetworkManager-wait-online.service",
    "dbus-org.freedesktop.nm-dispatcher.service":
        "NetworkManager-dispatcher.service",
}


def use_networkmanager(out: str) -> None:
    """Swap releng's network services for NetworkManager, as symlinks for the
    same reason the installer's unit is enabled with one."""
    units = os.path.join(out, "airootfs/etc/systemd/system")
    for link in NETWORKD_LINKS:
        os.remove(os.path.join(units, link))
    for link, unit in NETWORKMANAGER_LINKS.items():
        path = os.path.join(units, link)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        os.symlink(f"/usr/lib/systemd/system/{unit}", path)


def add_installer_entries(out: str) -> None:
    """The installer-only entry, second on each menu; see boot_menu."""
    config = os.path.join(out, "grub", "grub.cfg")
    with open(config) as fh:
        text = fh.read()
    write(config, boot_menu.grub_with_installer_entry(text, INSTALLER_TARGET))
    config = os.path.join(out, "syslinux", "archiso_sys-linux.cfg")
    with open(config) as fh:
        text = fh.read()
    write(config, boot_menu.syslinux_with_installer_entry(text, INSTALLER_TARGET))


def add_local_repository(out: str, repository: str) -> None:
    """Let the build install the `osiris` package from iso/repo.py's output.

    mkarchiso reads the profile's pacman.conf to install packages and leaves
    the live system with pacman's own, so the repository is not configured on
    the medium afterwards.
    """
    with open(os.path.join(out, "pacman.conf"), "a") as fh:
        fh.write(f"\n[{package.NAME}]\n"
                 "SigLevel = Optional TrustAll\n"
                 f"Server = file://{os.path.abspath(repository)}\n")


def add_live_session(out: str) -> None:
    """The build-time hook that provisions the live desktop, and its login.

    oh-my-zsh is cloned here, on the build host: the hook runs in a chroot
    without name resolution, and apps.py skips the clone when it finds one.
    """
    root = os.path.join(out, "airootfs")
    write(os.path.join(root, "etc/pacman.d/hooks/80-osiris-live.hook"), LIVE_HOOK)
    shutil.copy(os.path.join(HERE, "live_session.py"),
                os.path.join(root, LIVE_SETUP_PATH.lstrip("/")))
    write(os.path.join(root, "etc/lightdm/lightdm.conf.d/60-osiris-live.conf"),
          LIVE_AUTOLOGIN)
    write(os.path.join(root, SUDOERS_PATH.lstrip("/")), LIVE_SUDOERS)
    run("git", "clone", "--depth", "1", apps.OMZ_REPO,
        os.path.join(root, apps.OMZ_DIR.lstrip("/")))


def drop_apm_entries(out: str) -> None:
    """Remove the BIOS menu's Reboot and Power Off; see boot_menu.APM_MODULES."""
    tail = os.path.join(out, "syslinux", "archiso_tail.cfg")
    with open(tail) as fh:
        text = fh.read()
    write(tail, boot_menu.without_apm_entries(text))


def generate(out: str, version: str, repository: str,
             releng: str = RELENG) -> str:
    """Write a complete archiso profile to `out`. Returns the path."""
    if not os.path.isdir(releng):
        raise FileNotFoundError(
            f"{releng} not found - install the 'archiso' package")
    if not os.path.exists(os.path.join(repository, "osiris.db")):
        raise FileNotFoundError(
            f"no osiris repository in {repository} - run iso/repo.py first")
    if os.path.isdir(out):
        shutil.rmtree(out)
    shutil.copytree(releng, out, symlinks=True)

    with open(os.path.join(out, "profiledef.sh"), "a") as fh:
        fh.write(profiledef_overrides(version))
    add_local_repository(out, repository)

    packages_file = os.path.join(out, "packages.x86_64")
    with open(packages_file) as fh:
        upstream = fh.read().rstrip("\n").splitlines()
    present = {line.strip() for line in upstream}
    added = [name for name in live_packages.additions() if name not in present]
    write(packages_file, "\n".join([*upstream, "", "# Osiris", *added]) + "\n")

    rebrand(out)
    theme_boot_menu(out)
    drop_apm_entries(out)
    install_splash(out)
    use_networkmanager(out)
    add_installer_entries(out)
    add_live_session(out)

    root = os.path.join(out, "airootfs")
    write(os.path.join(root, "etc/systemd/system/osiris-installer.service"),
          INSTALLER_SERVICE)
    write(os.path.join(root, f"etc/systemd/system/{INSTALLER_TARGET}"),
          INSTALLER_TARGET_UNIT)
    write(os.path.join(root, LAUNCHER_PATH.lstrip("/")), LAUNCHER, 0o755)
    # The unit lives in /etc, so its symlink points there rather than at
    # /usr/lib where packaged units live. Not systemctl: that would enable it
    # on the build host.
    wants = os.path.join(root, f"etc/systemd/system/{INSTALLER_TARGET}.wants")
    os.makedirs(wants, exist_ok=True)
    os.symlink("/etc/systemd/system/osiris-installer.service",
               os.path.join(wants, "osiris-installer.service"))

    # repo-add makes osiris.db a symlink to the tarball; pacman reads both.
    shutil.copytree(repository, os.path.join(root, REPOSITORY_DIR.lstrip("/")),
                    symlinks=True)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=os.path.join(REPO, "build"),
                        help="build directory (default: <repo>/build)")
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--repository",
                        help="the osiris repository (default: <out>/repo)")
    parser.add_argument("--releng", default=RELENG,
                        help="archiso's releng profile to start from")
    parser.add_argument("--generate-only", action="store_true",
                        help="write the profile but do not build")
    args = parser.parse_args()

    repository = args.repository or os.path.join(args.out, "repo")
    profile = generate(os.path.join(args.out, "iso-profile"), args.version,
                       repository, args.releng)
    print(f"profile: {profile}")
    if args.generate_only:
        return

    if os.geteuid() != 0:
        sys.exit("mkarchiso must run as root")
    if shutil.which("mkarchiso") is None:
        sys.exit("mkarchiso not found - install the 'archiso' package")

    work = os.path.join(args.out, "work")
    output = os.path.join(args.out, "out")
    os.makedirs(output, exist_ok=True)
    stream("mkarchiso", "-v", "-w", work, "-o", output, profile)

    images = sorted(f for f in os.listdir(output) if f.endswith(".iso"))
    for name in images:
        path = os.path.join(output, name)
        print(f"  {path}  ({os.path.getsize(path) / 1e9:.2f} GB)")
    print("ISO_BUILT")


if __name__ == "__main__":
    main()
