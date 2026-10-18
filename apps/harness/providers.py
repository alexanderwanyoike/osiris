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


#: Offered first: the accounts Osiris is built around (ADR 0015). Every other
#: Provider the Engine reaches is still listed after them.
FEATURED = ("openai", "opencode-go")


#: Logos Osiris ships (apps/harness/logos), as icon names.
LOGOS = {
    "openai": "osiris-provider-openai-symbolic",
    "opencode": "osiris-provider-opencode-symbolic",
    "opencode-go": "osiris-provider-opencode-symbolic",
}


def _badge(provider) -> Gtk.Widget:
    if provider.id in LOGOS:
        logo = Gtk.Image(icon_name=LOGOS[provider.id], pixel_size=20)
        logo.add_css_class("harness-logo")
        return logo
    monogram = Gtk.Label(label=provider.name[:1].upper())
    monogram.add_css_class("harness-monogram")
    return monogram


def _featured_first(providers):
    rank = {name: index for index, name in enumerate(FEATURED)}
    return sorted(providers, key=lambda p: rank.get(p.id, len(FEATURED)))


class ProvidersPage(Gtk.Box):
    #: Seconds between checks on a sign-in in progress.
    POLL_SECONDS = 2

    def __init__(self, accounts, background, open_page=None, later=None,
                 default=None, on_model_chosen=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("harness-providers")
        self._accounts = accounts
        self._background = background
        self._open_page = open_page
        self._later = later
        self._list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._problem = Gtk.Label(xalign=0, wrap=True, visible=False)
        self._problem.add_css_class("harness-error")
        self._default = default
        self._on_model_chosen = on_model_chosen
        self._models = []
        self._picker_handler = 0
        self._picker = Gtk.DropDown()
        self._picker.add_css_class("harness-model-picker")
        model_line = Gtk.Box(spacing=8)
        model_line.append(Gtk.Label(label="Default model", xalign=0, hexpand=True))
        model_line.append(self._picker)
        self._search = Gtk.SearchEntry(placeholder_text="Search other providers")
        self._search.connect("changed", self._filter)
        self.append(model_line)
        self.append(self._list)
        self.append(self._search)
        self.append(self._problem)
        self._others = []
        self.reload()

    def reload(self) -> None:
        self._background(self._accounts.providers, self._show)
        self._background(self._accounts.models, self._show_models)

    def _show_models(self, models) -> None:
        self._models = models
        if self._picker_handler:
            self._picker.disconnect(self._picker_handler)
        self._picker.set_model(Gtk.StringList.new([m.name for m in models]))
        refs = [m.ref for m in models]
        if self._default in refs:
            self._picker.set_selected(refs.index(self._default))
        self._picker_handler = self._picker.connect("notify::selected", self._picked)

    def _picked(self, picker, _spec) -> None:
        index = picker.get_selected()
        if 0 <= index < len(self._models) and self._on_model_chosen:
            self._default = self._models[index].ref
            self._on_model_chosen(self._default)

    def _show(self, providers) -> None:
        child = self._list.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            self._list.remove(child)
            child = following
        self._others = []
        for provider in _featured_first(providers):
            section = self._section(provider)
            self._list.append(section)
            if provider.id not in FEATURED:
                self._others.append((provider.name.lower(), section))
        self._filter()

    def _section(self, provider) -> Gtk.Widget:
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        row = Gtk.Box(spacing=10)
        row.add_css_class("harness-provider")
        row.append(_badge(provider))
        row.append(Gtk.Label(label=provider.name, xalign=0, hexpand=True))
        section.append(row)
        if provider.connected:
            status = Gtk.Label(label="Connected")
            status.add_css_class("harness-meta")
            row.append(status)
            return section
        for method in provider.methods:
            if method.kind == "oauth":
                section.append(self._sign_in_button(provider.id, method))
        if any(m.kind == "key" for m in provider.methods):
            form = self._key_form(provider.id)
            form.set_visible(False)
            add = Gtk.Button(label="Add key", halign=Gtk.Align.START)
            add.add_css_class("flat")
            add.connect("clicked", lambda _b: (form.set_visible(True), add.set_visible(False)))
            section.append(add)
            section.append(form)
        return section

    def _filter(self, *_args) -> None:
        """Other Providers stay out of the way until a search names them."""
        query = self._search.get_text().strip().lower()
        for name, section in self._others:
            section.set_visible(bool(query) and query in name)

    def _sign_in_button(self, provider: str, method) -> Gtk.Widget:
        button = Gtk.Button(label=method.label, halign=Gtk.Align.START)
        button.add_css_class("harness-sign-in")
        button.connect("clicked", lambda _b: self._background(
            lambda: self._accounts.start_sign_in(provider, method.id),
            self._signing_in))
        return button

    def _signing_in(self, sign_in) -> None:
        self._open_page(sign_in.url)
        if sign_in.needs_code:
            self._list.append(self._code_form(sign_in))
        else:
            self._later(self.POLL_SECONDS, lambda: self._check(sign_in))

    def _code_form(self, sign_in) -> Gtk.Widget:
        instructions = Gtk.Label(label=sign_in.instructions, xalign=0, wrap=True)
        entry = Gtk.Entry(placeholder_text="Code", hexpand=True)
        finish = Gtk.Button(label="Finish")
        finish.connect("clicked", lambda _b: self._background(
            lambda: self._accounts.finish_sign_in(
                sign_in.provider, sign_in.attempt, entry.get_text().strip()),
            lambda _result: self._check(sign_in)))
        line = Gtk.Box(spacing=6)
        line.append(entry)
        line.append(finish)
        form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        form.add_css_class("harness-code-form")
        form.append(instructions)
        form.append(line)
        return form

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
