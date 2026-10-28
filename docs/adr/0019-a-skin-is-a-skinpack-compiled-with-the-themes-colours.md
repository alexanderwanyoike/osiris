# 19. A Skin is a skinpack compiled with the Theme's colours

**Status:** Accepted. Supersedes [0013](0013-gtk-skins-are-shape-layers-on-recolourable-bases.md).

## Context

ADR 0013 allowed only GTK themes Osiris can recolour through named colours
(adw-gtk3 and Breeze), each with an Osiris shape layer on top. Shape layers on
those two bases were tried and judged too alike to be worth choosing between.

The themes people want as looks (Colloid, Graphite, Orchis, Qogir, Jasper,
elementary) draw their installed CSS with hundreds of fixed colours, so
rewriting it by role was unreliable (`.notes`, the recolour prototype). Their
sources are different: each is Sass whose colours come from a palette file,
and their own installers already recolour them by swapping that palette and a
handful of colours in their SVGs.

A proof on 2026-10-24 turned Colloid's source into a folder whose palette
reads from named gaps, filled them from an Osiris Theme, compiled with sassc,
and switched to the result: GTK 3, GTK 4, the Cinnamon panel and Plank all
followed Rose Pine, Rose Pine Dawn and Nord.

## Decision

A **Skin** is a **skinpack**: a folder (one file when shared) holding a label,
style sheets and SVGs with named gaps for the Theme's colours, and the Plank
theme. Osiris fills the gaps from the Theme, compiles the Sass with sassc and
installs the result as a GTK theme named for the Skin and the Theme, so every
Theme switch is an ordinary theme-name change (ADR 0006). Nothing in a
skinpack runs: it is data that Osiris's own code turns into a theme.

The gaps are the Theme's own roles (`background`, `surface`, `foreground`,
`accent`, `success`, `warning`, `danger`, and whether it is dark). A skinpack
decides how its look uses them, and may keep colours that make it what it is,
such as round window buttons in red, yellow and green.

The Osiris Skin stays what it is today: adw-gtk3 recoloured by named colours
(ADR 0006), with no skinpack.

## Considered options

- **Recolour installed CSS by role.** Tried in the recolour prototype: text
  vanished on selected tabs and dark variants were misread. Fragile per theme.
- **A skinpack that carries a build script.** More freedom for authors, but a
  pack from a stranger would then be a Program needing the trust story of
  ADR 0017. Data with gaps keeps opening a shared Skin safe.
- **Shape layers on adw-gtk3 (ADR 0013).** Safe and small, but the looks
  differ too little.

## Consequences

- sassc becomes a dependency of the `osiris` package.
- Skins are built from upstream source and kept in this repository as
  skinpacks; following an upstream release means regenerating the pack.
- libadwaita 1.6+ reads its accent from CSS variables only Osiris's own sheet
  sets, so a Skin's libadwaita sheet is followed by `adwaita_css(theme)`: the
  Skin gives shape, the Theme colour.
- A Skin replaces Osiris's GTK theme, and its Cinnamon stylesheet, Plank theme
  and launcher theme when it brings them; each it leaves out stays Osiris's
  own. It may name icons, a cursor and a font, each otherwise the Theme's
  choice. The Theme still owns the terminal, the wallpaper, and the icons'
  tint when the Skin names no icons.
