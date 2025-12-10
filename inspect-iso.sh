#!/bin/bash
# Osiris ISO Inspection Script
# Checks Plymouth, LightDM, and other critical configs

set -e

ISO_PATH="${1:-output/live-image-amd64.hybrid.iso}"
MOUNT_DIR="/mnt/osiris-iso"
EXTRACT_DIR="/tmp/osiris-inspect"

if [ ! -f "$ISO_PATH" ]; then
    echo "ERROR: ISO not found at $ISO_PATH"
    echo "Usage: $0 [path-to-iso]"
    exit 1
fi

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "This script requires sudo. Re-running with sudo..."
    exec sudo "$0" "$@"
fi

echo "=== Osiris ISO Inspection ==="
echo "ISO: $ISO_PATH"
echo "Timestamp: $(stat -c %y "$ISO_PATH")"
echo ""

# Cleanup any previous run
umount "$MOUNT_DIR" 2>/dev/null || true
rm -rf "$EXTRACT_DIR"
mkdir -p "$MOUNT_DIR" "$EXTRACT_DIR"

# Mount ISO
echo "[1/6] Mounting ISO..."
mount -o loop "$ISO_PATH" "$MOUNT_DIR"
echo "      Done"
echo ""

# Extract initrd
echo "[2/6] Extracting initrd..."
mkdir -p "$EXTRACT_DIR/initrd"
cd "$EXTRACT_DIR/initrd"
unmkinitramfs "$MOUNT_DIR/live/initrd.img" . 2>/dev/null
cd "$EXTRACT_DIR"
echo "      Done"
echo ""

# Check Plymouth in initrd
echo "[3/6] Plymouth in initrd:"
echo ""
echo "  Themes directory:"
ls -la "$EXTRACT_DIR/initrd/main/usr/share/plymouth/themes/" 2>/dev/null || echo "    NOT FOUND"
echo ""

echo "  default.plymouth:"
if [ -L "$EXTRACT_DIR/initrd/main/usr/share/plymouth/themes/default.plymouth" ]; then
    echo "    SYMLINK -> $(readlink "$EXTRACT_DIR/initrd/main/usr/share/plymouth/themes/default.plymouth")"
elif [ -f "$EXTRACT_DIR/initrd/main/usr/share/plymouth/themes/default.plymouth" ]; then
    echo "    FILE (should be symlink!)"
    head -5 "$EXTRACT_DIR/initrd/main/usr/share/plymouth/themes/default.plymouth"
else
    echo "    NOT FOUND (this is the problem!)"
fi
echo ""

echo "  Osiris theme files:"
if [ -d "$EXTRACT_DIR/initrd/main/usr/share/plymouth/themes/osiris" ]; then
    ls "$EXTRACT_DIR/initrd/main/usr/share/plymouth/themes/osiris/" | wc -l | xargs -I{} echo "    {} files"
    ls "$EXTRACT_DIR/initrd/main/usr/share/plymouth/themes/osiris/" | head -5 | sed 's/^/    /'
else
    echo "    NOT FOUND"
fi
echo ""

echo "  plymouthd.conf:"
cat "$EXTRACT_DIR/initrd/main/etc/plymouth/plymouthd.conf" 2>/dev/null | sed 's/^/    /' || echo "    NOT FOUND"
echo ""

echo "  plymouthd.defaults:"
grep "^Theme=" "$EXTRACT_DIR/initrd/main/usr/share/plymouth/plymouthd.defaults" 2>/dev/null | sed 's/^/    /' || echo "    NOT FOUND or no Theme line"
echo ""

echo "  two-step.so module:"
ls "$EXTRACT_DIR/initrd/main/usr/lib/"*/plymouth/two-step.so 2>/dev/null | sed 's/^/    /' || echo "    NOT FOUND"
echo ""

echo "  Fonts in initrd:"
find "$EXTRACT_DIR/initrd/main" -name "*.ttf" -o -name "*.otf" 2>/dev/null | head -5 | sed "s|$EXTRACT_DIR/initrd/main||" | sed 's/^/    /' || echo "    NOT FOUND"
echo ""

