#!/bin/bash
# Osiris OS - Phase 2 Build Script

set -e

echo "=== Building Osiris OS Phase 2 ==="
echo "Desktop: GNOME"
echo "Apps: Firefox, VSCode, Ollama"
echo ""

# Create output directory
mkdir -p output

# Clean and prepare config directory
echo "Preparing config directory..."
rm -rf config
cp -r config-gnome config
chmod +x config/hooks/live/*.chroot

# Build the Docker image
echo "Building Docker image..."
docker build -t osiris-builder .

# Run the build with config mounted
echo ""
echo "Starting ISO build (this will take 30-60 minutes)..."
docker run --rm --privileged \
    -v "$(pwd)/output:/build" \
    -v "$(pwd)/config:/build/config" \
    osiris-builder

echo ""
echo "✓ Build complete!"
echo ""
echo "ISO: $(ls output/*.iso 2>/dev/null || echo 'Not found - check output directory')"
echo ""
echo "Test with:"
echo "  qemu-system-x86_64 -enable-kvm -m 4096 -cdrom output/*.iso -boot d"