# 5. Orchestrate existing components, do not write our own

**Status:** Accepted

## Context

A distribution that wants a coherent look has two options. It can write its own
GTK theme, icon set, panel and file manager - as elementary OS and Deepin do -
or it can configure the ones that exist.

Writing them is a permanent cost against four independently moving upstreams.
GTK's internals change between minor releases, icon themes drift as
applications change their icon names, and a desktop shell is a full-time
project. Distributions that take this path spend most of their effort there.

Osiris has one maintainer.

## Decision

Osiris ships **no GTK theme, no icon set and no desktop component of its own**.
Every one comes from Arch's repositories. What Osiris adds is the configuration
that makes them agree with each other.

Concretely:

- The generated GTK theme `@import`s `adw-gtk3` and overrides colour
  definitions on top. It is not a fork.
- Folder tinting **selects among Papirus's own shipped colour variants** by
  symlink. Not one icon is drawn or recoloured.
- The dock is Plank with a generated `dock.theme`. The panel is Cinnamon's own.
- The launcher is rofi with a generated `.rasi`.

## Consequences

An upstream release improves Osiris for free, and a breaking upstream change
costs a configuration fix rather than a port.

The visible value of the project is **coherence**: one theme choice retints
nine surfaces together, where a user doing it by hand would match nine things
separately. That is a real thing to offer and it is cheap to maintain.

The cost is a ceiling on how distinctive the result can look. Osiris cannot
have a visual identity that no packaged theme can express. That is accepted:
the alternative is a maintenance burden the project cannot carry.

The rule has teeth. When a feature appears to require writing a component, the
answer is to find what upstream already ships. Folder tinting looked like it
needed an icon theme; Papirus already had the icons.
