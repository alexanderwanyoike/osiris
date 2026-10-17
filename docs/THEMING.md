# Osiris theming

How themes, icons, fonts and wallpapers are defined, shipped and switched.

This describes the system as built. Where it is going - a **Theme** that is
colours only, **Skins** for shape, Boot screens that follow a **System theme**,
and themes made from a wallpaper or a sentence - is roadmap phase P3, with the
terms in [CONTEXT.md](../CONTEXT.md) and the decisions in ADRs 0013 and 0014.

## Principle

**Osiris does not implement a theming engine. It orchestrates the ones that
already exist.**

GTK, the icon theme spec, fontconfig and Cinnamon all have working theming.
Writing our own would mean maintaining a GTK3 theme, a GTK4/libadwaita theme, a
Cinnamon shell theme and an icon set - four moving targets that break on every
upstream release. Distributions that try this spend most of their time on it.

An Osiris theme is therefore a **manifest**: one file that names a coherent set
of existing pieces, plus the colour tokens for the few surfaces nobody else
themes for us (terminal, launcher, dock, splash).

The value we add is coherence. Picking "Nord" should set the GTK theme, icon
theme, fonts, wallpaper, terminal palette, launcher, dock and login screen
together, rather than leaving the user to match nine things by hand.

## The theme contract

One JSON file per theme in `shell/themes/<name>.json`.

```jsonc
{
    "name": "nord",              // identifier, matches the filename
    "label": "Nord",             // shown in the picker
    "dark": true,
    "pairs_with": "nord-light",  // counterpart for the light/dark toggle

    "colors": {                  // 12 semantic tokens, not raw palette
        "background": "#2e3440",
        "surface": "#3b4252",
        "surfaceMuted": "#434c5e",
        "border": "#4c566a",
        "borderActive": "#88c0d0",
        "foreground": "#eceff4",
        "foregroundMuted": "#d8dee9",
        "accent": "#88c0d0",
        "accentMuted": "#5e81ac",
        "success": "#a3be8c",
        "warning": "#ebcb8b",
        "danger": "#bf616a"
    },

    "terminal": { "regular0": "…", "…": "…", "bright7": "…" },

    "ui": {
        "gtk": "adw-gtk3-dark",          // package: adw-gtk-theme
        "icons": "Papirus-Dark",         // package: papirus-icon-theme
        "cursor": "Adwaita",
        "font": "Noto Sans 10",
        "mono": "FiraCode Nerd Font"
    },

    "requires": [                        // packages this theme needs
        "adw-gtk-theme", "papirus-icon-theme",
        "noto-fonts", "ttf-firacode-nerd"
    ],

    "wallpaper": "generated",            // or a filename in branding/wallpapers/
    "wallpaper_style": "contour",        // contour | arcs | strata
    "folder_colour": "blue"              // a Papirus folder colour
}
```

The `ui` block and `requires` describe shape, not colour: under P3.2 they move
out of the theme into **Skins** (see CONTEXT.md).

Two fields matter more than they look:

**`requires`** - a theme that names an icon theme which is not installed does
not fail; GTK silently falls back and the user sees a half-applied theme. The
switcher checks this list and refuses rather than half-applying, and
`osiris-themes` depends on the union of every theme's requirements.

**`pairs_with`** - light/dark is a toggle users expect to be instant. Each theme
names its counterpart so one keybinding can flip between them without a picker.

## How a theme is applied

Each palette is compiled into a **real GTK theme** at
`~/.themes/Osiris-<palette>`, and every theme setting points at it.

This is the load-bearing decision. The obvious approach - keep one base theme
and rewrite colour overrides into `~/.config/gtk-*/gtk.css` - does not work:
GTK reads user CSS once at startup and Muffin caches decorations, so running
applications keep the previous palette. Trying to force reloads by bouncing
settings keys with sleeps between them is a hack, and an unreliable one.

Toolkits *do* reload when the theme **name** changes, because that is the
supported path. Giving each palette its own theme name makes switching an
ordinary theme change that GTK, Muffin and Cinnamon already handle.

The generated theme contains:

