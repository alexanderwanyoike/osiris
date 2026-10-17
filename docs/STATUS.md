# Osiris work status

Living document. Update at the end of each working session so the next one can
pick up cold.

## Last update

**Date:** 2026-10-01
**Branch:** `v2`
**Phase:** Phases 1 and 2 complete. Phase 3 (polish) not started.

## What Osiris is now

A Cinnamon desktop on Arch, themed and branded, with a graphical installer on a
live ISO. Hyprland, AGS and greetd were removed; see
[ARCHITECTURE.md](ARCHITECTURE.md) for the current stack.

The project was previously framed as an AI-first distribution with a chat
harness as the primary interface. That framing is gone and the speculative
design for it has been removed from the documents - it described a layer that
was never built, around a premise the project had stopped acting on. Osiris is
a Linux distribution. The old design is in git history if it is ever wanted.

## Phase 1: desktop

| Task | Status |
|---|---|
| Cinnamon + Plank dock + rofi launcher, single top panel | done |
| LightDM + slick-greeter, branded | done |
| Plymouth boot splash with the Osiris mark | done |
| ghostty, zsh + oh-my-zsh, FiraCode with ligatures, fastfetch | done |
| Theme engine: a real GTK theme compiled per palette | done |
| Appearance app: picker with rendered desktop previews | done |
| Theme creator: three colours in, a full palette out | done |
| Generative wallpapers: contour, arcs, strata | done |
| Folder icons tinted to the accent over Papirus | done |
| Plank dock themed from the palette | done |

Seven shipped themes plus anything the user creates. See
[THEMING.md](THEMING.md).

## Phase 2: installer

| Task | Status |
|---|---|
| `iso/profile.py` generates an archiso profile and builds the ISO | done |
| GTK4 installer wizard | done |
| `provision/install.py` as an importable API with progress | done |
| Disk picker with size, transport and in-use guards | done |
| Full provisioning on install, not just the desktop | done |
| Disk layout options: ext4 or btrfs, swap size | done |
| Software rendering switch, defaulted from systemd-detect-virt | done |
| Retry after a failed install | done |

See [INSTALLER.md](INSTALLER.md).

## Verified end to end

The ISO boots UEFI, starts X with no display manager, runs the installer, and
installs a system that boots to a complete Osiris desktop: branded greeter,
top panel, Plank dock, generated wallpaper with the mark.

Run again on 2026-10-17, from `dev`, through archinstall (UEFI, erase disk,
ext4): the install took about three minutes, and the installed system has
Plank Reloaded, both Cinnamon extensions, Super+Space, Super+T and Super+Enter
working, the medium's repository removed from pacman.conf, no failed units, and
a theme switch that retints everything, open terminal included.

Seven defects were found by actually doing it, all fixed:

1. **`systemd-firstboot` took tty1** and asked for a timezone before the
   installer could start. mkarchiso writes `/etc/machine-id` as
   `uninitialized` deliberately, which turns on systemd's first-boot
   mechanism. Masked, and `/etc/localtime` shipped.
2. **No pacman mirrorlist**, so pacstrap failed with "no servers configured
   for repository". The `pacman-mirrorlist` package ships every mirror
   commented out.
3. **No keyring initialisation.** Added `pacman-init.service` and the tmpfs
   mount for `/etc/pacman.d/gnupg`, plus `systemd-timesyncd` - signatures
   carry validity windows, and a wrong clock reads as an invalid signature.
4. **The window sat at 880x660 in the corner.** There is no window manager on
   the ISO, so nothing honours `fullscreen()`; the window now asks for the
   monitor's size itself.
5. **Only `cinnamon.py` ran**, so an install produced stock Cinnamon with no
   themes, no Appearance app, no ghostty or zsh config and no splash. The
   install now runs the full provisioning set.
6. **The install reported failure after succeeding.** The final `umount -R
   /mnt` returned 32 because arch-chroot leaves a gpg-agent holding the
   mountpoint for a few seconds. Everything was written; the installer now
   flushes and falls back to a lazy detach instead of failing.
7. **`~/.config` was owned by root on every fresh install.** The worst of the
   seven. Provisioners created directories under the user's home and chowned
   only some of what they created, so the user could never write to their own
   `~/.config` - no theme could be applied, no configuration saved. Fixed with
   `provision/homes.py`, which chowns every component it creates. It never
   appeared in development because there the user had logged in first, so
   `.config` already existed and was theirs.

Number 7 is the reason to test on a fresh install rather than a development
machine: the development VM had been hiding it for weeks.

## Also fixed since

**A race in `partition()`.** `partprobe` returns before udev has created the
device nodes - measured at 1.7 seconds on a disk that already held a
filesystem - and the `mount` that followed failed intermittently. Found by
running the new btrfs path against a scratch disk; it would have been a
miserable bug to chase from a user report. `wait_for_devices()` now blocks, and
old filesystem signatures are wiped from the new partitions.

Both filesystem paths were then run six times alternating, and `swapon` was
verified to accept the generated swap file on each - btrfs refuses a swap file
that is copy-on-write or compressed, so that was worth proving rather than
assuming.

## Repository

Cleaned up: `shell/bash/` and `shell/foot/` removed (foot was replaced by
ghostty, bash by zsh), two superseded wallpaper scripts removed in favour of the
one generator, orphaned brand assets removed, `__pycache__` ignored, and the
stale `DEV_SHELL.md` replaced by [DEVELOPMENT.md](DEVELOPMENT.md).

Documentation is now a README plus six documents, each with a stated job; see
the table in the README.

## Since

**COSMIC is gone.** `provision/desktop.py`, `DESKTOP_COSMIC`, the `DESKTOPS`
dict and the `--desktop` flag are removed. Cinnamon is the desktop, settled.
`packages.for_install()` now takes only `software_rendering`.

**GRUB replaced systemd-boot**, so the boot menu can carry the mark.
systemd-boot has no theme engine at all. See [INSTALLER.md](INSTALLER.md#the-boot-menu).
The install medium's menu now carries it too: themed GRUB on UEFI, the Osiris
backdrop behind syslinux on BIOS. The medium also shows the Osiris boot splash.

**The medium boots into the live desktop**, with the installer on its dock and
desktop, and a second boot entry that starts the installer alone. See
[INSTALLER.md](INSTALLER.md#decisions-worth-knowing).

## Known gaps

- Four open theming decisions, listed at the end of [THEMING.md](THEMING.md).
- The installer has no manual partitioning, and cannot encrypt an install
  that shares another system's EFI partition (see INSTALLER.md).
- `user-home.svg` and `user-desktop.svg` keep their stock colour, since Papirus
  ships no variants of them.
- Phase 3 (polish) has not been started: packaging, a themed splash and
  greeter, and public documentation.

## Development environment

A libvirt VM, `osiris-dev`, provisioned from this repo. Guest networking uses
passt; ufw on the host with `policy drop` on INPUT and FORWARD breaks it
otherwise, which cost a long debugging detour once already.

The ISO is built as root with the `archiso` package: `python3 iso/profile.py`.
