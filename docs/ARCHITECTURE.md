# Osiris Architecture

This document captures the design of Osiris v2. v1 (Debian + live-build, dual Sway/Cinnamon desktop) was scrapped: too painful to build, too bloated, not the vision. v2 is a ground-up rebuild around a different premise.

## Vision

Osiris is a minimal AI-first operating system. The premise: modern AI assistants can do most of what desktop GUI software does, so the OS should be a thin substrate around an AI interface rather than shipping window managers, file managers, theme tools, and a hundred other applications.

The user's primary interface is a chat panel summoned by a keybind. The agent has tools to manipulate the system: change the theme, install a package, edit a config, run a command, launch an app. Anything the user would normally click through, the agent can do. The desktop itself is fully customizable by the agent because the customization surface is TypeScript files in a known location.

A terminal exists and bash is the user's login shell, but the user is never required to type a command to use the system. The terminal is a fallback, not the primary UX.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Base distro | Arch Linux | Rolling, minimal, no opinionated bloat, fast package availability |
| Compositor | Hyprland | Rich live IPC, hot-reload of every setting, mature |
| Desktop shell | AGS / Astal (TypeScript over GTK) | Reactive TS framework for bar, launcher, OSDs, notifications. Hot-reloads on save. |
| Chat UI | Webview hosting a TS web app | Rich markdown, code blocks, streaming, attachments. Native GTK chat is awkward. |
| Harness daemon | Bun + TypeScript | Fast, single-binary, native TS, matches the rest of the stack |
| Installer | Webview frontend (TS) + Bun backend, packaged as an Arch live ISO via mkosi | Same TS aesthetic from boot through daily use. mkosi is declarative, no bash hooks. |
| Default model | Gemma 4 2B local via Ollama | Works offline out of the box, no required cloud signup |
| Provider neutrality | OpenAI-compatible API as universal protocol | Adapter shims for Claude and Gemini if needed; OpenAI/OpenRouter/Ollama native |
| User shell | bash | Universal, expected on Linux. Ship a sensible `/etc/skel/.bashrc`. |
| Login manager | TBD (greetd + tuigreet candidate) | Minimal, no GTK greeter |
| Terminal | TBD (foot or ghostty candidate) | Wayland-native |

## Components

### The harness

A long-running Bun daemon that:

1. Runs the agent loop: model calls, tool execution, conversation state.
2. Owns the tool surface: filesystem ops, shell exec (sandboxed), Hyprland IPC via `hyprctl`, AGS reload, pacman wrapper, optional browser automation.
3. Enforces the permission model (see below).
4. Exposes a local websocket for the chat UI.
5. Maintains persistent conversation history.
6. Runs as a systemd user service.

The chat UI is a separate webview process that talks to the daemon over websocket. Two processes, one mental model.

### The user's `~/.osiris/` project

A TypeScript project the agent edits to customize the system. Themes, widgets, keybinds, agent prompts, tool configs all live as TS modules. AGS hot-reloads on save. This is the surface the agent operates on for "make a new theme" or "add a calendar widget."

### The installer

ISO boots into a minimal Wayland session running just the installer webview fullscreen. User clicks through:

1. Language and keyboard
2. Disk selection (with partition preview)
3. Username, password, hostname
4. Default model selection (local Gemma, or configure cloud provider with API key)
5. Optional API keys for OpenAI, Claude, Gemini, OpenRouter
6. Install button: shows progress for partitioning, formatting, pacstrap, config copy, bootloader install, model download

Backend is Bun spawning binaries directly (`Bun.spawn(["parted", ...])`), never `bash -c`.

## Permission model

Three discrete modes the user toggles in the harness UI. Default on fresh install is **PLAN**.

| Mode | Behavior |
|---|---|
| **PLAN** | Read-only. Agent can read files, query system state, and respond, but cannot execute, write, or modify anything. Safe default. |
| **DEFAULT** | Ask-on-risky. Reads and safe writes (inside `~/.osiris/`, `$HOME` non-system files) auto-allowed. Sudo, package install, network writes, and shell exec prompt for confirmation. |
| **ALLOW ALL** | No prompts. Power user / autonomous mode. |

`shell_exec` runs inside bubblewrap with `$HOME` and `~/.osiris/` writable, system paths read-only. Sudo-requiring tools always prompt regardless of mode.

## Capability warnings

The default model (Gemma 4 2B local) is small. It cannot do non-trivial code generation or multi-step planning well. The harness flags each provider config with a `capability_tier` (small | medium | large) at install time. When the user's message triggers a heuristic suggesting the task exceeds the current model (length over a threshold, code-task keywords like `build`/`implement`/`debug`/`refactor`, code blocks present), the chat panel shows an inline warning: "This task may exceed Gemma's capability. Configure a stronger model? Send anyway?"

## Conventions

### No bash that we author

The v1 pain point was bash chroot hooks inside a 30-60 minute Docker build, with no stack traces and no debugger. v2 contains zero `.sh` files we wrote. Build, install, hooks, glue: all Python or TypeScript. Agent shell tool spawns binaries via argv arrays, never `bash -c`.

bash still exists on the system (Arch base depends on it, PKGBUILDs are bash) and bash is the user's interactive login shell. The rule is about what *we* write, not what's installed.

### Thinness rules for the harness

The default model is 2-4B parameters. Every token in the system prompt and tool descriptions eats into a tiny context. Therefore:

- System prompt under ~500 tokens. No role-play preamble, no formatting instructions, no examples.
- Tool descriptions one short sentence each.
- Tools added per mode, not all loaded at once. Default conversation gets a small set; coding mode adds more; system config mode adds privileged ones.
- No chain-of-thought scaffolding in the system prompt.

### TypeScript everywhere we can

Harness daemon, chat UI, AGS shell, user `~/.osiris/` project, installer frontend, installer backend. One language across the stack. The exception is the language inside the OS itself (kernel, systemd, pacman) which we do not write.

### Branding

The v1 branding assets (logos, SVGs, the wallpaper-branding Python script) are kept in `branding/` and carry forward to v2.
