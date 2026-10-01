# Osiris

A Linux distribution built on Arch: a Cinnamon desktop that is themed,
branded, and installable from a live ISO.

Nothing here is novel in the way a new init system would be. Arch, Cinnamon,
Plank, rofi, LightDM and ghostty all already work. What Osiris adds is
**coherence** - one theme choice retints the GTK stack, the panel, window
decorations, the terminal, the launcher, the dock, the folder icons and the
wallpaper together - and an install that produces that, rather than a base
system you then spend an evening configuring.

```
python3 iso/profile.py        # build the ISO (as root)
```

## What this is, concretely

| | |
|---|---|
| Base | Arch Linux |
| Desktop | Cinnamon (Muffin, X11), Plank dock, rofi launcher |
| Login | LightDM with slick-greeter, branded |
| Terminal | ghostty, FiraCode with ligatures |
| Shell | zsh with oh-my-zsh |
| Themes | Seven shipped, plus a creator. Every palette compiles to a real GTK theme. |
| Installer | GTK4 wizard on a live ISO built with archiso |

Seven themes ship. Each one retints the GTK theme, the Cinnamon panel, window
decorations, the terminal, the launcher, the **dock**, the **folder icons**,
and generates its own wallpaper. Switching is live - no logout.

## Repository layout

```
provision/      Turning a blank disk into an Osiris system
  install.py      partition, pacstrap, configure, bootloader
  packages.py     what an Osiris system is made of, as data
  cinnamon.py     panel, dock and greeter configuration
  apps.py         zsh, ghostty, fastfetch
  branding.py     boot splash and greeter branding
  themes.py       installs the theme system and the Appearance app
  homes.py        writing into a user's home from root, correctly
  run.py          argv-only process helpers

iso/            The live installation medium
  profile.py      generates an archiso profile, then builds the ISO
  live_packages.py  what goes on the medium

apps/
  appearance/     theme picker and creator (GTK4 + libadwaita)
  installer/      the install wizard (GTK4 + libadwaita)

shell/themes/   The theme system
  engine.py       load and apply a theme
  derive.py       a full palette from three colours
  wallpaper.py    generative backgrounds
  icons.py        folder tinting
  plank.py        dock theming
  preview.py      the picker's thumbnails
  *.json          the shipped palettes

branding/       Logos, the mark, generated wallpapers
docs/           Design documents
```

## Documentation

| Document | What it covers |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | The stack and why each piece was chosen |
| [THEMING.md](docs/THEMING.md) | How themes work, how to write one, how the creator works |
| [INSTALLER.md](docs/INSTALLER.md) | Building the ISO, the install flow, the guardrails |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Working on this: the VM, the loop, the gotchas |
| [ROADMAP.md](docs/ROADMAP.md) | Phases and definition-of-done |
| [STATUS.md](docs/STATUS.md) | Where things stand now |
| [CLAUDE.md](CLAUDE.md) | Project context and hard rules, for automated coding sessions |

## Conventions

**No bash that we author.** Build, install, hooks and glue are Python.
Processes are spawned as argv arrays - no `shell=True`, no `bash -c`, no string
interpolation into a command line. The repository contains zero `.sh` files;
the one bash file archiso requires is *generated* by `iso/profile.py`. See
[DEVELOPMENT.md](docs/DEVELOPMENT.md#how-much-bash-is-in-here) for the full
accounting.

**Orchestrate, do not implement.** Osiris ships no GTK theme and no icon set of
its own. GTK, the icon theme spec, fontconfig and Cinnamon all have working
theming; maintaining a fork of any of them is a permanent cost against a moving
target. The value added is coherence - picking one theme sets nine things at
once. See [THEMING.md](docs/THEMING.md).

**No emojis.** Code, configs, docs, commit messages.

## Status

The desktop works, the ISO boots, and the installer produces a system that
boots to it - verified end to end in a VM. See [STATUS.md](docs/STATUS.md) for
what is done, what is known-missing, and the defects fixed along the way.

Next is polish: packaging the tree as `osiris-desktop` and `osiris-themes`,
theming the boot splash and greeter with the palette, and public install
documentation. See [ROADMAP.md](docs/ROADMAP.md).
