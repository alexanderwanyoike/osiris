"""The Canvas: what a Conversation made, beside it in Expanded
(docs/HARNESS-LAYOUT.md). For now each Program it touched, its code shown
read-only in the Theme's colours, editing handed to Code (ADR 0016).
"""
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Adw, Gio, GObject, Gtk, GtkSource, Pango  # noqa: E402

from osiris.harness.engine import FileChange  # noqa: E402
from osiris.harness.review import file_lines  # noqa: E402
from osiris.programs.programs import Program  # noqa: E402

#: Narrower than this a Program's file tree slides over its code instead of
#: sitting beside it.
TREE_BESIDE = "max-width: 900sp"


class Canvas(Gtk.Box):
    def __init__(self, *, read: Callable[[Path], str],
                 open_in_code: Callable[[Path, Path], None],
                 scheme: GtkSource.StyleScheme | None = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("harness-canvas")
        self._read = read
        self._open_in_code = open_in_code
        self._scheme = scheme
        self._views: dict[Adw.TabPage, GtkSource.View] = {}
        #: The tab of a question's changes, kept while Programs come and go.
        self._changes: Adw.TabPage | None = None
        self.tabs = Adw.TabView(vexpand=True)
        self._items = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self._items.add_css_class("navigation-sidebar")
        self._items.connect("row-activated", self._picked)
        self._picker = Gtk.MenuButton(icon_name="view-list-symbolic",
                                      tooltip_text="Everything in this conversation",
                                      popover=Gtk.Popover(child=self._items))
        self._picker.add_css_class("flat")
        self.strip = Adw.TabBar(view=self.tabs, autohide=False, expand_tabs=False,
                                end_action_widget=self._picker)
        self.append(self.strip)
        self.append(self.tabs)

    def show(self, programs: list[tuple[Program, list[Path]]]) -> None:
        """A tab for each Program, keeping the one on screen if it is still there."""
        selected = self.tabs.get_selected_page()
        keep = selected.get_title() if selected is not None else None
        for index in reversed(range(self.tabs.get_n_pages())):
            page = self.tabs.get_nth_page(index)
            if page is not self._changes:
                self.tabs.close_page(page)
        self._views = {page: view for page, view in self._views.items()
                       if page is self._changes}
        self._items.remove_all()
        for program, files in programs:
            content, view = self._page(program, files)
            page = self.tabs.append(content)
            page.set_title(program.manifest.label)
            self._views[page] = view
            self._items.append(Gtk.Label(label=program.manifest.label, xalign=0))
            if program.manifest.label == keep:
                self.tabs.set_selected_page(page)

    def show_changes(self, question: str, files: tuple[FileChange, ...],
                     on_comment: Callable[[str, tuple[int, int], str], None]) -> None:
        """A question's changes in a tab of their own: the files it changed,
        each opening to its diff, and a comment on picked lines."""
        if self._changes is not None:
            self.tabs.close_page(self._changes)
            self._views.pop(self._changes, None)
        content, view = self._changes_page(files, on_comment)
        page = self.tabs.append(content)
        page.set_title(f"Changes: {question}")
        self._changes = page
        self._views[page] = view
        self.tabs.set_selected_page(page)

    def _changes_page(self, files: tuple[FileChange, ...],
                      on_comment: Callable[[str, tuple[int, int], str], None],
                      ) -> tuple[Gtk.Widget, GtkSource.View]:
        buffer = GtkSource.Buffer(
            language=GtkSource.LanguageManager.get_default().get_language("diff"))
        if self._scheme is not None:
            buffer.set_style_scheme(self._scheme)
        view = GtkSource.View(buffer=buffer, editable=False, monospace=True,
                              left_margin=12, right_margin=12, top_margin=12,
                              bottom_margin=12, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        view.add_css_class("harness-code")
        shown: list[FileChange] = []

        def show(change: FileChange) -> None:
            shown[:] = [change]
            buffer.set_text(change.patch)

        listing = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        listing.add_css_class("navigation-sidebar")
        for change in files:
            line = Gtk.Box(spacing=8)
            line.append(Gtk.Label(label=change.path, xalign=0, hexpand=True,
                                  ellipsize=Pango.EllipsizeMode.MIDDLE))
            counts = Gtk.Label(label=f"+{change.additions} −{change.deletions}")
            counts.add_css_class("harness-meta")
            line.append(counts)
            row = Gtk.ListBoxRow(child=line)
            row.change = change
            listing.append(row)
        listing.connect("row-activated", lambda _l, row: show(row.change))

        entry = Gtk.Entry(placeholder_text="Comment on the picked lines")

        def commented(_entry) -> None:
            text = entry.get_text().strip()
            picked = buffer.get_selection_bounds()
            if not text or not shown:
                return
            if picked:
                first, last = picked[0].get_line() + 1, picked[1].get_line() + 1
            else:
                first = last = buffer.get_iter_at_mark(buffer.get_insert()).get_line() + 1
            lines = file_lines(shown[0].patch, first, last)
            if lines is None:
                return
            on_comment(shown[0].path, lines, text)
            entry.set_text("")

        entry.connect("activate", commented)
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        page.append(Gtk.ScrolledWindow(child=listing, max_content_height=160,
                                       propagate_natural_height=True,
                                       hscrollbar_policy=Gtk.PolicyType.NEVER))
        page.append(Gtk.ScrolledWindow(child=view, vexpand=True, hexpand=True,
                                       hscrollbar_policy=Gtk.PolicyType.NEVER))
        page.append(entry)
        if files:
            show(files[0])
            listing.select_row(listing.get_row_at_index(0))
        return page, view

    def current_view(self) -> GtkSource.View | None:
        page = self.tabs.get_selected_page()
        return self._views.get(page) if page is not None else None

    def restyle(self, scheme: GtkSource.StyleScheme | None) -> None:
        self._scheme = scheme
        for view in self._views.values():
            view.get_buffer().set_style_scheme(scheme)

    def _picked(self, _list, row) -> None:
        self.tabs.set_selected_page(self.tabs.get_nth_page(row.get_index()))
        self._picker.popdown()

    def _page(self, program: Program,
              files: list[Path]) -> tuple[Gtk.Widget, GtkSource.View]:
        buffer = GtkSource.Buffer()
        if self._scheme is not None:
            buffer.set_style_scheme(self._scheme)
        view = GtkSource.View(buffer=buffer, editable=False, cursor_visible=False,
                              monospace=True, show_line_numbers=True, left_margin=12,
                              right_margin=12, top_margin=12, bottom_margin=12,
                              wrap_mode=Gtk.WrapMode.WORD_CHAR)
        view.add_css_class("harness-code")
        where = Gtk.Label(xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.START)
        where.add_css_class("harness-meta")
        shown: list[Path] = []

        def show_file(relative: Path) -> None:
            shown[:] = [relative]
            buffer.set_text(self._read(program.source / relative))
            language = GtkSource.LanguageManager.get_default().guess_language(
                relative.name, None)
            buffer.set_language(language)
            where.set_text(f"{program.manifest.name} / {relative}")

        tree = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        tree.add_css_class("navigation-sidebar")
        for relative in files:
            row = Gtk.ListBoxRow(child=Gtk.Label(label=str(relative), xalign=0,
                                                 ellipsize=Pango.EllipsizeMode.MIDDLE))
            row.relative = relative
            tree.append(row)
        tree.connect("row-activated", lambda _t, row: show_file(row.relative))

        files_toggle = Gtk.ToggleButton(icon_name="folder-symbolic", tooltip_text="Files",
                                        active=True)
        files_toggle.add_css_class("flat")
        open_code = Gtk.Button(icon_name="document-edit-symbolic",
                               tooltip_text="Open in Code")
        open_code.add_css_class("flat")
        open_code.connect("clicked", lambda _b: self._open_in_code(
            program.source, shown[0] if shown else Path(".")))
        bar = Gtk.Box(spacing=6)
        bar.add_css_class("harness-path")
        bar.append(files_toggle)
        bar.append(where)
        bar.append(open_code)

        split = Adw.OverlaySplitView(
            sidebar=Gtk.ScrolledWindow(child=tree, hscrollbar_policy=Gtk.PolicyType.NEVER),
            content=Gtk.ScrolledWindow(child=view, vexpand=True, hexpand=True,
                                       hscrollbar_policy=Gtk.PolicyType.NEVER),
            min_sidebar_width=170, max_sidebar_width=220, vexpand=True)
        files_toggle.bind_property(
            "active", split, "show-sidebar",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        holder = Adw.BreakpointBin(child=split, width_request=280, height_request=200,
                                   vexpand=True)
        narrow = Adw.Breakpoint.new(Adw.BreakpointCondition.parse(TREE_BESIDE))
        narrow.add_setter(split, "collapsed", True)
        narrow.add_setter(files_toggle, "active", False)
        holder.add_breakpoint(narrow)

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        page.append(bar)
        page.append(holder)
        first = _first_file(program, files)
        if first is not None:
            show_file(first)
            for row in _rows(tree):
                if row.relative == first:
                    tree.select_row(row)
        return page, view


def _first_file(program: Program, files: list[Path]) -> Path | None:
    """What the Program runs, if it is among its files, else its first file."""
    for word in program.manifest.run:
        if Path(word) in files:
            return Path(word)
    return files[0] if files else None


def _rows(tree: Gtk.ListBox):
    index = 0
    while (row := tree.get_row_at_index(index)) is not None:
        yield row
        index += 1


def open_in_code(folder: Path, file: Path) -> None:
    """Code - OSS on the Program's folder, at the file being read."""
    Gio.Subprocess.new(["code", str(folder), str(folder / file)],
                       Gio.SubprocessFlags.NONE)
