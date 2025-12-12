# Osiris OS - Project Context

## Overview
Osiris is a custom Debian-based Linux distribution built using `live-build`. It provides a minimal, polished desktop experience with **both Sway (Wayland) and Cinnamon (X11)** desktop environments in a single ISO. Users can choose which desktop to use at login.

## Code Style Guidelines

**IMPORTANT**: This project maintains a professional, technical tone:
- **NO EMOJIS** - Do not use emojis in code, documentation, commit messages, or any project files
- Keep all communication clear, technical, and professional
- Documentation should be clean and readable without decorative elements
- Focus on technical accuracy and clarity

## Development Guidelines

**Research Before Implementation**:
- **DO NOT GUESS** - Always research technical details before implementing solutions
- Use WebSearch to look up documentation, specifications, and best practices
- For configuration files, search for official documentation on syntax and supported features
- For application behavior, consult official docs or reliable sources
- Verify assumptions with research rather than trial-and-error
- Examples of what to research:
  - Does application X support tilde (~) expansion in config files?
  - What is the exact syntax for configuration option Y?
  - What are the documented behaviors of feature Z?
- Only proceed with implementation after confirming technical details through research

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
- **Terminal**: Foot, Alacritty
- **Status Bar**: Waybar
- **App Launcher**: Wofi
- **Features**:
  - Theme switching system (dark/light modes via `osiris-theme` command)
  - Custom wallpapers
  - Auto-tiling support
  - Nerd Fonts

#### Cinnamon (X11)
- **Desktop**: Cinnamon (modern, polished)
- **File Manager**: Nemo
- **Display Server**: Xorg
- **Features**:
  - Built-in theme switching via Settings > Themes
  - Light theme default with Papirus icons
  - Osiris logo as menu icon
  - Modern, familiar desktop experience

### Common Components
- **Display Manager**: LightDM with auto-login and session selection
- **Browser**: Chromium
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
├── config-all/             # Main configuration (Sway + Cinnamon)
│   ├── hooks/live/         # Chroot hooks (numbered 0010-0095)
│   ├── includes.chroot/    # Files to copy into ISO
│   │   ├── etc/skel/.config/  # Default user configs
│   │   └── usr/share/backgrounds/  # Wallpapers
│   └── package-lists/      # Package lists
│       ├── desktop.list.chroot      # Sway and Cinnamon packages
│       ├── build-tools.list.chroot  # Build tools for SwayFX
│       └── fonts.list.chroot        # Font packages
└── output/                 # Build output (gitignored)
```

## Hook System

Hooks are bash scripts that run during the `chroot` phase of the build. They execute in numerical order:

### Hooks
- **0010-autologin.hook.chroot**: Creates `user` account with passwordless sudo and LightDM auto-login
- **0050-install-swayfx-official.hook.chroot**: Builds wlroots and SwayFX from source
- **0055-install-nerd-fonts.hook.chroot**: Installs Nerd Fonts
- **0060-setup-themes.hook.chroot**: Sets dark mode as default for Sway, installs `osiris-theme` CLI
- **0065-install-autotiling.hook.chroot**: Installs i3-autotiling for Sway
- **0070-setup-cinnamon.hook.chroot**: Configures Cinnamon defaults (light theme, Papirus icons, menu icon)
- **0090-install-vscode.hook.chroot**: Adds Microsoft repo and installs VSCode

## Package Lists

### desktop.list.chroot
Contains packages for both Sway and Cinnamon:
- Sway ecosystem: waybar, foot, wofi, swaybg, alacritty
- Cinnamon: cinnamon-core, xserver-xorg, xorg
- Common: chromium, network-manager-gnome, papirus-icon-theme
- Display manager: lightdm, slick-greeter, lightdm-gtk-greeter

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

## Debugging

### Plymouth Debug Mode
To debug Plymouth boot splash issues:
1. At GRUB menu, press `e` to edit the boot entry
2. Find the `linux` line and add `plymouth.debug`, remove `quiet`:
   ```
   linux /live/vmlinuz boot=live components splash plymouth.debug plymouth.ignore-serial-consoles vga=791
   ```
3. Press `F10` to boot
4. After boot, check the debug log:
   ```bash
   sudo cat /var/log/plymouth-debug.log
   journalctl -b | grep -i plymouth
   ```

**Note:** Plymouth 24 (Debian Trixie) looks for themes in `/run/plymouth/themes/` first, then falls back to `/usr/share/plymouth/themes/`.

## Key Features

1. **Dual Desktop**: Both Sway and Cinnamon in one ISO - choose at login
2. **Live Boot + Installer**: Supports both live sessions and installation via Calamares
3. **Minimal & Bloat-free**: Only essential packages included
4. **Auto-login**: LightDM auto-login to `user` account on live boot
5. **Passwordless Sudo**: User has full sudo access without password
6. **Theme System**:
   - Sway: Dark/light mode switching via `osiris-theme` command
   - Cinnamon: Use built-in Settings > Themes
7. **Custom Builds**: SwayFX built from source for modern compositor features

## Important Notes

- **config/ directory**: GENERATED at build time, gitignored
- **output/ directory**: Build artifacts, gitignored
- **Build time**: 30-60 minutes
- **Privileged container**: Docker runs with `--privileged` flag for ISO creation
- **Debian version**: Trixie (testing) - bleeding edge but stable
- **Session selection**: At LightDM greeter, choose Sway or Cinnamon

## Development Workflow

1. Modify configs in `config-all/`
2. Run `./build.sh`
3. Build script cleans, copies config, and rebuilds ISO
4. Test ISO in VM
5. Iterate

## Session Selection Details

The LightDM greeter allows users to select between:
- **Sway Session**: Modern Wayland compositor with SwayFX, theme switcher, auto-tiling, Waybar, Wofi
- **Cinnamon Session**: Modern traditional desktop with familiar workflow, built-in theme switching

**Shared Components**: VSCode, Chromium, NetworkManager work in both desktops.

**Use Case**: Perfect for users who want flexibility - modern Wayland for power users, polished Cinnamon for traditional desktop experience.
