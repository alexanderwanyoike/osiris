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

**Status:** Open
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

### Current Behavior
Sway starts without Waybar. Users must manually launch Waybar from terminal.

### Potential Causes
1. **Waybar not in Sway autostart**
   - Sway config `/etc/skel/.config/sway/config` missing `exec waybar` command
   - Or autostart section not configured properly

2. **Waybar binary not found**
   - PATH issue or waybar not installed
   - Check if `waybar` package is in `desktop.list.chroot`

3. **Waybar configuration error**
   - Config file has syntax errors preventing launch
   - Check `/etc/skel/.config/waybar/config`

### Possible Solutions
- [ ] Add `exec waybar` to Sway config autostart section
- [ ] Verify waybar package installed
- [ ] Check waybar config syntax
- [ ] Test manual launch: `waybar` to see error output

### References
- Sway config: `config-all/includes.chroot/etc/skel/.config/sway/config`
- Waybar config: `config-all/includes.chroot/etc/skel/.config/waybar/`

---

## Issue #6: Wofi Not Auto-Starting and Missing Styling

**Status:** Open
**Priority:** Medium
**Component:** Sway Desktop Environment

### Description
Wofi (application launcher) is not configured to launch via keybind and lacks proper styling/theming.

### Expected Behavior
- Wofi should launch when user presses Super+D (or configured launcher key)
- Wofi should match Osiris theme (dark mode with proper colors)
- Wofi should display application icons

### Current Behavior
- Wofi keybind not working or not configured
- If launched manually, Wofi appears unstyled or with default theme

### Potential Causes
1. **Keybind not configured**
   - Sway config missing `bindsym $mod+d exec wofi --show drun`
   - Or keybind points to different launcher

2. **Wofi not installed**
   - Check if `wofi` package is in `desktop.list.chroot`

3. **Wofi styling not configured**
   - Missing `/etc/skel/.config/wofi/style.css`
   - Or config doesn't reference style file

4. **Theme switcher not updating Wofi**
   - `osiris-theme` command might not be switching Wofi theme
   - Check hook `0060-setup-themes.hook.chroot`

### Possible Solutions
- [ ] Add Wofi keybind to Sway config: `bindsym $mod+d exec wofi --show drun`
- [ ] Verify wofi package installed
- [ ] Create/update Wofi style.css for dark/light themes
- [ ] Update osiris-theme to switch Wofi styling
- [ ] Test: `wofi --show drun` to see current state

### References
- Sway config: `config-all/includes.chroot/etc/skel/.config/sway/config`
- Wofi config: `config-all/includes.chroot/etc/skel/.config/wofi/`
- Theme hook: `config-all/hooks/live/0060-setup-themes.hook.chroot`

---

## Issue Summary

| Issue | Status | Priority | Component | Impact |
|-------|--------|----------|-----------|--------|
| #1 GRUB Theme | Open | Medium | Bootloader | Low (cosmetic) |
| #2 Session Selector | **FIXED** | High | Display Manager | High (UX) |
| #3 Plymouth Theme | Open | Low | Boot Splash | Low (cosmetic) |
| #4 Greeter Icons | **RESOLVED** | Medium | Display Manager | Medium (polish) |
| #5 Waybar Autostart | **Open** | **High** | Sway Desktop | **High (UX)** |
| #6 Wofi Configuration | **Open** | Medium | Sway Desktop | Medium (UX) |

---

## Recommended Fix Order

1. **Issue #5 (Waybar)** - Sway session incomplete without status bar
2. **Issue #6 (Wofi)** - Sway needs application launcher
3. **Issue #1 (GRUB Theme)** - Adds branding, medium effort
4. **Issue #3 (Plymouth)** - Lowest priority, purely cosmetic

---

## What's Working Great

- Core system installation
- Dual desktop environments (Sway + XFCE)
- LightDM session selector (can switch between Sway/XFCE)
- XFCE desktop fully functional with proper theming
- Desktop installer icon
- Password validation
- GRUB bootloader installation
- System boots successfully
- Both desktop environments function properly

**The distro is functional!** Remaining issues are UX improvements for Sway and cosmetic polish.

---

## Notes for Future Development

- Document GRUB theme creation process
- Consider using a Plymouth theme package instead of custom theme
- Fix Sway autostart configuration for Waybar and Wofi
- Add automated checks for desktop environment completeness
- Consider creating a unified theming hook that handles XFCE, LightDM, Sway, and GRUB together
- Test both Sway and XFCE sessions during build validation

---

**Last Updated:** 2025-11-19
**Status:** System functional, session selector working, Sway UX improvements needed
