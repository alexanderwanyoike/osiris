"""The Providers page: the person's accounts, and the Default model.

Which Providers exist and how to sign in to each comes from the Engine, behind
the Accounts port (osiris/harness/accounts.py); this page only draws them.
Calls to the Engine run through `background`, so the page never blocks the
main loop and tests can run it synchronously.
"""
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402


class ProvidersPage(Gtk.Box):
    def __init__(self, accounts, background):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("harness-providers")
        self._accounts = accounts
        self._background = background
        self._list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.append(self._list)
        self.reload()

    def reload(self) -> None:
        self._background(self._accounts.providers, self._show)

    def _show(self, providers) -> None:
        child = self._list.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            self._list.remove(child)
            child = following
        for provider in providers:
            row = Gtk.Box(spacing=8)
            row.add_css_class("harness-provider")
            row.append(Gtk.Label(label=provider.name, xalign=0, hexpand=True))
            if provider.connected:
                status = Gtk.Label(label="Connected")
                status.add_css_class("harness-meta")
                row.append(status)
            self._list.append(row)
            if not provider.connected and any(m.kind == "key" for m in provider.methods):
                self._list.append(self._key_form(provider.id))

    def _key_form(self, provider: str) -> Gtk.Widget:
        entry = Gtk.PasswordEntry(placeholder_text="API key", hexpand=True,
                                  show_peek_icon=True)
        save = Gtk.Button(label="Save")
        save.connect("clicked", lambda _b: self._background(
            lambda: self._accounts.connect_key(provider, entry.get_text().strip()),
            lambda _result: self.reload()))
        form = Gtk.Box(spacing=6)
        form.add_css_class("harness-key-form")
        form.append(entry)
        form.append(save)
        return form
