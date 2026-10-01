# 1. Record architecture decisions

**Status:** Accepted

## Context

This project has already reversed several significant decisions: Debian to
Arch, Hyprland to Cinnamon, AGS to Cinnamon's own shell, greetd to LightDM,
mkosi to archiso, systemd-boot to GRUB, and an AI-first framing to none.

Every one of those was decided well at the time. None of them left a record of
*why*, so the reasoning had to be reconstructed from commit messages and
memory - and in at least one case a decision was carried forward into
documentation long after the project had stopped acting on it.

The specific failure that prompted this: `docs/ARCHITECTURE.md` specified mkosi
for building the installation medium. mkosi has no ISO output format. The
decision had never been verified against the tool, and nothing recorded what it
was weighed against, so the error survived until somebody tried to build an
ISO.

## Decision

Significant architectural decisions are recorded as numbered files in
`docs/adr/`, in the Context / Decision / Consequences form.

A record is immutable once accepted. Changing a decision means writing a new
record that supersedes the old one, with both pointing at the other.

"Significant" means: it constrains what can be built later, it was chosen over
a reasonable alternative, or getting it wrong would cost more than a day.

## Consequences

Decisions acquire an audit trail, and the alternatives that were rejected stay
visible - which is what stops them being re-proposed, and equally what makes it
possible to revisit one honestly when circumstances change.

The cost is a file per decision and the discipline to write it at the time
rather than afterwards. Records written afterwards are reconstructions, and
read like it.
