"""Install Osiris onto a disk from the live ISO.

    python3 provision/install.py --disk /dev/vda --hostname osiris --user alexander

Destroys everything on --disk. UEFI only: Osiris uses systemd-boot.

This is the install flow, and the only one. `install()` takes an Options and a
progress callback; the command line and the graphical installer are both thin
callers of it. apps/installer/ imports this module rather than shelling out to
it, so a failure arrives as an exception with a traceback instead of a non-zero
exit code and some text to parse.
"""
import argparse
import dataclasses
import getpass
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import packages  # noqa: E402
from run import capture, emit, run, stream  # noqa: E402

ESP_SIZE_MB = 1024
ESP_SIZE = f"+{ESP_SIZE_MB}M"


@dataclasses.dataclass
class Options:
    """Everything the install needs. The installer UI fills one of these in."""

    disk: str
    user: str
    password: str
    hostname: str = "osiris"
    timezone: str = "Europe/London"
    locale: str = "en_GB.UTF-8"
    keymap: str = "us"
    desktop: str = "cinnamon"
    filesystem: str = "ext4"          # ext4 or btrfs
    swap_mb: int = 0                  # 0 for none
    software_rendering: bool = False
    ssh_key: str | None = None
    virtiofs_tag: str | None = None

    def layout(self) -> list[str]:
        """The partition plan in words, for the installer to show."""
        plan = [f"{ESP_SIZE_MB} MB  EFI system partition (FAT32)",
                f"rest     Osiris root ({self.filesystem})"]
        if self.filesystem == "btrfs":
            plan.append("         subvolumes @ and @home"
                        + (", @swap" if self.swap_mb else ""))
        if self.swap_mb:
            plan.append(f"{self.swap_mb} MB  swap file")
        return plan


# Rough share of wall-clock each step takes, for an honest progress bar.
# pacstrap dominates; a bar that spends 90% of its life on one step is not
# lying, and pretending otherwise just makes the last 10% feel broken.
STEPS = (
    ("partition", "Partitioning the disk", 0.02),
    ("format", "Creating filesystems", 0.03),
    ("packages", "Installing packages", 0.62),
    ("fstab", "Writing fstab", 0.01),
    ("configure", "Configuring the system", 0.14),
    ("desktop", "Setting up the desktop", 0.16),
    ("finish", "Finishing up", 0.02),
)


