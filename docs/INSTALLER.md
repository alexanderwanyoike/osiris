# The Osiris installer

How the ISO is built, how the installer works, and how to test both.

## Shape

```
iso/live_packages.py       what goes on the live medium
iso/profile.py             generates an archiso profile, then builds the ISO
apps/installer/main.py     the GTK4 wizard
apps/installer/disks.py    which disks may be installed onto
provision/install.py       the install itself - partitioning through bootloader
```

The wizard contains no install logic. It fills in an `install.Options` and
calls `install.install(options, progress)`. The command line does the same
thing with the same function, so the two cannot drift apart.

## Building

```
sudo python3 iso/profile.py
```

Needs the `archiso` package and root, because mkarchiso mounts and chroots.
Writes `build/out/osiris-<version>-x86_64.iso` and leaves the generated profile
in `build/iso-profile` for inspection.

```
python3 iso/profile.py --generate-only     # write the profile, build nothing
python3 iso/profile.py --out /var/tmp/x    # build somewhere with room
```

Budget around 8GB of scratch space and a package download on first run.

## Testing

UEFI only, so the VM needs OVMF firmware:

```
qemu-system-x86_64 -enable-kvm -m 4096 -smp 4 \
    -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/x64/OVMF_CODE.4m.fd \
    -drive if=pflash,format=raw,file=OVMF_VARS.4m.fd \
    -cdrom build/out/osiris-0.1.0-x86_64.iso \
    -drive file=target.qcow2,if=virtio
```

A BIOS VM will not boot it, by design: Osiris installs GRUB in EFI mode, so a
BIOS machine would boot the installer and then install a system it could not
start.

## Decisions worth knowing

**archiso, not mkosi.** `docs/ARCHITECTURE.md` specified mkosi. mkosi has no
ISO output format - `Format=` accepts directory, tar, cpio, disk, uki, esp,
oci, sysext, confext, portable, addon and none. It builds bootable disk images,
not bootable removable media.

**The profile is generated, not checked in.** archiso requires
`profiledef.sh`, which is bash, and this project does not author bash. It holds
no logic - only variable assignments - so `iso/profile.py` emits it. The
artefact is bash; the source is Python. The other two things that used to need
bash do not any more: `customize_airootfs.sh` no longer exists in archiso, and
services are enabled with symlinks into `*.target.wants/`.

**No display manager on the ISO.** A systemd unit runs:

```
xinit /usr/local/bin/osiris-installer -- /usr/bin/X :0 vt1 -keeptty -nolisten tcp
```

xinit takes the client and then the server on argv, so a graphical session
starts with no shell and no login manager to configure.

**The installer runs as root.** The alternative is a polkit action and a
privilege boundary in the middle of a program whose entire purpose is to
repartition the disk, on a medium with nothing to protect and no other user to
protect it from.

**The install runs every provisioner, not just the desktop one.** For a while
it ran only `cinnamon.py`, which produced a working Cinnamon desktop with none
of Osiris on it: no themes, no Appearance app, no ghostty or zsh config, no
boot splash. `configure_desktop()` now copies `provision/`, `apps/`,
`branding/` and `shell/themes/` into the target and runs the same scripts a
development machine runs, in the same order.

## What the user chooses

| Step | Choices |
|---|---|
| Region | Language (locale), time zone, keyboard layout |
| Hardware | Software rendering, defaulted on inside a VM |
| Disk | Which disk, filesystem, swap size |
| Account | Computer name, username, password |
| Confirm | A summary, the destructive warning, and a gate |

### Software rendering

A switch on the first page, defaulted from `systemd-detect-virt`. A guest
usually has no GPU to accelerate anything and a desktop that tries comes up to
a black screen, so the common case is pre-selected rather than left as a trap.

### Disk layout

The whole disk, always: an EFI system partition of 1GB and one root filesystem.
Within that:

- **Filesystem** - ext4 or btrfs. btrfs is laid out with subvolumes `@` and
  `@home`, mounted `compress=zstd:1,noatime`, so the system can be snapshotted
  without taking the user's files with it. The bootloader entry gains
  `rootflags=subvol=@`; without it the kernel mounts the top-level volume and
  finds no init.
