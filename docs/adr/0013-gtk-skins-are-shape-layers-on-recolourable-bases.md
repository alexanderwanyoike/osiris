# 13. GTK skins are shape layers on recolourable bases

**Status:** Accepted

## Context

A **Theme** is colours and a **Skin** is shape, and switching one must keep the
other (see CONTEXT.md). Osiris recolours GTK by importing a base theme's CSS and
overriding its named colours (ADR 0006), which only works on a base that draws
through named colours.

Of the GTK themes in Arch's repositories, two do: `adw-gtk3` (about 1,180
named-colour references in its GTK 3 sheet) and `Breeze` (about 760). `Materia`
and `Orchis` define named colours but draw with hundreds of literal hex values,
and `Pop` is compiled into a gresource with no CSS to override.

## Decision

A GTK **Skin** is one of the recolourable bases plus an Osiris **shape layer**:
CSS that sets corner radius, density, border weight and button style, and no
colour. Bases that cannot be recoloured are not offered as skins.

## Considered options

- **Any base, some ignoring the Theme.** More variety, but switching Theme would
  leave some applications in their base's own colours, breaking the split.
- **Rewriting the literal colours of Materia and Orchis.** Hundreds of values to
  remap on every upstream release: the cost ADR 0005 exists to avoid.

## Consequences

- Skins differ visibly in GTK 3 applications, the panel, the dock and the
  launcher. libadwaita applications accept colour but little shape, so they look
  much alike under every skin.
- A shape layer is Osiris-authored CSS. It stays within ADR 0005 only while it
  carries geometry and no colour or widget drawing of its own.
