"""Widgets for the blocks of an answer, and for one turn of the conversation.

What the blocks are, and how inline text becomes Pango markup, is decided in
osiris/harness/markdown.py, where it is tested. Every widget here only carries
CSS classes; how they look is the Skin's, in which colour the Theme's.
"""
import re
import time
from collections.abc import Callable
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import GLib, Gtk, GtkSource, Pango  # noqa: E402

from osiris.harness.activity import elapsed  # noqa: E402
from osiris.harness.conversation import State, Turn  # noqa: E402
from osiris.harness.markdown import (  # noqa: E402
    Code,
    Heading,
    InlineStyle,
    ListBlock,
    Paragraph,
    Quote,
    Rule,
    Table,
    parse,
    unchanged_prefix,
)

# Fence names as models write them, mapped to GtkSourceView's language ids.
LANGUAGES = {
    "sh": "sh", "bash": "sh", "shell": "sh", "zsh": "sh", "console": "sh",
    "py": "python3", "python": "python3", "python3": "python3",
    "js": "js", "javascript": "js", "ts": "typescript", "typescript": "typescript",
    "json": "json", "yaml": "yaml", "yml": "yaml", "toml": "toml", "ini": "ini",
    "diff": "diff", "patch": "diff", "c": "c", "cpp": "cpp", "c++": "cpp",
    "rust": "rust", "rs": "rust", "go": "go", "css": "css", "html": "html",
    "xml": "xml", "markdown": "markdown", "md": "markdown", "sql": "sql",
    "lua": "lua", "java": "java", "kotlin": "kotlin", "ruby": "ruby",
    "make": "makefile", "makefile": "makefile", "dockerfile": "dockerfile",
}
COPIED_MS = 1500
_LINK_TAGS = re.compile(r'<a href="[^"]*">|</a>')


def _markup_label(markup: str, *classes: str) -> Gtk.Label:
    label = Gtk.Label(xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR,
                      selectable=True, hexpand=True)
    try:
        # The markup is built escaped, so this should never fail; if it does,
        # the text is shown plain rather than not at all. Links are GTK's
        # own extension to Pango markup, so they are left out of the check.
        Pango.parse_markup(_LINK_TAGS.sub("", markup), -1, "\0")
        label.set_markup(markup)
    except GLib.Error:
        label.set_text(markup)
    for name in classes:
        label.add_css_class(name)
    return label


