-- Processes started once when Hyprland starts.
-- The AGS shell expects to be runnable as `ags run` against a project the user has symlinked
-- to ~/.config/ags (dev) or installed to /usr/share/osiris/shell/ags (production install).

hl.on("hyprland.start", function()
    -- Wallpaper, idle, polkit agent.
    hl.exec_cmd("hyprpaper")
    hl.exec_cmd("hypridle")
    hl.exec_cmd("systemctl --user start hyprpolkitagent.service")

    -- XDG desktop portal (screen share, file pickers, OAuth).
    hl.exec_cmd("systemctl --user start xdg-desktop-portal-hyprland.service")

    -- The Osiris shell (bar, launcher, notifications).
    hl.exec_cmd("ags run")
end)
