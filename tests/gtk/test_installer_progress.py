"""The installer's progress page, while archinstall runs."""

from __future__ import annotations

from typing import Any

import pytest
from gi.repository import Gtk

from osiris.provision.install_progress import Status

from .conftest import find, now, shown
from .test_installer_network import FakeNetwork, installer


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
