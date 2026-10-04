# The Osiris installer

How the ISO is built, how the installer works, and how to test both.

## Shape

The install is done by archinstall, Arch's official installer. Osiris supplies
the screens in front of it and the package installed by it. See
[ADR 0012](adr/0012-do-not-hand-roll-critical-machinery.md).

```
apps/installer/main.py              the GTK4 wizard
apps/installer/disks.py             which disks may be installed onto
osiris/provision/installer.py       detects the hardware, runs archinstall
osiris/provision/archinstall_config.py
                                    the wizard's answers as an archinstall config
osiris/iso/package.py               what the `osiris` package contains and needs
provision/setup.py                  `osiris-setup`, run inside the new system
iso/repo.py                         builds the package and its repository
iso/live_packages.py                what the medium adds to archiso's releng
iso/profile.py                      generates the archiso profile, builds the ISO
```

An install, in order:

1. The wizard collects region, disk, filesystem and account.
2. `Installer` reads the machine's GPUs and Bluetooth, and builds an
   archinstall configuration from archinstall's own objects. The password goes
   in a separate credentials file under `/root`, readable by root only, and is
   deleted when archinstall exits.
3. `archinstall --config --creds --silent` partitions, formats, installs the
   base system, microcode and graphics drivers, creates the user, installs
   GRUB (UEFI or BIOS), PipeWire, NetworkManager, LightDM with slick-greeter,
   Plymouth and zram swap.
4. archinstall installs the `osiris` package from the repository on the medium.
   Its dependencies bring in Cinnamon, Plank, rofi, ghostty and the rest.
5. archinstall runs `osiris-setup` inside the new system. It applies what a
   package cannot ship as plain files: desktop defaults, themes, the boot
   splash, the GRUB theme. It also removes the medium's repository from the new
   system's pacman.conf, or every later update would fail on it.

## Building

```
python3 iso/repo.py            # as a normal user: makepkg refuses root
sudo python3 iso/profile.py
```

`iso/repo.py` builds the `osiris` package with makepkg and indexes it with
repo-add into `build/repo`. `iso/profile.py` copies archiso's releng profile,
adds the installer and that repository, and runs mkarchiso. It needs the
`archiso` package and root. Writes `build/out/osiris-<version>-x86_64.iso` and
leaves the generated profile in `build/iso-profile`.

```
python3 iso/profile.py --generate-only     # write the profile, build nothing
python3 iso/profile.py --out /var/tmp/x    # build somewhere with room
```

## Testing

The medium boots on BIOS and UEFI, because releng does, and archinstall
installs GRUB for whichever the machine booted with. Test both:

```
qemu-system-x86_64 -enable-kvm -m 4096 -smp 4 \
    -cdrom build/out/osiris-0.1.0-x86_64.iso \
    -drive file=target.qcow2,if=virtio

# and with UEFI firmware
    -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/x64/OVMF_CODE.4m.fd \
    -drive if=pflash,format=raw,file=OVMF_VARS.4m.fd \
```

archinstall's own log is in `/var/log/archinstall/install.log` on the medium.

## Decisions worth knowing

**archinstall does the install.** The hand-written install this replaced had
no microcode, no graphics drivers, no BIOS support and a partitioning race
that took a day to find. archinstall had solved all of it. Osiris now writes
no partitioning, package installation or bootloader code.

**The configuration is built with archinstall's objects, not written as
JSON.** `archinstall_config.build` returns an `ArchConfig`, and archinstall's
own serialiser writes it. The tests read every configuration back through
archinstall's parser, the code path `archinstall --config` takes.

**The medium is releng.** Arch's own install medium, copied and added to
rather than reimplemented: it boots on BIOS and UEFI, and carries archinstall
and the disk tools already. `profiledef.sh` keeps upstream's contents with a
few assignments appended, so boot modes and compression keep tracking upstream.

**Osiris is a package.** It reaches a machine the way everything else on Arch
does. The PKGBUILD is generated from Python (`osiris/iso/package.py`) and holds
assignments and one copy - the project authors no bash.

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

## What the user chooses

| Step | Choices |
|---|---|
| Region | Language (locale), time zone, keyboard layout |
| Hardware | Software rendering, defaulted on inside a VM |
| Disk | Which disk, how (erase, free space, a partition), filesystem |
| Account | Computer name, username, password |
| Confirm | A summary, the destructive warning, and a gate |

The account is a sudoer and root is locked, as on Mint and Ubuntu.

### Graphics

Detected, not chosen. Turing and newer NVIDIA cards get the open kernel
modules; older NVIDIA cards get nouveau, because their proprietary driver is
AUR-only now. AMD and Intel get their open drivers, and hybrid laptops get
both. Software rendering forces the all-open-source set, whose mesa renders in
software where no driver works.

### Disk layout

Three ways onto a disk, and the page offers only the ones that fit:

- **Erase the disk.** archinstall's default layout: a 1GB boot partition and
  one root filesystem.
- **Install in free space.** The root is created in the largest unallocated
  region. Nothing that exists is touched.
- **Install on a partition.** The chosen partition is formatted as the root.
  Nothing else is touched.

The root is ext4, or btrfs with archinstall's default subvolumes (`@`,
`@home`, `@log`, `@pkg`) and compression. Swap is zram, compressed RAM, so
there is no swap file or partition to size.

**Making room** is GParted's job, opened from a button on the disk page. Osiris
never shrinks a partition itself (see `osiris/model/layout.py`). When GParted
closes, the disks are read again.

**Installing beside another system needs UEFI and a GPT disk.** Osiris shares
the existing EFI system partition rather than touching anything else's boot
code. That partition is mounted at `/efi`, never formatted, and receives only
GRUB's files (a few MB, theme included); the kernels stay on Osiris's own
root, so a 100MB ESP made by Windows does not fill up. The removable fallback
loader, `/EFI/BOOT/BOOTX64.EFI`, is not written on a shared ESP, because it
belongs to whichever system put it there. If the disk has no ESP, a new 1GB
one is created in the free space.

The disk is read through archinstall: its device handler for partitions, and
the free-space logic of its own partitioning screen, so the installer offers
exactly the space archinstall will accept. The layout goes to archinstall as a
manual layout listing every existing partition as it is. It is read and
checked again immediately before archinstall runs, since the disk may have
changed after the page was drawn.

Known limits: archinstall always names the boot entry `GRUB`, so a second
archinstall-made system on the same ESP shares that entry and the boot menu,
which os-prober populates with the other system. os-prober identifies an
Osiris install as "Arch Linux", because Osiris does not brand `/etc/os-release`.

### Retrying

A failed install offers **Try again** and **Change settings**. archinstall
unmounts whatever a previous attempt left mounted on the disk before it
repartitions, so a second run starts clean.

## The boot menu

GRUB, installed by archinstall. `provision/grub.py` only themes it: it copies
the theme to `/boot/grub/themes/osiris`, merges Osiris's settings into
`/etc/default/grub` and regenerates the menu. It merges rather than overwrites
because archinstall writes the kernel command line into that file - the root
device, the subvolume, and on an encrypted install what is needed to unlock it.

Assets are generated at build time by `branding/scripts/make-grub-theme.py`
from the `osiris-obsidian` palette and checked in. Two things that are easy to
get wrong:

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

## Writing into a user's home

Provisioning runs as root, so every directory it creates under a home belongs
to root unless it is handed back explicitly. `provision/homes.py` exists
because getting that subtly wrong produced, on every fresh install, a user who
could not write to their own `~/.config`. Create directories with
`homes.makedirs` and write with `homes.write` or `homes.copy`.
