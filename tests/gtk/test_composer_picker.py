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
