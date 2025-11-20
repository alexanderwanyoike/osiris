# Live-Build Hook Best Practices

This document outlines best practices for writing robust, maintainable, and secure live-build chroot hooks for Osiris OS.

## Table of Contents
- [Core Principles](#core-principles)
- [Error Handling](#error-handling)
- [Idempotency](#idempotency)
- [Security](#security)
- [Testing and Debugging](#testing-and-debugging)
- [Code Style](#code-style)
- [Common Patterns](#common-patterns)
- [Anti-Patterns to Avoid](#anti-patterns-to-avoid)

---

## Core Principles

### 1. Hook Execution Context

Hooks run in the chroot environment AFTER:
- All packages from package lists are installed
- Files from `includes.chroot/` are copied
- Other configuration is applied

This means:
- Dependencies MUST be in package lists, not installed in hooks
- Hook scripts can assume package dependencies are available
- Hooks should focus on configuration, not package installation (with exceptions)

### 2. Naming and Organization

```bash
# Format: NNNN-descriptive-name.hook.chroot
0010-autologin.hook.chroot        # Runs first
0050-install-swayfx.hook.chroot   # Runs middle
0090-install-vscode.hook.chroot   # Runs near end
```

**Rules:**
- Use numerical prefixes for execution order (increment by 5 or 10)
- Use descriptive, kebab-case names
- Suffix must be `.hook.chroot`
- Place in `config-all/hooks/live/`

---

## Error Handling

### Always Use set -e

```bash
#!/bin/bash
set -e  # Exit immediately if any command fails

echo "Starting configuration..."
# Your commands here
```

### Enhanced Error Handling

For critical hooks, use comprehensive error handling:

```bash
#!/bin/bash
set -euo pipefail  # Exit on error, undefined variables, pipe failures

# Optional: Add cleanup trap
cleanup() {
    echo "Cleaning up temporary files..."
    rm -rf /tmp/build-*
}
trap cleanup EXIT ERR
```

**When to use:**
- `set -e`: Always (mandatory)
- `set -u`: For hooks with variables
- `set -o pipefail`: For hooks with pipelines
- `trap`: For hooks that create temporary resources

### Verify Critical Operations

Don't just assume commands succeeded:

```bash
# BAD: No verification
wget https://example.com/file.tar.gz
tar -xf file.tar.gz

# GOOD: Verify success
if ! wget https://example.com/file.tar.gz; then
    echo "ERROR: Failed to download file.tar.gz"
    exit 1
fi

if [ ! -f "file.tar.gz" ]; then
    echo "ERROR: Download failed - file not found"
    exit 1
fi

tar -xf file.tar.gz
```

### Handle Optional Operations

Use `|| true` for operations that shouldn't fail the build:

```bash
# These operations are optional - don't fail if they don't work
chmod 644 /usr/share/backgrounds/osiris/*.png 2>/dev/null || true
chown -R lightdm:lightdm /var/lib/lightdm/.config 2>/dev/null || true

# Cache updates shouldn't fail the build
gtk-update-icon-cache -f -t "$theme" 2>/dev/null || true
```

**When to use `|| true`:**
- Cache updates (icon cache, font cache, desktop database)
- Permissions on files that might not exist
- Operations on users/groups that might not exist
- Cleanup operations

**When NOT to use `|| true`:**
- File downloads
- Package installations
- Critical file creation
- User creation
- Service configuration

---

## Idempotency

Hooks should be safe to run multiple times without causing errors or unexpected behavior.

### Use mkdir -p

```bash
# BAD: Fails if directory exists
mkdir /etc/plymouth

# GOOD: Idempotent
mkdir -p /etc/plymouth
```

### Use ln -sfn for Symlinks

```bash
# BAD: Fails if symlink exists
ln -s /path/to/source /path/to/link

# GOOD: Overwrites existing symlink
ln -sfn /path/to/source /path/to/link
```

### Check Before Modifying

```bash
# Check if modification already applied
if ! grep -q "GRUB_DISTRIBUTOR=" /etc/default/grub; then
    echo 'GRUB_DISTRIBUTOR="Osiris OS"' >> /etc/default/grub
fi

# Or use sed to replace/add
if grep -q "^GRUB_DISTRIBUTOR=" /etc/default/grub; then
    sed -i 's/^GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR="Osiris OS"/' /etc/default/grub
else
    echo 'GRUB_DISTRIBUTOR="Osiris OS"' >> /etc/default/grub
fi
```

### Append vs Replace

```bash
# BAD: Appends every time hook runs (not idempotent)
echo "Hidden=true" >> /etc/xdg/autostart/app.desktop

# GOOD: Check if already present
if ! grep -q "^Hidden=" /etc/xdg/autostart/app.desktop; then
    echo "Hidden=true" >> /etc/xdg/autostart/app.desktop
fi

# BETTER: Use sed to set value
if [ -f /etc/xdg/autostart/app.desktop ]; then
    if grep -q "^Hidden=" /etc/xdg/autostart/app.desktop; then
        sed -i 's/^Hidden=.*/Hidden=true/' /etc/xdg/autostart/app.desktop
    else
        echo "Hidden=true" >> /etc/xdg/autostart/app.desktop
    fi
fi
```

---

## Security

### Always Verify Downloads

**CRITICAL:** Never download files without verification.

```bash
# BAD: No verification (SECURITY VULNERABILITY)
wget https://github.com/project/releases/download/v1.0/file.tar.gz
tar -xf file.tar.gz

# GOOD: Download with checksum verification
EXPECTED_SHA256="abc123..."
wget https://github.com/project/releases/download/v1.0/file.tar.gz

# Verify checksum
ACTUAL_SHA256=$(sha256sum file.tar.gz | cut -d' ' -f1)
if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
    echo "ERROR: Checksum mismatch!"
    echo "Expected: $EXPECTED_SHA256"
    echo "Actual:   $ACTUAL_SHA256"
    exit 1
fi

tar -xf file.tar.gz
```

### Download from HTTPS Only

```bash
# BAD: Insecure HTTP
wget http://example.com/file.tar.gz

# GOOD: Secure HTTPS
wget https://example.com/file.tar.gz
```

### Verify GPG Keys

When adding package repositories:

```bash
# BAD: No verification
wget -qO- https://packages.example.com/key.asc | gpg --dearmor > /usr/share/keyrings/example.gpg

# GOOD: Verify key fingerprint
EXPECTED_FINGERPRINT="1234 5678 90AB CDEF 1234  5678 90AB CDEF 1234 5678"
wget -qO /tmp/key.asc https://packages.example.com/key.asc

# Import and verify
gpg --import /tmp/key.asc
ACTUAL_FINGERPRINT=$(gpg --fingerprint --with-colons | grep fpr | cut -d: -f10)

if [ "$ACTUAL_FINGERPRINT" != "${EXPECTED_FINGERPRINT// /}" ]; then
    echo "ERROR: GPG key fingerprint mismatch!"
    exit 1
fi

gpg --dearmor < /tmp/key.asc > /usr/share/keyrings/example.gpg
rm /tmp/key.asc
```

### Pin Package Versions

```bash
# BAD: Installs latest version (unpredictable)
pip3 install autotiling --break-system-packages

# GOOD: Pin specific version (reproducible builds)
pip3 install autotiling==1.6.0 --break-system-packages
```

### Avoid --break-system-packages

```bash
# BAD: Breaks system package management
pip3 install package --break-system-packages

# BETTER: Use pipx (if available)
pipx install package

# ALTERNATIVE: Use virtual environment
python3 -m venv /opt/package-env
/opt/package-env/bin/pip install package
ln -s /opt/package-env/bin/package /usr/local/bin/package
```

---

## Testing and Debugging

### Interactive Shell Testing

Test hooks in an interactive chroot before committing:

```bash
# Build with interactive shell
./build.sh --interactive

# Or using lb directly
lb config --interactive shell
lb build

# When shell spawns, test your hook:
bash /root/config/hooks/live/0050-install-something.hook.chroot
```

### Add Verbose Output

```bash
#!/bin/bash
set -e

echo "=== Starting Configuration ==="

echo "Creating directory..."
mkdir -p /etc/example

echo "Downloading file..."
wget https://example.com/file.tar.gz

echo "Extracting..."
tar -xf file.tar.gz

echo "Configuration complete"
```

### Verify Operations

Add verification steps to catch issues:

```bash
# Create user
useradd -m -s /bin/bash user

# Verify user was created
if ! id user &>/dev/null; then
    echo "ERROR: User 'user' was not created"
    exit 1
fi
echo "User created successfully"

# Verify home directory exists
if [ ! -d /home/user ]; then
    echo "ERROR: Home directory not created"
    exit 1
fi
echo "Home directory exists"
```

### Check Dependencies

Verify required commands/packages are available:

```bash
# Check if command exists
if ! command -v wget &>/dev/null; then
    echo "ERROR: wget not found - add to package list"
    exit 1
fi

# Check if file exists
if [ ! -f /usr/share/plymouth/themes/osiris/osiris.plymouth ]; then
    echo "ERROR: Plymouth theme files not found"
    exit 1
fi
```

---

## Code Style

### Follow Project Guidelines

**NO EMOJIS** in any code, documentation, or output:

```bash
# BAD: Uses emojis
echo "✓ Configuration complete"
echo "✗ Error occurred"

# GOOD: Clean, professional output
echo "Configuration complete"
echo "ERROR: Operation failed"
```

### Use Clear Variable Names

```bash
# BAD: Unclear abbreviations
SKEL_DIR="/etc/skel"
CFG_FILE="/etc/app.conf"

# GOOD: Descriptive names
SKELETON_DIR="/etc/skel"
CONFIG_FILE="/etc/app.conf"
```

### Comment Complex Operations

```bash
# Configure Plymouth to use Osiris theme
# - Updates plymouthd.defaults (system-wide default)
# - Creates plymouthd.conf (runtime configuration)
# - Sets theme via update-alternatives (Debian standard)
update-alternatives --install \
    /usr/share/plymouth/themes/default.plymouth \
    default.plymouth \
    /usr/share/plymouth/themes/osiris/osiris.plymouth \
    150
```

### Use Heredocs for Multi-line Content

```bash
# GOOD: Heredoc for clean, readable content
cat > /etc/motd <<'EOF'
Welcome to Osiris OS

Choose your desktop:
  - Sway (Wayland)
  - XFCE (X11)
EOF
```

---

## Common Patterns

### Pattern: Download, Verify, Extract

```bash
#!/bin/bash
set -e

echo "=== Installing Package from Source ==="

PACKAGE_VERSION="1.0.0"
PACKAGE_URL="https://github.com/project/releases/download/v${PACKAGE_VERSION}/package.tar.gz"
PACKAGE_SHA256="abc123def456..."

# Download
cd /tmp
wget "$PACKAGE_URL" -O package.tar.gz

# Verify
ACTUAL_SHA256=$(sha256sum package.tar.gz | cut -d' ' -f1)
if [ "$ACTUAL_SHA256" != "$PACKAGE_SHA256" ]; then
    echo "ERROR: Checksum mismatch"
    exit 1
fi

# Extract
tar -xf package.tar.gz
cd package-${PACKAGE_VERSION}

# Build/Install
./configure
make
make install

# Cleanup
cd /
rm -rf /tmp/package.tar.gz /tmp/package-${PACKAGE_VERSION}

echo "Package installed"
```

### Pattern: User Creation

```bash
#!/bin/bash
set -e

echo "=== Creating Live User ==="

USERNAME="user"

# Create user (idempotent - won't fail if exists)
useradd -m -s /bin/bash -G sudo,audio,video "$USERNAME" 2>/dev/null || true

# Verify user exists
if ! id "$USERNAME" &>/dev/null; then
    echo "ERROR: User creation failed"
    exit 1
fi

# Configure user
passwd -d "$USERNAME"
echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/"$USERNAME"
chmod 0440 /etc/sudoers.d/"$USERNAME"

echo "User configured"
```

### Pattern: Configuration File Modification

```bash
#!/bin/bash
set -e

echo "=== Configuring GRUB ==="

CONFIG_FILE="/etc/default/grub"
SETTING="GRUB_DISTRIBUTOR"
VALUE="Osiris OS"

# Check file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "WARNING: $CONFIG_FILE not found"
    exit 0
fi

# Update or add setting
if grep -q "^${SETTING}=" "$CONFIG_FILE"; then
    # Setting exists - update it
    sed -i "s/^${SETTING}=.*/${SETTING}=\"${VALUE}\"/" "$CONFIG_FILE"
else
    # Setting doesn't exist - add it
    echo "${SETTING}=\"${VALUE}\"" >> "$CONFIG_FILE"
fi

echo "GRUB configured"
```

---

## Anti-Patterns to Avoid

### Don't: Download Without Verification

```bash
# NEVER DO THIS
wget https://example.com/file.tar.gz
tar -xf file.tar.gz
```

### Don't: Use --break-system-packages

```bash
# AVOID THIS
pip3 install package --break-system-packages
```

### Don't: Append Without Checking

```bash
# NOT IDEMPOTENT
echo "setting=value" >> /etc/config
```

### Don't: Assume Files Exist

```bash
# WILL FAIL IF FILE MISSING
cp /etc/skel/.config/app/config-dark /etc/skel/.config/app/config
```

### Don't: Ignore Errors on Critical Operations

```bash
# BAD: Critical operation silenced
wget https://example.com/critical-file.tar.gz || true
tar -xf critical-file.tar.gz || true
```

### Don't: Use Hardcoded Paths

```bash
# BAD: Hardcoded user
cp file.txt /home/user/

# GOOD: Use variable or $HOME
cp file.txt /home/"$USERNAME"/
# Or better: put in /etc/skel
```

---

## Summary Checklist

Before committing a hook, verify:

- [ ] Uses `set -e` at minimum
- [ ] All downloads have checksum verification
- [ ] Uses HTTPS for all downloads
- [ ] Critical operations have verification checks
- [ ] Idempotent (can run multiple times safely)
- [ ] No emojis in output
- [ ] Clear, descriptive variable names
- [ ] Comments for complex operations
- [ ] Proper error messages
- [ ] Uses `|| true` only for optional operations
- [ ] Dependencies are in package lists, not installed in hook
- [ ] Tested in interactive chroot

---

## References

- [Debian Live Manual - Customizing Contents](https://live-team.pages.debian.net/live-manual/html/live-manual/customizing-contents.en.html)
- [Bash Error Handling Best Practices](https://www.davidpashley.com/articles/writing-robust-shell-scripts/)
- [Writing Idempotent Bash Scripts](https://arslan.io/2019/07/03/how-to-write-idempotent-bash-scripts/)

---

**Last Updated:** 2025-11-19
