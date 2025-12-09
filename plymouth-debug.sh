#!/bin/bash
# Plymouth Debug Script - Run this from the live Osiris session

echo "=== Plymouth Debug Info ==="
echo ""

echo "1. Current default theme (update-alternatives):"
update-alternatives --query default.plymouth 2>/dev/null | grep -E "^(Value|Status):" || echo "   Not configured"
echo ""

echo "2. plymouthd.conf:"
cat /etc/plymouth/plymouthd.conf 2>/dev/null || echo "   Not found"
echo ""

echo "3. plymouthd.defaults:"
cat /usr/share/plymouth/plymouthd.defaults 2>/dev/null | grep -E "^Theme=" || echo "   Not found"
echo ""

echo "4. Osiris theme files in /usr/share/plymouth/themes/osiris/:"
ls -la /usr/share/plymouth/themes/osiris/ 2>/dev/null || echo "   Directory not found"
echo ""

echo "5. default.plymouth symlink:"
ls -la /usr/share/plymouth/themes/default.plymouth 2>/dev/null || echo "   Not found"
echo ""

echo "6. Available themes:"
ls /usr/share/plymouth/themes/
echo ""

echo "7. Plymouth status:"
plymouth --ping 2>/dev/null && echo "   Plymouth is running" || echo "   Plymouth not running"
echo ""

echo "8. Check initramfs for osiris theme:"
lsinitramfs /boot/initrd.img-$(uname -r) 2>/dev/null | grep -E "(osiris|plymouth/themes)" | head -20 || echo "   Could not read initramfs"
echo ""

echo "9. Kernel cmdline:"
cat /proc/cmdline
echo ""

echo "10. two-step.so module exists:"
ls -la /usr/lib/*/plymouth/two-step.so 2>/dev/null || echo "   Not found"
echo ""
