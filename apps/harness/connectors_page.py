"""The Connectors page (#155): the person's MCP servers.

What a connector is, where it is kept and how its state is said are decided in
osiris/harness/connectors.py; this draws them and passes on what is changed.
"""
from collections.abc import Callable

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gtk  # noqa: E402

from osiris.harness.connectors import Connector, State, said_of  # noqa: E402


class ConnectorsPage(Gtk.Box):
    def __init__(self, read: Callable[[], list[Connector]],
                 save: Callable[[Connector], bool], remove: Callable[[str], bool],
                 states: Callable[[], dict[str, State]], background):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add_css_class("harness-connectors")
        self._read, self._save, self._remove = read, save, remove
        self._states, self._background = states, background
        self._connectors: list[Connector] = []
        self._said: dict[str, Gtk.Label] = {}
        self._list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")
        self.append(self._list)
        self.reload()

    def reload(self) -> None:
        self._list.remove_all()
        self._said.clear()
        self._connectors = self._read()
        for connector in self._connectors:
            self._list.append(self._row(connector))
        self._background(self._states, self._show_states)

    def _row(self, connector: Connector) -> Gtk.Widget:
        row = Adw.ActionRow(title=connector.name, use_markup=False,
                            subtitle=" ".join(connector.command) or connector.url)
        said = Gtk.Label(valign=Gtk.Align.CENTER)
        said.add_css_class("harness-connector-state")
        row.add_suffix(said)
        self._said[connector.name] = said
        return row

    def _show_states(self, states: dict[str, State]) -> None:
        for connector in self._connectors:
            # Switched off here, it is off before the Engine has reloaded.
            state = states.get(connector.name) or (
                None if connector.on else State("disabled"))
            words, tone = said_of(state)
            label = self._said[connector.name]
            label.set_text(words)
            label.set_css_classes(["harness-connector-state", f"harness-{tone}"])
