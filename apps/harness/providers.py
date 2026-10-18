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
        self._list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.append(self._list)
        background(accounts.providers, self._show)

    def _show(self, providers) -> None:
        for provider in providers:
            row = Gtk.Box(spacing=8)
            row.add_css_class("harness-provider")
            row.append(Gtk.Label(label=provider.name, xalign=0, hexpand=True))
            if provider.connected:
                status = Gtk.Label(label="Connected")
                status.add_css_class("harness-meta")
                row.append(status)
            self._list.append(row)
