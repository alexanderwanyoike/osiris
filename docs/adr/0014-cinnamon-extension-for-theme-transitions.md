# 14. A Cinnamon extension for theme transitions

**Status:** Accepted

## Context

Switching **Theme** wrote about thirteen settings one at a time, each repainting
on its own, so the desktop visibly passed through mixed states; terminals kept
the old colours until relaunched. Batching the writes removes the mixed states
but still cuts hard, and Cinnamon's shell theme reload flickers the panel.

Only code running inside the shell can draw over every surface while they
change. On Cinnamon that is an extension, and extensions are JavaScript.

## Decision

Every switch writes its settings as one batch and asks running terminals to
reload. On top of that, an Osiris Cinnamon extension snapshots the screen, the
switch is applied beneath the snapshot, and the snapshot fades out over about
300ms. The switcher triggers it over D-Bus.

This is a deliberate, narrow exception to ADR 0005 and to Python-only tooling
(ADR 0002): Osiris may write shell glue that has no look of its own. The
extension draws nothing but the frozen frame it fades.

## Consequences

- Osiris carries one JavaScript component, tied to Cinnamon's extension API,
  which changes between Cinnamon releases.
- If the extension is missing or fails, the switch still applies as one batch,
  without the fade.
