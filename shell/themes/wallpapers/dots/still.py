"""The dots' still, and the noise its shader draws from.

The noise is normalised by its range over the whole image, which a shader
cannot see, so ranges() measures it round the loop for the shader to use.
"""
import numpy as np

import wallpaper


def still(theme, size, phase=None):
    return wallpaper.compose(theme, size, style="dots", logo=False, phase=phase)


def _lattices(theme):
    # dots() asks fbm for cells=2, octaves=3 before anything else.
    return wallpaper.fbm_lattices(wallpaper._rng(theme), 2, 3,
                                  wallpaper._rng(theme, "drift"))


def uniforms(theme, size):
    found = _lattices(theme)
    return {"u_reach": [1, [wallpaper.QUIET_RADIUS]],
            "u_lat": [4, [float(v) for a, _ in found for v in a.ravel()]],
            "u_par": [4, [float(v) for _, b in found for v in b.ravel()]]}


def ranges(theme, size, phases):
    found = _lattices(theme)
    # A quarter of the size measures the same smooth field closely enough.
    small = (size[1] // 4, size[0] // 4)
    fields = (wallpaper.fbm_raw(small, found, phase=p) for p in phases)
    return [[float(np.min(f)), float(np.max(f))] for f in fields]
