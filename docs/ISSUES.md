# Osiris OS - Known Issues

Post-installation polish issues that need addressing. Core functionality works, these are cosmetic/UX improvements.

---

## Issue #1: GRUB Theme Not Applied After Install

**Status:** Open
**Priority:** Medium
**Component:** Bootloader (GRUB)

### Description
After installation, GRUB boots with the default Debian theme instead of the Osiris custom theme.

### Expected Behavior
GRUB should display custom Osiris branding/theme on boot.

### Current Behavior
Default Debian GRUB theme is shown.

### Potential Causes
1. **GRUB theme not installed in live system**
   - Custom theme files not in `/usr/share/grub/themes/`
   - Calamares copies live system, so theme must be present in ISO

2. **GRUB configuration not updated**
   - `/etc/default/grub` not configured to use custom theme
   - Missing `GRUB_THEME="/path/to/theme/theme.txt"` setting

3. **Theme not applied during installation**
   - Calamares might not be running `update-grub` with custom config
   - Hook needed to configure GRUB theme before bootloader module runs

### Possible Solutions
- [ ] Add GRUB theme package to `desktop.list.chroot`
- [ ] Create custom GRUB theme in `config-all/includes.chroot/usr/share/grub/themes/osiris/`
- [ ] Add hook to configure `/etc/default/grub` with theme path
- [ ] Ensure Calamares bootloader module applies configuration

### References
- GRUB themes location: `/usr/share/grub/themes/`
- GRUB config: `/etc/default/grub`
- Calamares bootloader module: `/etc/calamares/modules/bootloader.conf`

---

## Issue #2: LightDM Session Selector Not Showing

**Status:** FIXED
**Priority:** High (UX Impact)
**Component:** Display Manager (LightDM)

### Description
LightDM session selector wasn't displaying, preventing users from choosing between Sway and XFCE at login.

### Root Cause
Slick-greeter has limited support for detecting Wayland sessions in `/usr/share/wayland-sessions/`. The `show-session-menu` option doesn't exist in slick-greeter configuration.

### Solution Implemented
Switched from `slick-greeter` to `lightdm-gtk-greeter`:
- [x] Changed greeter-session in `/etc/lightdm/lightdm.conf.d/50-gtk-greeter.conf`
- [x] Added `lightdm-gtk-greeter` package to `desktop.list.chroot`
- [x] GTK greeter config already has `indicators=~session` for session selector
- [x] Repositioned login form to left side (`position=20%,center 50%,center`)

### Files Modified
- `config-all/includes.chroot/etc/lightdm/lightdm.conf.d/50-slick-greeter.conf` → `50-gtk-greeter.conf`
- `config-all/package-lists/desktop.list.chroot`
- `config-all/includes.chroot/etc/lightdm/lightdm-gtk-greeter.conf`

### Result
Session selector now visible in LightDM GTK greeter, allowing users to choose between Sway and XFCE sessions.

---

## Issue #3: Plymouth Ignoring Custom Boot Screen

**Status:** Open
**Priority:** Low (Cosmetic)
**Component:** Boot Splash (Plymouth)

### Description
Plymouth (boot splash screen) shows default theme instead of custom Osiris branding during boot.

### Expected Behavior
Custom Osiris boot splash should appear during system startup.

### Current Behavior
Default Plymouth theme (or no splash) is shown.

### Potential Causes
1. **Plymouth theme not installed**
   - Custom theme files not in `/usr/share/plymouth/themes/`
   - Package list has `plymouth` and `plymouth-themes` but no custom theme

2. **Theme not set as default**
   - `/etc/plymouth/plymouthd.conf` doesn't reference custom theme
   - `update-alternatives` not configured for custom theme

3. **Initramfs not updated**
   - Plymouth theme is baked into initramfs
   - Must run `update-initramfs -u` after changing theme
   - This might not happen during Calamares installation

4. **Kernel parameters missing**
   - Missing `splash` parameter in GRUB config
   - Check `/etc/default/grub`: `GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"`

### Possible Solutions
- [ ] Create custom Plymouth theme in `config-all/includes.chroot/usr/share/plymouth/themes/osiris/`
- [ ] Add hook to set Plymouth theme:
  ```bash
  plymouth-set-default-theme osiris
  update-initramfs -u
  ```
- [ ] Ensure GRUB has `splash` kernel parameter
- [ ] Configure `/etc/plymouth/plymouthd.conf`
- [ ] Add Calamares hook to update initramfs post-install

