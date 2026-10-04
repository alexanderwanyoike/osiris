# 6. A palette compiles to a real GTK theme per theme

**Status:** Accepted

## Context

Switching theme has to retint running applications. The obvious approach - keep
one base theme and rewrite colour overrides into `~/.config/gtk-3.0/gtk.css` -
does not work: **GTK reads user CSS once at startup**. Running applications
keep the previous palette indefinitely.

The workaround people reach for is to force a reload by bouncing settings keys
with sleeps between them. That was tried. It is unreliable, visibly hacky, and
leaves some applications a palette behind. Muffin additionally caches the GTK
theme for server-side title bars, so a window could display two palettes at
once.

## Decision

Each palette is compiled into a **real GTK theme** at
`~/.themes/Osiris-<palette>`, and every theme setting points at it. The theme
imports the base theme and adds `@define-color` overrides.

The same approach is used for the dock: each palette gets its own Plank theme
name, not one theme whose file is rewritten.

## Consequences

Switching becomes an ordinary **theme change**, which is the supported path
that GTK, Muffin, Cinnamon and Plank all already handle. Nine surfaces repaint
live with no logout and no sleeps.

It also removed code: an earlier version ended every theme change with
`cinnamon --replace` to force decorations to reload. With a per-palette theme
name that is unnecessary - verified on a running file manager across three
consecutive switches - and it was actively harmful, since replacing the shell
repeatedly left Cinnamon wedged.

The costs:

- `~/.themes` would accumulate a directory per palette, so themes for other
  palettes are deleted on switch.
- Terminal and launcher read their configuration once at startup and keep the
  old palette until relaunched. The switcher says so rather than leaving the
  user wondering.
- The theme name is user-visible in Cinnamon's own settings, where
  `Osiris-nord` appears instead of `adw-gtk3-dark`.
