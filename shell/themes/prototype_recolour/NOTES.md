# Prototype: more window themes for Skins

Throwaway. It answers one question for ROADMAP P3.4 (Skins) and is deleted
when the real thing is built, test-first, in `osiris/`.

## The question

Skin sets need visibly different windows. ADR 0013 allows only GTK themes
Osiris can recolour through named colours, and in Arch that is two: adw-gtk3
and Breeze. Shape layers on those two (CSS for corners, spacing, borders,
buttons; `shapes/`) were tried first and judged too samey. Can Osiris recolour
other GTK themes into any Theme instead?

## What was measured

GTK 3 sheets, named colour references against fixed colour values:

| Theme | Where | named | fixed | Recolourable by |
|---|---|---|---|---|
| adw-gtk3 | extra | 1315 | 317 | named colours (today's path) |
| Breeze | extra | 992 | 131 | named colours, with its own names mapped |
| Materia | extra | 38 | 1161 | rewriting fixed colours |
| Orchis | extra | 98 | 869 | rewriting fixed colours |
| elementary | extra | 450 | 517 | rewriting fixed colours |
| Arc | AUR, built from source | 50 | 1206 | rewriting fixed colours |
| Colloid | AUR, built from source | 98 | 1034 | rewriting fixed colours |
| Numix | AUR, built from source | 63 | 1410 | rewriting, once unpacked from its gresource |
| Deepin, Yaru (MATE's) | extra | - | - | rejected by the person: look |
| Adapta, Pop | extra | - | - | compiled into a gresource only |

Arc, Colloid and Numix are not in Arch's repositories; they would be built into
Osiris's own packages as Plank Reloaded is (needs sassc, meson, inkscape).

## What worked

`recolour.py` rewrites every fixed colour by role:

- Choose the theme's variant that matches the Theme: Arc for light Themes,
  Arc-Dark for dark ones; likewise Colloid-Light and Colloid-Dark.
- Read the theme's own background, text and accent from its stylesheet
  (`.background` / `window` and `:selected`, comments stripped first). Arc gave
  exactly its sources' `#383c4a`, `#d3dae3`, `#5294e2`.
- Greys map between its background and text onto the Theme's background and
  text; accent shades onto the Theme's accent at the same relative lightness;
  reds, greens and yellows onto danger, success and warning.

Materia, Arc, Colloid and Orchis (light) came out convincing in Rose Pine and
Rose Pine Dawn.

## Still broken

- Text on the accent: forcing a readable colour by selector caught selected
  tabs too, so their text vanished. Needs to apply only where the fill is the
  accent.
- adw-gtk3 and Breeze should not go through `recolour.py`; adw-gtk3 already
  recolours by its named colours, and Breeze needs its names mapped.
- Orchis-Dark and elementary's dark sheet: their roles were not found and the
  frequency guess picked borders; give each theme a small note of its three
  colours where reading fails.
- Pictures: Arc's switches and checks are PNGs and stay blue; recolour their
  accent pixels, or their SVG sources before rendering.
- Numix: its CSS lives in a gresource with its images; unpack both.
- Nothing yet checks readability on every shipped Theme, which the real build
  must do before offering a window theme.

## Decided so far

In CONTEXT.md: a person keeps only their choice (the Skin set and their swaps);
a modified set sits beside its stock one; five Skin sets (Osiris, Crisp, Paper,
Pebble, Bold) shape the windows, panel, dock, launcher, Harness, fonts, icons
and cursor. Recolouring fixed colours reverses ADR 0013's limit and needs a new
ADR when it is built.
