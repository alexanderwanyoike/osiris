# 7. archiso, not mkosi, for the installation medium

**Status:** Accepted
**Supersedes:** the stack table in `docs/ARCHITECTURE.md` as it stood before.

## Context

The architecture document specified mkosi, on the grounds that it is
declarative and needs no bash hooks. Both true.

**mkosi has no ISO output format.** Its `Format=` accepts directory, tar, cpio,
disk, uki, esp, oci, sysext, confext, portable, addon and none. It builds
bootable *disk images*, which are not bootable removable media. The roadmap
task as written was not implementable, and nobody noticed until somebody tried
to build one.

The objection to archiso was that it needed bash hooks. That was true when the
rule was written and is no longer:

- `customize_airootfs.sh`, the hook the objection was about, **no longer exists
  in archiso**. Neither shipped profile has one.
- Services are enabled with symlinks into `*.target.wants/`. Filesystem, not
  scripts.
- `profiledef.sh` is the one bash file required, and contains only variable
  assignments.

## Decision

The installation medium is built with archiso. `iso/profile.py` **generates**
the profile, including `profiledef.sh`, and then invokes `mkarchiso`.

## Consequences

The ISO is buildable, which it was not before.

ADR 0002 survives intact: the generated `profiledef.sh` is an artefact, not a
source file, in the same sense that a compiler emits assembly.

The medium is UEFI only. Osiris installs GRUB in EFI mode (ADR 0008), so a BIOS
machine would boot the installer and then install a system it could not start.
Refusing at the medium is better than failing after the install.

mkosi remains the better tool for building a disk image, if Osiris ever wants
to ship one. That would be a separate decision.

## Note

The general lesson is recorded in ADR 0001: this decision had never been
checked against the tool's documentation. "Research before implementation" is a
project rule for exactly this reason.
