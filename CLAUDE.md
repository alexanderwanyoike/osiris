# Osiris OS - Project Context

## Overview

Osiris is a minimal AI-first Linux distribution. v2 is being built ground-up after v1 (Debian + live-build, dual Sway/Cinnamon desktop) was scrapped as too painful to build and too bloated.

The full design is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Read it before making non-trivial decisions.

The build order and priorities are in [docs/ROADMAP.md](docs/ROADMAP.md). Refer to it before starting new work.

## Stack at a glance

- **Base**: Arch Linux
- **Compositor**: Hyprland
- **Desktop shell**: AGS / Astal (TypeScript over GTK)
- **Chat UI**: webview hosting a TS web app
- **Harness daemon**: Bun + TypeScript
- **Installer**: webview frontend + Bun backend, packaged as a live ISO via mkosi
- **Default model**: Gemma 4 2B local via Ollama, with optional cloud providers (OpenAI, Claude, Gemini, OpenRouter)
- **User shell**: bash (universal, expected; do not propose alternatives as default)

## Hard rules

### No bash that we author

The v1 pain point was bash chroot hooks inside a 30-60 minute Docker build with no stack traces. v2 contains zero `.sh` files we wrote. Build, install, hooks, glue: all Python or TypeScript. Agent shell tool spawns binaries via argv arrays (`Bun.spawn(["pacman", ...])`), never `bash -c`.

bash exists on the system as an Arch dependency and is the user's interactive shell. The rule is about what we author, not what's installed.

### No emojis

Project-wide: no emojis in code, configs, docs, commit messages, or PR descriptions. Keep tone professional and technical.

### Research before implementation

Do not guess technical details. Use WebSearch for documentation, syntax, supported features. Verify assumptions before writing code. Examples: "does this config file support tilde expansion," "what is the exact pacman syntax for X," "what tool flag does Y."

### Thinness rules for the harness

The default model is small (2-4B parameters). Every token in system prompts and tool descriptions costs context. Therefore: system prompts under ~500 tokens, tool descriptions one short sentence each, tools added per mode rather than all at once, no chain-of-thought scaffolding in prompts.

### Permission model defaults

PLAN mode (read-only) is the install default. DEFAULT mode (ask-on-risky) and ALLOW ALL are user-toggled. `shell_exec` always runs in a bubblewrap sandbox. Sudo always prompts.

## Development workflow

Phase 1 (shell) can be developed on any Linux machine without an Arch VM. Symlink the AGS configs in this repo into `~/.config/ags`, point Hyprland at `shell/hyprland/`, iterate. No ISO build needed for shell development.

Phase 2 (installer) requires testing in a VM (QEMU recommended) once mkosi produces an ISO.

Phase 3 (harness) develops alongside the shell in a Bun project; the daemon can run on the dev host.

## What this project is not

- Not a Debian or Ubuntu derivative. Arch only.
- Not a multi-DE distro. Hyprland only.
- Not a general-purpose distro. AI-first, opinionated.
- Not built with bash, live-build, Docker chroot hooks, or Calamares. None of that.
