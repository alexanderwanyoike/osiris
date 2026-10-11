"""Build the Osiris live ISO.

    python3 iso/repo.py                         # first, as a normal user
    sudo python3 iso/profile.py                 # generate the profile and build
    python3 iso/profile.py --generate-only      # just write build/iso-profile

The medium is archiso's releng profile - the official Arch install medium -
with the Osiris installer added on top. releng is maintained by Arch, boots on
BIOS and UEFI, and already carries archinstall, which does the install (ADR
0012). This copies it and adds: the installer and the X session it runs in,
the provisioning tree, and the local repository holding the `osiris` package,
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

import live_packages  # noqa: E402
from osiris.iso import boot_menu  # noqa: E402
from run import stream  # noqa: E402

RELENG = "/usr/share/archiso/configs/releng"

# Where things go on the medium.
PAYLOAD = ("osiris", "provision", "apps", "branding", "shell/themes")
PAYLOAD_DIR = "/usr/share/osiris/source"
REPOSITORY_DIR = "/usr/share/osiris/repo"
LAUNCHER_PATH = "/usr/local/bin/osiris-installer"


def profiledef_overrides(version: str) -> str:
    """Assignments appended to releng's profiledef.sh.

    Appended rather than rewritten, so every setting Osiris does not care
    about - boot modes, compression, permissions on upstream's own files -
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
        f'file_permissions+=(["{LAUNCHER_PATH}"]="0:0:755")\n'
    )


# xinit takes the client and then the server on argv, so a graphical session
# starts here without a shell or a display manager. Conflicts with getty@tty1
# so the two do not fight over the console; the other consoles keep releng's
# root login for rescue work.
INSTALLER_SERVICE = f"""[Unit]
Description=Osiris installer
After=systemd-user-sessions.service
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
WantedBy=multi-user.target
"""

LAUNCHER = f"""#!/usr/bin/env python3
import runpy
import sys

sys.argv[0] = "osiris-installer"
runpy.run_path("{PAYLOAD_DIR}/apps/installer/main.py", run_name="__main__")
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

    packages_file = os.path.join(out, "packages.x86_64")
    with open(packages_file) as fh:
        upstream = fh.read().rstrip("\n").splitlines()
    present = {line.strip() for line in upstream}
    added = [name for name in live_packages.additions() if name not in present]
    write(packages_file, "\n".join([*upstream, "", "# Osiris", *added]) + "\n")

    rebrand(out)

    root = os.path.join(out, "airootfs")
    write(os.path.join(root, "etc/systemd/system/osiris-installer.service"),
          INSTALLER_SERVICE)
    write(os.path.join(root, LAUNCHER_PATH.lstrip("/")), LAUNCHER, 0o755)
    # The unit lives in /etc, so its symlink points there rather than at
    # /usr/lib where packaged units live. Not systemctl: that would enable it
    # on the build host.
    wants = os.path.join(root, "etc/systemd/system/multi-user.target.wants")
    os.makedirs(wants, exist_ok=True)
    os.symlink("/etc/systemd/system/osiris-installer.service",
               os.path.join(wants, "osiris-installer.service"))

    payload = os.path.join(root, PAYLOAD_DIR.lstrip("/"))
    for relative in PAYLOAD:
        source = os.path.join(REPO, relative)
        if not os.path.isdir(source):
            raise FileNotFoundError(f"missing {source}")
        shutil.copytree(source, os.path.join(payload, relative),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
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
