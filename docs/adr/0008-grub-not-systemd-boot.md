# 8. GRUB, not systemd-boot

**Status:** Accepted
**Supersedes:** ADR-less decision to use systemd-boot.

## Context

Osiris installed systemd-boot: small, no configuration language, and it does
one job. The boot sequence was firmware, a one-second text menu, Plymouth with
the Osiris mark, then the greeter.

A branded boot menu was wanted. **systemd-boot has no theme engine at all.** It
draws a text menu and offers no way to put an image on screen. There is no
configuration that achieves this; the only route is a different bootloader.

## Decision

GRUB, in UEFI mode, with a theme on the ESP at `/boot/grub/themes/osiris`.

Theme assets are generated at build time from the `osiris-obsidian` palette by
`branding/scripts/make-grub-theme.py` and checked in.

`grub-install` runs **twice**:

1. `--bootloader-id=Osiris`, writing `/EFI/Osiris/grubx64.efi` and a UEFI boot
   variable naming it.
2. `--removable`, writing the same loader to `/EFI/BOOT/BOOTX64.EFI`.

## Consequences

The boot menu carries the mark, and the whole sequence from firmware to desktop
is one identity.

`os-prober` finds other installed systems, which systemd-boot never did. For an
operating system people may dual boot, that is the more practical default
regardless of appearance.

**The second `grub-install` is not redundant.** The boot variable written by the
first lives in the *installing machine's* NVRAM, not on the disk. Without the
removable fallback, a disk installed in one machine and booted in another
reports "no bootable device" with the loader sitting there intact. This was
found by doing exactly that.

The costs:

- GRUB is considerably larger than systemd-boot and has a configuration
  language, a module system and a theme format to get wrong. Two things did:
  fonts must be converted to `.pf2` with a family name matching the theme, and
  a 9-slice pixmap set silently draws nothing if one of its nine files is
  missing.
- The bootloader cannot follow the user's chosen theme, because it runs before
  any user session exists. It stays branded, consistent with the splash and the
  greeter.
