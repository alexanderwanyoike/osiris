# Osiris work status

Living document. Update at the end of each working session so the next one can pick up cold.

## Last update

**Date:** 2026-05-02
**Branch:** `v2`
**Phase:** Phase 1 (Desktop Shell), partway through

## Phase 1 progress

| ID | Task | Status |
|---|---|---|
| P0.0 | docs/DEV_SHELL.md | done |
| P0.1 | shell/hyprland/ Lua configs | done |
| P0.6 | shell/foot/foot.ini, shell/bash/bashrc | done |
| P0.5p | shell/ags/lib/theme.ts + branding/wallpapers/osiris-default.png | done |
| P0.2 | shell/ags/ AGS top bar | done, **unverified at runtime** |
| P0.7 | shell/greetd/config.toml stub | done (deployment in Phase 2) |
| P0.3 | AGS app launcher widget | **pending** |
| P0.4 | AGS notification widget | **pending** |
| P0.5r | theme polish sweep | pending (after P0.3, P0.4) |

## Recent commits

```
6a0064d Phase 1: AGS bar widget scaffold and greetd stub
c0e2266 Phase 1: Hyprland configs, foot/bash defaults, theme tokens, wallpaper
815221c Reset v1 and document v2 design
```

## Known caveats to verify before continuing

The AGS bar widgets in `shell/ags/widget/bar/` were written by pattern-matching from `Neurarian/matshell` (a known-good reference shell). They have not been runtime-verified. The first `ags run shell/ags` on a real Hyprland host will likely surface small API drifts. Suspect property names that may need correcting:

- `AstalHyprland`: `focusedWorkspace` vs `focused_workspace`, the `focus()` method on workspace objects
- `AstalWp`: how to access the default speaker (`wp.audio.defaultSpeaker` vs `wp.audio.default_speaker` vs other)
- `AstalNetwork.Primary.WIRED` enum: may not exist with that exact name
- `AstalBattery`: `isBattery` / `batteryIconName` casing - some bindings prefer kebab-case strings to `createBinding()`

## Next step when resuming

1. Get a Hyprland host ready (Arch native, distrobox+nested, or full VM per `docs/DEV_SHELL.md`).
2. Symlink configs:
   ```
   ln -s "$PWD/shell/hyprland" ~/.config/hypr
   ln -s "$PWD/shell/ags" ~/.config/ags
   mkdir -p ~/.local/share/osiris/wallpapers
   ln -s "$PWD/branding/wallpapers/osiris-default.png" ~/.local/share/osiris/wallpapers/
   ```
3. Run `ags run shell/ags` and report errors.
4. Fix the API drift in `shell/ags/widget/bar/` files.
5. Then write `shell/ags/widget/launcher/` (P0.3) and `shell/ags/widget/notif/` (P0.4) on the verified API base.
6. Polish theme tokens (P0.5r) once everything renders.

## Files of interest

- `docs/ARCHITECTURE.md` - product vision and stack rationale
- `docs/ROADMAP.md` - all four phases with definition-of-done per task
- `docs/DEV_SHELL.md` - how to set up the dev environment
- `/home/alexander/.claude/plans/okay-lets-plan-phase-graceful-swan.md` - the approved Phase 1 plan
- `shell/ags/lib/theme.ts` - the agent-editable color/spacing/radius/typography tokens (and `themeToCss()` helper)
- `shell/hyprland/hyprland.lua` - Hyprland entrypoint (requires the rest)
- `shell/ags/app.tsx` - shell entrypoint
