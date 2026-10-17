"""The ridges' still, and the noise its shader draws from.

ridges() takes fbm over (count, width), one row per ridge, and normalises each
row by its own range. The rows are interpolated here, once, so the shader only
interpolates along x; ranges() measures each row's range round the loop.
"""
import numpy as np

import wallpaper

COUNT = 14


def still(theme, size, phase=None):
    return wallpaper.compose(theme, size, style="ridges", logo=False, phase=phase)


def _lattices(theme):
    # ridges() asks fbm for cells=3, octaves=4 before anything else.
    return wallpaper.fbm_lattices(wallpaper._rng(theme), 3, 4,
                                  wallpaper._rng(theme, "drift"))


def uniforms(theme, size):
    rows = [(wallpaper._smooth(a, (COUNT, a.shape[1])),
             wallpaper._smooth(b, (COUNT, b.shape[1])))
            for a, b in _lattices(theme)]
    return {"u_reach": [1, [wallpaper.QUIET_RADIUS]],
            "u_rl": [4, [float(v) for a, _ in rows for v in a.ravel()]],
            "u_rp": [4, [float(v) for _, b in rows for v in b.ravel()]]}


def ranges(theme, size, phases):
    found = _lattices(theme)
    out = []
    for p in phases:
        raw = wallpaper.fbm_raw((COUNT, 640), found, phase=p)
        out.append([float(v) for pair in zip(raw.min(axis=1), raw.max(axis=1),
                                             strict=True) for v in pair])
    return out
