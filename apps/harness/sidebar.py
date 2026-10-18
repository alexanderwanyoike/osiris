"""The sidebar of Expanded: past Conversations grouped by Project
(docs/HARNESS-LAYOUT.md). Quiet on purpose: no counts, badges or previews.

The grouping is decided in osiris/harness/history.py, where it is tested.
"""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango  # noqa: E402

from osiris.harness.engine import Past  # noqa: E402
from osiris.harness.history import Project  # noqa: E402

#: How far a Conversation is set in under its Project.
INDENT = 26


class Sidebar(Gtk.Box):
    def __init__(self, *, on_open: Callable[[str], None], on_new: Callable[[], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("harness-sidebar")
        self._on_open = on_open
        self._on_new = on_new
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.list.add_css_class("navigation-sidebar")
        self.list.connect("row-activated", self._activated)
        self.append(Gtk.ScrolledWindow(child=self.list, vexpand=True,
                                       hscrollbar_policy=Gtk.PolicyType.NEVER))
        self.show_history([], [], None)

    def show_history(self, projects: list[Project], loose: list[Past],
                     current: str | None) -> None:
        self.list.remove_all()
        self._row("New conversation", icon="list-add-symbolic", action="new")
        if projects:
            self._heading("Projects")
            for project in projects:
                self._row(project.name, icon="folder-symbolic", action=None)
                for past in project.conversations:
                    self._conversation(past, current, indent=INDENT)
        if loose:
            self._heading("Conversations")
            for past in loose:
                self._conversation(past, current, indent=0)

    def _row(self, text: str, *, icon: str | None, action: str | None,
             indent: int = 0) -> Gtk.ListBoxRow:
        box = Gtk.Box(spacing=8, margin_start=indent)
        if icon:
            box.append(Gtk.Image(icon_name=icon))
        box.append(Gtk.Label(label=text, xalign=0, hexpand=True,
                             ellipsize=Pango.EllipsizeMode.END))
        row = Gtk.ListBoxRow(child=box, selectable=action not in (None, "new"),
                             activatable=action is not None)
        row.action = action
        self.list.append(row)
        return row

    def _heading(self, text: str) -> None:
        label = Gtk.Label(label=text, xalign=0)
        label.add_css_class("harness-meta")
        row = Gtk.ListBoxRow(child=label, selectable=False, activatable=False)
        row.action = None
        row.add_css_class("harness-sidebar-heading")
        self.list.append(row)

    def _conversation(self, past: Past, current: str | None, *, indent: int) -> None:
        row = self._row(past.title or "Untitled", icon=None, action=past.session,
                        indent=indent)
        if past.session == current:
            self.list.select_row(row)

    def _activated(self, _list, row) -> None:
        if row.action == "new":
            self._on_new()
        elif row.action is not None:
            self._on_open(row.action)
