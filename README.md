<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="branding/logo-white.svg">
    <img src="branding/logo.svg" alt="Osiris" width="120">
  </picture>
</p>

<h1 align="center">Osiris</h1>

<p align="center">
  Arch underneath. A Cinnamon desktop themed as one system.<br>
  An AI built in that changes your desktop and builds you programs.
</p>

<p align="center">
  <a href="https://github.com/alexanderwanyoike/osiris/actions/workflows/ci.yml"><img src="https://github.com/alexanderwanyoike/osiris/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/status-alpha-orange" alt="Status: alpha">
  <img src="https://img.shields.io/badge/base-Arch%20Linux-1793d1" alt="Base: Arch Linux">
</p>

![The Osiris desktop: a terminal and a Program the Harness built, both on the Tokyo Night Theme](docs/screenshots/desktop.png)

Osiris is a Linux distribution with a narrow scope on purpose. It writes no GTK
theme, no icon set and no compositor of its own; Arch, Cinnamon, Plank, rofi,
LightDM and ghostty already work. What it adds is **coherence**: one Theme
choice repaints every surface of the desktop at once, live. It also adds an
install that gives you that desktop, so you aren't left with a base system and
an evening of configuring, and the **Harness**, an AI that can change the
desktop and build programs for you.

## What you get

### One Theme, every surface

Choose a Theme and the GTK 3 and GTK 4 applications, the window borders, the
Cinnamon panel, the Plank dock, the rofi launcher, the terminal, the folder
icons and the wallpaper all change together, without logging out.

- **Super+T** opens a full-screen switcher: arrow through the Themes, Enter to apply.
- Seven Themes ship: Osiris Obsidian, Tokyo Night, Nord, Catppuccin Mocha,
  Rose Pine, Rose Pine Dawn and Everforest.
- Make your own in the Appearance app, from one colour or from a picture, or
  ask the Harness for "a calm theme for working late". Osiris derives a
  legible palette with OKLCH harmony rules, so a Theme stays readable.
- Every Theme has a generated wallpaper, and on a machine with a GPU the
  wallpaper moves.

![Super+T, the Theme switcher](docs/screenshots/switcher.png)

![The same desktop on Rose Pine Dawn: the terminal and the Program repaint with it](docs/screenshots/light.png)

### The Harness

**Super+A**, or the button at the right of the panel, slides the Harness in
from the right edge. It is an AI agent that runs inside Osiris, with tools that
let it act on your desktop.

- **It makes and applies Themes.** It describes what you asked for, and
  Osiris's own rules turn that into the colours. Every change it makes ends
  with an Undo.
- **It builds Programs.** Ask for a Pomodoro timer and it writes one in
  `~/Code/pomodoro`, a git repository with one atomic commit per change. It
  writes Python, C or C++, Rust, Go or JavaScript, and its windows use GTK 4
  and libadwaita, so they follow your Theme as you change it. From the card
  under its answer you **Try** a Program, then **Install** it into the
  applications menu, rofi and the dock.
- **Osiris decides what it may do, not the model.** It may look around and
  make changes that can be undone, and edit files only inside a Program's own
  folder. Anything else it reaches for is refused, and the drawer shows you
  what was refused.