### References
- Plymouth themes: `/usr/share/plymouth/themes/`
- Plymouth config: `/etc/plymouth/plymouthd.conf`
- Set theme: `plymouth-set-default-theme <theme-name>`
- Update: `update-initramfs -u`

---

## Issue #4: Greeter Icons Not Displaying Correctly

**Status:** RESOLVED
**Priority:** Medium
**Component:** Display Manager (LightDM)

### Description
Icons in LightDM slick-greeter were not displaying properly due to icon theme mismatch.

### Root Cause
Icon theme inconsistency between slick-greeter config and installed themes.

### Solution
Issue resolved by switching to `lightdm-gtk-greeter` (see Issue #2). GTK greeter uses standard icon themes with better compatibility.

### Result
Greeter icons now display correctly with GTK greeter's built-in theme support.

---

## Issue #5: Waybar Not Auto-Starting in Sway

**Status:** RESOLVED
**Priority:** High (UX Impact)
**Component:** Sway Desktop Environment

### Description
Waybar (status bar) does not automatically start when logging into a Sway session, leaving users without a status bar, system tray, or clock.

### Expected Behavior
Waybar should automatically launch when Sway starts, displaying:
- Workspace indicators
- System tray
- Clock
- Network/battery/volume indicators

### Root Cause
Investigation revealed that Waybar autostart was already implemented correctly in all Sway config files.

### Solution Implemented
Verified that all components were already in place:
- [x] `exec waybar` present in all Sway configs (config, config-dark, config-light)
- [x] Waybar package installed in desktop.list.chroot
- [x] Waybar configuration files exist with proper dark/light theming
- [x] Theme switching integrated via osiris-theme command
- [x] Removed duplicate window rules (code quality improvement)

### Files Verified
- `config-all/includes.chroot/etc/skel/.config/sway/config` (line 43)
- `config-all/includes.chroot/etc/skel/.config/sway/config-dark` (line 43)
- `config-all/includes.chroot/etc/skel/.config/sway/config-light` (line 43)
- `config-all/includes.chroot/etc/skel/.config/waybar/`
- `config-all/package-lists/desktop.list.chroot`

### Result
Waybar autostart functionality was already implemented. Issue marked as resolved after code verification and cleanup.

---

## Issue #6: Wofi Not Auto-Starting and Missing Styling

**Status:** RESOLVED
**Priority:** Medium
**Component:** Sway Desktop Environment

### Description
Wofi (application launcher) is not configured to launch via keybind and lacks proper styling/theming.

### Expected Behavior
- Wofi should launch when user presses Super+D (or configured launcher key)
- Wofi should match Osiris theme (dark mode with proper colors)
- Wofi should display application icons

### Root Cause
Investigation revealed that Wofi keybind and styling were already implemented. A hardcoded path in the config file was identified and fixed.

### Solution Implemented
Verified and fixed:
- [x] Keybind configured: `bindsym $mod+d exec wofi --show drun` (line 78 in all configs)
- [x] Wofi package installed in desktop.list.chroot
- [x] Style files exist: style-dark.css and style-light.css
- [x] Theme switching integrated in osiris-theme command
- [x] Fixed hardcoded path: Changed `/home/user/.config/wofi/style.css` to `$HOME/.config/wofi/style.css`
- [x] Verified theme hook properly handles wofi styling

### Files Modified
- `config-all/includes.chroot/etc/skel/.config/wofi/config` - Fixed hardcoded path (line 16)

### Files Verified
- `config-all/includes.chroot/etc/skel/.config/sway/config` (keybind at line 78)
- `config-all/includes.chroot/etc/skel/.config/wofi/style-dark.css`
- `config-all/includes.chroot/etc/skel/.config/wofi/style-light.css`
- `config-all/hooks/live/0060-setup-themes.hook.chroot` (lines 42, 46, 177-180)

### Result
Wofi functionality was already implemented. Fixed path issue for better portability and verified theme integration.

---

## Issue Summary

| Issue | Status | Priority | Component | Impact |
|-------|--------|----------|-----------|--------|
| #1 GRUB Theme | Open | Medium | Bootloader | Low (cosmetic) |
| #2 Session Selector | **FIXED** | High | Display Manager | High (UX) |
| #3 Plymouth Theme | Open | Low | Boot Splash | Low (cosmetic) |
| #4 Greeter Icons | **RESOLVED** | Medium | Display Manager | Medium (polish) |
| #5 Waybar Autostart | **RESOLVED** | High | Sway Desktop | High (UX) |
| #6 Wofi Configuration | **RESOLVED** | Medium | Sway Desktop | Medium (UX) |
| #7 Theme Hook Refactor | Open | Low | Build System | Low (tech debt) |
| #8 Hook Security | **Open** | **CRITICAL** | Build System | **High (security)** |
| #9 Hook Idempotency | Open | Medium | Build System | Low (reliability) |
| #10 Hook Verification | **Open** | **High** | Build System | **Medium (reliability)** |
| #11 Hook Code Style | Open | Low | Build System | Low (polish) |
| #12 pip --break-system-packages | **Open** | **High** | Build System | **Medium (stability)** |

---

## Recommended Fix Order

### High Priority (Security & Reliability)
1. **Issue #8 (Hook Security)** - CRITICAL - Add checksum verification to downloads
2. **Issue #10 (Hook Verification)** - Add success checks to critical operations
3. **Issue #12 (pip --break-system-packages)** - Fix unsafe autotiling installation

### Medium Priority (Quality & Maintainability)
4. **Issue #9 (Hook Idempotency)** - Fix duplicate append operations
5. **Issue #7 (Theme Hook Refactor)** - Simplify theme system

### Low Priority (Cosmetic & Polish)
6. **Issue #11 (Hook Code Style)** - Remove emojis from all hooks
7. **Issue #1 (GRUB Theme)** - Adds branding
8. **Issue #3 (Plymouth)** - Boot splash theme

---

## Issue #7: Theme Hook System Needs Refactoring

**Status:** Open
**Priority:** Low (Technical Debt)
**Component:** Build System (Hook 0060-setup-themes.hook.chroot)

### Description
The theme switching hook (0060-setup-themes.hook.chroot) is overly complex and tries to do too much during build time. It attempts to copy default config files that should just exist in the filesystem.

### Current Problems
1. **Hook copies files during build** - Tries to copy style-dark.css to style.css, config-dark to config, etc.
2. **Fragile logic** - File copy operations in hooks can fail silently
3. **Redundant with filesystem** - Default files should just exist in includes.chroot
4. **Maintenance burden** - Hard to debug when hook logic doesn't execute as expected

### Recommended Approach
**Rely on filesystem defaults instead of hook logic:**
- Default config files (style.css, config, foot.ini) should exist in source tree
- These defaults should be dark mode (project standard)
- Theme switcher (osiris-theme command) handles runtime theme switching
- Hook should only install the osiris-theme script, not manage default files

### Benefits
- Simpler, more maintainable
- Easier to debug (what you see in source is what you get)
- No silent failures from hook file operations
- Clear separation: build-time vs runtime theme switching

### Files Affected
- `config-all/hooks/live/0060-setup-themes.hook.chroot`
- `config-all/includes.chroot/etc/skel/.config/sway/config` (default exists)
- `config-all/includes.chroot/etc/skel/.config/waybar/style.css` (default exists)
- `config-all/includes.chroot/etc/skel/.config/wofi/style.css` (default exists)
- `config-all/includes.chroot/etc/skel/.config/foot/foot.ini` (needs default)

### Notes
This is technical debt, not a functional bug. The current system works but is unnecessarily complex.

---

## Issue #8: Hook Security - Missing Download Verification

**Status:** Open
**Priority:** CRITICAL
**Component:** Build System (Hooks)

### Description
Multiple hooks download files from the internet without verifying checksums, creating security vulnerabilities and potential build inconsistencies.

### Affected Hooks
1. **0050-install-swayfx-official.hook.chroot**
   - Downloads wlroots 0.16.2 without SHA-256 checksum verification
   - Downloads SwayFX 0.3.2 without SHA-256 checksum verification

2. **0055-install-nerd-fonts.hook.chroot**
   - Downloads JetBrains Mono Nerd Font v3.1.1 without checksum verification

3. **0090-install-vscode.hook.chroot**
   - Downloads Microsoft GPG key without fingerprint verification

### Security Impact
- Man-in-the-middle attacks could inject malicious code during build
- Corrupted downloads could cause build failures
- No guarantee of build reproducibility between builds
- Supply chain attack vulnerability

### Recommended Solution
Add SHA-256 checksum verification for all downloads and GPG key fingerprint verification:

```bash
# Example for SwayFX
WLROOTS_VERSION="0.16.2"
WLROOTS_SHA256="<calculate-checksum>"
wget https://gitlab.freedesktop.org/wlroots/wlroots/-/archive/${WLROOTS_VERSION}/wlroots-${WLROOTS_VERSION}.tar.gz

# Verify checksum
ACTUAL_SHA256=$(sha256sum wlroots-${WLROOTS_VERSION}.tar.gz | cut -d' ' -f1)
if [ "$ACTUAL_SHA256" != "$WLROOTS_SHA256" ]; then
    echo "ERROR: Checksum mismatch for wlroots"
    exit 1
fi
```

### Tasks
- [ ] Calculate SHA-256 checksums for wlroots 0.16.2 and SwayFX 0.3.2
- [ ] Add checksum verification to 0050-install-swayfx-official.hook.chroot
- [ ] Add checksum verification to 0055-install-nerd-fonts.hook.chroot
- [ ] Verify Microsoft GPG key fingerprint in 0090-install-vscode.hook.chroot
- [ ] Document pattern in BEST_PRACTICES_HOOKS.md (done)

### References
- See `docs/BEST_PRACTICES_HOOKS.md` for security best practices

---

## Issue #9: Hook Idempotency - Duplicate Append Operations

**Status:** Open
**Priority:** Medium
**Component:** Build System (Hooks)

### Description
Hook 0089 appends to files without checking if content already exists, causing duplicate entries if the hook runs multiple times.

### Affected Hook
**0089-disable-debian-calamares-autostart.hook.chroot**
- Appends `Hidden=true` to desktop file without checking if already present
- Running hook twice creates malformed desktop file with duplicate lines

### Current Behavior
```bash
echo "Hidden=true" >> "$DEBIAN_AUTOSTART"
# If run twice: file contains multiple "Hidden=true" lines
```

### Expected Behavior
```bash
if ! grep -q "^Hidden=" "$DEBIAN_AUTOSTART"; then
    echo "Hidden=true" >> "$DEBIAN_AUTOSTART"
fi
```

### Tasks
- [ ] Fix 0089-disable-debian-calamares-autostart.hook.chroot to check before appending
- [ ] Audit all hooks for similar append-without-check patterns
- [ ] Test hook idempotency in build process

### References
- See `docs/BEST_PRACTICES_HOOKS.md` section on Idempotency

---

## Issue #10: Hook Safety - Missing Verification Checks

**Status:** Open
**Priority:** High
**Component:** Build System (Hooks)

### Description
Several hooks perform critical operations without verifying success, potentially causing silent failures that only manifest at runtime in the live system.

### Affected Hooks

**0010-autologin.hook.chroot:**
- Creates user but doesn't verify user exists before passwd/sudoers operations
- sudoers file created but not validated
- Could fail silently if user creation fails

**0015-setup-lightdm-icons.hook.chroot:**
- Attempts to chown to lightdm user without verifying user exists first
- Silences errors with `|| true`

**0065-install-autotiling.hook.chroot:**
- Installs autotiling but doesn't verify command is available after install
- Uses `--break-system-packages` without verification

**0090-install-vscode.hook.chroot:**
- Adds repository and installs VSCode without verifying binary exists
- No check that installation actually succeeded

### Recommended Approach
Add verification after critical operations:

```bash
# Create user
useradd -m -s /bin/bash user 2>/dev/null || true

# VERIFY user was created
if ! id user &>/dev/null; then
    echo "ERROR: User creation failed"
    exit 1
fi

# Continue with user configuration...
```

### Tasks
- [ ] Add user existence check to 0010-autologin.hook.chroot before passwd/sudoers
- [ ] Add lightdm user check to 0015-setup-lightdm-icons.hook.chroot before chown
- [ ] Add autotiling command verification to 0065-install-autotiling.hook.chroot
- [ ] Add VSCode binary check to 0090-install-vscode.hook.chroot
- [ ] Document verification pattern in BEST_PRACTICES_HOOKS.md (done)

### References
- See `docs/BEST_PRACTICES_HOOKS.md` section on Error Handling

---

## Issue #11: Code Style - Emoji Usage in Hooks

**Status:** Open
**Priority:** Low
**Component:** Build System (All Hooks)

### Description
All 16 hooks use emojis in output messages, violating the project's code style guidelines which explicitly state "NO EMOJIS".

### Current Examples
```bash
echo "✓ Configuration complete"
echo "✗ Error occurred"
echo "⚠ Warning: something happened"
```

### Expected Style
```bash
echo "Configuration complete"
echo "ERROR: Operation failed"
echo "WARNING: Something happened"
```

### Affected Hooks
All hooks use emojis in output:
- 0005-fix-permissions.hook.chroot
- 0010-autologin.hook.chroot
- 0015-setup-lightdm-icons.hook.chroot
- 0040-setup-plymouth.hook.chroot
- 0045-customize-branding.hook.chroot
- 0050-install-swayfx-official.hook.chroot
- 0055-install-nerd-fonts.hook.chroot
- 0060-setup-themes.hook.chroot
- 0065-install-autotiling.hook.chroot
- 0070-setup-xfce-minimal.hook.chroot
- 0085-enable-calamares-netinstall.hook.chroot
- 0086-fix-calamares-icon.hook.chroot
- 0088-generate-cracklib-dict.hook.chroot
- 0089-disable-debian-calamares-autostart.hook.chroot
- 0090-install-vscode.hook.chroot
- 0095-update-icon-cache.hook.chroot

### Tasks
- [ ] Remove all emojis from hook output
- [ ] Use standard prefixes: ERROR:, WARNING:, INFO: where appropriate
- [ ] Update BEST_PRACTICES_HOOKS.md with style examples (done)

### References
- See `CLAUDE.md` code style guidelines
- See `docs/BEST_PRACTICES_HOOKS.md` section on Code Style

---

## Issue #12: Hook Robustness - Unsafe pip Installation

**Status:** Open
**Priority:** High
**Component:** Build System (Hook 0065-install-autotiling.hook.chroot)

### Description
Hook uses `pip3 install --break-system-packages` to install autotiling, which bypasses Python's package management protections and could cause system instability.

### Current Implementation
```bash
pip3 install autotiling --break-system-packages
```

### Problems
1. **No version pinning** - Installs latest version (unreproducible builds)
2. **System package conflict risk** - Could conflict with Debian Python packages
3. **No verification** - Doesn't check if installation succeeded
4. **Bypasses protections** - `--break-system-packages` disables PEP 668 safety checks

### Recommended Solutions

**Option 1: Use pipx (preferred)**
```bash
# Add to package list: pipx
pipx install autotiling==1.6.0
```

**Option 2: Virtual environment**
```bash
python3 -m venv /opt/autotiling-env
/opt/autotiling-env/bin/pip install autotiling==1.6.0
ln -s /opt/autotiling-env/bin/autotiling /usr/local/bin/autotiling
```

**Option 3: Pin version and verify**
```bash
pip3 install autotiling==1.6.0 --break-system-packages

# Verify installation
if ! command -v autotiling &>/dev/null; then
    echo "ERROR: autotiling installation failed"
    exit 1
fi
```

### Tasks
- [ ] Research autotiling version compatibility with SwayFX 0.3.2
- [ ] Implement pipx or venv solution
- [ ] Add version pinning
- [ ] Add installation verification
- [ ] Test autotiling functionality in both live and installed systems

### References
- See `docs/BEST_PRACTICES_HOOKS.md` section on Security (Avoid --break-system-packages)

---

## What's Working Great

- Core system installation
- Dual desktop environments (Sway + XFCE)
- LightDM session selector (can switch between Sway/XFCE)
- XFCE desktop fully functional with proper theming
- Sway desktop with Waybar status bar and Wofi launcher
- Theme switching system (dark/light modes via osiris-theme)
- Desktop installer icon
- Password validation
- GRUB bootloader installation
- System boots successfully
- Both desktop environments function properly

**The distro is fully functional!** Remaining issues are purely cosmetic (GRUB and Plymouth themes).

---

## Notes for Future Development

- Document GRUB theme creation process
- Consider using a Plymouth theme package instead of custom theme
- Add automated checks for desktop environment completeness
- Consider creating a unified theming hook that handles XFCE, LightDM, Sway, and GRUB together
- Test both Sway and XFCE sessions during build validation

## Code Quality Improvements (2025-11-19)

Fixed several code quality issues during Sway configuration review:
- Removed duplicate window rules in all Sway config files (config, config-dark, config-light)
- Fixed hardcoded path in wofi config: `/home/user/` to `$HOME/`
- Verified theme switching system properly handles waybar and wofi styling
- All Sway components (waybar, wofi, theme switching) were already implemented correctly

---

**Last Updated:** 2025-11-19
**Status:** System fully functional, both desktops working, only cosmetic polish remaining
