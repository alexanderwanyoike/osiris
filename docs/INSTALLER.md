# The Osiris installer

How the ISO is built, how the installer works, and how to test both.

## Shape

The install is done by archinstall, Arch's official installer. Osiris supplies
the screens in front of it and the package installed by it. See
[ADR 0012](adr/0012-do-not-hand-roll-critical-machinery.md).

```
apps/installer/main.py              the GTK4 wizard
apps/installer/disks.py             which disks may be installed onto
apps/installer/network_page.py      the Connect to the internet step
apps/installer/slideshow.py         the slides on the progress page
apps/installer/slides/              those slides: slides.json and the pictures
osiris/provision/network.py         is the medium online; joining Wi-Fi with nmcli
osiris/model/wifi.py                Wi-Fi networks as nmcli lists them
osiris/provision/installer.py       detects the hardware, runs archinstall
osiris/provision/archinstall_outcome.py
                                    whether archinstall really installed anything
osiris/provision/install_progress.py
                                    how far the install has got, from its output
osiris/provision/archinstall_config.py
                                    the wizard's answers as an archinstall config
osiris/iso/package.py               what the `osiris` package contains and needs
provision/setup.py                  `osiris-setup`, run inside the new system
iso/repo.py                         builds the package and its repository
iso/live_packages.py                what the medium adds to archiso's releng
iso/live_session.py                 provisions the medium's live desktop, at build time
iso/profile.py                      generates the archiso profile, builds the ISO
```

An install, in order:

1. The wizard collects region, then checks the connection and, if the medium
   is offline, shows the connect step. Then disk, filesystem, encryption and
   account. Install checks the connection once more.
2. `Installer` reads the machine's GPUs and Bluetooth, and builds an
   archinstall configuration from archinstall's own objects. The password hash
   and any disk passphrase go in a separate credentials file under `/root`,
   readable by root only, and deleted when archinstall exits.
3. `archinstall --config --creds --silent --skip-wifi-check` partitions, encrypts if asked,
   formats, installs the base system, microcode and graphics drivers, creates
   the user, installs GRUB (UEFI or BIOS), PipeWire, NetworkManager, LightDM
   with slick-greeter, Plymouth and zram swap.
4. archinstall installs the `osiris` package from the repository on the medium.
   Its dependencies bring in Cinnamon, Plank, rofi, ghostty and the rest.
5. archinstall runs `osiris-setup` inside the new system. It applies what a
   package cannot ship as plain files: desktop defaults, themes, the boot
   splash, the GRUB theme. It also removes the medium's repository from the new
   system's pacman.conf, or every later update would fail on it.

## The internet connection

**An install needs the internet.** The medium carries only Osiris's own
packages, in its `file://` repository. archinstall downloads the base system,
the kernel, the drivers, Cinnamon and everything else from Arch's mirrors,
the ones in the medium's `/etc/pacman.d/mirrorlist` (Osiris sets no mirror
regions, so archinstall leaves that file alone).

**The connection is checked before anything is touched.** Leaving the welcome
page, and again when Install is pressed, `Network.online` sends a HEAD
request to the first mirror in that mirrorlist, for its `core.db`
(archlinux.org if the list names none). Any answer, even an error status,
counts as online; no answer at all does not. The check has a 10 second
timeout.

**Offline, the connect step comes first.** It says that Osiris downloads most
of the system while installing, and lists the Wi-Fi networks in range (name,
signal, open or secured), from
`nmcli -t -f IN-USE,SIGNAL,SECURITY,SSID device wifi list --rescan yes`. Each
name is listed once, the joined one first, then by signal. Hidden networks
are not listed. Continue stays unavailable, and so does everything after it,
until the check passes. A wired connection needs nothing: NetworkManager
brings it up when the cable goes in, and the step checks the connection
every 5 seconds while it is on screen. Check again rescans Wi-Fi as well.

- An open network is joined as soon as it is chosen, with
  `nmcli device wifi connect <ssid>`.
