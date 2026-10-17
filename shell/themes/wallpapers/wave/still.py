"""The wave's still, and the composition its shader draws from."""
import wallpaper


def still(theme, size, phase=None):
    return wallpaper.compose(theme, size, style="wave", logo=False, phase=phase)


def uniforms(theme, size):
    tilt, offsets = wallpaper.wave_shape(wallpaper._rng(theme))
    return {"u_reach": [1, [wallpaper.QUIET_REACH["wave"]]],
            "u_tilt": [1, [float(tilt)]],
            "u_offsets": [1, [float(v) for ribbon in offsets for v in ribbon]]}
