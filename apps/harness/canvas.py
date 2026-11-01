"""The Canvas: what a Conversation made, beside it in Expanded
(docs/HARNESS-LAYOUT.md): its Programs' files and its changes, each kind in a
group of tabs, code read-only in the Theme's colours, editing handed to Code
(ADR 0016).
"""
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Adw, Gio, Gtk, GtkSource, Pango  # noqa: E402

from osiris.harness.engine import FileChange  # noqa: E402
from osiris.harness.file_tree import Node, tree  # noqa: E402
from osiris.harness.panels import Kind, Panels, Tab  # noqa: E402
from osiris.harness.review import file_lines  # noqa: E402
from osiris.programs.programs import Program  # noqa: E402

#: Narrower than this a Program's file tree slides over its code instead of
#: sitting beside it.
TREE_BESIDE = "max-width: 900sp"


class Canvas(Gtk.Box):
    """Groups of tabs, one for each kind of thing shown, tiled side by side
    under a toolbar (#194). ``panels`` decides what is open; this draws it."""

    def __init__(self, *, read: Callable[[Path], str],
                 open_in_code: Callable[[Path, Path], None],
                 scheme: GtkSource.StyleScheme | None = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("harness-canvas")
        self._read = read
        self._open_in_code = open_in_code
        self._scheme = scheme
        self.panels = Panels()
        #: Each group's tabs, by kind, and the widget that holds them.
        self.views: dict[Kind, Adw.TabView] = {}
        self._groups: dict[Kind, Gtk.Widget] = {}
        self._pages: dict[Tab, Adw.TabPage] = {}
        self._sources: dict[Tab, GtkSource.View] = {}
        #: The group last opened or chosen in, whose code is current.
        self._focus: Kind | None = None
        self._programs: dict[str, tuple[Program, list[Path]]] = {}
        self.tree = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.tree.add_css_class("navigation-sidebar")
        self.tree.connect("row-activated", self._tree_activated)
        self.toolbar = Gtk.Box(spacing=4, halign=Gtk.Align.END)
        self.toolbar.add_css_class("harness-canvas-toolbar")
        files = Gtk.Button(icon_name="folder-symbolic", tooltip_text="Files")
        files.add_css_class("flat")
        files.connect("clicked", lambda _b: self.show_files())
        self.toolbar.append(files)
        self._tiles = Gtk.Box(vexpand=True, hexpand=True)
        self._paneds: list[Gtk.Paned] = []
        self.append(self.toolbar)
        self.append(self._tiles)

    def show(self, programs: list[tuple[Program, list[Path]]]) -> None:
        """The Programs whose files can be opened; tabs of any gone close, and
        with no file open, what the first runs opens."""
        self._programs = {p.manifest.name: (p, files) for p, files in programs}
        self._fill_tree()
        for tab in list(self._open(Kind.CODE)):
            if tab.key.split("/", 1)[0] not in self._programs:
                self.close(tab)
        if not self._open(Kind.CODE):
            self.show_files()

    def show_files(self) -> None:
        """Open the code group on what the first Program runs, or bring its
        file tree forward when it is open."""
        if self._open(Kind.CODE):
            self._split.set_show_sidebar(True)
            return
        for program, files in self._programs.values():
            first = _first_file(program, files)
            if first is not None:
                self.open_file(program.manifest.name, first)
                return

    def open_file(self, name: str, relative: Path) -> None:
        tab = Tab(Kind.CODE, f"{name}/{relative}", relative.name)
        if tab not in self._pages:
            program, _ = self._programs[name]
            content, view = self._code_page(program, relative)
            self._add(tab, content, view)
        self._opened(tab)

    def show_changes(self, question: str, files: tuple[FileChange, ...],
                     on_comment: Callable[[str, tuple[int, int], str], None]) -> None:
        """A question's changes in a tab of their own: the files it changed,
        each opening to its diff, and a comment on picked lines."""
        tab = Tab(Kind.CHANGES, question, f"Changes: {question}")
        if tab in self._pages:
            self.close(tab)
        content, view = self._changes_page(files, on_comment)
        self._add(tab, content, view)
        self._opened(tab)

    def close(self, tab: Tab) -> None:
        page = self._pages.get(tab)
        if page is not None:
            self.views[tab.kind].close_page(page)

    def _open(self, kind: Kind) -> list[Tab]:
        return next((g.tabs for g in self.panels.groups if g.kind is kind), [])

    def _add(self, tab: Tab, content: Gtk.Widget, view: GtkSource.View) -> None:
        page = self._view(tab.kind).append(content)
        page.set_title(tab.title)
        self._pages[tab] = page
        self._sources[tab] = view

    def _opened(self, tab: Tab) -> None:
        self.panels.open(tab)
        self._focus = tab.kind
        self.views[tab.kind].set_selected_page(self._pages[tab])
        self._tile()

    def _view(self, kind: Kind) -> Adw.TabView:
        """The group's tabs, made the first time it opens."""
        if kind in self.views:
            return self.views[kind]
        view = Adw.TabView(vexpand=True, hexpand=True)
        view.connect("close-page", self._closing)
        view.connect("notify::selected-page", lambda *_: setattr(self, "_focus", kind))
        group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        group.add_css_class("harness-canvas-group")
        group.append(Adw.TabBar(view=view, autohide=False, expand_tabs=False))
        group.append(view)
        self.views[kind] = view
        self._groups[kind] = self._beside_tree(group) if kind is Kind.CODE else group
        return view

    def _beside_tree(self, group: Gtk.Widget) -> Gtk.Widget:
        """The code group, with the Programs' files beside it."""
        self._split = Adw.OverlaySplitView(
            sidebar=Gtk.ScrolledWindow(child=self.tree,
                                       hscrollbar_policy=Gtk.PolicyType.NEVER),
            content=group, min_sidebar_width=170, max_sidebar_width=220,
            vexpand=True)
        holder = Adw.BreakpointBin(child=self._split, width_request=280,
                                   height_request=200, vexpand=True, hexpand=True)
        narrow = Adw.Breakpoint.new(Adw.BreakpointCondition.parse(TREE_BESIDE))
        narrow.add_setter(self._split, "collapsed", True)
        holder.add_breakpoint(narrow)
        return holder

    def _closing(self, view: Adw.TabView, page: Adw.TabPage) -> bool:
        tab = next(t for t, p in self._pages.items() if p is page)
        del self._pages[tab]
        self._sources.pop(tab, None)
        self.panels.close(tab)
        view.close_page_finish(page, True)
        self._tile()
        return True

    def _tile(self) -> None:
        """The open groups side by side: the first, then the rest stacked."""
        for paned in self._paneds:
            paned.set_start_child(None)
            paned.set_end_child(None)
        self._paneds = []
        while (child := self._tiles.get_first_child()) is not None:
            self._tiles.remove(child)
        shown = [self._groups[group.kind] for group in self.panels.groups]
        if not shown:
            return
        self._tiles.append(self._side_by_side(shown))

    def _side_by_side(self, shown: list[Gtk.Widget]) -> Gtk.Widget:
        if len(shown) == 1:
            return shown[0]
        stack = shown[-1]
        for widget in reversed(shown[1:-1]):
            stack = self._paned(Gtk.Orientation.VERTICAL, widget, stack)
        return self._paned(Gtk.Orientation.HORIZONTAL, shown[0], stack)

    def _paned(self, orientation: Gtk.Orientation, start: Gtk.Widget,
               end: Gtk.Widget) -> Gtk.Paned:
        paned = Gtk.Paned(orientation=orientation, start_child=start, end_child=end,
                          wide_handle=False, hexpand=True, vexpand=True)
        self._paneds.append(paned)
        return paned

    def _fill_tree(self) -> None:
        self.tree.remove_all()
        for name, (program, files) in self._programs.items():
            heading = Gtk.ListBoxRow(activatable=False, selectable=False,
                                     child=Gtk.Label(label=program.manifest.label,
                                                     xalign=0))
            heading.add_css_class("harness-tree-heading")
            self.tree.append(heading)
            self._add_nodes(name, tree(files), depth=0)

    def _add_nodes(self, name: str, nodes: tuple[Node, ...],
                   depth: int) -> list[Gtk.ListBoxRow]:
        """Rows for ``nodes``, a folder's contents hidden until it opens."""
        rows = []
        for node in nodes:
            row = Gtk.ListBoxRow(child=_tree_line(node, depth), visible=depth == 0)
            self.tree.append(row)
            rows.append(row)
            if node.folder:
                row.inside = self._add_nodes(name, node.children, depth + 1)
                row.add_css_class("harness-tree-folder")
            else:
                row.opens = (name, node.path)
        return rows

    def _tree_activated(self, _tree, row) -> None:
        opens = getattr(row, "opens", None)
        if opens is not None:
            self.open_file(*opens)
            return
        inside = getattr(row, "inside", [])
        _show_inside(inside, not (inside and inside[0].get_visible()))

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
        group = next((g for g in self.panels.groups if g.kind is self._focus), None)
        if group is None or group.selected is None:
            return None
        return self._sources.get(group.selected)

    def restyle(self, scheme: GtkSource.StyleScheme | None) -> None:
        self._scheme = scheme
        for view in self._sources.values():
            view.get_buffer().set_style_scheme(scheme)

    def _code_page(self, program: Program,
                   relative: Path) -> tuple[Gtk.Widget, GtkSource.View]:
        buffer = GtkSource.Buffer(
            language=GtkSource.LanguageManager.get_default().guess_language(
                relative.name, None))
        if self._scheme is not None:
            buffer.set_style_scheme(self._scheme)
        buffer.set_text(self._read(program.source / relative))
        view = GtkSource.View(buffer=buffer, editable=False, cursor_visible=False,
                              monospace=True, show_line_numbers=True, left_margin=12,
                              right_margin=12, top_margin=12, bottom_margin=12,
                              wrap_mode=Gtk.WrapMode.WORD_CHAR)
        view.add_css_class("harness-code")
        trail = " \u203a ".join((program.manifest.label, *relative.parts))
        where = Gtk.Label(label=trail, xalign=0, hexpand=True,
                          ellipsize=Pango.EllipsizeMode.START)
        where.add_css_class("harness-meta")
        open_code = Gtk.Button(icon_name="document-edit-symbolic",
                               tooltip_text="Open in Code")
        open_code.add_css_class("flat")
        open_code.connect("clicked",
                          lambda _b: self._open_in_code(program.source, relative))
        bar = Gtk.Box(spacing=8)
        bar.add_css_class("harness-path")
        bar.append(_file_icon(relative.name))
        bar.append(where)
        bar.append(open_code)
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        page.append(bar)
        page.append(Gtk.ScrolledWindow(child=view, vexpand=True, hexpand=True,
                                       hscrollbar_policy=Gtk.PolicyType.NEVER))
        return page, view


def _tree_line(node: Node, depth: int) -> Gtk.Widget:
    """A file or folder's icon and name, indented by how deep it is."""
    if node.folder:
        icon = Gtk.Image(icon_name="folder-symbolic")
    else:
        icon = _file_icon(node.name)
    line = Gtk.Box(spacing=8, margin_start=14 * depth)
    line.append(icon)
    line.append(Gtk.Label(label=node.name, xalign=0,
                          ellipsize=Pango.EllipsizeMode.MIDDLE))
    return line


def _file_icon(name: str) -> Gtk.Image:
    """GTK's own symbolic icon for the file's content type."""
    kind, _uncertain = Gio.content_type_guess(name, None)
    return Gtk.Image(gicon=Gio.content_type_get_symbolic_icon(kind))


def _show_inside(rows: list[Gtk.ListBoxRow], shown: bool) -> None:
    """Open a folder to its own contents, or close it and every folder in it."""
    for row in rows:
        row.set_visible(shown)
        if not shown:
            _show_inside(getattr(row, "inside", []), False)


def _first_file(program: Program, files: list[Path]) -> Path | None:
    """What the Program runs, if it is among its files, else its first file."""
    for word in program.manifest.run:
        if Path(word) in files:
            return Path(word)
    return files[0] if files else None


def open_in_code(folder: Path, file: Path) -> None:
    """Code - OSS on the Program's folder, at the file being read."""
    Gio.Subprocess.new(["code", str(folder), str(folder / file)],
                       Gio.SubprocessFlags.NONE)
