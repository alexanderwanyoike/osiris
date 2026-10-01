# 10. The installer imports the install flow

**Status:** Accepted

## Context

The graphical installer needs to partition a disk, pacstrap a system,
configure it and install a bootloader. That logic already exists and is driven
from the command line during development.

The conventional arrangement is for a GUI to shell out to the CLI and parse its
output. The original architecture went further: a TypeScript frontend and a Bun
backend that would have reimplemented the install in a second language.

Both arrangements have the same defect. The install flow and the thing driving
it drift, and the drift is only discovered when a user hits it. Parsing a
subprocess's stdout also turns a Python exception with a traceback into an exit
code and some text.

## Decision

`provision/install.py` exposes `install(Options, progress)`. The command line
and the graphical installer are both thin callers of that function. The
installer **imports** it and runs it on a worker thread, posting progress to
the UI through `GLib.idle_add`.

The installer contains no partitioning, no pacstrap and no bootloader logic.

## Consequences

The two paths cannot drift, because there is only one path.

A failure arrives as an exception with a traceback, which the installer can
show in full. The dialog that reports "pacstrap exited 1" also has the command
and the last four hundred characters of its output, because it has the
exception object rather than a parsed string.

Progress reporting is a callback rather than a protocol: `progress(fraction,
message)`. The caller does not need to know what the steps are.

The consequence that had to be accepted: **the installer runs as root.** The
alternative is a privilege boundary in the middle of a program whose entire
purpose is to repartition a disk, on a live medium with nothing to protect and
no other user to protect it from. A polkit action and an IPC channel would add
moving parts without adding safety here.

This also means the installer cannot be unit-tested as a whole. The install
*flow* is tested against fakes (ADR 0003); the GTK window is not. See ADR 0011.
