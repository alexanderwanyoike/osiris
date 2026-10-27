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

- A Skin is data only: style sheets, pictures, a dock and launcher theme, and
  its label. Add no scripts, programs or background services, here or
  anywhere else, and change no settings outside this folder; Osiris applies
  the Skin itself. If something cannot be done with gaps and data, say so to
  the person rather than building around it.
- Icon sets, cursor sets and fonts are named in `skin.json`'s `look` and must
  be installed under `~/.local/share/icons` or `~/.local/share/fonts`. Their
  colours are their own; only the style sheets and pictures here follow the
  Theme.
- Another style for this Skin, or a new one, is a Skin of the person's in
  `~/.local/share/osiris/skins`. Never write to `/usr/share/osiris`: it
  belongs to the system package, and needs no administrator rights for a
  Skin.
- Never write a colour from the Theme literally: use the gaps, so the Skin
  works under every Theme, light and dark. Fixed colours are only for things
  that are part of the look whatever the Theme, and only if asked.
- After each change, check it with the check_skin tool and wear it with
  wear_skin, and fix whatever check_skin reports. Without those tools, the
  engine does the same:

      python3 /usr/share/osiris/themes/engine.py --skin SKIN_NAME

- Commit each change in this folder with a message saying what changed and
  why, so the person can undo it with `git revert`.
