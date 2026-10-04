# 4. Configuration lives in data files, not string constants

**Status:** Accepted

## Context

193 lines of configuration were embedded in Python as triple-quoted constants
and dictionaries, spread across five modules: a fastfetch config as a Python
dict that is then serialised to JSON, a `.zshrc` as a string literal, a ghostty
config, LightDM settings, a gschema override, Plank launcher entries, and seven
blocks of archiso profile.

The costs are not theoretical:

- **No syntax checking.** A malformed fastfetch config is a valid Python
  string. The error surfaces at boot, on the target, as a program silently
  falling back to defaults.
- **No syntax highlighting, no formatter, no linter** for the embedded
  language.
- **Diffs read badly.** Changing one JSON key shows as a change to a Python
  string literal.
- **Escaping.** Every brace in an f-string template has to be doubled, and
  every backslash considered twice.
- **The wrong tool is reached for.** The fastfetch config was a Python `dict`
  being dumped to JSON, which is a JSON file written in the wrong notation.

## Decision

Configuration ships as files of its own format, under `osiris/resources/`,
loaded at runtime:

```
osiris/resources/
    bin/launcher                          the two-line Python launchers
    boot/osiris.plymouth, osiris.script   the boot splash
    desktop/dconf-defaults, dconf-profile Cinnamon, Plank and keybinding defaults
    desktop/99-osiris.gschema.override    schema defaults that beat first-login writes
    desktop/lightdm.conf, slick-greeter.conf
    desktop/plank.desktop, osiris-theme.desktop   autostart entries
    fetch/fastfetch.jsonc
    iso/osiris-installer.service          the live medium's installer unit
    shell/zshrc
    terminal/ghostty.conf
```

Python templates them only where a value genuinely has to be computed, and
templating is explicit substitution of named placeholders (`@WALLPAPER@`)
rather than f-string interpolation of a whole document. Not a template
language such as Jinja: every file here is static or needs one or two values,
and logic inside templates is the kind of hidden behaviour this ADR exists to
remove.

Two kinds of text stay in Python on purpose. The PKGBUILD and archiso's
`profiledef.sh` are generated from Python lists, which is how the rule against
authored bash is kept. Values computed from data, such as the dock's launcher
list, stay in Python and are substituted into the file around them.

**Status of the migration:** complete as of the change that added this
paragraph. Earlier, three files had been moved here while the provisioning
scripts kept writing their own inline copies, so the resources were unused.

## Consequences

Each file is checked by the tooling that understands it. A JSON config that
does not parse fails at build time rather than at a user's first login.

Editing a config no longer means editing Python, which widens who can do it.

The cost is indirection: finding what writes a file now takes one more step
than reading the constant beside the code. A resource loader with explicit
paths, rather than scattered `open()` calls, keeps that to one step.

A second cost: resources must be packaged. `pyproject.toml` declares
`package-data`, and anything that reads a resource must go through the loader
rather than assume a path relative to the source tree, which breaks when
installed.
