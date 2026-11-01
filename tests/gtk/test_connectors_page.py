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