- **Swap** - a swap file, none to 16GB. On btrfs it goes on its own `@swap`
  subvolume, because a subvolume holding an active swap file cannot be
  snapshotted; keeping it off `@` keeps that limitation off the root. It is
  created with `btrfs filesystem mkswapfile`, which preallocates and marks the
  file NODATACOW in one step - a copy-on-write or compressed file cannot be
  swapped on at all.

The page shows the resulting plan as it changes, so the layout is visible
before it is committed to rather than described after.

### Retrying

A failed install offers **Try again** and **Change settings**. Retrying is safe
to offer because the install is written to be repeatable: it unmounts whatever a
previous attempt left behind before it touches the partition table. Most
failures are a dropped network or a mirror that went away mid-download, and
those succeed on a second run without changing anything.

## The boot menu

GRUB, not systemd-boot. systemd-boot has no theme engine at all - it draws a
text menu and offers no way to put anything on screen before Plymouth starts -
and a branded boot screen was wanted. The second reason is `os-prober`, which
finds other installed systems; systemd-boot never did.

The theme lives on the ESP at `/boot/grub/themes/osiris`, because GRUB reads it
long before any other filesystem is mounted. `provision/grub.py` installs it,
writes `/etc/default/grub` and runs `grub-install` and `grub-mkconfig`.

Assets are generated at build time by `branding/scripts/make-grub-theme.py`
from the `osiris-obsidian` palette and checked in. The bootloader cannot follow
the user's chosen theme - it runs before any user session exists - so it stays
branded, the same decision as the boot splash and the greeter.

Two things that are easy to get wrong:

- **Fonts must be GRUB's own `.pf2` format**, converted with `grub-mkfont`. The
  family name baked in with `-n` is what `theme.txt` refers to; if the two
  disagree GRUB falls back to a bitmap font without saying so.
- **9-slice pixmaps need all nine pieces** named `<prefix>_<c|n|s|e|w|nw|ne|sw|se>.png`.
  GRUB silently draws nothing if one is missing.

## Guardrails

The one unrecoverable mistake this program can make is writing to the wrong
disk, so:

- Disks under 16GB are listed and disabled, with the reason.
- Mounted disks are listed and disabled. A disk is never mounted itself - its
  partitions are - so the check recurses through children. Without that, the
  USB stick being booted from looks idle, and it is the one device that must
  not be offered.
- The confirm step names the disk, and the Install button stays disabled until
  an explicit checkbox naming that disk is ticked.
- The window refuses to close while an install is running.
- Partition device nodes are waited for rather than assumed. `partprobe`
  returns before udev has created them - measured at 1.7 seconds on a disk that
  already held a filesystem - and the `mount` that followed failed
  intermittently, which is the worst way for an installer to fail.
- Old filesystem signatures are wiped from the new partitions. Zapping the
  partition table leaves them in place, where tools that read a signature
  before writing will still find them.

## Writing into a user's home

Provisioning runs as root, before anyone has logged in, so every directory it
creates under a home belongs to root unless it is handed back explicitly.

`provision/homes.py` exists because getting that subtly wrong is easy and the
consequences are not subtle. An earlier version created
`~/.config/ghostty` and chowned the file and `.config/ghostty` - but not
`.config`, which the same call had just created. Every fresh install produced a
user who could not write to their own `~/.config`: no theme could be applied,
no terminal or launcher configuration saved, and the symptom surfaced much
later as an unrelated permission error.

It never appeared in development, because there the account had already logged
in and `.config` existed before provisioning ran.

Create directories with `homes.makedirs` and write with `homes.write` or
`homes.copy`. `homes.chown_tree` covers an existing tree *including its root*,
which `os.walk` reports as a parent rather than an entry - the other half of
the same bug.

## Not in this phase

- **Disk encryption.** LUKS changes the boot path substantially and deserves
  testing proportional to the cost of getting it wrong.
- **Installing alongside an existing system.** Osiris takes the whole disk.
- **BIOS machines**, deliberately: Osiris installs GRUB in EFI mode, so a BIOS
  machine would boot the installer and then install a system it could not
  start.