```
~/.themes/Osiris-<palette>/
    index.theme          metatheme metadata
    gtk-3.0/gtk.css      @import the base theme, then @define-color overrides
    gtk-4.0/gtk.css      same, for libadwaita applications
    cinnamon/            Cinnamon's built-in shell theme plus palette rules
```

`url()` inside the imported sheet resolves relative to that sheet, so the base
theme's assets keep working. Themes for other palettes are deleted on switch,
so `~/.themes` does not accumulate.

## What consumes a theme

| Surface | Mechanism | Updates |
|---|---|---|
| GTK 3/4 applications | generated theme, `gtk-theme` | **live** |
| Cinnamon panel, menu, notifications | generated `cinnamon/` theme | **live** |
| Wallpaper | `picture-uri` | **live** |
| Folder icons | generated icon theme, `icon-theme` | **live** |
| Dock (Plank) | generated `dock.theme` | **live** |
| Cursor, fonts | dconf | **live** |
| Server-side title bars | Muffin, from the GTK theme | **live** |
| Terminal (ghostty) | generated config file, `SIGUSR2` | **live** |
| Launcher (rofi) | generated `.rasi` | each time it opens |
| Login greeter, boot splash | fixed to Osiris branding | n/a |

**Nothing restarts the shell.** An earlier version ended `apply()` with
`cinnamon --replace`, on the assumption that Muffin caches the GTK theme and
never re-reads it for server-side title bars. That is true when the theme
*name* stays the same and only its CSS changes. It is not true here: because
each palette gets its own theme name, Muffin and the Cinnamon panel both
repaint in place, verified on a running Nemo across three consecutive switches.

Removing the reload was not only redundant but a bug fix. Replacing the shell
several times in quick succession leaves Cinnamon wedged - a black desktop and
a half-drawn panel - which is exactly the kind of fragility a theme switcher
must not have.

**Running terminals reload.** ghostty re-reads its configuration on `SIGUSR2`,
so the switcher signals the user's ghostty processes once the new config is
written. The generated config turns off ghostty's "configuration reloaded"
toast, which would otherwise appear in every open terminal on every switch.
rofi is started afresh each time it opens, so it always has the current theme.

## Switching without the in-between

A switch is written as **one dconf change**. Setting each key with its own
`gsettings set` reached the desktop as one notification per key, and every one
repainted on its own: applications restyled, then title bars, then the panel,
then icons, then the wallpaper. `osiris/themes/switch.py` builds a single
keyfile that `dconf load /` applies, and every client receives one notification
carrying all the keys - measured with dbus-monitor: one `Notify` signal against
one per key for separate writes.

On top of that, the change happens **out of sight** (ADR 0014). The Cinnamon
extension `transition@osiris` covers the screen with a picture of itself, the
switch is applied beneath it, and the picture fades out. The sequence, driven by
`engine.apply()` over D-Bus (`dev.osiris.Transition`):

1. `Freeze` takes a screenshot with Cinnamon's own screenshot API, puts it over
   everything, and answers only once the stage has painted it.
2. The theme is built and loaded, and terminals are signalled.
3. `Release(400, 300)` holds the picture 400ms while applications repaint, then
   fades it over 300ms, easing in and out.

Things that were got wrong first and are worth not repeating:

- The picture is loaded with GdkPixbuf into a `Clutter.Image`, not set as a CSS
  `background-image`. St loads those asynchronously, so the cover was still
  transparent when `Freeze` answered and the switch happened in plain view.
- An ease-out fade looks like a jump in its first frame: a 300ms ease-out is
  already about a third of the way after 50ms. Ease-in-out starts gently.
- The wallpaper keeps fading a little after the picture has gone. That is
  Cinnamon's own crossfade between backgrounds, and it is welcome.

If the extension is missing or fails, `Freeze` fails at once and the switch
still applies as one change, without the fade. If the switcher dies between the
two calls, the extension releases the picture after five seconds on its own, so
the desktop is never left frozen.

Cinnamon accepts the extension on version 6.4 and anything newer, so it does not
need bumping with each Cinnamon release, but its JavaScript API can change.

## Where themes live

