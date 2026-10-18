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
| P1.1 | `iso/profile.py` builds the ISO from archiso's releng profile | `python3 iso/profile.py` produces a medium that boots on BIOS and UEFI | boots on UEFI under QEMU, to the live desktop; BIOS not yet tried |
| P1.2 | Installer wizard: region, disk, account, confirm, progress, done | All steps render, validation works, back navigation works | done |
| P1.3 | archinstall does the install (ADR 0012) | The wizard's answers become an archinstall config; archinstall installs the `osiris` package and runs `osiris-setup` | done: run end to end on 2026-10-17 (UEFI, erase disk, ext4) to a themed desktop |
| P1.4 | Disk picker | Lists disks with size and transport; refuses mounted and undersized ones with the reason | done |
| P1.5 | Full provisioning on install | Installed system has the themes, Appearance app, ghostty, zsh and branding, not plain Cinnamon | done |
| P1.6 | First-boot experience: welcome screen | Fresh install boots to a welcome flow | deferred to Phase 3 |
| P1.8 | Disk layout options, software rendering, retry | ext4 or btrfs with subvolumes, zram, detected graphics drivers, retry after failure | done |
| P1.9 | Install alongside another system | Free space or an existing partition, via an archinstall manual layout; GParted to make room | done (UEFI) |
| P1.10 | Full-disk encryption | An "Encrypt the system" switch puts the root in LUKS2 through archinstall; Plymouth asks for the passphrase at boot | done (whole disk, and free space with a new ESP) |
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
| P2.6 | Theme the remaining surfaces: Plymouth splash, greeter | The boot-to-desktop sequence is one palette, not three | moved to P3.3 |

---

## Phase 4: Appearance and the Harness (P3)

Two things Osiris adds over other opinionated desktops, both in service of
consistency: a look that is one choice of colours (a **Theme**) and one choice
of shapes (a **Skin set**) across every surface, and an AI **Harness** that is
part of the operating system rather than an application beside it. The terms
are defined in [CONTEXT.md](../CONTEXT.md); the decisions behind them are ADRs
0013, 0014 and 0015.

**Phase DoD**: switching Theme or Skin set changes every surface at once without
visible intermediate states; any Theme can be made from a seed colour, a
wallpaper or a sentence typed to the Harness; and the Harness works with the
person's own ChatGPT or OpenCode Go account from anywhere in the desktop,
showing everything it sends and does.

**Order.** P3.1 first. Then P3.2 and P3.5 in parallel: they do not depend on
each other. Then P3.3, P3.4 and P3.6, each of which needs one of those two.

| ID | Task | DoD | State |
|---|---|---|---|
| P3.1 | Smooth switching: one batched apply, running terminals reload, crossfade extension (ADR 0014) | A switch shows no intermediate state and open terminals change with everything else; without the extension it still applies as one batch | done |
| P3.2 | The colour model: Theme and Skin separated in the data, OKLCH harmony rules, Themes derived from a Wallpaper, more Generated wallpaper styles, partner colours suggested in the creator | A Theme is colours only; a seed colour or a picture plus a Harmony gives a legible, harmonious palette; existing themes migrate | mostly done: OKLCH harmony, Themes from a Wallpaper, partner colours and Generated wallpaper styles (drawn live on a GPU) are in; Theme and Skin are not yet separated in the data |
| P3.3 | Boot screens follow the System theme: GRUB, Plymouth and the greeter recoloured, changed with administrator approval | Choosing a System theme recolours all three Boot screens; the Osiris mark stays; the live medium keeps Osiris Obsidian | |
| P3.4 | Skins and Skin sets: shape layers on adw-gtk3 and Breeze (ADR 0013), panel layouts, dock geometry, launcher layouts, Harness placement; Appearance shows Skin sets and lets any surface be swapped | At least three Skin sets, each coherent under every shipped Theme; switching set replaces every Skin and a modified set can be chosen again | |
| P3.5 | Harness foundation: Engine port with an opencode adapter (ADR 0015), Settings for Providers with Default and Fallback models, a Usage indicator in the panel, the bar-and-panel surface, the Harness log, Action tiers, editable instructions, memory and permissions, Entry points | A person connects ChatGPT or OpenCode Go without a terminal, summons the Harness from a key, a file, selected text or the terminal, and can see the Provider, model and Usage in play and everything sent and done | |
| P3.6 | Harness capabilities: Theme intent from a sentence, then Programs with manifests, a sandbox, installation and single-file sharing | "A moody theme from this photo" produces applicable Themes; a Program the Harness writes installs only after its manifest is shown and follows the Theme and Skin | |

---

## Phase 5: Updates and hardening (P4)

An installed Osiris keeps up with Arch and with Osiris itself without being
reinstalled, and starts from a safe baseline. Everything here uses tools Arch
maintains (ADR 0012); Osiris supplies configuration and the screens.

**Phase DoD**: a machine installed from one release takes the next through
ordinary updates, keeps the person's Theme, Skins and Harness settings, can be
rolled back if an update goes wrong, and listens on nothing it does not need.

| ID | Task | DoD | State |
|---|---|---|---|
| P4.1 | A hosted, signed package repository | `osiris` and what it bundles (Plank Reloaded) are published at a stable URL, signed with a project key shipped as a keyring package; installed systems keep this repository in pacman.conf in place of the install medium's | |
| P4.2 | Upgrades re-apply Osiris safely | Upgrading the `osiris` package runs `osiris-setup` from a pacman hook; running it twice changes nothing the second time, and it never overwrites a choice the person made (Theme, Skin, keybindings, dock) | |
| P4.3 | Migrations for what Osiris keeps per user | Each per-user format (themes, the Harness's files) carries a version; a newer Osiris migrates older files on login, tested from every released version | |
| P4.4 | Update notice | The panel shows when updates are waiting and installs them on request, with progress, through pacman; never automatically | |
| P4.5 | Roll back a bad update | On btrfs, snapper with snap-pac snapshots before every pacman transaction and grub-btrfs offers them in the boot menu; on ext4 the installer says rollback needs btrfs | |
| P4.6 | Hardening baseline | A firewall on by default allowing nothing in, no services listening that the desktop does not need, checked on a fresh install | |

---

## What NOT to do (yet)

- No mobile or tablet form factor.
- No alternative desktops. Cinnamon only.
- No GTK theme, icon set or compositor of our own. Orchestrate what exists.
- No browser fork. Use whatever ships.
- No custom kernel patches.
- No reproducible-build infrastructure (Nix-style). archiso is enough.
- No manual partitioning in the installer. Encrypting beside a shared EFI
  system partition waits on archinstall supporting an encrypted /boot.
- No hosted package repository until P4.1. The medium carries Osiris's own:
  the `osiris` package and what it bundles because no official repository has
  it (Plank Reloaded). Nothing depends on the AUR.
