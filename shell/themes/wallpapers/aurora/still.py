"""Aurora's still, and the glows its shader draws from."""
import wallpaper


def still(theme, size, phase=None):
    return wallpaper.compose(theme, size, style="aurora", logo=False, phase=phase)


def uniforms(theme, size):
    glows = wallpaper.aurora_shape(wallpaper._rng(theme),
                                   drift=wallpaper._rng(theme, "drift"))
    return {"u_reach": [1, [wallpaper.QUIET_RADIUS]],
            "u_glow_a": [4, [float(v) for g in glows
                             for v in (g["angle"], g["turn"], g["fx"], g["fy"])]],
            "u_glow_b": [4, [float(v) for g in glows
                             for v in (g["rx"], g["ry"], 0, 0)]]}
