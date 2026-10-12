# Branding assets

The Osiris mark and everything derived from it. The source of truth is
`logo.svg`; the rest are renders, kept because the systems that need them
cannot render SVG.

| File | What it is | Used by |
|---|---|---|
| `logo.svg` | The mark, black fill on transparent. Source of truth. | the scripts below |
| `logo-white.svg` | The same mark, white fill | hand use on dark backgrounds |
| `logo-mask.png` | Alpha mask, 807x1965, cropped to the ink | `shell/themes/wallpaper.py` |
| `logo-dark.png` | Light mark for dark backgrounds, 1024px | greeter, installer, fastfetch |
| `logo-light.png` | Dark mark for light backgrounds, 1024px | reserved for a light greeter |
| `logo-simple.png` | High-contrast greyscale, 738x1766 | input to `make-terminal-logo.py` |
| `logo-splash.png` | 132x320 | Plymouth boot splash |
| `logo-greeter.png` | 30x72 | the LightDM greeter's small mark |
| `logo.txt` | Braille-rendered mark | fastfetch |
| `wallpapers/osiris-default.png` | The branded wallpaper | the greeter |
| `wallpapers/generated/` | One per shipped theme | the desktop |
| `grub/` | Boot menu theme: backdrop, mark, selection pixmaps | installed GRUB, the medium's UEFI menu |
| `syslinux/splash.png` | 640x480 backdrop with the mark | the medium's BIOS menu |

**`-dark` and `-light` name the background, not the ink.** `logo-dark.png` is
the *light* mark, for use *on* dark surfaces. This has caused confusion before;
when in doubt, composite it over the surface you mean to use it on and look.

## Regenerating

```
python3 branding/scripts/make-logo-mask.py       # logo-mask.png, from logo.svg
python3 branding/scripts/make-terminal-logo.py   # logo.txt, from logo-simple.png
python3 shell/themes/wallpaper.py                # wallpapers/generated/
python3 branding/scripts/make-grub-theme.py      # grub/, syslinux/splash.png
```

The first two need `rsvg-convert`, ImageMagick and `chafa`, and run on a
development machine only - their outputs are checked in and shipped, so the
target needs no SVG stack.

The branded wallpaper is the `osiris-obsidian` theme's wallpaper:

```
python3 -c "import sys, json; sys.path.insert(0, 'shell/themes'); import wallpaper; \
wallpaper.render(json.load(open('shell/themes/osiris-obsidian.json')), \
'branding/wallpapers/osiris-default.png')"
```

It used to come from a separate script that drew its own gradient. There is one
wallpaper generator now; see [docs/THEMING.md](../docs/THEMING.md#wallpapers).
