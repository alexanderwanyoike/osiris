"""A theme switch written as one dconf change."""

from __future__ import annotations

import configparser

from osiris.themes.switch import Switch, keyfile

DOCK = "/net/launchpad/plank/docks/dock1/"

NORD = Switch(
    theme="Osiris-nord",
    icons="Osiris-nord",
    cursor="Adwaita",
    font="Noto Sans 10",
    dark=True,
    wallpaper="/home/alex/.local/share/osiris/wallpapers/nord.png",
    dock="Osiris-nord",
)


def parsed(switch: Switch) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str  # type: ignore[assignment,method-assign]
    parser.read_string(keyfile(switch, DOCK))
    return parser


def test_every_surface_takes_the_theme_in_one_document() -> None:
    settings = parsed(NORD)
    for section, key in [
        ("org/cinnamon/desktop/interface", "gtk-theme"),
        ("org/cinnamon/desktop/wm/preferences", "theme"),
        ("org/cinnamon/theme", "name"),
        ("org/gnome/desktop/interface", "gtk-theme"),
    ]:
        assert settings[section][key] == "'Osiris-nord'"


def test_icons_cursor_and_font_are_set() -> None:
    interface = parsed(NORD)["org/cinnamon/desktop/interface"]
    assert interface["icon-theme"] == "'Osiris-nord'"
    assert interface["cursor-theme"] == "'Adwaita'"
    assert interface["font-name"] == "'Noto Sans 10'"


def test_libadwaita_follows_light_and_dark() -> None:
    assert parsed(NORD)["org/gnome/desktop/interface"]["color-scheme"] == (
        "'prefer-dark'"
    )
    light = Switch(**{**NORD.__dict__, "dark": False})
    assert parsed(light)["org/gnome/desktop/interface"]["color-scheme"] == (
        "'prefer-light'"
    )


def test_the_wallpaper_is_a_file_uri() -> None:
    background = parsed(NORD)["org/cinnamon/desktop/background"]
    assert background["picture-uri"] == f"'file://{NORD.wallpaper}'"
    assert background["picture-options"] == "'zoom'"


def test_the_dock_theme_is_written_at_its_relocatable_path() -> None:
    assert parsed(NORD)["net/launchpad/plank/docks/dock1"]["theme"] == ("'Osiris-nord'")


def test_absent_wallpaper_and_dock_leave_them_alone() -> None:
    bare = parsed(Switch(**{**NORD.__dict__, "wallpaper": None, "dock": None}))
    assert not bare.has_section("org/cinnamon/desktop/background")
    assert not bare.has_section("net/launchpad/plank/docks/dock1")


def test_quotes_in_values_are_escaped_for_gvariant() -> None:
    odd = Switch(**{**NORD.__dict__, "wallpaper": "/home/o'brien/car.png"})
    uri = parsed(odd)["org/cinnamon/desktop/background"]["picture-uri"]
    assert uri == r"'file:///home/o\'brien/car.png'"
