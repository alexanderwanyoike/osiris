# This folder is an Osiris Skin

It is the person's own copy of a Skin: the shape of their desktop (windows,
panel, dock, launcher), whose colours always come from their current Theme.
Change it when they ask; never touch Skins outside this folder.

## How it is made

- `skin.json` is its label. An optional `look` block names an icon set
  (`icons`, one name or `{"light": ..., "dark": ...}`), a `cursor` and a `font`.
- `sass/` holds the Sass partials. Colours come only from these variables,
  which Osiris writes into `sass/_gaps.scss` (never edit or ship that file):
  `$gap-variant` ('light' or 'dark'), `$gap-background`, `$gap-surface`,
  `$gap-foreground`, `$gap-accent`, `$gap-success`, `$gap-warning`,
  `$gap-danger`.
- One entry per surface and variant: `gtk-3.0/gtk-<variant>.scss`,
  `gtk-4.0/gtk-<variant>.scss`, `cinnamon/cinnamon-<variant>.scss`,
  `libadwaita/libadwaita-<variant>.scss`. Every entry but GTK 3 is optional.
- `files/common/` and `files/<variant>/` are copied into the installed theme.
  In SVG and CSS files there, `{{accent}}`, `{{background}}` and the other
  role names are gaps.
- `plank/dock-<variant>.theme` is the dock; colours there are gaps like
  `{{background_plank}}`.
- `rofi/launcher.rasi`, if present, is the launcher, with `{{gap}}` markers.

## An imported theme

If `skin.json` says the author is "Imported", this Skin came from a GTK theme
the person downloaded: compiled CSS in `files/` with its colours written in.
Converting it means finding the colours its window backgrounds, header bars
and sidebars, text, selection and accent, and success, warning and error
states use, in `gtk-3.0/gtk.css`, `gtk-4.0/gtk.css` and
`cinnamon/cinnamon.css` of each variant, and replacing them with the matching
gaps. Keep a colour's transparency with GTK's own function, for example
`alpha({{accent}}, 0.5)`; Cinnamon's stylesheet takes plain colours only.
Leave colours that are part of the look whatever the Theme.

## Rules

- Never write a colour from the Theme literally: use the gaps, so the Skin
  works under every Theme, light and dark. Fixed colours are only for things
  that are part of the look whatever the Theme, and only if asked.
- After each change, build and wear it, and fix any sassc error it reports:

      python3 /usr/share/osiris/themes/engine.py --skin SKIN_NAME

- Commit each change in this folder with a message saying what changed and
  why, so the person can undo it with `git revert`.
