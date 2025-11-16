# Osiris OS - Project Context

## Overview
Osiris is a custom Debian-based Linux distribution built using `live-build`. It provides a minimal, polished desktop experience with **both Sway (Wayland) and XFCE (X11)** desktop environments in a single ISO. Users can choose which desktop to use at login.

## Project Architecture

### Build System
- **Base**: Debian Trixie (testing)
- **Build Tool**: `live-build` in Docker container
- **Build Method**: Single build script that:
  1. Cleans previous builds
  2. Copies `config-all/` to `config/`
  3. Builds Docker image (`osiris-builder`)
  4. Runs `lb config` and `lb build` in container
  5. Outputs ISO to `output/` directory

### Desktop Environments

Both desktop environments are included in a single ISO. Users select which to use at the LightDM login screen.

#### Sway (Wayland)
- **Compositor**: SwayFX (custom-built from source)
- **Terminal**: Foot
- **Status Bar**: Waybar
- **App Launcher**: Wofi
- **Features**:
  - Theme switching system (dark/light modes via `osiris-theme` command)
  - Custom wallpapers
  - Auto-tiling support
  - Nerd Fonts

#### XFCE (X11)
- **Desktop**: XFCE4 (minimal)
- **Terminal**: xfce4-terminal
- **Display Server**: Xorg
- **Traditional desktop experience**

### Common Components
- **Display Manager**: LightDM with auto-login and session selection
- **File Manager**: Thunar (works in both desktops)
- **Browser**: Firefox ESR
- **IDE**: VSCode (installed via hook from Microsoft repo)
- **Network**: NetworkManager with GNOME applet
- **Audio**: PipeWire with PulseAudio compatibility
- **Firmware**: linux-free and linux-nonfree

## Directory Structure

```
osiris/
├── Dockerfile              # Docker image with live-build
├── build.sh                # Main build script
├── Makefile                # Clean target
├── .gitignore              # Excludes build artifacts, ISOs, output/
├── config/                 # GENERATED - copied from config-all/
├── config-all/             # Main configuration (Sway + XFCE)
│   ├── hooks/live/         # Chroot hooks (numbered 0010-0090)
│   ├── includes.chroot/    # Files to copy into ISO
│   │   ├── etc/skel/.config/  # Sway default configs
│   │   └── usr/share/backgrounds/  # Wallpapers
│   └── package-lists/      # Package lists
│       ├── desktop.list.chroot      # Both Sway and XFCE packages
│       ├── build-tools.list.chroot  # Build tools for SwayFX
│       └── fonts.list.chroot        # Font packages
└── output/                 # Build output (gitignored)
```

## Hook System

Hooks are bash scripts that run during the `chroot` phase of the build. They execute in numerical order:

### Hooks
- **0010-autologin.hook.chroot**: Creates `user` account with passwordless sudo and LightDM auto-login with session selection
- **0050-install-swayfx-official.hook.chroot**: Builds wlroots 0.16.2 and SwayFX 0.3.2 from source
- **0055-install-nerd-fonts.hook.chroot**: Installs Nerd Fonts
- **0060-setup-themes.hook.chroot**:
  - Sets dark mode as default for Sway
  - Installs `osiris-theme` CLI tool for theme switching
  - Supports dark/light toggle for Sway, Waybar, Wofi, Foot
- **0065-install-autotiling.hook.chroot**: Installs i3-autotiling for Sway
- **0090-install-vscode.hook.chroot**: Adds Microsoft repo and installs VSCode

## Package Lists

### desktop.list.chroot
Contains packages for both Sway and XFCE:
- Sway ecosystem: waybar, foot, wofi, swaybg, etc.
- XFCE ecosystem: xfce4, xserver-xorg, xorg
- Common: thunar, firefox-esr, network-manager-gnome
- Display manager: lightdm, lightdm-gtk-greeter

### build-tools.list.chroot
Build tools for compiling SwayFX:
- cmake, meson, ninja-build
- build-essential, gcc, g++
- Python 3 and pip

### fonts.list.chroot
Font packages for both desktops

## Build Commands

```bash
# Build Osiris OS
./build.sh

# Clean all builds
make clean
```

## Testing

```bash
# QEMU
qemu-system-x86_64 -enable-kvm -m 4096 -cdrom output/*.iso -boot d

# VirtualBox
# Create VM, mount ISO from output/ directory
```

## Key Features

1. **Dual Desktop**: Both Sway and XFCE in one ISO - choose at login
2. **Live Boot + Installer**: Supports both live sessions and installation via debian-installer
3. **Minimal & Bloat-free**: Only essential packages included
4. **Auto-login**: LightDM auto-login to `user` account on live boot
5. **Passwordless Sudo**: User has full sudo access without password
6. **Theme System** (Sway): Dark/light mode switching via `osiris-theme` command
7. **Custom Builds**: SwayFX built from source for modern compositor features

## Important Notes

- **config/ directory**: GENERATED at build time, gitignored
- **output/ directory**: Build artifacts, gitignored
- **Build time**: 30-60 minutes
- **Privileged container**: Docker runs with `--privileged` flag for ISO creation
- **Debian version**: Trixie (testing) - bleeding edge but stable
- **Session selection**: At LightDM greeter, choose Sway or XFCE

## Development Workflow

1. Modify configs in `config-all/`
2. Run `./build.sh`
3. Build script cleans, copies config, and rebuilds ISO
4. Test ISO in VM
5. Iterate

## Session Selection Details

The LightDM greeter allows users to select between:
- **Sway Session**: Modern Wayland compositor with SwayFX, theme switcher, auto-tiling, Waybar, Wofi
- **XFCE Session**: Complete XFCE4 desktop with traditional workflow

**Shared Components**: VSCode, Firefox, Thunar file manager work in both desktops.

**Use Case**: Perfect for users who want flexibility - modern Wayland for daily use, traditional X11 for compatibility.