def wait_for_devices(*paths: str, timeout: float = 15.0) -> None:
    """Block until the kernel and udev have published these device nodes.

    `partprobe` asks the kernel to re-read the partition table and returns
    immediately; the nodes appear when udev gets round to it. On a disk that
    already held a filesystem this took 1.7 seconds here, and the `mount` that
    followed failed against a device that did not exist yet - intermittently,
    which is the worst way for an installer to fail.
    """
    run("udevadm", "settle", check=False, quiet=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if all(os.path.exists(path) for path in paths):
            return
        time.sleep(0.2)
    missing = [path for path in paths if not os.path.exists(path)]
    raise FileNotFoundError(
        f"partitions did not appear after {timeout:.0f}s: {', '.join(missing)}")


def partition(disk: str) -> tuple[str, str]:
    run("sgdisk", "--zap-all", disk)
    run("sgdisk", "-n", f"1:0:{ESP_SIZE}", "-t", "1:ef00", "-c", "1:EFI", disk)
    run("sgdisk", "-n", "2:0:0", "-t", "2:8300", "-c", "2:root", disk)
    run("partprobe", disk)
    # /dev/sda -> /dev/sda1 ; /dev/nvme0n1 -> /dev/nvme0n1p1
    sep = "p" if disk[-1].isdigit() else ""
    esp, root = f"{disk}{sep}1", f"{disk}{sep}2"
    wait_for_devices(esp, root)
    # Zapping the partition table leaves any old filesystem superblock sitting
    # inside the new partition, where blkid will still report it. mkfs forces
    # past it, but tools that read the signature first do not.
    for device in (esp, root):
        run("wipefs", "--all", device, check=False, quiet=True)
    return esp, root


def unmount_target() -> None:
    """Leave /mnt free, whatever state it is in.

    Used twice: before partitioning, because a failed attempt leaves the target
    mounted and the next one would fail at `mount` with a message about /mnt
    being busy that says nothing about what went wrong the first time; and at
    the end, to release the finished system.

    A busy target at the end is **not** an install failure. Everything is
    written by then, and arch-chroot routinely leaves a gpg-agent or a
    dbus-daemon holding the mountpoint for a few seconds after it returns.
    Reporting a complete install as failed because of that is worse than
    wrong - it tells the user to redo twenty minutes of work that succeeded.
    So: flush, try a plain unmount, and fall back to a lazy one.
    """
    if not os.path.ismount("/mnt"):
        return
    os.sync()
    emit("  $ umount -R /mnt")
    if subprocess.run(["umount", "-R", "/mnt"],
                      capture_output=True).returncode == 0:
        return
    emit("    busy; detaching lazily")
    subprocess.run(["umount", "-R", "-l", "/mnt"], capture_output=True)


# btrfs is mounted with compression and without access times. zstd:1 is the
# cheap end of the scale: it saves space on a package-heavy root without the
# write latency of the higher levels.
BTRFS_OPTIONS = "compress=zstd:1,noatime,ssd"

# Subvolumes, not directories. @ and @home so the system can be snapshotted
# without taking the user's files with it, and @swap because a subvolume
# holding an active swap file cannot be snapshotted at all - putting it on its
# own keeps that limitation off the root.
SUBVOLUMES = ("@", "@home", "@swap")


def format_and_mount(esp: str, root: str, options: Options) -> None:
    run("mkfs.fat", "-F32", "-n", "ESP", esp)
    if options.filesystem == "btrfs":
        run("mkfs.btrfs", "-f", "-L", "osiris", root)
        run("mount", root, "/mnt")
        for subvolume in SUBVOLUMES:
            if subvolume == "@swap" and not options.swap_mb:
                continue
            run("btrfs", "subvolume", "create", f"/mnt/{subvolume}")
        run("umount", "/mnt")
        run("mount", "-o", f"subvol=@,{BTRFS_OPTIONS}", root, "/mnt")
        os.makedirs("/mnt/home", exist_ok=True)
        run("mount", "-o", f"subvol=@home,{BTRFS_OPTIONS}", root, "/mnt/home")
        if options.swap_mb:
            os.makedirs("/mnt/swap", exist_ok=True)
            run("mount", "-o", "subvol=@swap,noatime", root, "/mnt/swap")
    else:
        run("mkfs.ext4", "-F", "-L", "osiris", root)
        run("mount", root, "/mnt")
    os.makedirs("/mnt/boot", exist_ok=True)
    run("mount", esp, "/mnt/boot")


def swap_path(options: Options) -> str:
    """Where the swap file goes, relative to the installed root."""
    return "/swap/swapfile" if options.filesystem == "btrfs" else "/swapfile"


def make_swap(options: Options) -> str | None:
    """Create the swap file. Returns its path inside the new system."""
    if not options.swap_mb:
        return None
    path = swap_path(options)
    target = "/mnt" + path
    if options.filesystem == "btrfs":
        # Preallocates and marks the file NODATACOW in one step, which is
        # required: a copy-on-write or compressed file cannot be swapped on.
        run("btrfs", "filesystem", "mkswapfile", "--size",
            f"{options.swap_mb}M", target)
    else:
        run("fallocate", "-l", f"{options.swap_mb}M", target)
        os.chmod(target, 0o600)
        run("mkswap", target)
    return path


def pacstrap(desktop: str, software_rendering: bool) -> None:
    stream("pacstrap", "-K", "/mnt",
           *packages.for_install(desktop, software_rendering))


def write_fstab(extra_mounts: list[str]) -> None:
    # genfstab writes to stdout; capture it here rather than shell-redirecting.
    fstab = subprocess.run(["genfstab", "-U", "/mnt"],
                           check=True, text=True, capture_output=True).stdout
    for line in extra_mounts:
        fstab += line + "\n"
    with open("/mnt/etc/fstab", "w") as fh:
        fh.write(fstab)


def in_chroot(*argv: str) -> None:
    run("arch-chroot", "/mnt", *argv)


def chpasswd(user: str, password: str) -> None:
    subprocess.run(["arch-chroot", "/mnt", "chpasswd"],
                   input=f"{user}:{password}\n", text=True, check=True)


def install_ssh_key(user: str, key_path: str) -> None:
    """Authorise a public key for root and the primary user."""
    with open(key_path) as fh:
        key = fh.read().strip()
    for home, owner in (("/root", "root"), (f"/home/{user}", user)):
        d = f"/mnt{home}/.ssh"
        os.makedirs(d, exist_ok=True)
        with open(f"{d}/authorized_keys", "w") as fh:
            fh.write(key + "\n")
        os.chmod(f"{d}/authorized_keys", 0o600)
        run("arch-chroot", "/mnt", "chown", "-R", f"{owner}:{owner}",
            f"{home}/.ssh")
    emit(f"  authorised {key_path} for root and {user}")


def configure(hostname: str, user: str, password: str, timezone: str,
              locale: str, root_dev: str, keymap: str = "us",
              filesystem: str = "ext4") -> None:
    in_chroot("ln", "-sf", f"/usr/share/zoneinfo/{timezone}", "/etc/localtime")
    in_chroot("hwclock", "--systohc")

    def put(path: str, text: str, mode: int | None = None) -> None:
        full = "/mnt" + path
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as fh:
            fh.write(text)
        if mode is not None:
            os.chmod(full, mode)

    put("/etc/locale.gen", f"{locale} UTF-8\n")
    in_chroot("locale-gen")
    put("/etc/locale.conf", f"LANG={locale}\n")
    # /etc/locale.conf alone does not reach a LightDM session, which leaves
    # LANG unset and LC_CTYPE=POSIX - UTF-8 then renders as replacement
    # characters everywhere. /etc/environment is read by pam_env for every
    # session type, graphical included.
    put("/etc/environment", f"LANG={locale}\nLC_ALL={locale}\n")
    put("/etc/vconsole.conf", f"KEYMAP={keymap}\n")
    put("/etc/hostname", f"{hostname}\n")
    put("/etc/hosts",
        f"127.0.0.1\tlocalhost\n::1\t\tlocalhost\n127.0.1.1\t{hostname}\n")
    put("/etc/sudoers.d/wheel", "%wheel ALL=(ALL:ALL) ALL\n", 0o440)

    in_chroot("mkinitcpio", "-P")

    chpasswd("root", password)
    in_chroot("useradd", "-m", "-G", "wheel,video,audio,input",
              "-s", "/bin/bash", user)
    chpasswd(user, password)

    in_chroot("bootctl", "install")
    uuid = capture("blkid", "-s", "UUID", "-o", "value", root_dev)
    put("/boot/loader/loader.conf",
        "default osiris.conf\ntimeout 1\nconsole-mode max\n")
    # btrfs puts the system on a subvolume, so the kernel has to be told which
    # one; without this it mounts the top-level volume and finds no /sbin/init.
    rootflags = " rootflags=subvol=@" if filesystem == "btrfs" else ""
    put("/boot/loader/entries/osiris.conf",
        "title   Osiris\n"
        "linux   /vmlinuz-linux\n"
        "initrd  /initramfs-linux.img\n"
        f"options root=UUID={uuid}{rootflags} rw\n")


def install(options: Options, progress=None) -> None:
    """Run the install. Raises on failure; never calls sys.exit.

    `progress(fraction, message)` is called before each step with the fraction
    already completed, so a caller can drive a progress bar without knowing
    what the steps are.
    """
    done = 0.0

    def step(key: str) -> None:
        nonlocal done
        label = next(l for k, l, _w in STEPS if k == key)
        if progress is not None:
            progress(done, label)
        done += next(w for k, _l, w in STEPS if k == key)

    if os.geteuid() != 0:
        raise PermissionError("the install must run as root")
    if not os.path.exists(options.disk):
        raise FileNotFoundError(f"no such disk: {options.disk}")

    step("partition")
    unmount_target()
    esp, root = partition(options.disk)

    step("format")
    format_and_mount(esp, root, options)

    step("packages")
    pacstrap(options.desktop, options.software_rendering)

    step("fstab")
    extra = []
    swap = make_swap(options)
    if swap:
        # genfstab does not see a swap file that is not switched on, and
        # switching it on inside the installer would then need switching off
        # again before the unmount. Simpler to write the line.
        extra.append(f"{swap} none swap defaults 0 0")
    if options.virtiofs_tag:
        mount = f"/home/{options.user}/osiris"
        extra.append(f"{options.virtiofs_tag} {mount} virtiofs rw,nofail 0 0")
    write_fstab(extra)

    step("configure")
    configure(options.hostname, options.user, options.password,
              options.timezone, options.locale, root, options.keymap,
              options.filesystem)
    if options.ssh_key:
        install_ssh_key(options.user, options.ssh_key)

    step("desktop")
    configure_desktop(options.desktop, options.software_rendering)

    step("finish")
    unmount_target()
    if progress is not None:
        progress(1.0, "Done")


# Everything the target needs to look like Osiris rather than like stock
# Cinnamon. Copied into the new system and run there, in this order.
PAYLOAD = ("provision", "apps", "branding", "shell/themes")
SETUP_DIR = "/root/osiris-setup"


def configure_desktop(desktop: str, software_rendering: bool) -> None:
    """Run the provisioning scripts inside the new system.

    For a long time this ran only the desktop configurator, which left an
    install with a working Cinnamon and none of Osiris: no themes, no
    Appearance app, no ghostty or zsh configuration, no boot splash. Those
    scripts are what make it this distribution, so the installer runs all of
    them - the same ones, in the same order, that a development machine runs.

    Each takes --repo and defaults it to the directory above its own, so the
    tree is copied with its original shape and they need no arguments.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(here)
    target = "/mnt" + SETUP_DIR

    if os.path.isdir(target):
        shutil.rmtree(target)
    for relative in PAYLOAD:
        source = os.path.join(repo, relative)
        if not os.path.isdir(source):
            continue
        destination = os.path.join(target, relative)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        # __pycache__ in the payload would be compiled for the build host's
        # Python, not the target's.
        shutil.copytree(source, destination,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    configurator = {"cosmic": "desktop.py", "cinnamon": "cinnamon.py"}[desktop]
    scripts = [configurator, "apps.py", "branding.py", "themes.py"]
    try:
        for script in scripts:
            if not os.path.exists(os.path.join(target, "provision", script)):
                continue
            argv = ["arch-chroot", "/mnt", "python3",
                    f"{SETUP_DIR}/provision/{script}"]
            if script == "desktop.py" and software_rendering:
                argv.append("--software-rendering")
            emit(f"  == {script} ==")
            stream(*argv)
    finally:
        shutil.rmtree(target, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disk", required=True, help="target disk, e.g. /dev/vda")
    parser.add_argument("--hostname", default="osiris")
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", help="prompted for if omitted")
    parser.add_argument("--timezone", default="Europe/London")
    parser.add_argument("--locale", default="en_GB.UTF-8")
    parser.add_argument("--keymap", default="us")
    parser.add_argument("--filesystem", default="ext4",
                        choices=("ext4", "btrfs"))
    parser.add_argument("--swap", type=int, default=0, metavar="MB",
                        help="size of the swap file in MB (0 for none)")
    parser.add_argument("--desktop", default="cinnamon",
                        choices=sorted(packages.DESKTOPS),
                        help="which desktop to install (default: cinnamon)")
    parser.add_argument("--software-rendering", action="store_true",
                        help="target has no GPU acceleration (e.g. a VM)")
    parser.add_argument("--ssh-key",
                        help="public key to authorise for root and the user")
    parser.add_argument("--virtiofs-tag",
                        help="mount a virtiofs share at /home/<user>/osiris")
    parser.add_argument("--yes", action="store_true",
                        help="skip the destructive-action confirmation")
    args = parser.parse_args()

    if os.geteuid() != 0:
        sys.exit("must run as root")
    if not os.path.exists(args.disk):
        sys.exit(f"no such disk: {args.disk}")
    if not args.yes:
        print(f"This ERASES {args.disk} completely.")
        if input("Type the disk path to confirm: ").strip() != args.disk:
            sys.exit("aborted")

    options = Options(
        disk=args.disk, user=args.user,
        password=args.password or getpass.getpass("password for root and user: "),
        hostname=args.hostname, timezone=args.timezone, locale=args.locale,
        keymap=args.keymap, desktop=args.desktop,
        filesystem=args.filesystem, swap_mb=args.swap,
        software_rendering=args.software_rendering,
        ssh_key=args.ssh_key, virtiofs_tag=args.virtiofs_tag)

    try:
        install(options, progress=lambda _f, message: print(f"== {message} =="))
    except (OSError, subprocess.CalledProcessError) as error:
        sys.exit(f"install failed: {error}")
    print("INSTALL_DONE")


if __name__ == "__main__":
    main()
