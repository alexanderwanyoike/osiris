# 21. A Theme names extra accents only when its look has them

**Status:** Proposed.

## Context

A Skin draws from eight of the Theme's colours, with one accent among them
(ADR 0019). Asked for a Skin themed on a cartoon, Osiris drew the right decals,
but every detail came out in the one accent, so a look known for several
colours was hard to recognise.

## Decision

Every Theme keeps its one accent and may name a second and a third, only when
its look has them. A Skin can ask for all three. Where a Theme does not name the
second or third, a Skin asking for it gets the first. Osiris never derives the
extra accents for a Theme.

## Considered options

- **Skins use the Theme's terminal colours.** Every Theme already has six, but
  they are tuned for a terminal, not for a look, and it ties Skins to them.
- **Identity details as Fixed colours in the Skin.** Allowed today, but the
  details then ignore every other Theme the person wears.
- **Derive the extra accents from the Theme's Harmony.** Fills them for every
  Theme, but adds colours a look does not have: a triadic Harmony would put
  purple and orange into a Theme that is only green and black.

## Consequences

- Shipped and generated Themes look exactly as before, because they name no
  extra accents.
- A Skin that uses the second or third accent still looks whole under a Theme
  with one, because the details fall back to its accent.
- The Skin gaps grow by two, so a Skinpack using them needs an Osiris that
  knows them.
