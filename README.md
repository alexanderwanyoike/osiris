# Osiris OS

A minimal Debian-based Linux distribution with both **Sway** and **XFCE** desktop environments.

## Features

- **Dual Desktop**: Choose between Sway (Wayland) or XFCE (X11) at login
- **Minimal & Fast**: Only essential packages, no bloat
- **Modern Compositor**: SwayFX with theme switching (dark/light modes)
- **Developer Ready**: VSCode and Firefox ESR pre-installed
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
