"""A page in the Canvas's browser group (#197): an address line over
WebKitGTK, for the person's research and for following Thoth's sources."""

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
from gi.repository import Adw, Gtk, WebKit  # noqa: E402

from osiris.harness.web import address  # noqa: E402


class Page(Gtk.Box):
    def __init__(self, at: str = "", on_title: Callable[[str], None] = lambda _t: None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("harness-page")
        self.view = WebKit.WebView(vexpand=True, hexpand=True)
        self._entry = Gtk.Entry(hexpand=True, placeholder_text="Search or enter an address",
                                input_purpose=Gtk.InputPurpose.URL)
        self._entry.connect("activate", lambda e: self.load(address(e.get_text())))
        bar = Gtk.Box(spacing=4)
        bar.add_css_class("harness-path")
        for icon, tip, act in (("go-previous-symbolic", "Back", self.view.go_back),
                               ("go-next-symbolic", "Forward", self.view.go_forward),
                               ("view-refresh-symbolic", "Reload", self.view.reload)):
            button = Gtk.Button(icon_name=icon, tooltip_text=tip)
            button.add_css_class("flat")
            button.connect("clicked", lambda _b, a=act: a())
            bar.append(button)
        bar.append(self._entry)
        start = Adw.StatusPage(icon_name="web-browser-symbolic",
                               title="Search or enter an address",
                               description="Pages Osiris reads while it answers open "
                               "here too.")
        start.add_css_class("compact")
        self.stack = Gtk.Stack(vexpand=True,
                               transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(start, "start")
        self.stack.add_named(self.view, "web")
        self.append(bar)
        self.append(self.stack)
        self.view.connect("notify::title", lambda v, _p: on_title(v.get_title() or ""))
        self.view.connect("notify::uri", lambda v, _p: self._entry.set_text(
            v.get_uri() or ""))
        if at:
            self.load(at)

    def load(self, at: str) -> None:
        self.stack.set_visible_child_name("web")
        self.view.load_uri(at)
