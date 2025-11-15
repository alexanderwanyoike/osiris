#!/bin/bash
# Osiris OS - Sway Variant Build Script

set -e

# Clean previous builds
echo "Cleaning previous builds..."
sudo rm -rf output-sway config

echo "=== Building Osiris OS - Sway Edition ==="
echo "Desktop: Sway"
echo "Apps: Firefox, VSCode"
echo ""

# Create output directory
mkdir -p output-sway

# Clean and prepare config directory
echo "Preparing config directory..."
rm -rf config
cp -r config-sway config
chmod +x config/hooks/live/*.chroot

# Build the Docker image
echo "Building Docker image..."
docker build -t osiris-builder .

# Run the build with config mounted
echo ""
echo "Starting ISO build (this will take 30-60 minutes)..."
docker run --rm --privileged \
    -v "$(pwd)/output-sway:/build" \
    -v "$(pwd)/config:/build/config" \
    osiris-builder

echo ""
echo "✓ Build complete!"
echo ""
echo "ISO: $(ls output-sway/*.iso 2>/dev/null || echo 'Not found - check output-sway directory')"
echo ""
echo "Test with:"
echo "  qemu-system-x86_64 -enable-kvm -m 4096 -cdrom output-sway/*.iso -boot d"