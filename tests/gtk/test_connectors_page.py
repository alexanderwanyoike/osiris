"""The Connectors page (#155): the person's MCP servers, each with what it runs
and whether it works, added, switched off and removed from here."""

from __future__ import annotations

from osiris.harness.connectors import Connector, State

from .conftest import now, texts

WIKI = Connector("wiki", url="https://mcp.example.com/mcp")
FILES = Connector("files", command=("npx", "files"), on=False)


class Store:
    """The person's config, as the page sees it."""

    def __init__(self, *saved: Connector, writable: bool = True) -> None:
        self.saved = {c.name: c for c in saved}
        self.writable = writable

    def read(self) -> list[Connector]:
        return sorted(self.saved.values(), key=lambda c: c.name)

    def save(self, connector: Connector) -> bool:
        if self.writable:
            self.saved[connector.name] = connector
        return self.writable

    def remove(self, name: str) -> bool:
        self.saved.pop(name, None)
        return True


def page(store: Store, states: dict[str, State] | None = None):
    from connectors_page import ConnectorsPage

    return ConnectorsPage(
        read=store.read,
        save=store.save,
        remove=store.remove,
        states=lambda: states or {},
        background=now,
    )


def test_each_connector_shows_what_it_runs_and_whether_it_works() -> None:
    shown = texts(
        page(
            Store(WIKI, FILES),
            {"wiki": State("failed", "connection refused"), "files": State("disabled")},
        )
    )
    assert "wiki" in shown and "https://mcp.example.com/mcp" in shown
    assert "files" in shown and "npx files" in shown
    assert "Failed: connection refused" in shown
    assert "Off" in shown


def test_a_connector_added_by_name_and_command_is_saved_and_listed() -> None:
    store = Store()
    shown = page(store)
    shown.add.emit("clicked")
    shown.name.set_text("files")
    shown.reach.set_text("npx -y files")
    shown.done.emit("clicked")
    assert store.saved == {"files": Connector("files", command=("npx", "-y", "files"))}
    assert "npx -y files" in texts(shown)
    assert not shown.form.get_visible()


def test_an_unfinished_form_says_what_is_missing_and_saves_nothing() -> None:
    store = Store()
    shown = page(store)
    shown.add.emit("clicked")
    shown.name.set_text("files")
    shown.done.emit("clicked")
    assert store.saved == {}
    assert shown.problem.get_visible()
    assert "command" in shown.problem.get_text()


def test_a_commented_config_is_left_and_the_page_says_so() -> None:
    store = Store(writable=False)
    shown = page(store)
    shown.add.emit("clicked")
    shown.name.set_text("files")
    shown.reach.set_text("npx files")
    shown.done.emit("clicked")
    assert shown.form.get_visible()
    assert "comments" in shown.problem.get_text()


def test_switching_a_connector_off_saves_it_off_and_says_so_at_once() -> None:
    store = Store(WIKI)
    shown = page(store, {"wiki": State("connected")})
    shown.row("wiki").switch.set_active(False)
    assert store.saved["wiki"] == Connector("wiki", url=WIKI.url, on=False)
    assert "Off" in texts(shown)


def test_a_removed_connector_leaves_the_list() -> None:
    store = Store(WIKI, FILES)
    shown = page(store)
    shown.row("wiki").trash.emit("clicked")
    assert list(store.saved) == ["files"]
    assert "https://mcp.example.com/mcp" not in texts(shown)


def test_a_chosen_connector_opens_in_the_form_and_saves_its_change() -> None:
    store = Store(WIKI)
    shown = page(store)
    shown.row("wiki").emit("activated")
    assert shown.form.get_visible()
    assert (shown.name.get_text(), shown.reach.get_text()) == ("wiki", WIKI.url)
    shown.reach.set_text("https://new.example.com/mcp")
    shown.done.emit("clicked")
    assert store.saved == {"wiki": Connector("wiki", url="https://new.example.com/mcp")}


def test_a_connector_renamed_in_the_form_is_kept_only_by_its_new_name() -> None:
    store = Store(WIKI)
    shown = page(store)
    shown.row("wiki").emit("activated")
    shown.name.set_text("docs")
    shown.done.emit("clicked")
    assert list(store.saved) == ["docs"]


def test_changing_a_connector_that_is_off_keeps_it_off() -> None:
    store = Store(FILES)
    shown = page(store)
    shown.row("files").emit("activated")
    shown.reach.set_text("npx -y files")
    shown.done.emit("clicked")
    assert store.saved["files"].on is False


