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

## Issue #2: LightDM Slick-Greeter Session Selector Not Showing

**Status:** Open
**Priority:** High (UX Impact)
**Component:** Display Manager (LightDM)

### Description
LightDM slick-greeter doesn't display the session selection dropdown, preventing users from choosing between Sway and XFCE at login.

### Expected Behavior
Slick-greeter should show a session dropdown/button allowing users to select:
- Sway Session
- XFCE Session

### Current Behavior
No session selector visible. Users default to one session without choice.

### Potential Causes
1. **Session selector disabled in slick-greeter config**
   - `/etc/lightdm/slick-greeter.conf` might have `show-session-menu=false`
   - Or selector is hidden/not configured

2. **Only one session detected**
   - If LightDM only finds one valid session, it might hide the selector
   - Check if both `/usr/share/xsessions/xfce.desktop` and `/usr/share/wayland-sessions/sway.desktop` are valid

3. **Theme/layout issue**
   - Session selector element might be off-screen or hidden by theme
   - Icon or button might be present but invisible

4. **LightDM configuration issue**
   - `/etc/lightdm/lightdm.conf` might not be configured for multi-session
   - User-session not set correctly

### Possible Solutions
- [ ] Verify both session files exist and are valid:
  - `/usr/share/xsessions/xfce.desktop`
  - `/usr/share/wayland-sessions/sway.desktop`
- [ ] Check `/etc/lightdm/slick-greeter.conf`:
  - Ensure `show-session-menu=true` (or not explicitly disabled)
  - Check if `session-menu-position` is visible
- [ ] Test with: `dm-tool switch-to-greeter` to reload greeter
- [ ] Check LightDM logs: `/var/log/lightdm/`
- [ ] Verify session .desktop files have proper permissions (644)

### References
- Slick-greeter config: `/etc/lightdm/slick-greeter.conf`
- LightDM config: `/etc/lightdm/lightdm.conf`
- Session files: `/usr/share/{xsessions,wayland-sessions}/`

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

## Issue #4: Slick-Greeter Icons Not Displaying Correctly

**Status:** Open
**Priority:** Medium
**Component:** Display Manager (LightDM)

### Description
Icons in the LightDM slick-greeter are not displaying properly - showing wrong icons, broken icons, or no icons.

### Expected Behavior
Slick-greeter should display proper icons for:
- User avatar
- Session selector
- Power options (shutdown, restart)
- Accessibility options

### Current Behavior
Icons are missing, broken, or using wrong/default icons.

### Potential Causes
1. **Icon theme mismatch**
   - Slick-greeter config points to icon theme not installed
   - Currently configured: `Papirus-Dark` (in hook 0015-setup-lightdm-icons.hook.chroot)
   - We switched to `elementary-xfce-dark` for XFCE but didn't update LightDM config

2. **Icon theme not installed for LightDM user**
   - Icon theme exists but LightDM user (`lightdm`) can't access it
   - Permissions issue with icon cache

3. **Icon names don't match theme**
   - Slick-greeter expects specific icon names
   - Theme doesn't provide those icon names

4. **GTK icon cache not updated**
   - Icon cache for LightDM not generated
   - Hook 0095-update-icon-cache might not cover LightDM

### Possible Solutions
- [ ] Update hook `0015-setup-lightdm-icons.hook.chroot`:
  - Change from `Papirus-Dark` to `elementary-xfce-dark`
  - Ensure consistency with XFCE settings
- [ ] Verify icon theme installed:
  - Check `elementary-xfce-icon-theme` package is in package list ✓ (already there)
- [ ] Update icon cache for LightDM:
  ```bash
  gtk-update-icon-cache -f -t /usr/share/icons/elementary-xfce-dark/
  ```
- [ ] Check slick-greeter config `/etc/lightdm/slick-greeter.conf`:
  - Verify `icon-theme-name` setting
  - Check if specific icons are configured
- [ ] Test with different icon theme to isolate issue

### References
- LightDM icon config: `/var/lib/lightdm/.config/gtk-3.0/settings.ini`
- Slick-greeter config: `/etc/lightdm/slick-greeter.conf`
- Hook: `config-all/hooks/live/0015-setup-lightdm-icons.hook.chroot`
- We already fixed XFCE to use `elementary-xfce-dark` - need to sync LightDM

---

## Issue Summary

| Issue | Priority | Component | Difficulty | Impact |
|-------|----------|-----------|------------|--------|
| #1 GRUB Theme | Medium | Bootloader | Medium | Low (cosmetic) |
| #2 Session Selector | **High** | Display Manager | Easy-Medium | **High (UX)** |
| #3 Plymouth Theme | Low | Boot Splash | Medium | Low (cosmetic) |
| #4 Greeter Icons | Medium | Display Manager | Easy | Medium (polish) |

---

## Recommended Fix Order

1. **Issue #2 (Session Selector)** - Highest UX impact, relatively easy fix
2. **Issue #4 (Greeter Icons)** - Related to #2, sync icon theme with XFCE changes
3. **Issue #1 (GRUB Theme)** - Adds branding, medium effort
4. **Issue #3 (Plymouth)** - Lowest priority, purely cosmetic

---

## Quick Wins

**Issue #4 is partially solved already!**
We fixed XFCE icons to use `elementary-xfce-dark` but forgot to update LightDM. Quick fix:

1. Edit `config-all/hooks/live/0015-setup-lightdm-icons.hook.chroot`
2. Change `gtk-icon-theme-name=Papirus-Dark` → `gtk-icon-theme-name=elementary-xfce-dark`
3. Rebuild

This might also help with Issue #2 if icons are making the session selector invisible.

---

## What's Working Great

- Core system installation
- Dual desktop environments (Sway + XFCE)
- XFCE icons and theming
- Desktop installer icon
- Password validation
- GRUB bootloader installation
- System boots successfully
- Both Sway and XFCE function properly

**The distro is functional!** These are polish issues that can be fixed incrementally.

---

## Notes for Future Development

- Document GRUB theme creation process
- Consider using a Plymouth theme package instead of custom theme
- LightDM/slick-greeter testing should be part of build validation
- Add automated checks for icon theme consistency across components
- Consider creating a unified theming hook that handles XFCE, LightDM, and GRUB together

---

**Last Updated:** 2025-11-19
**Status:** System functional, cosmetic polish needed
