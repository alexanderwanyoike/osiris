"""Moving the lit row of a list with the arrows while the keyboard stays in a
field above it: the composer picker's and the model menu's."""
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Graphene, Gtk  # noqa: E402


def move(rows: Gtk.ListBox, card: Gtk.ScrolledWindow, step: int) -> None:
    """Light the row ``step`` away from the lit one, kept in view."""
    row = rows.get_selected_row()
    if row is None:
        return
    last = len(list(rows)) - 1
    chosen = rows.get_row_at_index(min(max(row.get_index() + step, 0), last))
    rows.select_row(chosen)
    _found, at = chosen.compute_point(rows, Graphene.Point())
    shown = card.get_vadjustment()
    top, page = shown.get_value(), shown.get_page_size()
    if at.y < top:
        shown.set_value(at.y)
    elif at.y + chosen.get_height() > top + page:
        shown.set_value(at.y + chosen.get_height() - page)