- A WPA1/WPA2 or WPA3 network asks for its password, then:

  ```
  nmcli connection delete id <ssid>
  nmcli connection add type wifi con-name <ssid> ssid <ssid> wifi-sec.key-mgmt wpa-psk|sae
  nmcli connection up id <ssid> passwd-file /root/osiris-install/wifi-password
  ```

  The password never goes on a command line, where any user on the medium
  could read it in `/proc/<pid>/cmdline`. It goes in a file readable by root
  alone, as `802-11-wireless-security.psk:<password>`, which is deleted as
  soon as `connection up` returns. `device wifi connect` has no such option,
  so the profile is made first, naming its key management itself: wpa-psk for
  WPA1, WPA2 and WPA2/WPA3 transition networks, sae for WPA3 alone. A
  refused password deletes the profile again and says so.
- Enterprise (802.1X) and WEP networks are listed but refused: they need
  settings this step does not ask for.

**archinstall's own Wi-Fi menu never runs.** Offline, archinstall 4.5 opens a
terminal menu built on wpa_supplicant, which nobody behind the GTK window
could see, on a medium that runs NetworkManager. `--skip-wifi-check` turns it
off.

**An install counts only if archinstall says it finished.** archinstall 4.5
exits 0 having installed nothing when it finds itself offline, and when it
rejects the bootloader layout in silent mode. So the install succeeds only if
archinstall exits 0 **and** its output contains `Installation completed
without any errors`, which its Installer prints only once every step it
tracks is done and the custom commands, `osiris-setup` among them, ran
without raising. `osiris-setup` prints `OSIRIS_SETUP_DONE` last, but that
line cannot be used: archinstall captures a custom command's output and
never prints it. Anything else fails the install with a reason:

| What archinstall printed | What the person is told |
|---|---|
| a download failure from archinstall, pacman or curl (`Failed to sync Arch Linux package database`, `failed retrieving file`, `Could not resolve host`, ...) | The connection dropped while Osiris was downloading. Check the network, then press Try again. |
| exit 0 without the completion line | archinstall stopped without installing anything. |
| any other non-zero exit | archinstall exited N before the install finished. |

The strings are in `osiris/provision/archinstall_outcome.py`, each from
archinstall's, libalpm's or libcurl's own source.

## The progress page

While archinstall runs, the page shows a slide at a time above a real
progress bar: the stage's title, "Step N of 7" and a percentage under the
bar. archinstall's raw output is behind **Show details**, collapsed. If the
install fails, the slides go, the log opens so the error is the first thing
seen, and Try again and Change settings appear as before.

**The stages come from archinstall's own output.** archinstall reports no
fraction complete, but it prints a line as it starts each part of the
install, and `Installer.install` hands every line it streams to
`install_progress.Tracker` through the runner's `on_line`. Each stage begins
at a line from archinstall 4.5's source:

| Stage | Begins at | Weight |
|---|---|---|
| Preparing your disk | the start: partitioning, formatting, mounting, the keyring wait | 3 |
| Installing the base system | `Installing packages: ['base', ...` | 22 |
| Setting up the bootloader | `Adding bootloader grub to <partition>` | 6 |
| Installing drivers and sound | `Creating user <name>` | 10 |
| Installing the desktop | `Installing packages: ['osiris']` | 45 |
| Applying Osiris | `Executing custom command "osiris-setup" ...` | 12 |
| Finishing | `Updating /mnt/etc/fstab` | 2 |

The user is created just before archinstall installs Bluetooth, PipeWire,
Xorg, the graphics driver and the greeter, and that line is the last before
them, so it starts the drivers stage. NetworkManager goes in with the
bootloader stage, and `Syncing the system...` with Finishing. A line that
starts an earlier stage than the current one is ignored.

**The fraction is weighted by time, not by stage.** Each stage owns its
weight's share of the bar (the weights are rough minutes, out of 100, on a
typical connection: the package installs are most of an install). Within a
stage, pacman's own counts move the bar. archinstall runs pacman on a pty, so
pacman draws its progress lines, and they reach the installer as:

```
 Total ( 4/20)           9.5 MiB  15.7 MiB/s 00:00 [#########-------------]  43%
( 5/20) installing glibc                           [######################] 100%
:: Running post-transaction hooks...
(1/3) Generating the configured locale...
```

