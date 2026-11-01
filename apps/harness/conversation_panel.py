"""The Conversation panel (#169): where a Conversation runs, its connectors,
its context and its changes, in one place beside it.

What fills the context and how a connector's state is said are decided in
osiris/harness; this draws them.
"""
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango  # noqa: E402

from osiris.harness.connectors import State, said_of  # noqa: E402
from osiris.harness.context import Slice, grid  # noqa: E402

#: The context grid's squares, each a slice of the window, and per row.
SQUARES = 100
ACROSS = 20
#: What each kind is called in the legend.
NAMES = {
    "instructions": "Instructions",
    "questions": "Your questions",
    "answers": "Answers",
    "tools": "Tool calls",
    "free": "Free",
}


def _section(title: str) -> tuple[Gtk.Box, Gtk.Box]:
    """A titled part of the panel, and the box its rows go in."""
    part = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    part.add_css_class("harness-panel-section")
    heading = Gtk.Label(label=title, xalign=0)
    heading.add_css_class("harness-panel-heading")
    rows = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    part.append(heading)
    part.append(rows)
    return part, rows


def _fact(icon: str, text: str = "") -> Gtk.Box:
    line = Gtk.Box(spacing=8)
    line.add_css_class("harness-panel-fact")
    line.append(Gtk.Image(icon_name=icon))
    words = Gtk.Label(label=text, xalign=0, hexpand=True,
                      ellipsize=Pango.EllipsizeMode.MIDDLE)
    line.append(words)
    line.words = words
    return line


class ConversationPanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=22,
                         margin_top=16, margin_bottom=16, margin_start=18,
                         margin_end=18)
        self.add_css_class("harness-conversation-panel")
        where, rows = _section("Where")
        self.project = _fact("folder-symbolic")
        self.branch = _fact("osiris-branch-symbolic")
        self.model = _fact("starred-symbolic")
        for fact in (self.project, self.branch, self.model):
            rows.append(fact)
        self.append(where)
        connectors, self._connectors = _section("Connectors")
        self.append(connectors)
        context, self._context = _section("Context")
        self.append(context)

    def show_where(self, project: str, branch: str, model: str) -> None:
        self.project.words.set_text(project)
        self.branch.words.set_text(branch)
        self.branch.set_visible(bool(branch))
        self.model.words.set_text(model)

    def show_connectors(self, states: dict[str, State]) -> None:
        _clear(self._connectors)
        if not states:
            none = Gtk.Label(label="None yet. Add one in Settings, under Connectors.",
                             xalign=0, wrap=True)
            none.add_css_class("harness-meta")
            self._connectors.append(none)
        for name, state in sorted(states.items()):
            line = _fact("network-server-symbolic", name)
            words, tone = said_of(state)
            said = Gtk.Label(label=words, tooltip_text=words, max_width_chars=22,
                             ellipsize=Pango.EllipsizeMode.END)
            said.set_css_classes(["harness-connector-state", f"harness-{tone}"])
            line.append(said)
            self._connectors.append(line)

    def show_context(self, shared: list[Slice], used: int, window: int) -> None:
        _clear(self._context)
        total = Gtk.Label(label=f"{used:,} of {window:,} tokens", xalign=0)
        total.add_css_class("harness-context-total")
        self._context.append(total)
        squares = Gtk.Grid(row_spacing=3, column_spacing=3)
        squares.add_css_class("harness-context-grid")
        for at, kind in enumerate(grid(shared, SQUARES)):
            square = Gtk.Box(css_classes=["harness-context-square", kind])
            squares.attach(square, at % ACROSS, at // ACROSS, 1, 1)
        self._context.append(squares)
        legend = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        for part in shared:
            line = Gtk.Box(spacing=8)
            line.append(Gtk.Box(css_classes=["harness-context-swatch", part.kind],
                                valign=Gtk.Align.CENTER))
            line.append(Gtk.Label(label=NAMES[part.kind], xalign=0, hexpand=True))
            share = Gtk.Label(label=f"{round(part.tokens * 100 / window)}%"
                              if window else "")
            share.add_css_class("harness-meta")
            line.append(share)
            legend.append(line)
        self._context.append(legend)
        note = Gtk.Label(label="Approximate: the Engine says how much is in use, "
                               "not by what, so each share is estimated from the "
                               "messages it keeps.", xalign=0, wrap=True)
        note.add_css_class("harness-meta")
        self._context.append(note)


def _clear(box: Gtk.Box) -> None:
    while (child := box.get_first_child()) is not None:
        box.remove(child)
