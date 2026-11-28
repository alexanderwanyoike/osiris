Written by hand for Osiris; no maker makes it. Its GTK 3 and GTK 4 sheets
import the adw-gtk3 theme installed on the system, as the Osiris Skin does
(ADR 0006), and `sass/_adw-gtk3.scss` sets adw-gtk3's named colours from the
Theme's gaps. adw-gtk3's own Sass uses Sass modules (`@use ... with`), which
the sassc that compiles Skinpacks cannot read, so it is imported, not rebuilt.
`sass/_look.scss` is empty: a Skin started here draws its whole look there.
