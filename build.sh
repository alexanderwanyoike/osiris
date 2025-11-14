#!/bin/bash
# Osiris OS - Simple Build Script

set -e

echo "Building Osiris ISO..."

# Create output directory
mkdir -p output

# Build the Docker image
docker build -t osiris-builder .

# Run the build
docker run --rm --privileged -v "$(pwd)/output:/build" osiris-builder

echo ""
echo "✓ Build complete!"
echo "ISO: $(ls output/*.iso)"
echo ""
echo "Test with: qemu-system-x86_64 -enable-kvm -m 2048 -cdrom output/*.iso -boot d"