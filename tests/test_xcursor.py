"""Reading a cursor theme's pointer, so a Skin's picture and the Skin editor
can show its cursor: Xcursor files hold images at several sizes."""

from __future__ import annotations

import struct
import zlib

import pytest

from osiris.skins.xcursor import XcursorError, png, read

IMAGE = 0xFFFD0002


def xcursor(images: list[tuple[int, int, int]]) -> bytes:
    """A file holding one image per (nominal size, width, ARGB pixel)."""
    toc_end = 16 + 12 * len(images)
    chunks, toc, position = b"", b"", toc_end
    for nominal, width, pixel in images:
        chunk = struct.pack("<9I", 36, IMAGE, nominal, 1, width, width, 1, 2, 0)
        chunk += struct.pack("<I", pixel) * (width * width)
        toc += struct.pack("<3I", IMAGE, nominal, position)
        chunks += chunk
        position += len(chunk)
    return b"Xcur" + struct.pack("<3I", 16, 0x10000, len(images)) + toc + chunks


def test_the_image_nearest_the_size_asked_for_is_read() -> None:
    cursor = read(xcursor([(24, 24, 0xFF000000), (32, 32, 0xFF000000)]), 30)
    assert (cursor.width, cursor.height, cursor.xhot, cursor.yhot) == (32, 32, 1, 2)


def test_pixels_come_out_as_plain_rgba() -> None:
    """Xcursor stores premultiplied ARGB; pictures want straight RGBA."""
    cursor = read(xcursor([(24, 1, 0x80400000)]), 24)
    assert cursor.rgba == bytes([128, 0, 0, 128])


def test_a_file_that_is_not_a_cursor_is_refused() -> None:
    with pytest.raises(XcursorError):
        read(b"not a cursor at all", 24)


def test_a_cursor_becomes_a_png_of_its_size() -> None:
    data = png(read(xcursor([(24, 2, 0xFFFFFFFF)]), 24))
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    assert (width, height) == (2, 2)
    raw = zlib.decompress(data[data.index(b"IDAT") + 4 : data.index(b"IEND") - 8])
    assert raw == bytes([0, 255, 255, 255, 255] * 1 + [255, 255, 255, 255]) * 2


@pytest.mark.parametrize(
    "cut",
    [
        20,  # inside the table of contents
        -8,  # inside the pixels
    ],
)
def test_a_cut_short_file_is_refused_as_not_a_cursor(cut: int) -> None:
    """Review of #133: struct.error escaped, which callers do not expect."""
    data = xcursor([(24, 2, 0xFF000000)])
    with pytest.raises(XcursorError):
        read(data[:cut], 24)


def test_an_image_larger_than_any_cursor_is_refused() -> None:
    """Review of #133: a file could ask for any size, all read into memory."""
    with pytest.raises(XcursorError):
        read(xcursor([(24, 1025, 0xFF000000)]), 24)


def test_a_file_listing_more_images_than_any_cursor_is_refused() -> None:
    """Review of #133: the table of contents was read whatever its length."""
    with pytest.raises(XcursorError):
        read(xcursor([(24, 1, 0xFF000000)] * 0x10001), 24)