A pacman run is taken as half downloading (`Total (n/N)`), four tenths
installing (`(n/N) installing`), and a tenth running hooks (the `(n/N)`
lines after `:: Running post-transaction hooks...`; before it they are
pacman's checks, which are not counted). A run starts at `:: Synchronizing
package databases...`. Where archinstall installs a few packages at a time,
the bootloader and drivers stages, each run fills half of what is left of
the stage, so every run moves the bar and none fills it; the number of runs
varies with the machine. The base system and the desktop are one run each,
which fills the stage. The bar never goes backwards, and a line that says
nothing about progress changes nothing. `osiris-setup`'s output is captured
by archinstall and never printed, so Applying Osiris holds still until the
fstab is written.

**The slides** are `apps/installer/slides/slides.json`, a list of pictures
and one sentence each, as data (ADR 0004). The pictures are links to
`docs/screenshots/`, so a new screenshot reaches the installer too. `docs/`
is not in the package, but `iso/repo.py` stages the payload with
`shutil.copytree`, which follows links by default, so the package, and the
medium that installs it, carry the files themselves; a test fails if that
ever changes. They crossfade every seven seconds while the page is on
screen.

## Building

```
python3 iso/repo.py            # as a normal user: makepkg refuses root
sudo python3 iso/profile.py
```

`iso/repo.py` builds the `osiris` package with makepkg and indexes it with
repo-add into `build/repo`, along with the packages Osiris bundles from pinned
PKGBUILDs in `iso/bundled/` because no official repository has them (Plank
Reloaded). `iso/profile.py` copies archiso's releng profile,
adds the `osiris` package, the installer and that repository, and runs
mkarchiso. It needs the `archiso` package, root and a network connection: it
clones oh-my-zsh for the live session (see below). Writes `build/out/osiris-<version>-x86_64.iso` and
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
few assignments appended, so compression and the rest keep tracking upstream.
The one boot mode it changes is UEFI's; see [the boot menu](#the-boot-menu).

**Osiris is a package.** It reaches a machine the way everything else on Arch
does. The PKGBUILD is generated from Python (`osiris/iso/package.py`) and holds
assignments and one copy - the project authors no bash.

**The medium boots into the live desktop.** It carries the `osiris` package,
the same one archinstall installs, and while the ISO is built a pacman hook
runs `iso/live_session.py` inside the live root the moment that package lands.
That runs `osiris-setup --live` - the install's own provisioning, minus the
GRUB theme and the initramfs, which the medium does not need - then creates a
passwordless `live` account that LightDM logs in. Every boot gets the desktop
an install produces, already provisioned. Install Osiris is pinned first on
the dock and sits on the desktop; it runs the installer through `pkexec`, with
a polkit action that lets the active session do so without a password.

The hook's `Exec=` is that Python program, as argv. releng's own last hook
deletes every hook marked "remove from airootfs" once the build's packages are
in, so it never runs again on the medium. It runs in a chroot without name
resolution, so `iso/profile.py` clones oh-my-zsh on the build host first.

The live session's network is NetworkManager, as on an installed system,
rather than releng's systemd-networkd and iwd. Its writes go to a tmpfs of up
to 4G, where archiso's default is 256M.

**The second entry boots the installer alone.** "Osiris installer only" starts
`osiris-installer.target` in place of the desktop, for a machine whose graphics
will not bring the desktop up. A systemd unit in that target runs:

```
xinit /usr/local/bin/osiris-installer --bare-x -- /usr/bin/X :0 vt1 -keeptty -nolisten tcp
```

xinit takes the client and then the server on argv, so a graphical session
starts with no shell and no login manager to configure. `--bare-x` has the
launcher give the empty screen an arrow pointer, which no window manager is
there to do. The unit is ordered after `plymouth-quit`, as LightDM's own is, so
X does not race the splash for the display.

**The medium shows the installed system's boot splash.** The theme files come
from `osiris/provision/plymouth.py`, the same source `provision/branding.py`
installs from, and go into the live root before archiso builds the initramfs,
with the `plymouth` hook after `udev` and `quiet splash` on the kernel line.
In QEMU the splash appears a few seconds after the menu: the initramfs takes
that long to load from a virtual CD, and the screen is black until then.

**The installer runs as root, all of it.** From the live desktop `pkexec`
starts it as root; there is no privilege boundary inside it. The alternative
is a polkit action per operation in the middle of a program whose entire
purpose is to repartition the disk, on a medium with nothing to protect and no
other user to protect it from.

## What the user chooses

| Step | Choices |
|---|---|
| Region | Language (locale), time zone, keyboard layout |
| Hardware | Software rendering, defaulted on inside a VM |
| Connect | Only when offline: a Wi-Fi network and its password, or a cable |
| Disk | Which disk, how (erase, free space, a partition), filesystem, encryption and its passphrase |
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

### Encryption

"Encrypt the system" on the disk page encrypts Osiris's root filesystem with
LUKS2, and the passphrase is asked for on the boot splash every time the
machine starts. Osiris writes no encryption code: it puts archinstall's own
`DiskEncryption` (type `luks`, the root partition only) into the
configuration, and archinstall does the rest:

- `cryptsetup luksFormat` (LUKS2, argon2id) on the root partition, then the
  filesystem inside it. btrfs keeps its subvolumes; they are inside the
  encrypted volume.
- the `encrypt` initramfs hook, with `plymouth` placed ahead of it, so the
  hook asks through Plymouth rather than on a bare console;
- `cryptdevice=UUID=<luks uuid>:root` in `GRUB_CMDLINE_LINUX`.
  `osiris-setup` merges its GRUB settings around that line, never over it
  (see `osiris/provision/grub_defaults.py`).

The passphrase must be at least 8 characters of printable ASCII. It is typed
at boot through the console keymap the initramfs carries, before any input
method exists, and characters outside ASCII are where that goes wrong. It
crosses to archinstall in the credentials file, the only place archinstall
reads it from; `config.json` never carries it, and the credentials file is
deleted when archinstall exits. A forgotten passphrase means the data is
gone: there is no recovery key, and the disk page says so.

The boot partition is never encrypted: GRUB reads the kernels from it, and
archinstall does not configure GRUB to unlock anything (it never sets
`GRUB_ENABLE_CRYPTODISK`). So encryption is offered only where Osiris has a
boot partition of its own:

| Layout | Encryption |
|---|---|
| Erase the disk | yes |
| Free space, no EFI system partition on the disk yet | yes: the new 1GB ESP is mounted at `/boot` and holds the kernels |
| Free space beside an existing ESP | refused |
| An existing partition | refused (this mode always shares an existing ESP) |

A shared ESP is mounted at `/efi` and carries only GRUB; the kernels stay in
`/boot` on the root. Encrypting that root would leave GRUB unable to read the
kernels, an unbootable machine. Making it work would mean setting up GRUB's
own LUKS unlocking (`GRUB_ENABLE_CRYPTODISK`, the cryptodisk modules in the
EFI image, and a second passphrase prompt or a keyfile in the initramfs),
none of which archinstall does. That is hand-rolling boot machinery, so the
combination is refused on the disk page, in `Layout.problems`, and again in
`archinstall_config.encryption`.

At boot the Osiris splash shows the hook's prompt under the logo, with an
asterisk per character typed; a wrong passphrase clears it and asks again.
The prompt is drawn by the Osiris Plymouth script theme
(`osiris/provision/plymouth.py`), which registers Plymouth's password callbacks: a
script theme without them draws no prompt at all, and the machine looks hung
at the logo. The keyboard layout at that prompt is the one chosen on the
first page.

archinstall formats the key slot with its default argon2id iteration time of
10 seconds, so a correct passphrase takes several seconds to open the disk on
the machine it was installed from. Osiris keeps that default.

### Retrying

A failed install offers **Try again** and **Change settings**, under the
reason (see [the internet connection](#the-internet-connection)). archinstall
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

### On the medium

The medium boots UEFI machines through archiso's `uefi.grub` mode rather than
releng's systemd-boot, and draws the same theme: `iso/profile.py` installs it
with `provision/grub.py`'s own `install_theme` and points releng's `grub.cfg`
at it (`osiris/iso/boot_menu.py`). Its shutdown and restart entries work on
any UEFI machine.

BIOS machines get syslinux, because archiso has no BIOS GRUB mode. It cannot
draw a GRUB theme, so it gets `branding/syslinux/splash.png` behind releng's
menu. releng's Reboot and Power Off entries are removed there: syslinux does
both through APM, which most firmware no longer has, and on such a machine they
do nothing.

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
