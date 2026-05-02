# Osiris

A minimal AI-first operating system. Arch Linux base, Hyprland compositor, AGS desktop shell, with a TypeScript AI harness as the primary user interface.

The premise: modern AI assistants can do most of what desktop GUI software does, so the OS ships as a thin substrate around an agent that owns the customization and operation surface. Need a new theme? Tell the agent. Need to install something? Tell the agent. Need to write a config? Tell the agent.

## Status

v2 in early design and scaffolding. v1 (Debian-based with dual Sway/Cinnamon desktop) was scrapped: too painful to build, too bloated, not the vision.

## Documentation

- [Architecture](docs/ARCHITECTURE.md): vision, stack, components, conventions
- [Roadmap](docs/ROADMAP.md): prioritized work phases with definition-of-done

## Repository layout

This repo currently holds design docs and brand assets. Implementation directories (`shell/`, `installer/`, `harness/`) will be scaffolded as each phase begins.

```
osiris/
├── docs/         Design documents
├── branding/     Logos and brand assets carried forward from v1
├── README.md
└── CLAUDE.md     Instructions for AI-assisted development sessions
```