```
/usr/share/osiris/themes/*.json     shipped, owned by the osiris-themes package
~/.config/osiris/themes/*.json      user themes; same name overrides a shipped one
~/.config/osiris/theme               the active theme's name
```

User themes override shipped ones by name, so a user can fork "nord" without
editing a root-owned file, and a package update will not clobber it.

## Packaging

Themes ship as `osiris-themes`, separate from `osiris-desktop`:

- it is pure data, so it updates without touching the desktop
- its dependencies are the union of every theme's `requires`, so installing it
  guarantees every shipped theme actually applies
- a user can remove it and keep their own themes in `~/.config/osiris/themes/`

We ship **no GTK or icon themes of our own**. Every one comes from Arch's
repositories. This is the single most important decision here: authoring a GTK
theme is a permanent maintenance cost, and the packaged options are good.

## Switching

**Appearance** (`osiris-appearance`) is the switcher: a GTK4/libadwaita app
showing one card per theme, each a rendered miniature of the desktop in that
palette. Click a card and it applies immediately.

    apps/appearance/main.py          the picker
    apps/appearance/creator.py       the creator dialog
    apps/switcher/main.py            the Super+T carousel
    shell/themes/engine.py           load and apply; shared, not duplicated
    shell/themes/derive.py           a full palette from two or three seeds
    shell/themes/wallpaper.py        generative backgrounds from a palette
    shell/themes/icons.py            folder tinting over Papirus
    shell/themes/plank.py            the dock theme
    shell/themes/preview.py          renders the card thumbnails (Pillow)
    shell/themes/paths.py            the running user's home, done right
    shell/themes/transition@osiris/  the Cinnamon extension that fades a switch
    osiris/themes/switch.py          a switch as one dconf change
    provision/themes.py              installs all of the above

Written in Python against PyGObject because GTK4, libadwaita and Pillow are
already on the system - no new toolchain, no compile step, and it matches the
rest of the project.

Details that matter for it feeling finished:

- **It follows the active theme.** libadwaita normally takes light/dark from the
  XDG settings portal, which Cinnamon does not serve, so the app would render
  light on a dark desktop. It reads the active Osiris theme instead and switches
  as soon as you pick a light or dark one.
- **It refuses rather than half-applying.** If a theme's `requires` packages are
  missing it says which, instead of letting GTK silently fall back.
- **It restyles itself under the fade.** Appearance changes its own light or dark
  look right after `apply()` returns, inside the 400ms the frozen picture is
  held, so it changes with everything else.
- **It scales past a screenful.** Themes are grouped by colour family (Reds
  round the wheel to Pinks, then Neutrals), with favourites first. Typing
  anywhere searches by name or family ("blue" finds the Blues), and chips
  narrow to dark, light or the user's own themes. The grouping, search and
  filters are pure logic in `osiris/themes/library.py`, tested without GTK;
  the starred names live one per line in `~/.config/osiris/favourites`.

### Super+T

For switching without opening a window, **Super+T** brings up a full-screen
carousel (`apps/switcher/main.py`): the focused theme as a large card of its
wallpaper and palette, neighbours smaller and dimmer either side, over a
blurred backdrop of the focused wallpaper. Arrows, the scroll wheel or a click
on a neighbour slide along; Enter or a click on the centre card applies;
Escape or a click outside closes with nothing changed. Pressing Super+T again
while it is open steps on, the way Alt+Tab does. The order is the library's,
so favourites come first, and the carousel's geometry is pure logic in
`osiris/themes/carousel.py`.

It has to open at once, which is why it is resident. The autostart entry and
a D-Bus service file both start it with `--gapplication-service`, and the
keybinding runs `gapplication action dev.osiris.Switcher show`: a C tool
sending one D-Bus call, so a key press never waits for a Python interpreter
to start. If the switcher is not running, D-Bus starts it. Wallpapers are
decoded at 1280px and only the sixteen nearest the focus are kept, with the
small preview thumbnail standing in until a wallpaper has loaded.

Everything on screen is drawn in one cairo pass rather than built from
widgets, so cards, labels and backdrop move in step on every frame of the
slide.

`engine.py` is importable, so scripting a switch is `engine.apply("nord")`, and
`engine.save()` / `engine.delete()` manage user themes. There is deliberately
no separate CLI to keep in sync.