class CodeView(Gtk.Box):
    """A code block: its language and a Copy button over highlighted code."""

    def __init__(self, block: Code, scheme: GtkSource.StyleScheme | None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("harness-code")
        self._source = block.source

        name = Gtk.Label(label=block.language or "code", xalign=0, hexpand=True)
        name.add_css_class("harness-meta")
        self._copy = Gtk.Button(label="Copy")
        self._copy.add_css_class("flat")
        self._copy.add_css_class("harness-copy")
        self._copy.connect("clicked", self._copy_source)
        header = Gtk.Box()
        header.add_css_class("harness-code-header")
        header.append(name)
        header.append(self._copy)

        self.buffer = GtkSource.Buffer(text=block.source)
        language_id = LANGUAGES.get((block.language or "").lower())
        if language_id:
            language = GtkSource.LanguageManager.get_default().get_language(language_id)
            if language is not None:
                self.buffer.set_language(language)
        self.buffer.set_highlight_matching_brackets(False)
        if scheme is not None:
            self.buffer.set_style_scheme(scheme)
        # Long lines wrap rather than scroll: inside a scrolled window a text
        # view does not report its full height and the block is clipped, and
        # Copy always takes the source exactly as written.
        view = GtkSource.View(buffer=self.buffer, editable=False,
                              cursor_visible=False, monospace=True,
                              wrap_mode=Gtk.WrapMode.CHAR,
                              left_margin=12, right_margin=12,
                              top_margin=10, bottom_margin=10)
        view.add_css_class("harness-code-view")
        # A text view lays its lines out in idle time, after it was first
        # measured with none, and is not measured again: the block showed only
        # its margins. One more measure once it is on screen, at a priority
        # below that layout, gives it its full height.
        view.connect("map", lambda v: GLib.idle_add(
            self._remeasure, v, priority=GLib.PRIORITY_DEFAULT_IDLE))
        self.append(header)
        self.append(view)

    @staticmethod
    def _remeasure(view: Gtk.Widget) -> bool:
        view.queue_resize()
        return False

    def _copy_source(self, _button) -> None:
        self.get_clipboard().set(self._source)
        self._copy.set_label("Copied")
        GLib.timeout_add(COPIED_MS, self._restore)

    def _restore(self) -> bool:
        self._copy.set_label("Copy")
        return False


def _list(block: ListBlock) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    box.add_css_class("harness-list")
    for item in block.items:
        row = Gtk.Box(spacing=8, margin_start=item.depth * 18)
        marker = Gtk.Label(label=item.marker, xalign=1, valign=Gtk.Align.START)
        # The text's own class too, so the marker shares its line height.
        marker.add_css_class("harness-paragraph")
        marker.add_css_class("harness-list-marker")
        row.append(marker)
        row.append(_markup_label(item.markup, "harness-paragraph"))
        box.append(row)
    return box


def _table(block: Table) -> Gtk.Widget:
    grid = Gtk.Grid(column_homogeneous=False)
    grid.add_css_class("harness-table")
    for column, markup in enumerate(block.header):
        grid.attach(_markup_label(markup, "harness-table-header"), column, 0, 1, 1)
    for row, cells in enumerate(block.rows, start=1):
        for column, markup in enumerate(cells):
            grid.attach(_markup_label(markup, "harness-table-cell"), column, row, 1, 1)
    # Cells wrap rather than scroll: the drawer is narrow, and a table that
    # scrolls sideways hides half of every row.
    grid.set_valign(Gtk.Align.START)
    return grid


def block_widget(block, scheme: GtkSource.StyleScheme | None) -> Gtk.Widget:
    if isinstance(block, Heading):
        label = _markup_label(block.markup, "harness-heading", f"level-{block.level}")
        return label
    if isinstance(block, Paragraph):
        return _markup_label(block.markup, "harness-paragraph")
    if isinstance(block, Code):
        return CodeView(block, scheme)
    if isinstance(block, ListBlock):
        return _list(block)
    if isinstance(block, Quote):
        return _markup_label(block.markup, "harness-quote")
    if isinstance(block, Table):
        return _table(block)
    if isinstance(block, Rule):
        rule = Gtk.Box()
        rule.add_css_class("harness-rule")
        return rule
    return _markup_label(GLib.markup_escape_text(str(block)), "harness-paragraph")


class WorkingRow(Gtk.Box):
    """While Osiris works: a pulse, what it is doing, and how long it has been."""

    def __init__(self, clock: Callable[[], float]):
        super().__init__(spacing=10, halign=Gtk.Align.START, visible=False)
        self.add_css_class("harness-working")
        dots = Gtk.Box(spacing=4, valign=Gtk.Align.CENTER)
        dots.add_css_class("harness-dots")
        for _ in range(3):
            dot = Gtk.Box(valign=Gtk.Align.CENTER)
            dot.add_css_class("harness-dot")
            dots.append(dot)
        self._doing = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        self._doing.add_css_class("harness-doing")
        self._elapsed = Gtk.Label(xalign=0)
        self._elapsed.add_css_class("harness-meta")
        self._elapsed.add_css_class("harness-elapsed")
        self.append(dots)
        self.append(self._doing)
        self.append(self._elapsed)
        self._clock = clock
        self._since = clock()

    def show(self, doing: str) -> None:
        self._doing.set_text(doing)
        self._tick()
        self.set_visible(True)

    def _tick(self) -> bool:
        self._elapsed.set_text(elapsed(self._clock() - self._since))
        return True


class TurnView(Gtk.Box):
    """One question and its answer, redrawn only where the answer changed."""

    def __init__(self, turn: Turn, on_undo: Callable[[Turn], None],
                 program_card: Callable[[str], Gtk.Widget],
                 clock: Callable[[], float] = time.monotonic):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("harness-turn")
        self._on_undo = on_undo
        self._program_card = program_card
        question = Gtk.Label(label=turn.question, xalign=0, wrap=True,
                             wrap_mode=Pango.WrapMode.WORD_CHAR, selectable=True,
                             halign=Gtk.Align.END)
        question.add_css_class("harness-question")
        self.append(question)
        self.answer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.answer.add_css_class("harness-answer")
        self.append(self.answer)
        self.working = WorkingRow(clock)
        self.append(self.working)
        self.extras = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.append(self.extras)
        self._blocks: list = []
        self._widgets: list[Gtk.Widget] = []
        self._finished_at: datetime | None = None

    def update(self, turn: Turn, style: InlineStyle,
               scheme: GtkSource.StyleScheme | None) -> None:
        blocks = parse(turn.answer, style)
        keep = unchanged_prefix(self._blocks, blocks)
        for widget in self._widgets[keep:]:
            self.answer.remove(widget)
        self._widgets = self._widgets[:keep]
        for block in blocks[keep:]:
            widget = block_widget(block, scheme)
            self.answer.append(widget)
            self._widgets.append(widget)
        self._blocks = blocks
        self._extras(turn)

    def restyle(self, turn: Turn, style: InlineStyle,
                scheme: GtkSource.StyleScheme | None) -> None:
        """Redraw everything, for a Theme switch: inline colours are in markup."""
        self._blocks = []
        self.update(turn, style, scheme)

    def _changes(self, turn: Turn) -> Gtk.Widget:
        chip = Gtk.Box(spacing=6, halign=Gtk.Align.START)
        chip.add_css_class("harness-chip")
        chip.append(Gtk.Image(icon_name="object-select-symbolic"))
        chip.append(Gtk.Label(label="  ·  ".join(c.summary for c in turn.changes),
                              ellipsize=Pango.EllipsizeMode.END,
                              max_width_chars=48))
        if turn.undone:
            chip.append(Gtk.Label(label="Undone"))
        elif turn.undoable:
            undo = Gtk.Button(label="Undo")
            undo.add_css_class("flat")
            undo.connect("clicked", lambda _b: self._on_undo(turn))
            chip.append(undo)
        return chip

    def _extras(self, turn: Turn) -> None:
        child = self.extras.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            self.extras.remove(child)
            child = following
        if turn.state in (State.WAITING, State.ANSWERING):
            self.working.show(turn.doing)
        for refused in turn.refused:
            chip = Gtk.Box(spacing=6, halign=Gtk.Align.START)
            chip.add_css_class("harness-chip")
            chip.append(Gtk.Image(icon_name="changes-prevent-symbolic"))
            chip.append(Gtk.Label(label=f"Not allowed yet · {refused}",
                                  ellipsize=Pango.EllipsizeMode.END,
                                  max_width_chars=48))
            self.extras.append(chip)
        if turn.changes:
            self.extras.append(self._changes(turn))
        for name in turn.programs:
            self.extras.append(self._program_card(name))
        if turn.state is State.FAILED:
            error = Gtk.Label(label=turn.error or "The answer failed.", xalign=0,
                              wrap=True, selectable=True)
            error.add_css_class("harness-error")
            self.extras.append(error)
        if turn.state in (State.DONE, State.STOPPED):
            if self._finished_at is None:
                self._finished_at = datetime.now()
            parts = [turn.model.model] if turn.model else []
            if turn.state is State.STOPPED:
                parts.append("stopped")
            parts.append(self._finished_at.strftime("%H:%M"))
            meta = Gtk.Label(label="  ·  ".join(parts), xalign=0)
            meta.add_css_class("harness-meta")
            self.extras.append(meta)
