"""The Allowed tab (#181): every rule saved by "Always allow here", with its
Project, each one taken back from here so the Engine asks about it again."""
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gtk  # noqa: E402

from osiris.harness.saved_rules import SavedRule  # noqa: E402


class AllowedTab(Gtk.Box):
    def __init__(self, read: Callable[[], list[SavedRule]],
                 remove: Callable[[SavedRule], None],
                 project_name: Callable[[Path], str], background):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add_css_class("harness-allowed")
        self._read, self._remove = read, remove
        self._project_name, self._background = project_name, background
        self._intro = Gtk.Label(xalign=0, wrap=True)
        self._intro.add_css_class("harness-meta")
        self.append(self._intro)
        self._list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")
        self.append(self._list)
        self.reload()

    def reload(self) -> None:
        self._background(self._read, self._show)

    def _show(self, rules: list[SavedRule]) -> None:
        self._list.remove_all()
        self._intro.set_text(
            "What you allowed with Always allow here, in each Project. Take one "
            "back and Osiris asks about it again." if rules else
            "Nothing allowed for good yet. Choosing Always allow here on a card "
            "saves a rule, and it shows here.")
        self._list.set_visible(bool(rules))
        for rule in rules:
            self._list.append(self._row(rule))

    def _row(self, rule: SavedRule) -> Gtk.Widget:
        what = f"{rule.action}: {rule.resource}"
        where = self._project_name(rule.project) if rule.project else "Every Project"
        row = Adw.ActionRow(title=what, subtitle=where, use_markup=False)
        trash = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER,
                           tooltip_text=f"Take back {what}")
        trash.add_css_class("flat")
        trash.connect("clicked", lambda _b: self._background(
            lambda: self._remove(rule), lambda _r: self.reload()))
        row.add_suffix(trash)
        return row