One structural note, because it is easy to repeat: a card is a `Gtk.Overlay`
wrapping a `Gtk.Button`, not a `Gtk.Button` containing one. A GtkButton takes
the pointer across its whole area, so a menu button nested inside one renders,
highlights on hover, and never fires.

A second: card thumbnails are drawn by a small `Gtk.DrawingArea`, not a
`Gtk.Picture`. A FlowBox lays children out by their natural width, and a
Picture's natural width is its image's, so cards came out two to a row however
wide the window was.

## Folder icons and the dock

Two surfaces that used to ignore the palette entirely.

### Folders

Papirus already ships its folders in two dozen colours - `folder-teal.svg`,
`folder-violet.svg`, and a variant of every semantic folder
(`folder-teal-documents.svg`). So nothing is drawn here. `shell/themes/icons.py`
picks the shipped colour nearest the accent and assembles an icon theme that
points at it:

```
~/.icons/Osiris-<palette>/
    index.theme                 Inherits=Papirus-Dark
    <size>/places/folder.svg    -> Papirus/<size>/places/folder-teal.svg
```

Everything that is not a folder falls through the inherit to the real theme.
Recolouring an icon set would be the same trap as writing a GTK theme.

Shipped themes name their colour in `folder_colour`; the nearest-match is the
fallback for themes written on the machine. The match is made in hue,
saturation and lightness rather than RGB, because RGB weighs lightness as
heavily as hue and chose badly on exactly the palettes that need this most -
Nord's pale cyan came out a generic blue, Rose Pine Dawn's muted mauve came out
grey. The hue term is scaled by the lesser of the two saturations, since hue is
meaningless in a near-grey, and that needs a counterweight or every achromatic
candidate gets a free pass: hence an asymmetric penalty for a candidate duller
than the accent.

`user-home.svg` and `user-desktop.svg` keep their stock appearance - Papirus
ships no colour variants of them, and a tinted folder beside an untinted house
looks worse than leaving both alone.

### The dock

The dock is Plank Reloaded, Plank's maintained fork, which keeps its settings
schema and theme format. Plank itself, unreleased since 2019, aborts on some
GTK theme changes - its handler notifies a property under a name it has
already freed, and its log handler dies on the garbage - and an Osiris switch
is one. Plank Reloaded is in no official repository, so Osiris builds it into
its own (`iso/bundled/plank-reloaded`).

Plank reads a `dock.theme` ini file and is pointed at one through a relocatable
schema, `net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/`.
Colours in that file are `R;;G;;B;;A`, 0-255 - not hex.

As with the GTK theme, **each palette gets its own theme name**. Plank reads the
file when the setting changes; rewriting a file it is already pointed at leaves
the dock exactly as it was.

Two things were got wrong first time and are worth not repeating: a negative
`TopPadding` makes Plank draw the icons overflowing the top edge, so the dock
looks like it has come away from them; and filling it darker than the
background, on the theory that a dock should recede, reads as a hole in the
wallpaper. A dock floats above the desktop, so it is lighter than what is
behind it.

## Creating a theme

**Appearance** has a creator that starts from **one colour** or **a picture**
and offers finished themes to pick from, rather than controls to set. Asking
people to choose a harmony and a mood asks them to do colour theory; choosing
between finished themes is easy. Each start shows six looks - Calm, Contrast,
Lively, Playful, Tonal and Soft (`SUGGESTIONS` in `osiris/themes/intent.py`) -
as miniatures of the desktop, and the person picks one.

A picture also proposes light or dark and the mood, and becomes the theme's
wallpaper. **Fine-tune**, collapsed by default, holds the harmony and mood
behind the chosen look and **Choose colours myself**: background, accent and
secondary by hand, with the colours that go with the accent offered as swatches.
Nothing stops a clash there - a **User theme** is the user's - but **Make these
go together** moves the secondary to the nearest harmony with the accent, at a
supporting strength.

A theme carries about thirty colours; however it starts, the rest are derived
the same way. The preview re-renders on every change, debounced by 120ms against a
render that costs about 25ms.

