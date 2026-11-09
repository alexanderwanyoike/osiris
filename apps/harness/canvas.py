"""The Canvas: what a Conversation made, beside it in Expanded
(docs/HARNESS-LAYOUT.md): its Programs' files and its changes, each kind in a
group of tabs, code read-only in the Theme's colours, editing handed to Code
(ADR 0016).
"""
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Adw, Gio, Gtk, GtkSource, Pango  # noqa: E402

from osiris.harness.engine import FileChange  # noqa: E402
from osiris.harness.file_tree import Node, tree  # noqa: E402
from osiris.harness.panels import Kind, Panels, Tab  # noqa: E402
from osiris.harness.review import file_lines  # noqa: E402
from osiris.harness.titles import title_of  # noqa: E402
from osiris.programs.programs import Program  # noqa: E402

#: Narrower than this a Program's file tree slides over its code instead of
#: sitting beside it.
TREE_BESIDE = "max-width: 900sp"


class Canvas(Gtk.Box):
    """Groups of tabs, one for each kind of thing shown, tiled side by side
    under a toolbar (#194). ``panels`` decides what is open; this draws it."""

    def __init__(self, *, read: Callable[[Path], str],
                 open_in_code: Callable[[Path, Path], None],
                 scheme: GtkSource.StyleScheme | None = None,
                 on_changes: Callable[[], None] = lambda: None,
                 terminal: Callable[[Path], Gtk.Widget] | None = None,
                 page: Callable[[str, Callable[[str], None]], Gtk.Widget] | None = None,
                 home: Path | None = None):
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
        self._terminal = terminal
        self._home = home
        self._page = page
        #: Pages opened so far, which keys each one's tab.
        self._pages_opened = 0
        #: Terminals opened so far, which names each one's tab.
        self._shells = 0
        #: What each tab shows, ended when its tab closes.
        self._contents: dict[Tab, Gtk.Widget] = {}
        #: Redraw each group's header, by kind.
        self._redraws: dict[Kind, Callable[[], None]] = {}
        #: The Conversation shown, and each one's Changes tabs by question, to
        #: open again when it comes back (#220).
        self._conversation: str | None = None
        self._changes: dict[str | None, dict[str, tuple[Any, Any]]] = {}
        self.tree = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.tree.add_css_class("navigation-sidebar")
        self.tree.connect("row-activated", self._tree_activated)
        self.toolbar = Gtk.Box(spacing=4, halign=Gtk.Align.END)
        self.toolbar.add_css_class("harness-canvas-toolbar")
        files = Gtk.Button(icon_name="folder-symbolic", tooltip_text="Files")
        files.add_css_class("flat")
        files.connect("clicked", lambda _b: self.show_files())
        self.toolbar.append(files)
        changes = Gtk.Button(icon_name="osiris-changes-symbolic", tooltip_text="Changes")
        changes.add_css_class("flat")
        changes.connect("clicked", lambda _b: on_changes())
        self.toolbar.append(changes)
        shell = Gtk.Button(icon_name="utilities-terminal-symbolic",
                           tooltip_text="Terminal")
        shell.add_css_class("flat")
        shell.connect("clicked", lambda _b: self.open_terminal())
        self.toolbar.append(shell)
        globe = Gtk.Button(icon_name="web-browser-symbolic", tooltip_text="Browser")
        globe.add_css_class("flat")
        globe.connect("clicked", lambda _b: self.show_browser())
        self.toolbar.append(globe)
        self._tiles = Gtk.Box(vexpand=True, hexpand=True)
        self._paneds: list[Gtk.Paned] = []
        self._start = self._start_page()
        self.append(self._tiles)
        self._tile()

    def show(self, programs: list[tuple[Program, list[Path]]],
             conversation: str | None = None) -> None:
        """The Programs whose files can be opened; tabs of any gone close, and
        with no file open, what the first runs opens. Another
        ``conversation`` brings its own Changes tabs."""
        if conversation != self._conversation:
            self._switch(conversation)
        self._programs = {p.manifest.name: (p, files) for p, files in programs}
        self._fill_tree()
        for tab in list(self._open(Kind.CODE)):
            if tab.key.split("/", 1)[0] not in self._programs:
                self.close(tab)
        if not self._open(Kind.CODE):
            self.show_files()

    def _switch(self, conversation: str | None) -> None:
        for tab in list(self._open(Kind.CHANGES)):
            self.close(tab)
        self._conversation = conversation
        for question, (files, on_comment) in list(
                self._changes.get(conversation, {}).items()):
            self.show_changes(question, files, on_comment)

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
        self._changes.setdefault(self._conversation, {})[question] = (
            files, on_comment)
        tab = Tab(Kind.CHANGES, question, title_of(question))
        if tab in self._pages:
            self.close(tab)
        content, view = self._changes_page(files, on_comment)
        self._add(tab, content, view)
        self._opened(tab)

    def open_terminal(self) -> None:
        """A new terminal, in the folder of the Program being read."""
        folder = self._folder()
        if self._terminal is None or folder is None:
            return
        self._shells += 1
        tab = Tab(Kind.TERMINAL, f"terminal-{self._shells}", folder.name)
        self._add(tab, self._terminal(folder), None)
        self._opened(tab)

    def show_browser(self) -> None:
        """Bring the browser group forward, or open it on a new page."""
        if self._open(Kind.BROWSER):
            self._focus = Kind.BROWSER
            return
        self.open_page("")

    def open_page(self, at: str) -> None:
        """A page in a tab of its own, named by its title once it has one."""
        if self._page is None:
            return
        self._pages_opened += 1
        tab = Tab(Kind.BROWSER, f"page-{self._pages_opened}", "New page")

        def titled(title: str) -> None:
            if title and tab in self._pages:
                self._pages[tab].set_title(title)

        self._add(tab, self._page(at, titled), None)
        self._opened(tab)

    def _folder(self) -> Path | None:
        """The Program of the code tab on screen, else the first Program, else
        the home folder."""
        code = next((g for g in self.panels.groups if g.kind is Kind.CODE), None)
        if code is not None and code.selected is not None:
            name = code.selected.key.split("/", 1)[0]
            if name in self._programs:
                return self._programs[name][0].source
        return next((p.source for p, _ in self._programs.values()), self._home)

    def close(self, tab: Tab) -> None:
        page = self._pages.get(tab)
        if page is not None:
            self.views[tab.kind].close_page(page)

    def _open(self, kind: Kind) -> list[Tab]:
        return next((g.tabs for g in self.panels.groups if g.kind is kind), [])

    def _add(self, tab: Tab, content: Gtk.Widget,
             view: GtkSource.View | None) -> None:
        page = self._view(tab.kind).append(content)
        page.set_title(tab.title)
        self._pages[tab] = page
        self._contents[tab] = content
        # Drawn before the tab was known, the header's tab had no icon.
        self._redraws[tab.kind]()
        if view is not None:
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
        view.connect("notify::selected-page", lambda v, _p: self._chosen(kind, v))
        group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        group.append(self._header(kind, view))
        group.append(view)
        # The frame is the whole panel: for code, its file tree as well.
        frame = self._beside_tree(group) if kind is Kind.CODE else group
        frame.add_css_class("harness-canvas-group")
        frame.set_overflow(Gtk.Overflow.HIDDEN)
        self.views[kind] = view
        self._groups[kind] = frame
        return view

    def _header(self, kind: Kind, view: Adw.TabView) -> Gtk.Widget:
        """The group's tabs, small and left-aligned, and its own actions."""
        header = Gtk.Box(spacing=2)
        header.add_css_class("harness-group-header")
        tabs = Gtk.Box(spacing=2, hexpand=True)
        header.append(tabs)
        new = _NEW.get(kind)
        if new is not None:
            icon, tip = new
            more = Gtk.Button(icon_name=icon, tooltip_text=tip)
            more.add_css_class("flat")
            more.connect("clicked", lambda _b: self._new(kind))
            header.append(more)
        close = Gtk.Button(icon_name="window-close-symbolic", tooltip_text="Close")
        close.add_css_class("flat")
        close.connect("clicked", lambda _b: self._close_group(kind))
        header.append(close)

        def redraw(*_args) -> None:
            while (child := tabs.get_first_child()) is not None:
                tabs.remove(child)
            for index in range(view.get_n_pages()):
                tabs.append(self._header_tab(view, view.get_nth_page(index)))

        for signal in ("page-attached", "page-detached", "notify::selected-page"):
            view.connect(signal, redraw)
        self._redraws[kind] = redraw
        view.connect("page-attached",
                     lambda _v, page, _i: page.connect("notify::title", redraw))
        return header

    def _header_tab(self, view: Adw.TabView, page: Adw.TabPage) -> Gtk.Widget:
        tab = Gtk.Box(valign=Gtk.Align.CENTER)
        tab.add_css_class("harness-group-tab")
        if view.get_selected_page() is page:
            tab.add_css_class("selected")
        named = Gtk.Box(spacing=6)
        named.append(self._tab_icon(page))
        named.append(Gtk.Label(label=page.get_title(), max_width_chars=24,
                               ellipsize=Pango.EllipsizeMode.END))
        title = Gtk.Button(child=named)
        title.add_css_class("flat")
        title.connect("clicked", lambda _b: view.set_selected_page(page))
        shut = Gtk.Button(icon_name="window-close-symbolic", tooltip_text="Close tab")
        shut.add_css_class("flat")
        shut.add_css_class("harness-tab-close")
        shut.connect("clicked", lambda _b: view.close_page(page))
        tab.append(title)
        tab.append(shut)
        return tab

    def _tab_icon(self, page: Adw.TabPage) -> Gtk.Image:
        tab = next((t for t, p in self._pages.items() if p is page), None)
        if tab is not None and tab.kind is Kind.CODE:
            return _file_icon(tab.title)
        return Gtk.Image(icon_name=_TAB_ICONS.get(tab.kind if tab else Kind.CODE,
                                                   "text-x-generic-symbolic"))

    def _new(self, kind: Kind) -> None:
        if kind is Kind.TERMINAL:
            self.open_terminal()
        elif kind is Kind.BROWSER:
            self.open_page("")

    def _close_group(self, kind: Kind) -> None:
        for tab in list(self._open(kind)):
            self.close(tab)

    def _chosen(self, kind: Kind, view: Adw.TabView) -> None:
        """A tab chosen on screen is the group's selected one, and current."""
        self._focus = kind
        page = view.get_selected_page()
        tab = next((t for t, p in self._pages.items() if p is page), None)
        if tab is not None:
            self.panels.open(tab)

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
        ended = getattr(self._contents.pop(tab, None), "close", None)
        if callable(ended):
            ended()
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
        self._tiles.append(self._side_by_side(shown) if shown else self._start)

    def _start_page(self) -> Gtk.Widget:
        """With nothing open: what can be, and two ways to start."""
        start = Adw.StatusPage(icon_name="view-dual-symbolic",
                               title="Nothing open yet",
                               description="Files, changes, terminals and pages open "
                               "here, from the toolbar or as Osiris works.",
                               vexpand=True, hexpand=True)
        start.add_css_class("compact")
        start.add_css_class("harness-canvas-start")
        start.add_css_class("harness-canvas-group")
        ways = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        for label, act in (("Open a terminal", self.open_terminal),
                           ("Open a page", lambda: self.open_page(""))):
            button = Gtk.Button(label=label)
            button.add_css_class("pill")
            button.connect("clicked", lambda _b, a=act: a())
            ways.append(button)
        start.set_child(ways)
        return start

    def _side_by_side(self, shown: list[Gtk.Widget]) -> Gtk.Widget:
        if len(shown) == 1:
            return shown[0]
        stack = shown[-1]
        for left, widget in enumerate(reversed(shown[1:-1]), start=2):
            # Each takes its share of the column: a half, then a third...
            stack = self._paned(Gtk.Orientation.VERTICAL, widget, stack, 1 / (left))
        return self._paned(Gtk.Orientation.HORIZONTAL, shown[0], stack, 1 / 2)

    def _paned(self, orientation: Gtk.Orientation, start: Gtk.Widget,
               end: Gtk.Widget, share: float) -> Gtk.Paned:
        """Two panels split at ``share`` of the room, once it is known; the
        person's own dragging is left alone after."""
        paned = Gtk.Paned(orientation=orientation, start_child=start, end_child=end,
                          wide_handle=False, hexpand=True, vexpand=True)

        def sized(_paned, _spec) -> None:
            room = paned.get_property("max-position")
            if room > 0:
                paned.set_position(round(room * share))
                paned.disconnect(handler)

        handler = paned.connect("notify::max-position", sized)
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
            path = Path(change.path)
            line.append(_file_icon(path.name))
            line.append(Gtk.Label(label=path.name, xalign=0))
            folder = Gtk.Label(label=str(path.parent) if path.parent != Path() else "",
                               xalign=0, hexpand=True,
                               ellipsize=Pango.EllipsizeMode.START)
            folder.add_css_class("harness-meta")
            line.append(folder)
            for text, kind in ((f"+{change.additions}", "harness-count-added"),
                               (f"−{change.deletions}", "harness-count-removed")):
                count = Gtk.Label(label=text)
                count.add_css_class(kind)
                line.append(count)
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

    def restyle(self, scheme: GtkSource.StyleScheme | None,
                theme: Mapping[str, Any] | None = None) -> None:
        self._scheme = scheme
        for view in self._sources.values():
            view.get_buffer().set_style_scheme(scheme)
        for content in self._contents.values():
            follow = getattr(content, "restyle", None)
            if theme is not None and callable(follow):
                follow(theme)

    def _code_page(self, program: Program,
                   relative: Path) -> tuple[Gtk.Widget, GtkSource.View]:
        buffer = GtkSource.Buffer(
            language=GtkSource.LanguageManager.get_default().guess_language(
                relative.name, None))
        if self._scheme is not None:
            buffer.set_style_scheme(self._scheme)
        buffer.set_text(self._read(program.source / relative))
        view = GtkSource.View(buffer=buffer, editable=False, cursor_visible=False,
                              monospace=True, show_line_numbers=True, left_margin=16,
                              right_margin=16, top_margin=16, bottom_margin=16,
                              pixels_below_lines=3, wrap_mode=Gtk.WrapMode.WORD_CHAR)
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


#: The icon on each kind of tab but code, whose files show their own.
_TAB_ICONS = {
    Kind.CHANGES: "osiris-changes-symbolic",
    Kind.TERMINAL: "utilities-terminal-symbolic",
    Kind.BROWSER: "web-browser-symbolic",
}

#: The group headers that open another tab of their kind: icon and tooltip.
_NEW = {
    Kind.TERMINAL: ("list-add-symbolic", "New terminal"),
    Kind.BROWSER: ("list-add-symbolic", "New page"),
}


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
