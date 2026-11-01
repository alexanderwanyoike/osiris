"""The Connectors page (#155): the person's MCP servers.

What a connector is, where it is kept and how its state is said are decided in
osiris/harness/connectors.py; this draws them and passes on what is changed.
"""
import shlex
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
    #: Seconds between asking again about a server still starting.
    POLL_SECONDS = 2
    #: How often to ask before leaving a server to say it has not started.
    POLLS = 15

    def __init__(self, read: Callable[[], list[Connector]],
                 save: Callable[[Connector], bool], remove: Callable[[str], bool],
                 states: Callable[[], dict[str, State]], background,
                 later: Callable[[int, Callable[[], None]], None] = lambda _s, _t: None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add_css_class("harness-connectors")
        self._read, self._save, self._remove = read, save, remove
        self._states, self._background, self._later = states, background, later
        self._connectors: list[Connector] = []
        #: The connector the form is changing, if it is not adding one.
        self._editing: Connector | None = None
        self._said: dict[str, Gtk.Label] = {}
        self._rows: dict[str, Adw.ActionRow] = {}
        intro = Gtk.Label(
            label="Connectors give Osiris other tools and data: an MCP server it "
                  "starts with a command, or one it reaches at a web address. "
                  "They are kept in your opencode config.",
            xalign=0, wrap=True)
        intro.add_css_class("harness-meta")
        self.append(intro)
        self.connectors = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.connectors.add_css_class("boxed-list")
        self.append(self.connectors)
        face = Gtk.Box(spacing=8)
        face.append(Gtk.Image(icon_name="list-add-symbolic"))
        face.append(Gtk.Label(label="Add a connector"))
        self.add = Gtk.Button(child=face, halign=Gtk.Align.START)
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
        self.done = Gtk.Button(label="Save")
        self.done.add_css_class("suggested-action")
        self.done.connect("clicked", lambda _b: self._finish())
        self.form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                            visible=False)
        self.form.add_css_class("harness-connector-form")
        self.problem = Gtk.Label(xalign=0, wrap=True, visible=False)
        self.problem.add_css_class("harness-problem")
        self.cancel = Gtk.Button(label="Cancel")
        self.cancel.add_css_class("flat")
        self.cancel.connect("clicked", lambda _b: self._close_form())
        buttons = Gtk.Box(spacing=6, halign=Gtk.Align.END)
        buttons.append(self.cancel)
        buttons.append(self.done)
        self.form.append(fields)
        self.form.append(self.problem)
        self.form.append(buttons)
        return self.form

    def _say(self, problem: str) -> None:
        self.problem.set_text(problem)
        self.problem.set_visible(bool(problem))

    def _open_form(self, connector: Connector | None = None) -> None:
        self._editing = connector
        self.name.set_text(connector.name if connector else "")
        self.reach.set_text(_reach(connector) if connector else "")
        self.form.set_visible(True)
        self.add.set_visible(False)

    def _finish(self) -> None:
        connector = connector_of(self.name.get_text(), self.reach.get_text())
        if connector is None:
            self._say("Give it a name, and the command that starts it or the "
                      "web address it answers at.")
            return
        if self._editing is not None:
            connector = replace(connector, on=self._editing.on)
        if not self._save(connector):
            self._say("Your opencode config has comments in it, so Osiris leaves "
                      "it for you to edit by hand.")
            return
        if self._editing is not None and self._editing.name != connector.name:
            self._remove(self._editing.name)
        self._close_form()
        self.reload()

    def _close_form(self) -> None:
        self._say("")
        self.form.set_visible(False)
        self.add.set_visible(True)

    def reload(self) -> None:
        self.connectors.remove_all()
        self._said.clear()
        self._rows.clear()
        self._connectors = self._read()
        self._polls = 0
        for connector in self._connectors:
            self.connectors.append(self._row(connector))
        self.connectors.set_visible(bool(self._connectors))
        self._ask_states()

    def _row(self, connector: Connector) -> Gtk.Widget:
        row = Adw.ActionRow(title=connector.name, use_markup=False,
                            subtitle=_reach(connector), activatable=True)
        row.connect("activated", lambda _r: self._open_form(connector))
        said = Gtk.Label(valign=Gtk.Align.CENTER)
        said.add_css_class("harness-connector-state")
        row.add_suffix(said)
        row.switch = Gtk.Switch(active=connector.on, valign=Gtk.Align.CENTER,
                                tooltip_text="Use this connector")
        row.switch.connect("notify::active", lambda switch, _p: self._switched(
            connector, switch.get_active()))
        row.add_suffix(row.switch)
        row.trash = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER,
                               tooltip_text="Remove this connector")
        row.trash.add_css_class("flat")
        row.trash.connect("clicked", lambda _b: self._removed(connector.name))
        row.add_suffix(row.trash)
        self._said[connector.name] = said
        self._rows[connector.name] = row
        return row

    def row(self, name: str) -> Adw.ActionRow:
        return self._rows[name]

    def _removed(self, name: str) -> None:
        if self._remove(name):
            self.reload()

    def _switched(self, connector: Connector, on: bool) -> None:
        if self._save(replace(connector, on=on)):
            self.reload()

    def _ask_states(self) -> None:
        self._polls += 1
        self._background(self._states, self._show_states)

    def _show_states(self, states: dict[str, State]) -> None:
        unsettled = False
        for connector in self._connectors:
            # Switched off here, it is off before the Engine has reloaded.
            state = (states.get(connector.name) if connector.on
                     else State("disabled"))
            words, tone = said_of(state)
            unsettled |= state is None or state.status == "pending"
            label = self._said[connector.name]
            label.set_text(words)
            label.set_css_classes(["harness-connector-state", f"harness-{tone}"])
        if unsettled and self._polls < self.POLLS:
            self._later(self.POLL_SECONDS, self._ask_states)


def _reach(connector: Connector) -> str:
    """How the server is reached, as the person would type it."""
    return shlex.join(connector.command) if connector.command else connector.url
