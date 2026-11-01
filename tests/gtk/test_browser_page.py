"""A page in the Canvas's browser group (#197): an address line over
WebKitGTK, the page's title passed on for its tab."""

from __future__ import annotations

import time
from pathlib import Path

from gi.repository import GLib, Gtk

from .conftest import find


def settle(until) -> None:
    context = GLib.MainContext.default()
    deadline = time.monotonic() + 20
    while not until() and time.monotonic() < deadline:
        context.iteration(False)


def test_an_address_typed_and_entered_is_loaded_and_its_title_passed_on(
    tmp_path: Path,
) -> None:
    from browser import Page

    (tmp_path / "notes.html").write_text("<title>Notes</title><p>hello</p>")
    titles: list[str] = []
    page = Page(on_title=titles.append)
    entry = find(page, Gtk.Entry)
    entry.set_text(f"file://{tmp_path}/notes.html")
    entry.emit("activate")
    settle(lambda: "Notes" in titles)
    assert page.view.get_uri() == f"file://{tmp_path}/notes.html"
    assert titles[-1] == "Notes"


def test_a_page_opened_at_an_address_shows_it_in_its_address_line(
    tmp_path: Path,
) -> None:
    from browser import Page

    (tmp_path / "a.html").write_text("<title>A</title>")
    page = Page(f"file://{tmp_path}/a.html")
    settle(lambda: page.view.get_title() == "A")
    assert find(page, Gtk.Entry).get_text() == f"file://{tmp_path}/a.html"
