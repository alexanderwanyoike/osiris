```
   ██████╗ ███████╗██╗██████╗ ██╗███████╗    ██████╗ ███████╗
  ██╔═══██╗██╔════╝██║██╔══██╗██║██╔════╝   ██╔═══██╗██╔════╝
  ██║   ██║███████╗██║██████╔╝██║███████╗   ██║   ██║███████╗
  ██║   ██║╚════██║██║██╔══██╗██║╚════██║   ██║   ██║╚════██║
  ╚██████╔╝███████║██║██║  ██║██║███████║   ╚██████╔╝███████║
   ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═╝╚═╝╚══════╝    ╚═════╝ ╚══════╝

          A minimal, polished Linux distribution
```

A minimalistic Linux distribution built for programmers who value stability and performance over flash.

## Philosophy

Osiris is designed for one purpose: **programming**. It's not flashy. It's not bloated. It's stable, fast, and gets out of your way.

### Core Tenant: NO BLOAT

Every package is intentional. Every feature earns its place. If you don't need it for coding or essential system operation, it's not here.

### Two Desktop Environments, One Choice

- **SwayFX (Wayland)**: Modern, GPU-accelerated compositor. Tiling workflow. Blazing fast.
- **XFCE (X11)**: Traditional desktop. Battle-tested. Rock solid compatibility.

Choose the tool that fits your workflow. Both are minimal. Both are fast.

## What You Get

Debian Trixie foundation. VSCode. Firefox. That's it. Everything else is up to you.

No office suites. No games. No thousand-package "complete desktop experience" metapackages. Just a clean foundation for writing code.

## Features

- **Zero Bloat**: Only essential packages for development
- **Dual Desktop**: SwayFX (Wayland) or XFCE (X11) - your choice at login
- **Fast Boot**: Minimal services, maximum performance
- **Developer Ready**: VSCode and Chromium pre-installed
- **Stable Foundation**: Debian Trixie (testing) - bleeding edge but reliable
- **Live + Installer**: Boot live or install to disk

## Quick Start

```bash
# Build the ISO
chmod +x build.sh
./build.sh
```

ISO will be in `output/` directory (30-60 minute build time).

## Test the ISO

```bash
# QEMU
qemu-system-x86_64 -enable-kvm -m 4096 -cdrom output/*.iso -boot d

# VirtualBox
# Create VM, mount ISO from output/ directory
```

## What's Included

### Desktop Environments
- **Sway (Wayland)**: SwayFX, Waybar, Wofi, Foot terminal
- **XFCE (X11)**: XFCE4 minimal desktop, traditional workflow

### Applications
- Firefox ESR
- VSCode (installed from Microsoft repo)
- Thunar file manager
- NetworkManager

### Features
- LightDM with auto-login
- Theme switching for Sway (`osiris-theme dark/light/toggle`)
- Auto-tiling for Sway
- Nerd Fonts

## Live Boot

- **Username**: `user`
- **Password**: none
- **Sudo**: passwordless
- **Desktop**: Choose Sway or XFCE at LightDM greeter

## Building

Based on Debian Trixie (testing) using `live-build` in Docker.

```bash
# Build
./build.sh

# Clean
make clean
```

## Configuration

Customize by editing `config-all/`:
- `hooks/live/` - Scripts run during build
- `package-lists/` - Packages to install
- `includes.chroot/` - Files to copy into ISO

See `CLAUDE.md` for detailed documentation.
