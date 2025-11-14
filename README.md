# Osiris OS - Docker Build

Build Osiris ISO with one command using Docker.

## Quick Start

```bash
chmod +x build.sh
./build.sh
```

ISO will be in `output/` directory.

## Test the ISO

```bash
qemu-system-x86_64 -enable-kvm -m 2048 -cdrom output/*.iso -boot d
```

## Custom Configuration

To customize packages, create `config/` directory before building:

```bash
mkdir -p config/package-lists

cat > config/package-lists/custom.list.chroot <<EOF
systemd
bash
vim
network-manager
EOF

./build.sh
```

The config will be automatically mounted and used.

## What It Does

1. Builds Docker image with Debian Trixie + live-build
2. Runs `lb config` and `lb build` inside container
3. Outputs ISO to `output/` directory

That's it! Simple and reproducible.