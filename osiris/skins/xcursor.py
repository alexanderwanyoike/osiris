"""Read one image from an Xcursor file, the format cursor themes use.

All values are little-endian: a header ("Xcur", size, version, entry count),
a table of (type, nominal size, position) entries, and image chunks of nine
words followed by premultiplied ARGB pixels.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

_IMAGE = 0xFFFD0002
#: Real themes stop at 256; anything past this is not a cursor worth reading.
_MAX_SIZE = 1024


class XcursorError(ValueError):
    """Bytes that are not an Xcursor file with an image."""


@dataclass(frozen=True)
class Cursor:
    width: int
    height: int
    xhot: int
    yhot: int
    rgba: bytes


def read(data: bytes, size: int) -> Cursor:
    try:
        return _read(data, size)
    except struct.error as error:
        raise XcursorError(f"not an Xcursor file: {error}") from None


def _read(data: bytes, size: int) -> Cursor:
    if data[:4] != b"Xcur" or len(data) < 16:
        raise XcursorError("not an Xcursor file")
    _header, _version, count = struct.unpack_from("<3I", data, 4)
    entries = [struct.unpack_from("<3I", data, 16 + 12 * i) for i in range(count)]
    images = [
        (nominal, position) for kind, nominal, position in entries if kind == _IMAGE
    ]
    if not images:
        raise XcursorError("no image in the cursor")
    _nominal, position = min(images, key=lambda image: abs(image[0] - size))
    width, height, xhot, yhot = struct.unpack_from("<4I", data, position + 16)
    if width > _MAX_SIZE or height > _MAX_SIZE:
        raise XcursorError(f"a {width}x{height} image is too large for a cursor")
    pixels = struct.unpack_from(f"<{width * height}I", data, position + 36)
    return Cursor(width, height, xhot, yhot, bytes(_straight(pixels)))


def _straight(pixels: tuple[int, ...]) -> list[int]:
    out: list[int] = []
    for pixel in pixels:
        alpha = pixel >> 24
        red, green, blue = (pixel >> 16) & 255, (pixel >> 8) & 255, pixel & 255
        if alpha:
            red, green, blue = (
                min(255, (c * 255 + alpha // 2) // alpha) for c in (red, green, blue)
            )
        out += (red, green, blue, alpha)
    return out


def png(cursor: Cursor) -> bytes:
    def chunk(kind: bytes, body: bytes) -> bytes:
        return (
            struct.pack(">I", len(body))
            + kind
            + body
            + struct.pack(">I", zlib.crc32(kind + body))
        )

    stride = cursor.width * 4
    rows = b"".join(
        b"\x00" + cursor.rgba[row * stride : (row + 1) * stride]
        for row in range(cursor.height)
    )
    header = struct.pack(">IIBBBBB", cursor.width, cursor.height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )
