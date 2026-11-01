"""The coding standards a Program starts with (#161).

Only what no linter checks: the reviewer skips whatever tooling enforces.
"""

from __future__ import annotations

STANDARDS_FILE = "CODING_STANDARDS.md"

STANDARDS = """\
# Coding standards

The rules a reviewer checks this Program against. Formatting and anything a
linter checks belong to the linter, not here. Change them as the Program grows;
where they disagree with a general rule, they win.

## Style

- Names say what a thing is or does, in the Program's own words; one idea has
  one name everywhere.
- Colours come only from the Theme: libadwaita's named colours, never values.
- A comment says why, never what the code does.
- Small functions with one job. Prefer a function to a class, and data to code.

## Testing

- Test first: the smallest test that fails for the right reason, the least code
  that passes it, then tidy with the tests green. One behaviour per cycle.
- A bug gets a failing test before its fix.
- Tests describe behaviour a person would recognise, not internals.
- Windows are tested headless where the toolkit allows it.

## Architecture

- One reason to change per module, and depend on small interfaces, not on
  implementations (SOLID). Behaviour lives with the data it needs; low
  coupling, high cohesion (GRASP).
- The simplest design that passes today's tests. An abstraction earns its place
  with a second use or a known variation point (KISS, YAGNI).
- Windows draw; the domain decides. Anything outside the process (files, the
  network, other programs) sits behind a small interface passed in, so tests can
  fake it (ports and adapters).
- Design patterns where one makes the code simpler, named where used (Strategy,
  Observer, Adapter, Command and the rest). Never one added in case.
- Domain-driven design where the Program has a real domain: its terms defined in
  `CONTEXT.md` and used unchanged in the code, entities and value objects for its
  concepts, and a boundary between parts that speak different languages. A
  small utility needs none of it.

## Commits

- Every commit does one thing and leaves the tests passing, except the failing
  test that starts a cycle. A refactor, rename or formatting change never shares
  a commit with a change in behaviour.
- The message says why.
"""
