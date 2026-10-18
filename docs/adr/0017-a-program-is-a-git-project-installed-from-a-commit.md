# 17. A Program is a git Project, installed as a copy of one commit

**Status:** Accepted

## Context

The **Harness** builds **Programs** (CONTEXT.md): apps, scripts, commands and
more, which the person keeps and uses like any other application. A Program
changes over its life, by the Harness and by the person, and some people carry
the work on in another editor or coding agent. Where a Program's source lives,
how its changes are kept and what the menu runs had to be decided before the
first one exists; moving them later means migrating everyone's Programs.

Three ways were open:

- **Run from the source.** The menu entry points into the folder the Harness
  writes. Simplest, but a half-finished change breaks the app in the dock, and
  trying a change cannot be separated from shipping it.
- **An Osiris store.** Programs kept in a hidden data folder in a format of
  Osiris's own. Nothing else could open them, and the person's work would live
  somewhere they never look.
- **A git Project, installed from a commit.** The source is an ordinary
  repository in `~/Code`; installing copies one commit into place.

## Decision

A Program's source is a **Project** in `~/Code/<Program>`, a git repository with
standard build files and an AGENTS.md, so any editor or coding agent can carry
it on. Every change to it is one atomic commit; undoing what an answer changed
reverts its commits. Its **Program manifest** is the one file that is
Osiris's own.

An installed Program is a copy of one commit, built if its language needs it,
with a menu entry generated from the manifest. Changing the source changes
nothing installed until the person updates it; uninstalling removes the copy
and keeps the source.

## Consequences

- History, diffs and undo come from git, which Osiris already ships, and the
  Canvas can show any change as a diff (ADR 0016).
- The app in the dock keeps working while its source is mid-change; Try runs
  the source, Install and Update move the installed copy between commits.
- The Harness knows its Programs by looking in `~/Code`; there is no registry
  to drift out of step with the folders.
- Python, C and C++, Rust and Go are first-class, so Osiris ships their
  toolchains: about 870 MB with gcc, rust, go, meson and cmake.
- Building runs code (build scripts, fetched dependencies). Until Programs are
  confined, builds happen when the person tries or installs, never on the
  Harness's own initiative.
