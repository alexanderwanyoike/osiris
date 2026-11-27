"""The installer's progress page, while archinstall runs."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from gi.repository import GLib, Gtk
from slideshow import Slideshow

from osiris.provision.install_progress import Status

from .conftest import find, now, settle, shown, texts
from .test_installer_network import FakeNetwork, installer

SLIDES = Path(__file__).resolve().parents[2] / "apps" / "installer" / "slides"
CAPTIONS = [
    slide["caption"] for slide in json.loads((SLIDES / "slides.json").read_text())
]


def a_progress_page() -> tuple[Any, Gtk.Widget]:
    window = installer.Window(None, network=FakeNetwork(connected=True), background=now)
    page = window.progress_page()
    window.nav.push(page)
    return window, page


def test_the_page_shows_the_stage_its_step_and_how_far() -> None:
    window, page = a_progress_page()
    window.show_status(Status("Installing the desktop", 5, 7, 0.42))
    seen = shown(page)
    assert "Installing the desktop" in seen
    assert "Step 5 of 7" in seen
    assert "42%" in seen
    bar = find(page, Gtk.ProgressBar)
    assert isinstance(bar, Gtk.ProgressBar)
    assert bar.get_fraction() == pytest.approx(0.42)


def test_archinstalls_log_waits_behind_show_details() -> None:
    _, page = a_progress_page()
    details = find(page, Gtk.Expander, "Show details")
    assert isinstance(details, Gtk.Expander)
    assert not details.get_expanded()


def test_a_failed_install_opens_the_log_so_the_error_shows() -> None:
    window, page = a_progress_page()
    window.failed(
        RuntimeError("archinstall exited 1 before the install finished."),
        "Traceback (most recent call last):\n",
    )
    details = find(page, Gtk.Expander, "Show details")
    assert isinstance(details, Gtk.Expander)
    assert details.get_expanded()
    assert "Install failed" in shown(page)


def test_the_page_shows_osiris_a_slide_at_a_time_crossfading() -> None:
    _, page = a_progress_page()
    slides = find(page, Gtk.Stack)
    assert isinstance(slides, Gtk.Stack)
    assert slides.get_transition_type() == Gtk.StackTransitionType.CROSSFADE
    showing = slides.get_visible_child()
    assert showing is not None
    assert CAPTIONS[0] in texts(showing)
    assert find(showing, Gtk.Picture).get_paintable() is not None


def test_the_slides_take_turns_and_start_again_after_the_last() -> None:
    window, _ = a_progress_page()
    seen = []
    for _ in range(len(CAPTIONS) + 1):
        seen += texts(window.slides.get_visible_child())
        window.slides.advance()
    assert seen == [*CAPTIONS, CAPTIONS[0]]


class FakeTimer:
    """GLib's repeating timeout, fired by hand.

    A real 50 ms timer raced the test's wait: five turns of five slides
    land back on the first, so how far the slides got depended on how many
    ticks Xvfb let through.
    """

    def __init__(self) -> None:
        self.every_ms: dict[int, int] = {}
        self.calls: dict[int, Callable[[], bool]] = {}

    def repeat(self, every_ms: int, call: Callable[[], bool]) -> int:
        source = len(self.every_ms) + 1
        self.every_ms[source] = every_ms
        self.calls[source] = call
        return source

    def cancel(self, source: int) -> None:
        del self.calls[source]

    def running(self) -> bool:
        return bool(self.calls)

    def fire(self) -> None:
        for source, call in list(self.calls.items()):
            if call() == GLib.SOURCE_REMOVE:
                del self.calls[source]


def test_the_slides_move_on_by_themselves_while_they_are_on_screen() -> None:
    timer = FakeTimer()
    slides = Slideshow(every_ms=50, repeat=timer.repeat, cancel=timer.cancel)
    window = Gtk.Window(child=slides)
    assert not timer.running()
    window.present()
    assert settle(timer.running)
    assert list(timer.every_ms.values()) == [50]
    timer.fire()
    timer.fire()
    assert CAPTIONS[2] in texts(slides.get_visible_child())
    window.close()
    assert settle(lambda: not timer.running())


def test_a_failed_install_puts_the_slides_away() -> None:
    window, page = a_progress_page()
    window.failed(RuntimeError("archinstall exited 1."), "")
    assert not any(caption in shown(page) for caption in CAPTIONS)