- **Bring your own model.** The agent loop runs on
  [opencode](https://opencode.ai), so any provider opencode supports works.
- Conversations are kept, grouped by Project. Expand the drawer and the code
  a Program is made of sits beside the conversation.

![The Harness expanded: a conversation and the Program it built, side by side](docs/screenshots/harness.png)

### An installer that leaves a finished desktop

The live ISO boots on BIOS and UEFI machines into the full Osiris desktop, with
**Install Osiris** on it. The installer is a GTK 4 app that asks for region,
disk, filesystem, encryption and an account, then hands the work to Arch's own
[archinstall](https://github.com/archlinux/archinstall). Osiris never writes
partitioning, bootloader or encryption code of its own.

- Erase a disk, or install beside another system on a UEFI machine.
- ext4, or btrfs with subvolumes and compression.
- Optional encryption of the whole system, unlocked at boot behind the Osiris
  boot splash.
- GRUB, Plymouth and the login screen all carry the Osiris mark.

![The login screen](docs/screenshots/greeter.png)

### Upgrades that keep what you chose

Upgrading Osiris never overwrites your Theme, your dock, your terminal
settings or the files you edit. Setup reruns after an upgrade, each home
catches up at your next login, and the Osiris apps that were running restart
onto the new code once you put them away.

## The stack

| | |
|---|---|
| Base | Arch Linux |
| Desktop | Cinnamon (Muffin, X11), Plank dock, rofi launcher (Super+Space) |
| Login and boot | LightDM with slick-greeter, Plymouth, GRUB, all branded |
| Terminal | ghostty, FiraCode Nerd Font with ligatures |
| Shell | zsh with oh-my-zsh |
| Apps | Appearance, the Theme switcher, the Harness and the installer: GTK 4 and libadwaita, in Python |
| Agent engine | opencode |

## Get it

Osiris is alpha software. It installs and runs, but expect rough edges, and
try it in a virtual machine before trusting it with a disk you care about.

There is no published ISO yet; for now you build it yourself. On an Arch Linux
machine with `archiso` installed:

```bash
python3 iso/repo.py
```

```bash
sudo python3 iso/profile.py
```

The first command builds the `osiris` package as a normal user (makepkg
refuses to run as root). The second builds the ISO into
`build/out/osiris-<version>-x86_64.iso`. It needs root and a network
connection, and takes around half an hour. [INSTALLER.md](docs/INSTALLER.md)
has the details and how to boot the result in QEMU.

## Where it stands

Working today: the themed desktop, the seven Themes and the creator, the
Super+T switcher, the Harness with Programs, the installer, and upgrades that
keep your choices.

Not there yet:

- **Osiris updates on installed machines.** An installed system takes Arch's
  updates through pacman, but there is no hosted Osiris package repository yet,
  so it cannot get new versions of Osiris itself.
- **Skins.** Swapping the shape of the desktop (window style, panel, dock,
  launcher) as well as its colours is designed and prototyped, not built.
- **Programs run unconfined**, as you. The Harness says so before you install one.

[ROADMAP.md](docs/ROADMAP.md) has every phase and its definition of done.

## How it is built

Three rules shape the code:

- **Orchestrate, do not implement.** Osiris configures and generates against
  what upstream already ships, rather than maintaining a theme, an icon set or a
  desktop component of its own.
- **Never hand-roll critical machinery.** Anything that could erase a disk or
  leave a machine unbootable (partitioning, bootloaders, building the ISO) is
  done by the tools Arch maintains: archinstall, archiso, pacman.
- **No bash that we author.** Build, install and glue code is Python, and every
  process is spawned as an argv list, never through a shell. The repository has
  no `.sh` files; the one bash file archiso requires is generated.

The code is tested test-first, with `ruff`, `mypy --strict`, import-layer
contracts and `pytest` in CI, and the GTK apps are driven headless under Xvfb.

## Documentation

| Document | What it covers |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | The stack and why each piece was chosen |
| [THEMING.md](docs/THEMING.md) | How Themes work, how to write one, how the creator works |
| [HARNESS.md](docs/HARNESS.md) | The Harness: its tools, what it may do, and why |
| [PROGRAMS.md](docs/PROGRAMS.md) | How the Harness builds, tries and installs Programs |
| [INSTALLER.md](docs/INSTALLER.md) | Building the ISO, the install flow, the guardrails |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Working on Osiris: the VM, the loop, the traps |
| [CONTEXT.md](CONTEXT.md) | The project's language: Theme, Skin, Harness, Program and the rest |
| [docs/adr/](docs/adr) | The architecture decisions, one per file |

## Contributing

Contributions are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) explains the
branch workflow, the checks a pull request has to pass, and the house rules.
