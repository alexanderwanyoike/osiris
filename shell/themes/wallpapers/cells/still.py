"""The cells' still, and the sites its shader draws from."""
import wallpaper


def still(theme, size, phase=None):
    return wallpaper.compose(theme, size, style="cells", logo=False, phase=phase)


def uniforms(theme, size):
    sites = wallpaper.cells_shape(wallpaper._rng(theme), size[0] / size[1],
                                  drift=wallpaper._rng(theme, "drift"))
    packed = [float(v) for i in range(len(sites["x"])) for v in (
        sites["x"][i], sites["y"][i], sites["turn"][i], sites["levels"][i])]
    return {"u_reach": [1, [wallpaper.QUIET_RADIUS]],
            "u_sites": [4, packed],
            "u_cells": [2, [float(len(sites["x"])), float(sites["rows"])]]}
