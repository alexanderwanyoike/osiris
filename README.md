<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="branding/logo-white.svg">
    <img src="branding/logo.svg" alt="Osiris" width="120">
  </picture>
</p>

<h1 align="center">Osiris</h1>

<p align="center">
  A Linux desktop you can ask for things.
</p>

<p align="center">
  <a href="https://github.com/alexanderwanyoike/osiris/actions/workflows/ci.yml"><img src="https://github.com/alexanderwanyoike/osiris/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/status-alpha-orange" alt="Status: alpha">
  <img src="https://img.shields.io/badge/base-Arch%20Linux-1793d1" alt="Base: Arch Linux">
</p>

![The Osiris desktop: a terminal and Pomodoro, a timer Osiris built, both on the Tokyo Night Theme](docs/screenshots/desktop.png)

Ask for a focus timer, and Osiris builds one: a real app, in your applications
menu, ready to keep in your dock, and painted in your theme, so it looks like
it came with the system. Ask for a calmer look, and the whole desktop changes
at once. Whatever it does, you can undo.

- **AI first.** Asking is how you get things done. Osiris builds the small
  tools you need, instead of sending you off to find, install and configure
  them.
- **Coherent.** Everything looks and works as one system: the windows, the
  panel, the dock, the terminal, and the apps Osiris builds for you.
- **Yours.** What Osiris builds is real code in a folder of yours, with its
  whole history, to read, change or delete. You choose the AI model, upgrades
  never touch your choices, and Osiris itself is open source.

## AI first

**Super+A**, or the button at the right of the panel, slides Osiris in from the
right edge. Ask it for something in your own words.

- **It builds Programs.** Ask for a Pomodoro timer and Osiris writes one
  and puts a card under its answer: **Try** runs it, **Install**
  adds it to your applications menu and rofi, and from there you can keep it in
  the dock. It writes Python, C or C++, Rust, Go or JavaScript.
- **It changes the desktop.** Ask for "a calm theme for working late" and
  Osiris makes one and applies it. It describes what you asked for, and the
  desktop's own colour rules turn that into a legible palette.
- **Every change ends with an Undo**, which reverses it without asking the AI
  again.
- **The desktop decides what Osiris may do, not the AI model.** It may look
  around, make changes that can be undone, and edit files only inside its own
  Programs' folders. Anything else it reaches for is refused, and you see what
  was refused.

![Osiris expanded: the conversation that built Pomodoro, beside its code](docs/screenshots/harness.png)

## Coherent

Choose a Theme and the apps, the window borders, the Cinnamon panel, the Plank
dock, the rofi launcher, the terminal, the folder icons and the wallpaper all
change together, live, without logging out. The Programs Osiris builds change
with them: they are written with GTK 4 and libadwaita, and follow your Theme as
you switch it.

- **Super+T** opens a full-screen switcher: arrow through the Themes, Enter to
  apply.
- Seven Themes ship: Osiris Obsidian, Tokyo Night, Nord, Catppuccin Mocha,
  Rose Pine, Rose Pine Dawn and Everforest.
- Make your own in the Appearance app, from one colour or from a picture, or
  ask Osiris for one.
- Every Theme has a generated wallpaper, and on a machine with a GPU the
  wallpaper moves.

![Super+T, the Theme switcher](docs/screenshots/switcher.png)

![The same desktop on Rose Pine Dawn: the terminal and Pomodoro repaint with it](docs/screenshots/light.png)

## Yours

- **Programs are yours.** Each one lives in `~/Code/<name>` as a git
  repository, one commit per change, so you can see what Osiris did and when.
  Open it in any editor, or hand it to another coding agent: an `AGENTS.md`
  explains how to carry on. Uninstalling a Program keeps its code.
- **You choose the model.** Osiris runs its AI through
  [opencode](https://opencode.ai), so any provider opencode supports works,
  and you connect your own account or key.
- **Upgrades keep what you chose.** Updating Osiris never overwrites your
  Theme, your dock, your terminal settings or the files you edit. Each home
  catches up at your next login, and the Osiris apps that were running restart
  onto the new version once you put them away.
- **Open source.** Osiris is free software under the GPL, and builds on Arch,
  Cinnamon and other open source projects rather than replacing them.

## Installing

The live ISO boots on BIOS and UEFI machines into the full Osiris desktop, with
**Install Osiris** on it. The installer asks for region, disk, filesystem,
encryption and an account, then hands the work to Arch's own
[archinstall](https://github.com/archlinux/archinstall), which partitions the
disk and sets up the bootloader. You end up with the finished desktop, not a
base system to configure.

- Erase a disk, or install beside another system on a UEFI machine.
- ext4, or btrfs with subvolumes and compression.
- Optional encryption of the whole system, unlocked at boot behind the Osiris
  boot splash.

![The login screen](docs/screenshots/greeter.png)

## The stack

| | |
|---|---|
| Base | Arch Linux |
| Desktop | Cinnamon (Muffin, X11), Plank dock, rofi launcher (Super+Space) |
| Login and boot | LightDM with slick-greeter, Plymouth, GRUB, all branded |
| Terminal | ghostty, FiraCode Nerd Font with ligatures |
| Shell | zsh with oh-my-zsh |
| Apps | Appearance, the Theme switcher, the Osiris drawer and the installer: GTK 4 and libadwaita, in Python |
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

Working today: asking Osiris and the Programs it builds, the themed desktop,
the seven Themes and the creator, the Super+T switcher, the installer, and
upgrades that keep your choices.

Not there yet:

- **Osiris updates on installed machines.** An installed system takes Arch's
  updates through pacman, but there is no hosted Osiris package repository yet,
  so it cannot get new versions of Osiris itself.
- **Skins.** Swapping the shape of the desktop (window style, panel, dock,
  launcher) as well as its colours is designed and prototyped, not built.
- **Programs run unconfined**, as you. Osiris says so before you install one.

[ROADMAP.md](docs/ROADMAP.md) has every phase and its definition of done.

## How it is built

Three rules shape the code:

- **Use what exists, and make it one.** Osiris doesn't make its own window
  style, icon set or graphics engine. It takes well-made Linux pieces
  (Cinnamon, Plank, rofi, ghostty, the adw-gtk3 theme, the Papirus icons) and
  makes them look and work as one system. There is less of our own code to
  maintain, and the pieces keep improving upstream.
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
| [HARNESS.md](docs/HARNESS.md) | The AI you ask (the Harness, in the code): its tools, what it may do, and why |
| [PROGRAMS.md](docs/PROGRAMS.md) | How Osiris builds, tries and installs Programs |
| [INSTALLER.md](docs/INSTALLER.md) | Building the ISO, the install flow, the guardrails |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Working on Osiris: the VM, the loop, the traps |
| [CONTEXT.md](CONTEXT.md) | The project's language: Theme, Skin, Harness, Program and the rest |
| [docs/adr/](docs/adr) | The architecture decisions, one per file |

## Contributing

Contributions are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) explains the
branch workflow, the checks a pull request has to pass, and the house rules.

## License

Osiris is free software, licensed under the
[GNU General Public License, version 3 or later](LICENSE). You may use, study,
change and share it; if you distribute a changed version, you share your
changes under the same terms.
