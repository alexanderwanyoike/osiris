"""The admin password card: sudo, run by Osiris in this Conversation, asks for
the administrator password (ADR 0018).

What the command is and how it is labelled is decided in osiris/harness/admin.py,
where it is tested. The password goes from the entry to on_allow and nowhere
else; the entry is emptied as it goes.
"""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango  # noqa: E402

from osiris.harness.admin import Request  # noqa: E402


class AdminCard(Gtk.Box):
    def __init__(self, request: Request, *, on_allow: Callable[[str], None],
                 on_deny: Callable[[], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("harness-admin")
        self._on_allow = on_allow
        self._on_deny = on_deny
        whom = "" if request.user == "root" else f" as {request.user}"
        heading = Gtk.Label(label=f"Osiris needs your password to run{whom}:",
                            xalign=0, wrap=True)
        heading.add_css_class("heading")
        self.append(heading)
        command = Gtk.Label(label=request.shown, xalign=0, wrap=True, selectable=True,
                            wrap_mode=Pango.WrapMode.WORD_CHAR)
        command.add_css_class("monospace")
        command.add_css_class("harness-admin-command")
        self.append(command)
        if request.note is not None:
            note = Gtk.Label(label=request.note, xalign=0, wrap=True)
            note.add_css_class("harness-meta")
            self.append(note)

        self.entry = Gtk.PasswordEntry(placeholder_text="Password", hexpand=True)
        self.entry.connect("activate", lambda _e: self._allow())
        deny = Gtk.Button(label="Deny")
        deny.connect("clicked", lambda _b: self._deny())
        allow = Gtk.Button(label="Allow")
        allow.add_css_class("suggested-action")
        allow.connect("clicked", lambda _b: self._allow())
        actions = Gtk.Box(spacing=6)
        actions.append(self.entry)
        actions.append(deny)
        actions.append(allow)
        self.append(actions)

    def _allow(self) -> None:
        password = self.entry.get_text()
        if not password:
            return
        self.entry.set_text("")
        self._on_allow(password)

    def _deny(self) -> None:
        self.entry.set_text("")
        self._on_deny()