A theme made from a picture names it in `wallpaper` by absolute path. On save
the picture is copied to `~/.local/share/osiris/wallpapers/<name>-picture.*`,
so moving or deleting the original does not take the wallpaper with it, and it
is copied again under the new name on a rename, because a rename deletes the old
theme. The engine never renders a generated wallpaper over a picture, its card
shows the picture, and deleting the theme removes only that copy. The theme
records its intent under `intent`, so reopening it restores the form.

Derived values are **written into the saved theme**, not recomputed on load.
That is what makes a theme a document: it can be hand-edited afterwards, it
does not shift under the user when the derivation is improved, and nothing
downstream needs to know it was generated. `derived_from` records the seeds so
reopening the theme restores the form rather than thirty swatches.

Cards carry a menu: **Duplicate** on any theme, plus **Edit** and **Delete** on
your own. Duplicating is how you fork a shipped theme - its file is root-owned
and an edit would be lost on the next package update, so the copy lands in
`~/.config/osiris/themes/` and shadows the original by name.

### Legibility is not a preference

Light/dark and the background colour can contradict each other - the switch
flips before you have chosen a matching background. Two things keep that from
producing an unusable theme:

- `derive.py` decides whether text goes light or dark by **measuring the
  background's relative luminance**, not by reading the theme's `dark` flag.
  When it trusted the flag, a "light" theme on a near-black ground derived
  black text at a contrast ratio of 1.16. The same bug sat in the state and
  terminal colours, where walking the wrong way never reached the contrast
  floor at all.
- The creator moves the background to a default for the variant when the two
  disagree, so the switch does what it says.

Every combination now clears 7:1 for body text and 4:1 for state colours. The
accent is left exactly as chosen - it is the user's decision, and it is used
for borders and fills rather than body text.

### Themes from an intent

`osiris/themes/intent.py` makes a theme from what it should be rather than from
chosen colours: a seed colour, a harmony (analogous, complementary,
split-complementary, triadic, monochrome), light or dark, and a mood (muted,
balanced, vivid, pastel). It produces the seeds above, so the rest of the
derivation is shared.

The rules work in **OKLCH**, where equal steps look equal; HLS does not, and a
yellow and a blue at the same HLS lightness look nothing alike. Harmony is a
turn of the hue wheel, mood is a band of lightness and chroma, and the variant
fixes the background's lightness. The seed contributes only its hue.

The secondary takes the harmony's hue at 60% of the accent's chroma. One strong
colour with a quieter partner reads as a palette; at equal strength,
complementary and triadic pairs fought each other.

The tests sweep every combination - twelve hues, five harmonies, four moods,
light and dark - and require body text at 7:1 and both accents at 3:1 against
the background. This is the path a model takes too: it writes an intent, never
colours (see CONTEXT.md).

**From a wallpaper**, `osiris/themes/from_wallpaper.py` reads the picture and
proposes an intent; the rules above still make every colour. The picture is
reduced to twelve colours. Its subject is the most colourful one, weighted by
the square root of how much of the picture it covers, so a small red car
outweighs a large grey sky and anything under 2% is a speck. Its average
lightness proposes light or dark, and its average chroma proposes the mood. Any
of those the person chooses wins over the proposal.

## Wallpapers

Every theme gets a generated wallpaper. `shell/themes/wallpaper.py` renders it
from the palette with numpy and Pillow - both installed on the target, so a
theme written on the machine gets real artwork rather than a fallback.

Three rules make the output reliable rather than lucky:

**Two or three tones.** Background and secondary carry the shapes; the accent
appears only as line work. A wallpaper that spends the whole palette stops
reading as a background.

**The centre stays quiet.** A radial mask flattens the pattern towards the
middle, leaving a calm field for the Osiris mark and for desktop icons. This is
why centre-seeking algorithms - phyllotaxis and friends - are not used: they
put their most interesting structure exactly where the mark goes.

**Low contrast between fills.** Shapes are separated by a few percent of
lightness, not by colour. The structure comes from accent hairlines on the
boundaries. That is the difference between a wallpaper and a poster.

Ten styles, all deterministic in the theme's name, so a theme's wallpaper is
stable across regeneration and no two themes compose alike:

