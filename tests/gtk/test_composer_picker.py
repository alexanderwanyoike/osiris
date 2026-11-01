"""The / and @ picker on the message box (#153), driven as the person types."""

from __future__ import annotations

from gi.repository import Graphene, Gtk

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


def test_moving_past_the_bottom_scrolls_the_chosen_entry_into_view() -> None:
    from gi.repository import Gdk

    many = [Entry("file", f"/p/f{n}.py", f"f{n}.py", "") for n in range(40)]
    picker, _ = docked("@", many)
    for _ in range(25):
        press(picker, Gdk.KEY_Down)
    settle()
    row = picker.list.get_selected_row()
    _ok, at = row.compute_point(picker.list, Graphene.Point())
    top = at.y
    shown_from = picker.card.get_vadjustment().get_value()
    assert shown_from <= top
    assert top + row.get_height() <= shown_from + picker.card.get_height()


def test_the_card_stands_clear_of_the_message_box() -> None:
    from composer_picker import GAP

    picker, _ = docked("@", [README])
    assert picker.popover.get_offset() == (0, -GAP)
    assert GAP >= 6


def test_the_card_lines_up_with_the_message_boxs_edges_padding_and_all() -> None:
    from composer_picker import Picker
    from gi.repository import Gdk

    padded = Gtk.CssProvider()
    padded.load_from_string(".padded-composer { padding: 10px 8px 8px 14px; }")
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), padded, 900)
    entry = Gtk.TextView(hexpand=True)
    composer = Gtk.Box(width_request=600, css_classes=["padded-composer"])
    composer.append(entry)
    window = Gtk.Window(child=composer)
    window.present()
    settle()
    picker = Picker(entry, lambda _sign: [README], anchor=composer)
    entry.get_buffer().set_text("@")
    settle()
    _found, edges = composer.compute_bounds(composer)
    minimum, _natural, _b, _c = picker.card.measure(Gtk.Orientation.HORIZONTAL, -1)
    Gtk.StyleContext.remove_provider_for_display(Gdk.Display.get_default(), padded)
    assert minimum == edges.get_width()


def test_opening_the_picker_says_so_once_not_at_every_key() -> None:
    from composer_picker import Picker

    entry = Gtk.TextView()
    window = Gtk.Window(child=entry)
    window.present()
    opened: list[str] = []
    picker = Picker(entry, lambda _sign: [README, CLOCK], on_open=opened.append)
    buffer = entry.get_buffer()
    for key in "@RE":
        buffer.insert_at_cursor(key)
    buffer.set_text("fix")
    buffer.insert_at_cursor(" /")
    assert opened == ["@", "/"]
    assert picker.popover.get_visible()


def test_an_open_picker_lists_afresh_when_told_its_offers_changed() -> None:
    from composer_picker import Picker

    entry = Gtk.TextView()
    window = Gtk.Window(child=entry)
    window.present()
    offers = [README]
    picker = Picker(entry, lambda _sign: offers)
    entry.get_buffer().insert_at_cursor("@")
    offers = [README, CLOCK]
    picker.refresh()
    assert shown(picker) == ["README.md", "clock.py"]


def test_the_pointer_chooses_the_entry_it_rests_on() -> None:
    picker, _ = docked("@", [README, CLOCK])
    second = picker.list.get_row_at_index(1)
    _ok, at = second.compute_point(picker.list, Graphene.Point())
    picker.pointed(None, 10, at.y + second.get_height() / 2)
    assert picker.list.get_selected_row() is second


def test_one_match_makes_a_card_no_taller_than_its_list() -> None:
    picker, _ = docked("@RE", [README, CLOCK])
    _minimum, card, _b, _c = picker.card.measure(Gtk.Orientation.VERTICAL, -1)
    _minimum, rows, _b, _c = picker.list.measure(Gtk.Orientation.VERTICAL, -1)
    assert len(shown(picker)) == 1
    assert card == rows
