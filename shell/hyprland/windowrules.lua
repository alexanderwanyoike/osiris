-- Window rules.

-- Apps cannot force their own maximize state; the user (or layout) decides.
hl.window_rule({
    name           = "suppress-maximize",
    match          = { class = ".*" },
    suppress_event = "maximize",
})

-- Float common picker / dialog windows.
hl.window_rule({
    name  = "float-pickers",
    match = { class = "(file_progress|confirm|dialog|download|notification|error|splash|pinentry)" },
    float = true,
})

-- XWayland drag fix from upstream defaults.
hl.window_rule({
    name  = "fix-xwayland-drags",
    match = {
        class      = "^$",
        title      = "^$",
        xwayland   = true,
        float      = true,
        fullscreen = false,
        pin        = false,
    },
    no_focus = true,
})
