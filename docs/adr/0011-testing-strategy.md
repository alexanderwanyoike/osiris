# 11. Testing strategy, and what is deliberately not tested

**Status:** Accepted

## Context

The project had no tests. Every check was a human looking at a virtual machine,
which meant defects were found late, by running an installer and watching, and
several shipped.

An operating system installer is also genuinely hard to test. It partitions
disks, chroots, and talks to a package manager over the network. A test suite
that tried to cover that end to end would be slow, flaky, and would need
hardware.

## Decision

Three tiers, with explicit boundaries.

**Unit tests, against fakes.** The default. Everything that can be expressed
against `FakeRunner`, `FakeFileSystem` and `FakeIdentity`: the install flow's
ordering and error handling, ownership rules, resource rendering. Fast enough
to run on every save. Parameterised against the real implementation where the
fake could plausibly diverge.

**Pure computation, tested directly.** Colour derivation, contrast ratios,
palette generation, the Papirus colour match. No dependencies to invert, so no
fakes: assert on the output. These catch real defects - a contrast ratio of
1.16 is a failing assertion, not a judgement call.

**Integration, marked and excluded from CI.** Anything needing a real machine,
marked `@pytest.mark.integration`. Run from a development machine against the
VM, never in CI.

CI runs lint, format, strict type checking, import contracts, dead code, and
the first two tiers. **It does not build an ISO**: that needs root, loop mounts
and around 8GB of scratch, and has no business in a pull request check.

## What is deliberately not tested

- **GTK windows.** `osiris/apps/` is excluded from coverage. Asserting that a
  button exists tests the toolkit, not the application. The logic behind the
  windows - disk filtering, validation, palette derivation - is in modules that
  are tested.
- **Whether the system boots.** No test replaces booting it. That is done in a
  VM, and the facts worth keeping from doing so are recorded here and in
  `docs/DEVELOPMENT.md`.
- **Third-party behaviour.** Osiris does not test that pacman installs
  packages. It tests that it is *asked* to, with the right arguments.

## Consequences

Most of the codebase becomes verifiable in under a second, which changes what
it is reasonable to refactor.

The tests encode the defects already paid for. The ownership rule, the
`partprobe` race and the shell-injection property each have a test that names
the failure in its docstring, so the next person to touch that code is told why
it is written the way it is.

The gap is honest and stated: nothing here proves the thing boots. It proves
the code asks for the right boot, which is the part that is cheap to get wrong
in a hundred small ways.
