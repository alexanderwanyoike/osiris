"""The Harness's own look stays on top of the GTK 4 user sheet, which a Skin
fills with whole-window rules; below it, a Skin's solid window background
replaces the drawer's glass."""

from __future__ import annotations

from look import Look

from osiris.apps.user_css import UserCss


def test_the_drawers_look_outranks_the_user_sheet() -> None:
    assert Look.PRIORITY > UserCss.PRIORITY
