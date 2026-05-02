# Osiris Roadmap

Work is grouped into four phases. Phases are sequential at the top level: shell before installer before harness before polish. Within a phase, tasks can be parallelized.

Each task lists a definition of done so we know when to move on.

---

## Phase 1: Desktop Shell (P0)

The visible product. Without it nothing else matters. Develops on any Linux box without an Arch VM by pointing AGS and Hyprland at the configs in this repo.

**Phase DoD**: a user runs Hyprland + AGS configs from this repo on any Linux machine. Bar, launcher, notifications all work. Looks intentional, not throwaway.

| ID | Task | DoD |
|---|---|---|
| P0.1 | Hyprland base config: keybinds, gaps, animations, window rules | Logs into Hyprland, can launch terminal, move/tile windows, use workspaces |
| P0.2 | AGS top bar: workspaces, audio, network, battery, clock, system tray | Bar visible on all monitors, all widgets reactive to state changes |
| P0.3 | AGS app launcher (wofi-style replacement) | Keybind opens launcher, fuzzy search across `.desktop` files, launches selected app |
| P0.4 | AGS notification daemon | Notifications appear, group, dismiss; replaces dunst/mako |
| P0.5 | Default theme: one opinionated dark theme, single wallpaper | Coherent color palette across bar, launcher, notifications, GTK apps |
| P0.6 | Terminal default: foot or ghostty (decide), launches bash with sensible `.bashrc` | Open terminal, get a usable prompt with history, completion, sane defaults |
| P0.7 | Login manager: greetd + tuigreet (or alternative) | Boots to login screen, password auth, lands in Hyprland session |

---

## Phase 2: Installer (P1)

Turns the shell into a real distributable OS. Webview frontend in TS, Bun backend, packaged as a live ISO via mkosi.

**Phase DoD**: ISO boots in QEMU. User clicks through the installer. After install + reboot, lands in the Phase 1 shell with the default model downloaded.

| ID | Task | DoD |
|---|---|---|
| P1.1 | mkosi config to build minimal Arch live ISO with shell baked in | `mkosi build` produces a bootable ISO under 2GB |
| P1.2 | Installer webview UI (TS, web framework TBD): wizard flow | All steps render, validation works, can navigate back/forward |
| P1.3 | Bun installer backend: parted, mkfs, pacstrap, arch-chroot wrappers via `Bun.spawn(argv)` | Each step exposes a typed function the UI can call over websocket |
| P1.4 | Disk picker UI with partition preview | User sees current disk layout, picks target, sees what will happen |
| P1.5 | Model selection step: local Gemma default, optional cloud provider config | API key entry, validation against the provider, capability_tier inferred |
| P1.6 | First-boot experience: welcome screen, Ollama check, default model download with progress | Fresh install boots to a welcome flow that ends with model ready |
| P1.7 | Bootloader: systemd-boot with branded splash | Install completes with a working bootloader, splash uses Osiris branding |

---

## Phase 3: Harness (P2)

The AI layer. Largest piece. Most novel work. Sits on top of a working desktop and installer.

**Phase DoD**: user opens chat, asks "change the bar to a warmer color palette," agent edits the AGS theme files in `~/.osiris/`, AGS hot-reloads, bar repaints. Permission prompts work in DEFAULT mode.

| ID | Task | DoD |
|---|---|---|
| P2.1 | Bun daemon scaffold + systemd user service | Daemon starts on login, exposes websocket, accepts connections |
| P2.2 | LLM provider abstraction: OpenAI-compatible base, Claude/Gemini adapters, Ollama default | Switching providers requires only `{baseUrl, model, apiKey}` change, no code path divergence |
| P2.3 | Tool registry: `read_file`, `write_file`, `set_theme`, `launch_app`, `hyprctl_call` | Each tool defined as TS function with one-sentence description; agent can invoke and get typed results |
| P2.4 | Permission model: PLAN / DEFAULT / ALLOW ALL with PLAN as install default | Mode toggle in chat UI; PLAN blocks all writes; DEFAULT prompts on risky |
| P2.5 | `shell_exec` tool sandboxed with bubblewrap, `$HOME` writable, system read-only | Agent can run commands, cannot escape to `/etc` or `/usr` |
| P2.6 | Webview chat UI: streaming markdown, code blocks, tool call visibility | Chat opens in own window, streams responses, shows what tools are running |
| P2.7 | Permission prompt UI: inline approve/deny for risky tool calls | When DEFAULT mode triggers a prompt, user sees what's about to happen and approves |
| P2.8 | Capability warning system: heuristic for code/complex tasks on small models | Inline banner appears when message looks like coding and current model is `small` tier |
| P2.9 | Keybind to summon chat window (Super+Space style) | Configured in Hyprland, summons or focuses the chat window |
| P2.10 | Persistent conversation history (SQLite likely) | Conversations survive daemon restart, browseable in UI |
| P2.11 | `~/.osiris/` skel: TS skeleton with example theme and example widget | New user has a working customizable starting point |

---

## Phase 4: Polish (P3)

Everything that makes Osiris feel like a product, not a project.

**Phase DoD**: someone who has never seen Osiris can install it, use it, and not feel like they're testing a prototype.

| ID | Task | DoD |
|---|---|---|
| P3.1 | Branding pass: logos in installer, login, about screen; bootloader theme; default wallpaper | Brand identity consistent across every visible surface |
| P3.2 | Documentation site or install instructions | Public docs for installation, customization, harness configuration |
| P3.3 | First-run user tutorial delivered via the harness chat itself | New user lands in chat with a "hi, here's how Osiris works" walkthrough |
| P3.4 | Distribution channel: GitHub releases or osiris.sh | ISO downloadable from a stable URL with checksums |
| P3.5 | "AI installs Osiris" mode: agent walks user through install via chat (deferred, requires harness) | Optional toggle on installer, agent partitions and installs via tool calls |

---

## What NOT to do (yet)

- No mobile or tablet form factor.
- No alternative compositors (no Sway, no GNOME, no KDE). Hyprland only.
- No alternative shells or launchers beyond AGS.
- No browser fork or AI browser integration. Use whatever browser ships.
- No custom kernel patches.
- No reproducible-build infrastructure (Nix-style). mkosi is enough.
- No package repository of our own. Use Arch + AUR.