# Check squashfs for comparison
echo "[4/6] Plymouth in squashfs (filesystem):"
echo ""
mkdir -p "$EXTRACT_DIR/squashfs"
echo "  Extracting Plymouth configs from squashfs..."
unsquashfs -f -d "$EXTRACT_DIR/squashfs" "$MOUNT_DIR/live/filesystem.squashfs" \
    etc/alternatives/default.plymouth \
    usr/share/plymouth/themes/default.plymouth \
    etc/plymouth/plymouthd.conf \
    usr/share/plymouth/plymouthd.defaults \
    > /dev/null 2>&1

echo ""
echo "  default.plymouth symlinks:"
if [ -L "$EXTRACT_DIR/squashfs/etc/alternatives/default.plymouth" ]; then
    echo "    /etc/alternatives/default.plymouth -> $(readlink "$EXTRACT_DIR/squashfs/etc/alternatives/default.plymouth")"
fi
if [ -L "$EXTRACT_DIR/squashfs/usr/share/plymouth/themes/default.plymouth" ]; then
    echo "    /usr/share/plymouth/themes/default.plymouth -> $(readlink "$EXTRACT_DIR/squashfs/usr/share/plymouth/themes/default.plymouth")"
fi
echo ""

echo "  plymouthd.conf in squashfs:"
cat "$EXTRACT_DIR/squashfs/etc/plymouth/plymouthd.conf" 2>/dev/null | sed 's/^/    /' || echo "    NOT FOUND"
echo ""

# Check LightDM config
echo "[5/6] LightDM in squashfs:"
unsquashfs -f -d "$EXTRACT_DIR/squashfs" "$MOUNT_DIR/live/filesystem.squashfs" \
    etc/lightdm > /dev/null 2>&1
echo ""
echo "  lightdm.conf.d/:"
ls "$EXTRACT_DIR/squashfs/etc/lightdm/lightdm.conf.d/" 2>/dev/null | sed 's/^/    /' || echo "    NOT FOUND"
echo ""
echo "  slick-greeter.conf:"
cat "$EXTRACT_DIR/squashfs/etc/lightdm/slick-greeter.conf" 2>/dev/null | head -10 | sed 's/^/    /' || echo "    NOT FOUND"
echo ""

# Check boot params
echo "[6/6] Boot configuration:"
echo ""
echo "  ISOLINUX (BIOS boot):"
grep -E "append" "$MOUNT_DIR/isolinux/menu.cfg" 2>/dev/null | head -2 | sed 's/^/    /' || echo "    NOT FOUND"
echo ""
echo "  GRUB (UEFI boot):"
grep -E "linux /live" "$MOUNT_DIR/boot/grub/grub.cfg" 2>/dev/null | head -2 | sed 's/^/    /' || echo "    NOT FOUND"
echo ""

# Summary
echo "=== Summary ==="
if [ -L "$EXTRACT_DIR/initrd/main/usr/share/plymouth/themes/default.plymouth" ]; then
    echo "  [OK] default.plymouth symlink exists in initrd"
elif [ -f "$EXTRACT_DIR/initrd/main/usr/share/plymouth/themes/default.plymouth" ]; then
    echo "  [WARN] default.plymouth is a file, not symlink"
else
    echo "  [FAIL] default.plymouth missing from initrd"
fi

if [ -d "$EXTRACT_DIR/initrd/main/usr/share/plymouth/themes/osiris" ]; then
    echo "  [OK] Osiris theme directory in initrd"
else
    echo "  [FAIL] Osiris theme missing from initrd"
fi

if grep -q "Theme=osiris" "$EXTRACT_DIR/initrd/main/etc/plymouth/plymouthd.conf" 2>/dev/null; then
    echo "  [OK] plymouthd.conf has Theme=osiris"
else
    echo "  [FAIL] plymouthd.conf missing or wrong theme"
fi

if ls "$EXTRACT_DIR/initrd/main/usr/lib/"*/plymouth/two-step.so >/dev/null 2>&1; then
    echo "  [OK] two-step.so module present"
else
    echo "  [FAIL] two-step.so module missing"
fi

if [ -f "$EXTRACT_DIR/initrd/main/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf" ]; then
    echo "  [OK] DejaVuSans.ttf in initrd (required for two-step)"
else
    echo "  [FAIL] DejaVuSans.ttf missing (only Mono variant found)"
fi

echo ""

# Cleanup
umount "$MOUNT_DIR"
rm -rf "$EXTRACT_DIR"

echo "Inspection complete."
