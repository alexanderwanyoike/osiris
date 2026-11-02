"""The Harness's own look stays on top of the GTK 4 user sheet, which a Skin
fills with whole-window rules; below it, a Skin's solid window background
replaces the drawer's glass."""

from __future__ import annotations

from pathlib import Path

from gi.repository import Gtk
from look import Look

from osiris.apps.user_css import UserCss

from .conftest import widgets


def test_the_drawers_look_outranks_the_user_sheet(tmp_path: Path) -> None:
    """A Skin's sheet redefining libadwaita's window colour leaves the
    drawer in the Theme's."""
    sheet = tmp_path / "gtk.css"
    sheet.write_text(
        "@define-color window_bg_color #ff0000;"
        " label.look-probe { color: @window_bg_color; }"
    )
    UserCss(sheet)
    Look(tmp_path, lambda: None)
    probe = Gtk.Label(css_classes=["look-probe"])
    assert probe.get_color().to_string() != "rgb(255,0,0)"


def test_code_is_drawn_in_the_themes_terminal_font(tmp_path: Path) -> None:
    look = Look(tmp_path, lambda: None)
    loaded = look._provider.to_string()
    assert "calt" in loaded and "liga" in loaded


def test_the_look_keeps_the_theme_it_loaded(tmp_path: Path) -> None:
    """For what draws itself from the Theme, such as a terminal."""
    look = Look(tmp_path, lambda: None)
    assert "background" in look.theme["colors"]


def test_a_panels_tabs_are_slim_in_every_look(tmp_path: Path) -> None:
    """The person found 26px tabs too big; 20px is the most a tab stands."""
    import time

    from canvas import Canvas
    from gi.repository import GLib

    from osiris.programs.manifest import parse
    from osiris.programs.programs import Program

    from .conftest import widgets

    manifest = parse(
        '{"name": "timer", "label": "Timer", "description": "x",'
        ' "run": ["python3", "main.py"]}'
    )
    for look in ("studio", "bubbles", "transcript"):
        (tmp_path / ".config/osiris/harness").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".config/osiris/harness/skin").write_text(look)
        Look(tmp_path, lambda: None)
        canvas = Canvas(read=lambda _p: "print(1)\n", open_in_code=lambda _f, _p: None)
        canvas.show([(Program(manifest, tmp_path, "a", None), [Path("main.py")])])
        window = Gtk.Window(child=canvas, default_width=1200, default_height=700)
        window.present()
        context = GLib.MainContext.default()
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            context.iteration(False)
        tab = next(
            w for w in widgets(canvas) if "harness-group-tab" in w.get_css_classes()
        )
        height = tab.get_height()
        window.destroy()
        assert 0 < height <= 20, (look, height)


def test_the_pickers_chosen_entry_keeps_its_name_in_the_text_colour_in_every_look(
    tmp_path: Path,
) -> None:
    """The chosen row is marked by a soft fill, as the person's reference
    shows, not by recolouring its name."""
    from composer_picker import Picker
    from gi.repository import Gdk

    from osiris.harness.picker import Entry

    readme = Entry("file", "/home/tester/Code/timer/README.md", "README.md", "")
    for skin in ("studio", "bubbles", "transcript"):
        (tmp_path / ".config/osiris/harness").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".config/osiris/harness/skin").write_text(skin)
        look = Look(tmp_path, lambda: None)
        entry = Gtk.TextView()
        window = Gtk.Window(child=entry)
        window.present()
        picker = Picker(entry, lambda _sign: [readme])
        entry.get_buffer().set_text("@")
        row = picker.list.get_selected_row()
        label = next(
            w for w in widgets(row) if "harness-picker-label" in w.get_css_classes()
        )
        text = Gdk.RGBA()
        text.parse(look.theme["colors"]["foreground"])
        window.destroy()
        assert label.get_color().equal(text), skin


def test_a_working_connector_says_so_in_the_themes_success_colour_in_every_look(
    tmp_path: Path,
) -> None:
    from connectors_page import ConnectorsPage
    from gi.repository import Gdk

    from osiris.harness.connectors import Connector, State

    from .conftest import now

    wiki = Connector("wiki", url="https://w.example/mcp")
    for skin in ("studio", "bubbles", "transcript"):
        (tmp_path / ".config/osiris/harness").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".config/osiris/harness/skin").write_text(skin)
        look = Look(tmp_path, lambda: None)
        page = ConnectorsPage(
            read=lambda: [wiki],
            save=lambda _c: True,
            remove=lambda _n: True,
            states=lambda: {"wiki": State("connected")},
            background=now,
        )
        window = Gtk.Window(child=page)
        window.present()
        said = next(
            w for w in widgets(page) if "harness-connector-state" in w.get_css_classes()
        )
        success = Gdk.RGBA()
        success.parse(look.theme["colors"]["success"])
        window.destroy()
        assert said.get_color().equal(success), skin


def test_a_question_waiting_on_the_person_ticks_in_the_themes_warning_in_every_look(
    tmp_path: Path,
) -> None:
    from gi.repository import Gdk
    from rail import Rail

    from osiris.harness.rail import Tick

    for skin in ("studio", "bubbles", "transcript"):
        (tmp_path / ".config/osiris/harness").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".config/osiris/harness/skin").write_text(skin)
        look = Look(tmp_path, lambda: None)
        shown = Rail(on_jump=lambda _i: None)
        shown.show_ticks([Tick(0.5, True, "waiting", "list /etc")])
        window = Gtk.Window(child=shown)
        window.present()
        line = next(
            w for w in widgets(shown) if "harness-rail-line" in w.get_css_classes()
        )
        warning = Gdk.RGBA()
        warning.parse(look.theme["colors"]["warning"])
        window.destroy()
        assert line.get_color().equal(warning), skin


def test_a_question_that_changed_something_ticks_in_the_themes_accent(
    tmp_path: Path,
) -> None:
    """Tints follow the Theme's own accent rather than a fixed green."""
    from gi.repository import Gdk
    from rail import Rail

    from osiris.harness.rail import Tick

    for skin in ("studio", "bubbles", "transcript"):
        (tmp_path / ".config/osiris/harness").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".config/osiris/harness/skin").write_text(skin)
        look = Look(tmp_path, lambda: None)
        shown = Rail(on_jump=lambda _i: None)
        shown.show_ticks([Tick(0.5, True, "changed", "make it calm", current=True)])
        window = Gtk.Window(child=shown)
        window.present()
        line = next(
            w for w in widgets(shown) if "harness-rail-line" in w.get_css_classes()
        )
        accent = Gdk.RGBA()
        accent.parse(look.theme["colors"]["accent"])
        window.destroy()
        assert line.get_color().equal(accent), skin


def test_no_look_flashes_a_glow_at_the_end_of_a_scroll(tmp_path: Path) -> None:
    """The person found the glow at the top and bottom of a scroll annoying."""
    import re

    for look in ("studio", "bubbles", "transcript"):
        (tmp_path / ".config/osiris/harness").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".config/osiris/harness/skin").write_text(look)
        loaded = Look(tmp_path, lambda: None)._provider.to_string()
        rules = re.findall(r"([^{}]*overshoot[^{}]*)\{([^}]*)\}", loaded)
        assert rules, look
        assert all("background-image: none" in body for _, body in rules), look
