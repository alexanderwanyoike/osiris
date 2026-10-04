# Osiris Architecture

This document captures the design of Osiris. v1 (Debian + live-build, dual
Sway/Cinnamon desktop) was scrapped: too painful to build and too bloated. This
is a ground-up rebuild on Arch.

## What Osiris is

A Linux distribution with a conventional desktop that is themed properly and
installs from a live ISO.

Nothing here is novel in the way a new init system or a new display protocol
would be. The pieces are Arch, Cinnamon, Plank, rofi, LightDM and ghostty - all
of which already work. What Osiris adds is **coherence**: one choice of theme
retints the GTK stack, the panel, window decorations, the terminal, the
launcher, the dock, the folder icons and the wallpaper together, instead of
leaving nine things to match by hand. And it adds an install that produces
that, rather than a base system you then spend an evening configuring.

The scope is deliberately small. Osiris does not write a GTK theme, an icon set,
a compositor or a file manager, because each of those is a permanent
maintenance cost against an upstream that keeps moving. It orchestrates the ones
that exist.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Base distro | Arch Linux | Rolling, minimal, no opinionated bloat, fast package availability |
| Desktop | Cinnamon (Muffin, X11) + Plank + rofi | Conventional and customisable, and it works without being rebuilt from parts. Superseded Hyprland + AGS. |
| Installer | GTK4 + libadwaita screens in front of archinstall, on archiso's releng medium | Osiris owns the screens; archinstall does the install. See [the note below](#the-installer) and ADR 0012. |
| Theme system | JSON palettes compiled to a real GTK theme per palette | Toolkits reload on a theme *name* change; that is the supported path. See [THEMING.md](THEMING.md). |
| User shell | zsh with oh-my-zsh | Chosen explicitly over bash. `/etc/skel/.zshrc` ships configured. |
| Bootloader | GRUB (UEFI or BIOS), installed by archinstall, with a themed menu | systemd-boot has no theme engine, and os-prober finds other installed systems |
| Login manager | LightDM + lightdm-slick-greeter | Branded, themeable, and it works with an X11 Cinnamon session |
| Terminal | ghostty | GTK4, and the only candidate that renders font ligatures - VTE terminals cannot |

## Components

### The desktop

Cinnamon, trimmed to a single top panel, with Plank as the dock and rofi on
`Super+Space` as the launcher. `provision/cinnamon.py` configures all three.

Cinnamon's own window list is removed from the panel, because Plank owns that
job and two task lists is worse than either.

### The theme system

`shell/themes/` holds one JSON palette per theme and the code that applies it.
A palette is compiled into a real GTK theme at `~/.themes/Osiris-<palette>`,
and every theme setting points at it.

That is the load-bearing decision, and it is worth stating here rather than
only in THEMING.md: rewriting colours into `~/.config/gtk-*/gtk.css` does not
work, because GTK reads user CSS once at startup. Toolkits reload when the
theme *name* changes. Giving each palette its own name makes switching an
ordinary theme change that GTK, Muffin, Cinnamon and Plank already handle.

### The Appearance app

`apps/appearance/` - a GTK4 + libadwaita picker showing a rendered miniature of
the desktop per theme, plus a creator that derives a full palette from three
colours. See [THEMING.md](THEMING.md).

### The installer

A GTK4 + libadwaita wizard in Python (`apps/installer/`), running as root on a
live ISO. It collects settings and hands them to archinstall as a
configuration file; archinstall partitions, installs the base system, drivers
and bootloader, then installs the `osiris` package and runs `osiris-setup`
inside the new system. The installer contains no install logic of its own. See
[INSTALLER.md](INSTALLER.md).

Steps: region, target disk, account, confirm, progress, restart.

**archiso, not mkosi.** This document specified mkosi, on the grounds that it
is declarative and has no bash hooks. Both true, and irrelevant: **mkosi has no
ISO output format.** `Format=` accepts directory, tar, cpio, disk, uki, esp,
oci, sysext, confext, portable, addon and none. It builds bootable disk images,
which are not bootable removable media. P1.1 as written was not implementable.

archiso is the tool for this. The "no bash we author" rule survives intact:

- `customize_airootfs.sh`, the bash hook the rule was written against, **no
  longer exists** in archiso. Neither shipped profile has one.
- Services are enabled with symlinks into `*.target.wants/`. Filesystem, not
  scripts.
- `profiledef.sh` is the one bash file archiso requires, and it contains only
  variable assignments. `iso/profile.py` **generates** it, so the artefact is
  bash and the source is not - the same arrangement as a compiler emitting
  assembly.

**No display manager on the ISO.** A systemd unit runs
`xinit /usr/local/bin/osiris-installer -- /usr/bin/X :0 vt1`. xinit takes the
client and then the server on argv, so a graphical session starts with no shell
and no login manager to configure.

**Running as root** is deliberate. The alternative is a polkit action and a
privilege boundary in the middle of a program whose whole purpose is to
repartition the disk, on a medium with nothing to protect and no other user to
protect it from.

## Conventions

### No bash that we author

The v1 pain point was bash chroot hooks inside a 30-60 minute Docker build,
with no stack traces and no debugger. This repository contains zero `.sh` files
we wrote. Build, install, hooks and glue are Python, and every process is
spawned as an argv array rather than through a shell.

bash still exists on the system - Arch depends on it and PKGBUILDs are written
in it. The rule is about what *we* write, not what is installed. The full
accounting is in [DEVELOPMENT.md](DEVELOPMENT.md#how-much-bash-is-in-here).

### Python everywhere we can

Provisioning, the ISO build, the theme engine, the Appearance app and the
installer are all Python. One language across the tooling, one idiom to read,
and the installer can import the install flow directly instead of shelling out
to it and parsing text back.

The exception is what is inside the OS already - kernel, systemd, pacman - which
we do not write.

### Branding

`logo.svg` is the source of truth; everything else in `branding/` is derived
from it and checked in so the target needs no SVG stack. See
[branding/README.md](../branding/README.md).
