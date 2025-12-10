```
   ██████╗ ███████╗██╗██████╗ ██╗███████╗    ██████╗ ███████╗
  ██╔═══██╗██╔════╝██║██╔══██╗██║██╔════╝   ██╔═══██╗██╔════╝
  ██║   ██║███████╗██║██████╔╝██║███████╗   ██║   ██║███████╗
  ██║   ██║╚════██║██║██╔══██╗██║╚════██║   ██║   ██║╚════██║
  ╚██████╔╝███████║██║██║  ██║██║███████║   ╚██████╔╝███████║
   ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═╝╚═╝╚══════╝    ╚═════╝ ╚══════╝
```

# Osiris OS

A minimal, developer-focused Linux distribution built on Debian Trixie. Dual desktop environments. Zero bloat. Maximum productivity.

## Overview

Osiris provides a clean foundation for software development with two desktop environments in a single ISO:

- **SwayFX (Wayland)** - Modern tiling compositor with blur, shadows, and corner effects
- **XFCE (X11)** - Traditional desktop for compatibility and familiarity

Select your desktop at the login screen. Both environments share a consistent minimal aesthetic.

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 64-bit (amd64) | Multi-core |
| RAM | 2 GB | 4 GB+ |
| Storage | 10 GB | 20 GB+ |
| Graphics | VESA compatible | GPU with OpenGL 3.0+ (for Sway) |

## Quick Start

### Build

```bash
./build.sh
```

The ISO will be generated in `output/` (build time: 30-60 minutes).

### Test

```bash
# QEMU with GPU acceleration
qemu-system-x86_64 -enable-kvm -m 4096 \
  -device virtio-vga-gl -display gtk,gl=on \
  -cdrom output/*.iso -boot d

# VirtualBox
# Enable 3D acceleration, allocate 128MB+ video memory
```

### Live Session

| Credential | Value |
|------------|-------|
| Username | `user` |
| Password | (none) |
| Sudo | Passwordless |

## Desktop Environments

### SwayFX (Wayland)

A customized build of SwayFX 0.3.2 compiled from source with wlroots 0.16.2.

**Components:**
- Waybar status bar
- Wofi application launcher
- Foot terminal
- Mako notifications
- Autotiling

**Key Bindings:**

| Action | Binding |
|--------|---------|
| Terminal | `Super + Return` |
| App Launcher | `Super + Space` |
| Close Window | `Super + Q` |
| Fullscreen | `Super + F` |
| Workspaces | `Super + 1-5` |
| Move Window | `Super + Shift + Arrow` |
| Screenshot | `Print` |

**Visual Effects:**
- Dual Kawase blur
- Window shadows
- 12px corner radius
- Inactive window dimming

### XFCE (X11)

Minimal XFCE4 installation with Picom compositor.

**Components:**
- XFCE4 Panel
- Thunar file manager
- XFCE4 Terminal
- Plank dock
- Picom compositor (blur, shadows, transparency)

## Theme System

Osiris includes a unified theme switcher for both desktop environments:

```bash
osiris-theme dark    # Switch to dark mode
osiris-theme light   # Switch to light mode
osiris-theme toggle  # Toggle between modes
```

The theme system updates:
- Window manager configuration
- Status bar styling
- Terminal colors
- GTK theme
- Icon theme
- Wallpaper

## Included Software

### Pre-installed

| Category | Software |
|----------|----------|
| Browser | Chromium |
| Editor | VSCode, Neovim |
| File Manager | Thunar |
| Terminal | Foot (Sway), XFCE4 Terminal (XFCE), Kitty |
| Audio | PipeWire, pavucontrol |
| Network | NetworkManager |

### Available via Installer

The Calamares installer includes optional development profiles:

**Base Profile:**
- htop, gparted, nano
- Python 3 with pip
- GCC, G++, Make, Git
- Evince PDF reader

**Development Profile:**
- CMake, Meson, Ninja
- Node.js, npm
- Rust toolchain
- Go toolchain
- Docker

## Installation

Boot the live ISO and click "Install Osiris" on the desktop, or run:

```bash
calamares
```

The installer supports:
- Full disk installation
- Manual partitioning
- BIOS and UEFI boot
- Encrypted installations

## Project Structure

```
osiris/
├── build.sh                    # Build script
├── Dockerfile                  # Docker build environment
├── Makefile                    # Clean target
├── config-all/
│   ├── hooks/live/             # Build hooks (numbered 0005-0095)
│   ├── package-lists/          # Package definitions
│   │   ├── desktop.list.chroot
│   │   ├── build-tools.list.chroot
│   │   └── fonts.list.chroot
│   └── includes.chroot/        # Files copied to ISO
│       ├── etc/
│       │   ├── lightdm/        # Display manager config
│       │   ├── calamares/      # Installer config
│       │   └── skel/.config/   # User default configs
│       └── usr/share/
│           ├── backgrounds/    # Wallpapers
│           └── plymouth/       # Boot splash
└── output/                     # Generated ISO (gitignored)
```

## Build Hooks

| Hook | Purpose |
|------|---------|
| 0005 | Fix file permissions |
| 0010 | Create user account, configure autologin |
| 0015 | Configure LightDM and Slick Greeter |
| 0040 | Setup Plymouth boot splash |
| 0045 | Configure branding (GRUB, MOTD) |
| 0050 | Build and install SwayFX from source |
| 0055 | Install Nerd Fonts |
| 0060 | Setup theme system |
| 0065 | Install autotiling |
| 0070 | Configure XFCE |
| 0085-0089 | Configure Calamares installer |
| 0090 | Install VSCode |
| 0095 | Update icon caches |

## Customization

### Adding Packages

Edit `config-all/package-lists/desktop.list.chroot`:

```
# Your packages here
package-name
```

### Modifying Configs

User default configurations are in `config-all/includes.chroot/etc/skel/.config/`.

### Creating Hooks

Add executable scripts to `config-all/hooks/live/` with naming format `NNNN-description.hook.chroot`.

## Technical Details

| Specification | Value |
|---------------|-------|
| Base | Debian Trixie (testing) |
| Architecture | amd64 |
| Init | systemd |
| Display Manager | LightDM + Slick Greeter |
| Boot Splash | Plymouth (Osiris theme) |
| Bootloader | GRUB 2 (BIOS + UEFI) |
| Filesystem | SquashFS (live), ext4 (installed) |
| Build System | live-build in Docker |

## Building from Source

### Prerequisites

- Docker
- 20GB+ free disk space
- Internet connection

### Commands

```bash
# Build ISO
./build.sh

# Clean build artifacts
make clean
```

### Build Output

```
output/
├── live-image-amd64.hybrid.iso    # Bootable ISO
├── live-image-amd64.contents      # Package manifest
├── live-image-amd64.packages      # Installed packages
└── build.log                      # Build log
```

## License

Osiris OS is built from open source components. Individual packages retain their respective licenses. The build configuration and custom scripts in this repository are released under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test the build
5. Submit a pull request

## Support

- Issues: [GitHub Issues](https://github.com/alexanderwanyoike/osiris/issues)
- Documentation: See `CLAUDE.md` for detailed technical documentation
