"""The / and @ picker on the message box (#153), driven as the person types."""

from __future__ import annotations

from gi.repository import Gtk

from osiris.harness.picker import Entry

README = Entry("file", "/home/tester/Code/timer/README.md", "README.md", "")
CLOCK = Entry("file", "/home/tester/Code/timer/clock.py", "clock.py", "")
REVIEW = Entry("skill", "review", "review", "Review the changes")


def typed(text: str):
    from composer_picker import Picker

    entry = Gtk.TextView()
    window = Gtk.Window(child=entry)
    window.present()
    offers = {"@": [README, CLOCK], "/": [REVIEW]}
    picker = Picker(entry, lambda sign: offers[sign])
    entry.get_buffer().set_text(text)
    return picker


def shown(picker) -> list[str]:
    rows = []
    while (row := picker.list.get_row_at_index(len(rows))) is not None:
        rows.append(row.entry.label)
    return rows


def test_a_sign_at_the_start_of_a_word_opens_the_picker_filtered() -> None:
    picker = typed("fix @RE")
    assert picker.popover.get_visible()
    assert shown(picker) == ["README.md"]


def press(picker, key: int) -> bool:
    from gi.repository import Gdk

    return picker.key(None, key, 0, Gdk.ModifierType(0))


def text(picker) -> str:
    buffer = picker.popover.get_parent().get_buffer()
    return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)


def test_the_arrow_keys_move_and_tab_puts_the_chosen_entry_in_the_message() -> None:
    from gi.repository import Gdk

    picker = typed("fix @")
    assert press(picker, Gdk.KEY_Down)
    assert press(picker, Gdk.KEY_Tab)
    assert text(picker) == "fix @clock.py "
    assert not picker.popover.get_visible()


def test_escape_closes_the_picker_and_leaves_what_was_typed() -> None:
    from gi.repository import Gdk

    picker = typed("fix @RE")
    assert press(picker, Gdk.KEY_Escape)
    assert not picker.popover.get_visible()
    assert text(picker) == "fix @RE"


def test_a_completed_entry_is_sent_as_a_reference_where_it_stands() -> None:
    from gi.repository import Gdk

    from osiris.harness.picker import Reference

    picker = typed("fix @")
    press(picker, Gdk.KEY_Tab)
    assert picker.references(text(picker)) == (Reference(README, 4, 14),)


def test_a_completed_entry_shows_as_a_token_and_what_follows_does_not() -> None:
    from gi.repository import Gdk

    picker = typed("fix @")
    press(picker, Gdk.KEY_Tab)
    buffer = picker.popover.get_parent().get_buffer()
    buffer.insert(buffer.get_end_iter(), "please")
    marked = [buffer.get_iter_at_offset(at).has_tag(picker.token) for at in range(23)]
    assert marked == [False] * 4 + [True] * 10 + [False] * 9


def test_a_completed_entry_is_a_token_the_moment_it_is_put_in() -> None:
    from gi.repository import Gdk

    picker = typed("fix @")
    press(picker, Gdk.KEY_Tab)
    buffer = picker.popover.get_parent().get_buffer()
    assert buffer.get_iter_at_offset(4).has_tag(picker.token)


def test_tokens_take_the_colours_they_are_given() -> None:
    picker = typed("")
    picker.restyle(("#7c8aeb", "#2e3048"))
    assert picker.token.props.foreground_rgba.to_string() == "rgb(124,138,235)"
    assert picker.token.props.background_rgba.to_string() == "rgb(46,48,72)"


def test_clicking_an_entry_puts_it_in_the_message() -> None:
    picker = typed("fix @")
    picker.list.emit("row-activated", picker.list.get_row_at_index(1))
    assert text(picker) == "fix @clock.py "


def test_after_a_click_typing_carries_on_in_the_message() -> None:
    picker = typed("fix @")
    entry = picker.popover.get_parent()
    row = picker.list.get_row_at_index(0)
    row.grab_focus()
    picker.list.emit("row-activated", row)
    assert entry.get_root().get_focus() is entry


def test_a_long_description_does_not_widen_the_picker() -> None:
    from composer_picker import Picker

    entry = Gtk.TextView()
    window = Gtk.Window(child=entry)
    window.present()
    wordy = Entry("skill", "opencode", "opencode", "Use this skill for anything. " * 20)
    picker = Picker(entry, lambda _sign: [wordy])
    entry.get_buffer().set_text("/")
    _minimum, natural, _b, _c = picker.list.measure(Gtk.Orientation.HORIZONTAL, -1)
    assert natural <= 480


def settle() -> None:
    import time

    from gi.repository import GLib

    context, deadline = GLib.MainContext.default(), time.monotonic() + 0.5
    while time.monotonic() < deadline:
        context.iteration(False)


def docked(text: str, offered: list[Entry]):
    """A picker over a message box 600 wide, as the drawer lays it out."""
    from composer_picker import Picker

    entry = Gtk.TextView(hexpand=True)
    composer = Gtk.Box(width_request=600)
    composer.append(entry)
    window = Gtk.Window(child=composer)
    window.present()
    settle()
    picker = Picker(entry, lambda _sign: offered, anchor=composer)
    entry.get_buffer().set_text(text)
    settle()
    return picker, composer


def test_the_picker_is_a_card_as_wide_as_the_message_box_it_sits_over() -> None:
    picker, composer = docked("@", [README, CLOCK])
    card = picker.popover.get_child()
    minimum, _natural, _b, _c = card.measure(Gtk.Orientation.HORIZONTAL, -1)
    assert picker.popover.get_parent() is composer
    assert minimum == composer.get_width() == 600


def test_each_entry_shows_an_icon_for_its_kind() -> None:
    from composer_picker import ICONS

    from .conftest import widgets

    picker, _ = docked("/", [README, REVIEW])
    icons = [
        next(w.get_icon_name() for w in widgets(row) if isinstance(w, Gtk.Image))
        for row in (picker.list.get_row_at_index(0), picker.list.get_row_at_index(1))
    ]
    assert icons == [ICONS["file"], ICONS["skill"]]
    assert ICONS["file"] != ICONS["skill"]


def test_a_long_list_is_all_there_and_scrolls_rather_than_grows() -> None:
    many = [Entry("file", f"/p/f{n}.py", f"f{n}.py", "") for n in range(40)]
    picker, _ = docked("@", many)
    _minimum, natural, _b, _c = picker.popover.get_child().measure(
        Gtk.Orientation.VERTICAL, -1
    )
    assert len(shown(picker)) == 40
    assert natural <= 320
