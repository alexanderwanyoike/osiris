# Osiris Roadmap

Work is grouped into phases, sequential at the top level: desktop before
installer before polish. Within a phase, tasks can be parallelised.

Each task lists a definition of done so we know when to move on.

---

## Phase 1: Desktop (P0)

The visible product. Without it nothing else matters.

**Phase DoD**: a themed, branded Cinnamon desktop that looks intentional rather
than assembled, and switches theme live.

| ID | Task | DoD | State |
|---|---|---|---|
| P0.1 | Cinnamon trimmed to one top panel, Plank dock, rofi launcher | Boots to a desktop with one panel, a populated dock, and a launcher on Super+Space | done |
| P0.2 | LightDM with slick-greeter, branded | Login screen carries the Osiris mark and the user's name | done |
| P0.3 | Plymouth boot splash | Boot shows the mark rather than kernel messages | done |
| P0.4 | Terminal and shell: ghostty, zsh with oh-my-zsh, FiraCode with ligatures | A new user opens a terminal and gets a configured prompt | done |
| P0.5 | Theme system: each palette compiled to a real GTK theme | Picking a theme retints GTK, panel, decorations, terminal, launcher live | done |
| P0.6 | Appearance app: picker with rendered desktop previews | Each theme shows as a miniature of the desktop in that palette | done |
| P0.7 | Theme creator: a full palette from three colours | Name, light/dark and three colours produce a usable theme | done |
| P0.8 | Generative wallpapers per palette | Every theme has matching artwork with no files to commission | done |
| P0.9 | Dock and folder icons follow the palette | Plank and the folder icons retint with everything else | done |

Seven themes ship. See [THEMING.md](THEMING.md).

---

## Phase 2: Installer (P1)

Turns the desktop into a distributable OS. GTK4 + libadwaita wizard in Python
on a live ISO built with archiso.

**Phase DoD**: ISO boots in QEMU. User clicks through the installer. After
install and reboot, lands in the Phase 1 desktop, themed and branded.

| ID | Task | DoD | State |
|---|---|---|---|
| P1.1 | `iso/profile.py` builds the ISO from archiso's releng profile | `python3 iso/profile.py` produces a medium that boots on BIOS and UEFI | built, not yet booted |
| P1.2 | Installer wizard: region, disk, account, confirm, progress, done | All steps render, validation works, back navigation works | done |
| P1.3 | archinstall does the install (ADR 0012) | The wizard's answers become an archinstall config; archinstall installs the `osiris` package and runs `osiris-setup` | written and unit-tested, not yet run end to end |
| P1.4 | Disk picker | Lists disks with size and transport; refuses mounted and undersized ones with the reason | done |
| P1.5 | Full provisioning on install | Installed system has the themes, Appearance app, ghostty, zsh and branding, not plain Cinnamon | done |
| P1.6 | First-boot experience: welcome screen | Fresh install boots to a welcome flow | deferred to Phase 3 |
| P1.8 | Disk layout options, software rendering, retry | ext4 or btrfs with subvolumes, zram, detected graphics drivers, retry after failure | done |
| P1.9 | Install alongside another system | Free space or an existing partition, via an archinstall manual layout | model only |
| P1.7 | Bootloader: GRUB with a themed menu carrying the mark | Install completes with a working bootloader; the boot menu and splash are both branded | done |

Dropped from this phase: model selection and API key entry (P1.5 as originally
written). The installer installs an operating system; asking for an API key
before there is anything to use it is the wrong order.

Why archiso rather than mkosi, which this document used to specify: mkosi has
no ISO output format. See [ARCHITECTURE.md](ARCHITECTURE.md#the-installer).

---

## Phase 3: Polish (P2)

Everything that makes Osiris feel like a product, not a project.

**Phase DoD**: someone who has never seen Osiris can install it, use it, and not feel like they're testing a prototype.

| ID | Task | DoD | State |
|---|---|---|---|
| P2.1 | Branding pass: logos in installer, login, about screen; bootloader theme; default wallpaper | Brand identity consistent across every visible surface | mostly done |
| P2.2 | Public installation and customisation documentation | Someone who has not seen the repo can install Osiris and write a theme | |
| P2.3 | First-run welcome: what Osiris is, where Appearance lives | A fresh install explains itself once, briefly | |
| P2.4 | Distribution channel: GitHub releases or osiris.sh | ISO downloadable from a stable URL with checksums | |
| P2.5 | Package the tree properly | Installing is pacman installing packages, not a script copying files | `osiris` package exists; a hosted repository for updates does not |
| P2.6 | Theme the remaining surfaces: Plymouth splash, greeter | The boot-to-desktop sequence is one palette, not three | |

---

## What NOT to do (yet)

- No mobile or tablet form factor.
- No alternative desktops. Cinnamon only.
- No GTK theme, icon set or compositor of our own. Orchestrate what exists.
- No browser fork. Use whatever ships.
- No custom kernel patches.
- No reproducible-build infrastructure (Nix-style). archiso is enough.
- No disk encryption, dual boot or manual partitioning in the installer yet.
- No package repository of our own. Use Arch + AUR.
