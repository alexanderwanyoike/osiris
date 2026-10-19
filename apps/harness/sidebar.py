"""The sidebar of Expanded: past Conversations grouped by Project
(docs/HARNESS-LAYOUT.md). Quiet on purpose: no counts or previews, only a
spinner while Osiris works and a dot for an answer not yet seen.

The grouping is decided in osiris/harness/history.py, where it is tested.
"""
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Pango  # noqa: E402

from osiris.harness.engine import Past  # noqa: E402
from osiris.harness.history import Project  # noqa: E402

#: How far a Conversation is set in under its Project.
INDENT = 26


class Sidebar(Gtk.Box):
    def __init__(self, *, on_open: Callable[[str], None], on_new: Callable[[], None],
                 on_new_in: Callable[[Path], None], on_archive: Callable[[str], None],
                 on_delete: Callable[[str, str], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("harness-sidebar")
        self._on_open = on_open
        self._on_new = on_new
        self._on_new_in = on_new_in
        self._on_archive = on_archive
        self._on_delete = on_delete
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.list.add_css_class("navigation-sidebar")
        self.list.connect("row-activated", self._activated)
        self.append(Gtk.ScrolledWindow(child=self.list, vexpand=True,
                                       hscrollbar_policy=Gtk.PolicyType.NEVER))
        self.show_history([], [], None, frozenset(), frozenset())

    def show_history(self, projects: list[Project], loose: list[Past],
                     current: str | None, running: frozenset[str],
                     unread: frozenset[str]) -> None:
        self.list.remove_all()
        self._row("New conversation", icon="list-add-symbolic", action="new")
        if projects:
            self._heading("Projects")
            for project in projects:
                row = self._row(project.name, icon="folder-symbolic", action=None)
                start = Gtk.Button(icon_name="list-add-symbolic",
                                   tooltip_text=f"New conversation in {project.name}")
                start.add_css_class("flat")
                start.connect("clicked", lambda _b, f=project.folder: self._on_new_in(f))
                row.get_child().append(start)
                for past in project.conversations:
                    self._conversation(past, current, running, unread,
                                       indent=INDENT)
        if loose:
            self._heading("Conversations")
            for past in loose:
                self._conversation(past, current, running, unread, indent=0)

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

    def _conversation(self, past: Past, current: str | None, running: frozenset[str],
                      unread: frozenset[str], *, indent: int) -> None:
        title = past.title or "Untitled"
        row = self._row(title, icon=None, action=past.session, indent=indent)
        if past.session in running:
            spinner = Adw.Spinner(tooltip_text="Osiris is working on this")
            spinner.add_css_class("harness-running")
            row.get_child().append(spinner)
        if past.session in unread:
            row.get_child().get_first_child().add_css_class("harness-unread")
            dot = Gtk.Box(valign=Gtk.Align.CENTER, tooltip_text="New answer")
            dot.add_css_class("harness-unread-dot")
            row.get_child().append(dot)
        actions = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for label, act in (("Archive", lambda: self._on_archive(past.session)),
                           ("Delete…", lambda: self._on_delete(past.session, title))):
            choice = Gtk.Button(label=label)
            choice.add_css_class("flat")
            choice.connect("clicked", lambda _b, act=act: act())
            actions.append(choice)
        more = Gtk.MenuButton(icon_name="view-more-symbolic", tooltip_text="More",
                              popover=Gtk.Popover(child=actions))
        more.add_css_class("flat")
        row.get_child().append(more)
        if past.session == current:
            self.list.select_row(row)

    def _activated(self, _list, row) -> None:
        if row.action == "new":
            self._on_new()
        elif row.action is not None:
            self._on_open(row.action)
