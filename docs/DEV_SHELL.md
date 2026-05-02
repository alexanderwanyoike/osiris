# Developing the Osiris shell on a host machine

The Osiris desktop shell (Hyprland configs in `shell/hyprland/`, AGS project in `shell/ags/`) can be developed and iterated on without building an ISO or installing Osiris itself. This document covers how to set up your dev environment.

## What you are setting up

You will run:

- **Hyprland** as your active session (or as a nested Wayland session on top of an existing compositor for quick tests)
- **AGS** (Aylur's GTK Shell, v3) pointed at `shell/ags/` so the bar, launcher, and notifications come from this repo
- Supporting daemons: **hyprpaper**, **hypridle**, **hyprpolkitagent**, **xdg-desktop-portal-hyprland**
- **foot** terminal, **PipeWire** + **wireplumber** audio (most distros ship these by default)

## Recommended dev environment by distro

The shell targets Arch Linux. The cleanest dev experience is also on Arch. If you are not on Arch, the next-cleanest path is an Arch container or VM.

### Arch Linux (native)

```
sudo pacman -S hyprland foot hyprpaper hypridle hyprpolkitagent \
  xdg-desktop-portal-hyprland pipewire wireplumber networkmanager
```

AGS v3 is on the AUR as `aylurs-gtk-shell-git`. Use your preferred AUR helper (`yay`, `paru`):

```
yay -S aylurs-gtk-shell-git
```

### Ubuntu / Debian / other non-Arch (distrobox path, recommended)

AGS v3 is not packaged for Debian-family distros. The cleanest way to develop is an Arch [distrobox](https://distrobox.it/) container that shares your home directory and Wayland socket with the host:

```
sudo apt install distrobox podman
distrobox create --name osiris-dev --image archlinux:latest
distrobox enter osiris-dev
# inside container:
sudo pacman -S hyprland foot hyprpaper hypridle hyprpolkitagent \
  xdg-desktop-portal-hyprland pipewire wireplumber yay
yay -S aylurs-gtk-shell-git
```

The container can run AGS against the host's compositor for widget development. For Hyprland-specific testing (window rules, animations, keybinds), you need Hyprland actually running, which means either:
- Boot Hyprland on the host (install from your distro's repo or build from source), or
- Use a full Arch VM (next section).

### Full Arch VM (if distrobox or native Arch is not viable)

```
qemu-img create -f qcow2 osiris-dev.qcow2 40G
qemu-system-x86_64 -enable-kvm -m 8G -smp 4 \
  -drive file=osiris-dev.qcow2 \
  -cdrom archlinux-latest.iso \
  -boot d
```

Install Arch normally, then follow the native Arch instructions above. Mount the repo via `9p` or `virtiofs`.

## Pointing your environment at this repo

### Hyprland config

Hyprland reads `~/.config/hypr/hyprland.lua` (Lua, since v0.55). Symlink the repo's config:

```
ln -s "$(pwd)/shell/hyprland" ~/.config/hypr
```

Reload after edits with `hyprctl reload` (or restart the session for changes to autostart entries).

### AGS shell

From the repo root:

```
ags run shell/ags
```

AGS hot-reloads on file save. No build step required during development. For a production-style invocation (single bundled script):

```
ags bundle shell/ags -o /tmp/osiris-shell
/tmp/osiris-shell
```

## Dev loop

1. Edit a `.tsx` widget in `shell/ags/widget/` or a `.lua` file in `shell/hyprland/`.
2. Save.
3. AGS auto-reloads its widgets. For Hyprland config changes: `hyprctl reload`.
4. See result immediately.

For widget styling (`shell/ags/style/main.scss` and `shell/ags/lib/theme.ts`), AGS recompiles SCSS and reapplies on save.

## Verifying each piece

| Component | How to test |
|---|---|
| Hyprland keybinds | After `hyprctl reload`, try Super+Return, Super+1-9, Super+Q |
| foot terminal | Super+Return should open foot; check prompt and history work |
| Bar | AGS running should show bar at top of all monitors |
| Audio widget | `pactl set-sink-volume @DEFAULT_SINK@ +10%` should change the volume display live |
| Network widget | Toggle WiFi via `nmcli`, widget reflects state |
| Battery widget | On a laptop, widget shows percentage; on a desktop it should hide |
| Launcher | Super+Space opens the launcher; type to filter; Enter to launch |
| Notifications | `notify-send "test" "body"` produces a styled notification |
| Wallpaper | hyprpaper should show the wallpaper from `branding/` after autostart |

## Common gotchas

- **AGS v3 is a major rewrite from v1.** Tutorials and dotfiles older than mid-2024 use the v1 API and will not work. Stick to AGS v3 / Astal documentation: https://aylur.github.io/astal/
- **Hyprland v0.55+ uses Lua, not hyprlang.** Tutorials referencing `hyprland.conf` and the older syntax are outdated. Our configs are `.lua`.
- **GTK4 + Wayland** can be slow to start the first time on some systems (color-scheme detection hang). Subsequent launches are fast.
- **Inside distrobox**, the AGS bar may render on the host compositor but Hyprland-specific IPC (workspace switching, window rules) only works when the actual Hyprland session is the one being shown.
- **xdg-desktop-portal-hyprland** must be running for screen sharing, file pickers, and OAuth flows to work. Hyprland's autostart in this repo handles this.

## What NOT to install for dev

- No nm-applet: the bar widget handles network UI directly.
- No light-locker / xscreensaver: hyprlock is the lock screen.
- No swaybg: hyprpaper is the wallpaper daemon.
- No external launcher (wofi, rofi): the AGS launcher widget handles this.

If you find yourself reaching for one of these, check whether the AGS shell or Hypr ecosystem already provides it.
