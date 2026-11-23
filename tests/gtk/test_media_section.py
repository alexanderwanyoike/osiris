"""Connecting FAL, the media Provider, in Settings."""

from __future__ import annotations

from dataclasses import dataclass

from gi.repository import Gtk
from media_section import MediaSection

from osiris.harness.media.limit_setting import SUGGESTED_LIMIT
from tests.gtk.conftest import find, shown, widgets


@dataclass
class Keys:
    key: str | None = None
    images: int | None = None

    def limit(self) -> int | None:
        return self.images

    def set_limit(self, images: int | None) -> None:
        self.images = images

    def connected(self) -> bool:
        return self.key is not None

    def save(self, key: str) -> None:
        self.key = key

    def remove(self) -> None:
        self.key = None


def section(keys: Keys) -> MediaSection:
    return MediaSection(
        keys.connected, keys.save, keys.remove, keys.limit, keys.set_limit
    )


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


def test_the_section_says_what_fal_is_for_without_promising_a_limit() -> None:
    said = shown(section(Keys()))

    assert any("Themes" in text and "FAL account" in text for text in said)
    assert not any("a day" in text for text in said)


def test_there_is_no_limit_until_the_person_turns_one_on() -> None:
    keys = Keys()
    page = section(keys)

    assert "Daily picture limit" in shown(page)
    assert not find(page, Gtk.Switch).get_active()
    assert not find(page, Gtk.SpinButton).get_visible()
    assert keys.images is None


def test_turning_the_limit_on_suggests_a_number_and_saves_it() -> None:
    keys = Keys()
    page = section(keys)

    find(page, Gtk.Switch).set_active(True)

    assert find(page, Gtk.SpinButton).get_visible()
    assert keys.images == SUGGESTED_LIMIT


def test_turning_the_limit_off_removes_it() -> None:
    keys = Keys(images=30)
    page = section(keys)

    find(page, Gtk.Switch).set_active(False)

    assert keys.images is None
    assert not find(page, Gtk.SpinButton).get_visible()


def test_a_saved_limit_is_shown_and_opening_settings_does_not_change_it() -> None:
    keys = Keys(images=30)
    page = section(keys)

    assert find(page, Gtk.Switch).get_active()
    assert find(page, Gtk.SpinButton).get_value_as_int() == 30
    assert keys.images == 30
