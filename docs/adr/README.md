# Architecture decision records

One file per decision that would otherwise be re-litigated every few months,
or re-discovered the hard way. Each records what was decided, what it was
decided *against*, and what it costs - the last one being the part that is
usually missing and always wanted later.

A record is immutable once accepted. If a decision changes, write a new record
that supersedes it and say so in both.

| | Decision | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-python-and-argv-only-execution.md) | Python, and argv-only process execution | Accepted |
| [0003](0003-ports-and-adapters.md) | Ports and adapters around the operating system | Accepted |
| [0004](0004-configuration-is-data.md) | Configuration lives in data files, not string constants | Accepted |
| [0005](0005-orchestrate-do-not-implement.md) | Orchestrate existing components, do not write our own | Accepted |
| [0006](0006-a-theme-is-a-compiled-gtk-theme.md) | A palette compiles to a real GTK theme per theme | Accepted |
| [0007](0007-archiso-not-mkosi.md) | archiso, not mkosi, for the installation medium | Accepted |
| [0008](0008-grub-not-systemd-boot.md) | GRUB, not systemd-boot | Accepted |
| [0009](0009-one-desktop.md) | One desktop, Cinnamon | Accepted |
| [0010](0010-the-installer-imports-the-install.md) | The installer imports the install flow | Accepted |
| [0011](0011-testing-strategy.md) | Testing strategy, and what is deliberately not tested | Accepted |
| [0012](0012-do-not-hand-roll-critical-machinery.md) | Do not hand-roll critical system machinery | Accepted |
| [0013](0013-gtk-skins-are-shape-layers-on-recolourable-bases.md) | GTK skins are shape layers on recolourable bases | Accepted |
| [0014](0014-cinnamon-extension-for-theme-transitions.md) | A Cinnamon extension for theme transitions | Accepted |
| [0015](0015-harness-owns-tools-rents-engine.md) | The harness owns its tools and surfaces and rents its engine | Accepted |

## Format

Context, Decision, Consequences. Short. If a record needs more than a page it
is probably two decisions.