| Style | Mathematics | Reads as |
|---|---|---|
| `contour` | iso-bands through fractional Brownian motion | topography |
| `arcs` | Truchet tiling of quarter circles | woven circuitry |
| `strata` | horizontal bands warped by a slow noise field | sedimentary layers |
| `aurora` | wide gaussian glows centred just beyond the frame, no line work | light from off screen |
| `dots` | a dot grid sized by a slow field, mostly below threshold | a sparse halftone |
| `cells` | Voronoi cells around sites jittered off a grid | stained glass |
| `bubbles` | circle packing, largest first | circles that never touch |
| `ridges` | noise-lifted ridgelines drawn back to front, each hiding those behind | a ridgeline landscape |
| `facets` | a jittered triangle mesh shaded by a slow field | low-poly stone |
| `wave` | sums of sines with a hairline core, a soft halo and a fading sheet beneath | the PS3's rolling ribbons of light |

`wallpaper_variation` in a theme gives it a different composition in the same
style; 0, the default, keeps the name alone as the seed, so wallpapers rendered
before variations existed did not change. A theme that names no style falls
back to one of the original three, chosen by hashing its name; hashing over all
ten would move every such theme to a new wallpaper whenever a style is added.

### Drift

A generated wallpaper **drifts**: it is always gently moving, the way a games
console's home screen is. Two earlier designs did not work and are worth not
repeating. A new frame every few minutes was never seen to move. Blending
between pre-rendered frames was smoother on paper but reads as a slideshow:
shapes dissolve into the next frame's shapes rather than travelling.

So the wallpaper is drawn live, on the GPU, every frame:

- Each moving wallpaper is a **package** (below). The `drift@osiris` Cinnamon
  extension compiles the active one's shader after a shared prelude and draws
  it as the first child of `global.bottom_window_group`: under nemo-desktop's
  transparent icon window and every other window, and a group Muffin never
  restacks. The Osiris mark is an overlay above it, as `compose()` draws it
  above the still wallpaper.
- `shell/themes/drift.py`, started at login, publishes what the extension
  needs in `~/.cache/osiris/drift/current.json`: the package, the theme's
  colours, whatever the package's `still.py` hands its shader - for the
  built-in five, the same random draws as the still renderer, so the two are
  the same picture - and the mark. Or, instead, the reason it cannot move.

The extension paces itself on what Cinnamon spends: up to 30 frames a second,
halved while Cinnamon is over 15% of a core, down to two a second. On a GPU
the wave costs about 5% of a core and ridges, the heaviest, about 4%. It
pauses while anything is fullscreen or the screensaver is up, and draws only
over the theme its state belongs to.

A theme switch changes the moving wallpaper with everything else, beneath the
transition's frozen picture: `engine.apply()` publishes the new theme's state
itself before it releases the picture, rather than leaving drift.py to notice
at its next poll, and the extension swaps at once when the theme has changed.
The one fade of the frozen picture then covers the wallpaper too. Only the
**Drift** switch in Appearance (`~/.config/osiris/drift`), which the extension
reads itself, fades the motion in or out on its own.

### When it does not move

The still wallpaper is always underneath, so every failure leaves the desktop
as it would have been without drift, and Appearance turns its **Drift** button
amber and says why:

- **No GPU.** Drawing every frame on the CPU costs more than a moving
  wallpaper is worth. Muffin reports a software renderer as accelerated, so
  drift.py asks `glxinfo -B` instead: Mesa states "Accelerated: no" outright,
  and NVIDIA's own driver, which does not, is judged by its renderer's name.
  As a backstop, the extension gives up for the session if drawing is still
  over budget at its slowest rate.
- **A shader that does not compile.** drift.py checks every package with
  `glslangValidator` against the exact program Cogl will compile
  (`osiris/themes/wallpapers.py`), and reports errors by the package's own
  line numbers, `name/shader.glsl:3: ...`, so an agent can fix them.
- **A `still.py` that raises.** Reported the same way.

### Wallpaper packages

