"""The Providers page: the person's accounts, and the Default model.

Which Providers exist and how to sign in to each comes from the Engine, behind
the Accounts port (osiris/harness/accounts.py); this page only draws them.
Calls to the Engine run through `background`, so the page never blocks the
main loop; `open_page` opens a sign-in page in the browser and `later` waits
before checking on a sign-in again. All three are passed in, so tests run the
page synchronously.
"""
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402


class ProvidersPage(Gtk.Box):
    #: Seconds between checks on a sign-in in progress.
    POLL_SECONDS = 2

    def __init__(self, accounts, background, open_page=None, later=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("harness-providers")
        self._accounts = accounts
        self._background = background
        self._open_page = open_page
        self._later = later
        self._list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._problem = Gtk.Label(xalign=0, wrap=True, visible=False)
        self._problem.add_css_class("harness-error")
        self.append(self._list)
        self.append(self._problem)
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
            if provider.connected:
                continue
            for method in provider.methods:
                if method.kind == "oauth":
                    self._list.append(self._sign_in_button(provider.id, method))
            if any(m.kind == "key" for m in provider.methods):
                self._list.append(self._key_form(provider.id))

    def _sign_in_button(self, provider: str, method) -> Gtk.Widget:
        button = Gtk.Button(label=method.label, halign=Gtk.Align.START)
        button.add_css_class("harness-sign-in")
        button.connect("clicked", lambda _b: self._background(
            lambda: self._accounts.start_sign_in(provider, method.id),
            self._signing_in))
        return button

    def _signing_in(self, sign_in) -> None:
        self._open_page(sign_in.url)
        self._later(self.POLL_SECONDS, lambda: self._check(sign_in))

    def _check(self, sign_in) -> None:
        self._background(
            lambda: self._accounts.sign_in_state(sign_in.provider, sign_in.attempt),
            lambda state: self._checked(sign_in, state))

    def _checked(self, sign_in, state) -> None:
        if state.status == "pending":
            self._later(self.POLL_SECONDS, lambda: self._check(sign_in))
            return
        problems = {"failed": state.message or "Signing in failed.",
                    "expired": "The sign-in page expired. Try again."}
        self._problem.set_text(problems.get(state.status, ""))
        self._problem.set_visible(state.status in problems)
        self.reload()

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