def test_cancel_closes_the_form_and_saves_nothing() -> None:
    store = Store()
    shown = page(store)
    shown.add.emit("clicked")
    shown.name.set_text("files")
    shown.reach.set_text("npx files")
    shown.cancel.emit("clicked")
    assert store.saved == {}
    assert not shown.form.get_visible()


def test_a_server_still_starting_is_asked_about_again_until_it_settles() -> None:
    from connectors_page import ConnectorsPage

    answers = [{}, {"wiki": State("pending")}, {"wiki": State("connected")}]
    waits: list[object] = []
    shown = ConnectorsPage(
        read=Store(WIKI).read,
        save=lambda _c: True,
        remove=lambda _n: True,
        states=lambda: answers.pop(0),
        background=now,
        later=lambda _seconds, then: waits.append(then),
    )
    while waits:
        waits.pop(0)()
    assert "Connected" in texts(shown)
    assert answers == []


def test_a_server_that_never_starts_is_not_asked_about_for_ever() -> None:
    from connectors_page import ConnectorsPage

    asked: list[int] = []
    waits: list[object] = []
    ConnectorsPage(
        read=Store(WIKI).read,
        save=lambda _c: True,
        remove=lambda _n: True,
        states=lambda: asked.append(1) or {},
        background=now,
        later=lambda _seconds, then: waits.append(then),
    )
    while waits and len(asked) < 100:
        waits.pop(0)()
    assert len(asked) < 100


def test_with_no_connectors_the_page_says_what_one_is_and_draws_no_empty_list() -> None:
    shown = page(Store())
    assert any("MCP server" in text for text in texts(shown))
    assert not shown.connectors.get_visible()


def test_a_long_failure_is_cut_short_on_its_pill_and_whole_on_hover() -> None:
    from gi.repository import Gtk

    from .conftest import widgets

    reason = "connection refused by the server at mcp.example.com " * 4
    shown = page(Store(WIKI), {"wiki": State("failed", reason)})
    pill = next(
        w for w in widgets(shown) if "harness-connector-state" in w.get_css_classes()
    )
    _minimum, natural, _b, _c = pill.measure(Gtk.Orientation.HORIZONTAL, -1)
    assert natural < 260
    assert reason.strip() in pill.get_tooltip_text()


def test_a_short_state_is_shown_whole_however_narrow_the_drawer() -> None:
    import time

    from gi.repository import GLib, Gtk

    from .conftest import widgets

    long = Connector("everything", command=("npx", "-y", "@acme/server-everything"))
    shown = page(Store(long), {"everything": State("connected")})
    window = Gtk.Window(child=shown, default_width=300)
    window.present()
    context, deadline = GLib.MainContext.default(), time.monotonic() + 0.5
    while time.monotonic() < deadline:
        context.iteration(False)
    pill = next(
        w for w in widgets(shown) if "harness-connector-state" in w.get_css_classes()
    )
    ellipsized = pill.get_layout().is_ellipsized()
    window.destroy()
    assert not ellipsized


def test_a_server_needing_sign_in_signs_in_from_its_row_without_a_terminal() -> None:
    from connectors_page import ConnectorsPage

    from osiris.harness.accounts import SignIn, SignInState

    linear = Connector("linear", url="https://mcp.linear.app/mcp")
    started = SignIn("mcp_x", "att_1", "https://linear.app/oauth", "", False)
    progress = [SignInState("pending", ""), SignInState("complete", "")]
    answers = [
        {"linear": State("needs_auth", "login first", "mcp_x")},
        {"linear": State("connected")},
    ]
    opened: list[str] = []
    began: list[str] = []
    waits: list[object] = []
    shown = ConnectorsPage(
        read=Store(linear).read,
        save=lambda _c: True,
        remove=lambda _n: True,
        states=lambda: answers.pop(0),
        background=now,
        later=lambda _seconds, then: waits.append(then),
        sign_in=lambda integration: began.append(integration) or started,
        sign_in_state=lambda _s: progress.pop(0),
        open_page=opened.append,
    )
    shown.row("linear").sign_in.emit("clicked")
    while waits:
        waits.pop(0)()
    assert began == ["mcp_x"]
    assert opened == ["https://linear.app/oauth"]
    assert "Connected" in texts(shown)
