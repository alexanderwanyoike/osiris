# 9. One desktop, Cinnamon

**Status:** Accepted

## Context

The project has tried Sway, Hyprland with an AGS shell, COSMIC, XFCE and
Cinnamon. For a while the install flow carried a `--desktop` flag and package
sets for two of them.

Supporting more than one desktop multiplies everything downstream: the theme
engine needs a backend per desktop, the panel configuration is per desktop,
the greeter session differs, and every feature needs testing on each. The
COSMIC path had a configurator, a package set and a branch in the installer,
and had never once been installed.

Hyprland was dropped because it is a set of parts rather than a desktop - a bar,
a launcher and a notification daemon all have to be chosen and assembled, and
that assembly is the maintenance. AGS compounded it by being AUR-only, which a
distribution cannot depend on.

## Decision

Cinnamon, with Plank as the dock and rofi as the launcher. One desktop, no
flag, no abstraction over desktops.

`packages.for_install()` takes only `software_rendering`.

## Consequences

Every feature is built once, against one desktop, and tested there. The theme
engine targets GTK, Muffin and Cinnamon specifically rather than through an
abstraction that would have exactly one implementation.

Osiris is not for someone who wants a tiling compositor. That is accepted: it
is a small opinionated distribution, not a menu.

The cost is a real ceiling - adding a second desktop later means building the
abstraction that was deliberately not built. If that day comes, the seam will
be the provisioning step, which is already a list of scripts rather than a
monolith.
