#!/bin/bash
# Osiris OS - Build Script (Sway + XFCE)

set -e

# Clean previous builds
echo "Cleaning previous builds..."
sudo rm -rf output config

echo "=== Building Osiris OS ==="
echo "Desktops: Sway + XFCE"
echo "Display Manager: LightDM (auto-login)"
echo "Apps: Firefox, VSCode"
echo ""

# Create output directory
mkdir -p output

# Clean and prepare config directory
echo "Preparing config directory..."
rm -rf config
cp -r config-all config
chmod +x config/hooks/live/*.chroot

# Build the Docker image if needed
if [[ "$(docker images -q osiris-builder 2> /dev/null)" == "" ]]; then
    echo "Building Docker image..."
    docker build -t osiris-builder .
else
    echo "Using existing Docker image..."
fi

# Run the build with config mounted
echo ""
echo "Starting ISO build (this will take 30-60 minutes)..."
echo "Build log will be saved to output/build.log"
docker run --rm --privileged \
    -v "$(pwd)/output:/build" \
    -v "$(pwd)/config:/build/config" \
    osiris-builder 2>&1 | tee output/build.log

echo ""
echo "✓ Build complete!"
echo "✓ Build log saved to output/build.log"
echo ""
echo "ISO: $(ls output/*.iso 2>/dev/null || echo 'Not found - check output directory')"
echo ""
echo "Test with:"
echo "  qemu-system-x86_64 -enable-kvm -m 4096 -cdrom output/*.iso -boot d"
echo ""
echo "At LightDM login, select either Sway or XFCE session"
