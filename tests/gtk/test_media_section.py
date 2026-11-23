"""Connecting FAL, the media Provider, in Settings."""

from __future__ import annotations

from dataclasses import dataclass

from gi.repository import Gtk
from media_section import MediaSection

from osiris.harness.media.limit import DAILY_IMAGES
from tests.gtk.conftest import find, shown, widgets


@dataclass
class Keys:
    key: str | None = None

    def connected(self) -> bool:
        return self.key is not None

    def save(self, key: str) -> None:
        self.key = key

    def remove(self) -> None:
        self.key = None


def section(keys: Keys) -> MediaSection:
    return MediaSection(keys.connected, keys.save, keys.remove)


def test_without_a_key_fal_offers_to_add_one() -> None:
    page = section(Keys())

    assert "Media" in shown(page)
    assert "FAL" in shown(page)
    assert "Connected" not in shown(page)
    assert find(page, Gtk.Button, "Add key").get_visible()
    assert not find(page, Gtk.PasswordEntry).get_parent().get_visible()


def test_a_saved_key_connects_fal_and_is_no_longer_on_screen() -> None:
    keys = Keys()
    page = section(keys)

    find(page, Gtk.PasswordEntry).set_text("a-secret-key")
    find(page, Gtk.Button, "Save").emit("clicked")

    assert keys.key == "a-secret-key"
    assert "Connected" in shown(page)
    assert not any(isinstance(widget, Gtk.PasswordEntry) for widget in widgets(page))


def test_removing_the_key_disconnects_fal_and_offers_to_add_one_again() -> None:
    keys = Keys("a-secret-key")
    page = section(keys)

    find(page, Gtk.Button, "Remove key").emit("clicked")

    assert keys.key is None
    assert "Connected" not in shown(page)
    assert find(page, Gtk.Button, "Add key").get_visible()


def test_an_empty_key_is_not_saved() -> None:
    keys = Keys()
    page = section(keys)

    find(page, Gtk.PasswordEntry).set_text("   ")
    find(page, Gtk.Button, "Save").emit("clicked")

    assert keys.key is None
    assert "Connected" not in shown(page)


def test_the_section_says_what_fal_is_for_and_the_daily_limit() -> None:
    assert any(
        "Themes" in text and f"{DAILY_IMAGES} a day" in text
        for text in shown(section(Keys()))
    )
