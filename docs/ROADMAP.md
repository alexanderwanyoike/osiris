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
P3.7 needs nothing else, and comes after the first slice of P3.5.

| ID | Task | DoD | State |
|---|---|---|---|
| P3.1 | Smooth switching: one batched apply, running terminals reload, crossfade extension (ADR 0014) | A switch shows no intermediate state and open terminals change with everything else; without the extension it still applies as one batch | done |
| P3.2 | The colour model: Theme and Skin separated in the data, OKLCH harmony rules, Themes derived from a Wallpaper, more Generated wallpaper styles, partner colours suggested in the creator | A Theme is colours only; a seed colour or a picture plus a Harmony gives a legible, harmonious palette; existing themes migrate | mostly done: OKLCH harmony, Themes from a Wallpaper, partner colours and Generated wallpaper styles (drawn live on a GPU) are in; Theme and Skin are not yet separated in the data |
| P3.3 | Boot screens follow the System theme: GRUB, Plymouth and the greeter recoloured, changed with administrator approval | Choosing a System theme recolours all three Boot screens; the Osiris mark stays; the live medium keeps Osiris Obsidian | |
| P3.4 | Skins (ADR 0019): skinpacks built from upstream Sass in the Theme's colours, a Skins section in Appearance, seven Skins (Osiris, Colloid, Graphite, Orchis, Qogir, Jasper, elementary) | Choosing a Skin restyles windows, panel, dock and libadwaita apps in the current Theme; switching Theme keeps the Skin | started: skinpacks (`osiris/skins`), the engine wearing the chosen Skin on every Theme switch, the Skins section with Open, Export and Delete, Super+S to switch Skins as Super+T switches Themes, all seven Skins, packs carrying their own icons, cursor, font and launcher, and Osiris's own apps following a Skin live; the person's own Skins with history, a Skin editor, sharing, importing downloaded themes, icon sets, cursors and fonts, and Osiris making and changing a Skin through its own tools, refused unless it is data only. To come: icon sets in the shipped packs, and icons and cursors drawn in the Theme's colours |
| P3.5 | Harness foundation: Engine port with an opencode adapter (ADR 0015), Settings for Providers with Default and Fallback models, a Usage indicator in the panel, the bar-and-panel surface, the Harness log, Action tiers, editable instructions, memory and permissions, Entry points | A person connects ChatGPT or OpenCode Go without a terminal, summons the Harness from a key, a file, selected text or the terminal, and can see the Provider, model and Usage in play and everything sent and done | started: the Engine port, the opencode 2.0 adapter, the Harness log, the drawer on Super+A and the panel, and answers drawn as Markdown in two Skins that follow the Theme are in; Action tiers exist for looks and undoable changes |
| P3.6 | Harness capabilities: Theme intent from a sentence, then Programs with manifests, a sandbox, installation and single-file sharing | "A moody theme from this photo" produces applicable Themes; a Program the Harness writes installs only after its manifest is shown and follows the Theme and Skin | started: Themes from a sentence, through the Osiris tools with an Undo. Programs v0 designed ([PROGRAMS.md](PROGRAMS.md), ADR 0017): built in `~/Code` with atomic commits, installed from a commit into the menu, rofi and Plank, unconfined until the sandbox; Themes from a photo to come |
| P3.7 | Sudo delegation: a program with no terminal that runs `sudo` (an agent's shell, the Harness) gets an Osiris prompt asking a person for the administrator password; the program never sees it | `sudo` from the Harness's agent shows an admin password card in its Conversation, and `sudo -A` from any other program a dialog naming the asking program; both show the exact command; the password goes from the card or dialog to sudo only; Deny fails the command; a person in a real terminal still gets the normal prompt; `pacman -S`/`-R` show the packages and size from pacman's own plan (`--print`); `rm` lists the files and marks the deletion as permanent; a shell string (`sh -c`, a script) is shown in full and labelled, never summarised | started (ADR 0018): the agent's sudo (`/usr/lib/osiris/agent-bin/sudo`, `sudo -k -A`) asks through the askpass helper, which asks the Harness for a card or shows its own dialog; shell strings and scripts are labelled; nothing is cached, every command asks. The earlier note that sudo runs the `/etc/sudo.conf` helper by itself without a terminal was wrong: sudo 1.9.17 uses a helper only with `-A`, so the agent's sudo is wrapped and other programs reach the dialog only with `-A`. To come: pacman's plan and `rm`'s file list on the card, and checking on a VM that Claude Code's shell, which may give sudo a terminal, gets the prompt it can answer |
| P3.8 | Generated media: images, video and 3D models through a media Provider behind one port (candidates: fal.ai and OpenRouter, possibly both), so the source can change; then Themes from a description, whose generated picture is the Wallpaper and whose palette comes from it (osiris/themes/from_wallpaper.py), and artwork for Programs | A media Provider is connected in Settings like a model Provider; "make me a theme from a misty forest at dawn" gives an applied Theme with a generated Wallpaper, with Undo; generated video and 3D models are kept as files the person owns; swapping the Provider changes no other code | idea, 2026-10-20: replaces the ChatGPT-plan image route, which was unofficial outside ChatGPT; which Provider offers which media, and how they are billed, to be checked in a design session. Planned in [Thoth: media](https://github.com/alexanderwanyoike/osiris/milestone/5), fal.ai first |
| P3.9 | A richer Conversation: answers show images (generated ones too), Mermaid diagrams drawn rather than shown as code, and previews of video and 3D models | An image, a Mermaid diagram, a video and a 3D model in an answer each render in place, follow the Theme, and open full size | idea, 2026-10-20; planned in [Thoth for research](https://github.com/alexanderwanyoike/osiris/milestone/3) |
| P3.10 | Tool calls in full: each step in the folded activity record opens to show what the agent asked for and what came back | A step opens to its input and its output, long output folded, and a refused step says why | idea, 2026-10-20; planned in [Thoth for coding](https://github.com/alexanderwanyoike/osiris/milestone/2) |

### Thoth

The Harness is being renamed **Thoth**: opencode, the Engine, is what is
commonly called a harness, and Osiris's own AI client needs a name of its own.
Until the rename lands, CONTEXT.md and the rows above still say Harness.

The next stretch of work is in Units, each tracked as a GitHub milestone whose
issues are its slices.

| Unit | Milestone | Covers |
|---|---|---|
| The rename | [Thoth: the rename](https://github.com/alexanderwanyoike/osiris/milestone/1) | CONTEXT.md, the ADRs and the code use Thoth, Harness and Osiris as newly defined |
| Coding | [Thoth for coding](https://github.com/alexanderwanyoike/osiris/milestone/2) | Undo per request, checks before "done", P3.10, a clearer approval card, typing while it works |
| Research | [Thoth for research](https://github.com/alexanderwanyoike/osiris/milestone/3) | Web search with sources, documents on the Canvas, P3.9 |
| Models | [Thoth: models](https://github.com/alexanderwanyoike/osiris/milestone/4) | Local models, and a Claude plan through opencode |
| Media | [Thoth: media](https://github.com/alexanderwanyoike/osiris/milestone/5) | P3.8, fal.ai first |
| Parity | [Thoth: parity](https://github.com/alexanderwanyoike/osiris/milestone/6) | What a full AI desktop app offers, beyond the Units above |

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
| P4.1 | A hosted, signed package repository | `osiris` and what it bundles (Plank Reloaded) are published at a stable URL, signed with a project key shipped as a keyring package; installed systems keep this repository in pacman.conf in place of the install medium's | built: tagging vX.Y.Z builds the ISO and the packages on GitHub, signs the packages with the project key, and publishes both to R2 at https://osiris-downloads.alphaneuron.net/; the key ships in the osiris package as a pacman keyring, and setup points pacman at repo/$arch. A separate keyring package can follow if the key ever rotates |
| P4.2 | Upgrades re-apply Osiris safely | Upgrading the `osiris` package runs `osiris-setup` from a pacman hook; running it twice changes nothing the second time, and it never overwrites a choice the person made (Theme, Skin, keybindings, dock) | built, not yet tried on an installed machine: the hook (`zz-osiris-setup.hook`), setup and Theme switches seed the person's files once and write only what Osiris generates (`osiris.provision.seeding`), and running Osiris apps restart onto the new code once put away (`osiris.provision.upgrade`) |
| P4.3 | Migrations for what Osiris keeps per user | Each per-user format (themes, the Harness's files) carries a version; a newer Osiris migrates older files on login, tested from every released version | started: each home records the Osiris version it was brought up to, and the first login on a newer one re-applies the person's Theme, regenerating what Osiris keeps there (`osiris.themes.at_login`). No format carries its own version yet; the Theme/Skin data split will be the first real migration |
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
