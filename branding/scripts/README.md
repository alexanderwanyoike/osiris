# Branding scripts

Two tools, both run on a development machine, both writing assets that are
checked in and shipped. Neither runs on an installed system.

## make-logo-mask.py

Renders `logo.svg` to `branding/logo-mask.png`: an 8-bit greyscale alpha mask
cropped to the ink's bounding box, so callers control the size directly rather
than compensating for the SVG's generous margin.

`shell/themes/wallpaper.py` composites this into every generated wallpaper.
Shipping the mask rather than the SVG is what lets the generator run on the
target with no SVG stack installed.

Needs `rsvg-convert` (librsvg) and ImageMagick.

## make-terminal-logo.py

Renders the mark to `branding/logo.txt` as braille characters, which fastfetch
prints at login.

Braille rather than ASCII because each cell carries 2x4 addressable dots rather
than one character's worth of shape, which is the difference between a
recognisable obelisk and a smudge. Six other approaches were tried first.

fastfetch on Arch links no image libraries, so a PNG logo silently falls back to
the stock Arch ASCII art - the text file is what it actually uses.

Needs `chafa` and ImageMagick.

## What used to be here

`brand-wallpaper.py` and `make-default-wallpaper.py` drew wallpapers by
overlaying the logo on a gradient. Both are gone: `shell/themes/wallpaper.py`
generates wallpapers from a palette, composites the mark itself, and runs on the
target as well as here. One generator, not three.