A package is a folder named after the wallpaper, in
`/usr/share/osiris/themes/wallpapers/` for the shipped five (aurora, cells,
dots, ridges, wave) or `~/.local/share/osiris/wallpapers/` for a user's own -
written by hand or by an agent. A theme names one in `wallpaper_style`, and it
appears in the creator's pattern list under its label. A user's package
replaces a shipped one of the same name.

    wallpaper.json   {"name": "<folder>", "label": "Shown in Appearance", "loop": 60}
    shader.glsl      vec3 wallpaper(vec2 uv) { ... }
    still.py         def still(theme, size, phase=None) -> PIL.Image

- `shader.glsl` is GLSL 1.20, which is what Cogl compiles, after
  `shell/themes/wallpapers/prelude.glsl`. The prelude declares what every
  shader is given - where the loop is (`u_time`, 0 to 1), the monitor
  (`u_size`), and the theme's colours - and a few helpers, `compose()` among
  them. `uv` runs from (0, 0) at the top left to (1, 1). The function returns
  the colour; the mark is drawn above it.
- `still.py` draws the same picture without motion, from the same colours,
  at `phase` radians round the loop (None for the still itself), without the
  mark. It is what previews, the boot screen and a machine without a GPU
  show. It may import `wallpaper` for the theme's tones and helpers.
- `still.py` may also define `uniforms(theme, size)`, returning
  `{"u_name": [components, [floats]]}` for the shader to declare and use, and
  `ranges(theme, size, phases)`, values measured round the loop that the
  extension interpolates into the prelude's `u_range`.

Edit a package while it is showing and drift.py notices within seconds,
checks it again and the desktop picks it up.

Truchet tiling earns its place: each cell's arcs meet the midpoints of its
edges whichever orientation it takes, so neighbouring tiles always connect into
continuous paths. The composition cannot fail, only vary.

Shipped themes name their style in `wallpaper_style`. Hashing seven names over
three styles gave four of one, which is what hashing does; curating is cheap at
this scale. User themes, which have no curator, fall back to the hash.

The Osiris mark is composited in the centre at low opacity from
`branding/logo-mask.png`, an alpha mask rendered from `logo.svg` by
`branding/scripts/make-logo-mask.py`. The mask is checked in and shipped, so
the generator needs no SVG stack on the target.

Preview cards are miniatures of the desktop drawn over the theme's actual
wallpaper at card size. An earlier version drew its own gradient there and the
cards quietly stopped matching the desktop.

### Keeping generated assets current

User assets are cached under `~/.local/share/osiris/`, with
`assets.json` recording what each was rendered from: a hash of the theme
content plus `preview.RENDERER_VERSION`. Both halves are load-bearing. An
earlier version re-rendered only when a file was missing, so an edited theme
kept its old card forever; the obvious fix, comparing timestamps, still misses
the case that actually bit - changing the renderer changes every output without
touching a single theme file. Bump `RENDERER_VERSION` when the drawing changes
and every cached asset refreshes on next load.

Assets in root-owned directories are never refreshed this way. They belong to
the package and are rendered at build time.

## Fonts

Fonts are declared per theme but **must be packaged**, not downloaded. Currently
shipped: `ttf-firacode-nerd` (mono, ligatures), `noto-fonts` and
`noto-fonts-emoji` (UI and fallback), `ttf-jetbrains-mono-nerd`.

A theme naming a font outside that set has to add it to `requires`, which adds
it to `osiris-themes`' dependencies. That keeps "the theme looks wrong" from
being a font that was never installed.

## Open decisions

1. **How many themes ship by default?** Seven exist. More is not obviously
   better - each is a support surface. A curated six to eight, half light and
   half dark, is probably right.
2. ~~**Do splash and greeter follow the theme, or stay branded?**~~ Resolved:
   the **Boot screens** take the colours of one **System theme** per machine,
   chosen with administrator approval, and keep the Osiris mark (CONTEXT.md,
   roadmap P3.3).
3. **Accent independent of theme?** COSMIC and GNOME let you pick an accent
   colour separately from light/dark. It is a nice affordance but multiplies the
   combinations every generated file has to cover.
4. ~~**Per-theme icon themes, really?**~~ Resolved: no. The icon set belongs to
   a **Skin**, so it stays put when the colours change; only the folder tint
   follows the **Theme**.
