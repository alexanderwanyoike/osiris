"""The Connectors page (#155): the person's MCP servers.

What a connector is, where it is kept and how its state is said are decided in
osiris/harness/connectors.py; this draws them and passes on what is changed.
"""
from collections.abc import Callable
from dataclasses import replace

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gtk  # noqa: E402

from osiris.harness.connectors import (  # noqa: E402
    Connector,
    State,
    connector_of,
    said_of,
)


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
        self._rows: dict[str, Adw.ActionRow] = {}
        self._list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")
        self.append(self._list)
        self.add = Gtk.Button(
            child=Adw.ButtonContent(icon_name="list-add-symbolic",
                                    label="Add a connector"),
            halign=Gtk.Align.START)
        self.add.add_css_class("flat")
        self.add.connect("clicked", lambda _b: self._open_form())
        self.append(self.add)
        self.append(self._form())
        self.reload()

    def _form(self) -> Gtk.Widget:
        self.name = Adw.EntryRow(title="Name")
        self.reach = Adw.EntryRow(title="Command, or a web address")
        fields = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        fields.add_css_class("boxed-list")
        fields.append(self.name)
        fields.append(self.reach)
        self.done = Gtk.Button(label="Save", halign=Gtk.Align.END)
        self.done.add_css_class("suggested-action")
        self.done.connect("clicked", lambda _b: self._finish())
        self.form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                            visible=False)
        self.form.add_css_class("harness-connector-form")
        self.problem = Gtk.Label(xalign=0, wrap=True, visible=False)
        self.problem.add_css_class("harness-problem")
        self.form.append(fields)
        self.form.append(self.problem)
        self.form.append(self.done)
        return self.form

    def _say(self, problem: str) -> None:
        self.problem.set_text(problem)
        self.problem.set_visible(bool(problem))

    def _open_form(self) -> None:
        self.name.set_text("")
        self.reach.set_text("")
        self.form.set_visible(True)
        self.add.set_visible(False)

    def _finish(self) -> None:
        connector = connector_of(self.name.get_text(), self.reach.get_text())
        if connector is None:
            self._say("Give it a name, and the command that starts it or the "
                      "web address it answers at.")
            return
        if not self._save(connector):
            self._say("Your opencode config has comments in it, so Osiris leaves "
                      "it for you to edit by hand.")
            return
        self._say("")
        self.form.set_visible(False)
        self.add.set_visible(True)
        self.reload()

    def reload(self) -> None:
        self._list.remove_all()
        self._said.clear()
        self._rows.clear()
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
        row.switch = Gtk.Switch(active=connector.on, valign=Gtk.Align.CENTER,
                                tooltip_text="Use this connector")
        row.switch.connect("notify::active", lambda switch, _p: self._switched(
            connector, switch.get_active()))
        row.add_suffix(row.switch)
        self._said[connector.name] = said
        self._rows[connector.name] = row
        return row

    def row(self, name: str) -> Adw.ActionRow:
        return self._rows[name]

    def _switched(self, connector: Connector, on: bool) -> None:
        if self._save(replace(connector, on=on)):
            self.reload()

    def _show_states(self, states: dict[str, State]) -> None:
        for connector in self._connectors:
            # Switched off here, it is off before the Engine has reloaded.
            state = (states.get(connector.name) if connector.on
                     else State("disabled"))
            words, tone = said_of(state)
            label = self._said[connector.name]
            label.set_text(words)
            label.set_css_classes(["harness-connector-state", f"harness-{tone}"])
