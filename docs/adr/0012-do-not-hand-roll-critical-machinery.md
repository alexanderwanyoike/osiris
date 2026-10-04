# 12. Do not hand-roll critical system machinery

**Status:** Accepted
**Supersedes:** the install flow in ADR 0010 (the wizard stays; the engine
underneath it changes). Narrows ADR 0005 into a hard rule.

## Context

Osiris wrote its own installer: partitioning, pacstrap, fstab, users, GRUB.
Every serious gap found in it was something Arch's own installer, archinstall,
already handled:

- no CPU microcode was installed, on any machine
- no GPU drivers were installed
- the whole disk was always erased; no way to keep another OS
- legacy BIOS machines could not be installed to
- a partitioning race that failed intermittently
- no disk encryption

The ISO had the same pattern: firstboot prompting on tty1, no mirrorlist, no
keyring setup. All three were already solved in archiso's releng profile, which
we chose not to start from.

Each was found by testing, and each was fixed. But the honest lesson is that a
one-person project will keep finding these, one install at a time, in code
whose failure mode is a dead machine or lost data. archinstall has thousands of
users finding them instead.

## Decision

Osiris does not write code for anything that can leave a machine unbootable or
a disk erased. Those jobs go to the tools Arch maintains:

| Job | Done by |
|---|---|
| Partitioning, formatting, encryption | archinstall |
| Base install, users, locale, fstab | archinstall |
| Bootloader install | archinstall (Osiris adds only the GRUB theme) |
| Microcode and GPU drivers | archinstall |
| The live ISO | archiso, starting from the releng profile |
| Delivering Osiris itself | pacman packages, not files copied by scripts |

Osiris keeps: the GTK installer screens (which write an archinstall config and
run it), the desktop configuration, the theme system, the Appearance app, and
the branding.

## Consequences

The installer stops being something we have to get right. The wizard collects
answers and hands archinstall a JSON config; archinstall does the dangerous
part.

Code goes away: most of `osiris/provision/steps.py`, `layout.py`, the disk
model's partitioning logic, and `osiris/model/hardware.py`. That is the point.
The tests written for them were not wasted effort in the sense that they found
real bugs, but the right response to those bugs is to stop owning the code.

The cost is a dependency on archinstall's config format, which changes between
releases. That is a far smaller and safer thing to track than an installer.

The rule for future work: when a feature seems to need us to write system-level
machinery, the first step is to find who already maintains it.
