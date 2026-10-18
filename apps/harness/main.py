#!/usr/bin/env python3
"""Osiris Harness - a drawer on the right edge, opened with Super+A.

The conversation fills the drawer with the newest at the bottom, and the line
to ask in sits below it, as in any chat. The model in play and the tokens
spent are always on show. Escape, Super+A or the panel button close it and
keep the conversation.

Placement and the slide belong to the harness-drawer@osiris Cinnamon
extension: GTK4 on X11 gives an application no way to place its own window.
Without the extension the drawer still works, wherever Muffin puts it.

The app stays resident, like the theme switcher: started at login or by D-Bus
with --gapplication-service, and Super+A runs
`gapplication action dev.osiris.Harness show`.

The conversation logic lives in osiris/harness, where it is tested; this file
only draws it. The Engine's events arrive on a thread and are handed to the
main loop one at a time.
"""
import os
import sys
import threading
import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkX11", "4.0")
gi.require_version("Graphene", "1.0")
from gi.repository import Adw, Gdk, GdkX11, Gio, GLib, Graphene, Gtk, Pango  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for candidate in ("/usr/share/osiris/lib", REPO):
    if os.path.isdir(os.path.join(candidate, "osiris")):
        sys.path.insert(0, candidate)
        break
# render.py and look.py sit beside this file.
sys.path.insert(0, HERE)

from look import Look  # noqa: E402
from providers import ProvidersPage  # noqa: E402
from render import TurnView  # noqa: E402

from osiris.harness.conversation import Conversation, State  # noqa: E402
from osiris.harness.harness import Harness  # noqa: E402
from osiris.harness.log import LOG_FILE, HarnessLog  # noqa: E402
from osiris.harness.engine import ModelRef  # noqa: E402
from osiris.harness.opencode import OpencodeAccounts, OpencodeEngine, locate  # noqa: E402
from osiris.harness.settings import Models, load_models, save_models  # noqa: E402
from osiris.platform import (  # noqa: E402
    HttpError,
    RealFileSystem,
    SubprocessRunner,
    SystemIdentity,
    UrllibClient,
)

APP_ID = "dev.osiris.Harness"
# Matches WIDTH in harness-drawer@osiris, which sizes the window to the
# monitor's full height.
WIDTH = 440
RECONNECT_SECONDS = 3
#: The widest the conversation grows, in pixels, however wide the drawer.
READABLE = 820

DRAWER_BUS = "dev.osiris.HarnessDrawer"
DRAWER_PATH = "/dev/osiris/HarnessDrawer"

class Drawer(Gtk.ApplicationWindow):
    def __init__(self, app: "Application"):
        super().__init__(application=app, title="Harness", decorated=False)
        self.app = app
        self.add_css_class("harness-drawer")
        self.set_default_size(WIDTH, 800)
        self.connect("realize", self._realize)

        title = Gtk.Label(label="Harness", xalign=0, hexpand=True)
        title.add_css_class("harness-title")
        self.meta = Gtk.Label(xalign=1, ellipsize=Pango.EllipsizeMode.START)
        self.meta.add_css_class("harness-meta")
        # The model in play doubles as the way to change it.
        providers_button = Gtk.Button(child=self.meta, tooltip_text="Providers and models")
        providers_button.add_css_class("flat")
        providers_button.connect("clicked", lambda _b: self.show_providers())
        # Deep agentic work wants the whole screen; the drawer comes back after.
        self.expanded = False
        self.expand_button = Gtk.Button(icon_name="view-fullscreen-symbolic",
                                        tooltip_text="Expand")
        self.expand_button.add_css_class("flat")
        self.expand_button.connect("clicked", self._toggle_expanded)
        header = Gtk.Box(spacing=8)
        header.add_css_class("harness-header")
        header.append(Gtk.Image(icon_name="osiris-symbolic"))
        header.append(title)
        header.append(providers_button)
        header.append(self.expand_button)

        self.turns = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                             valign=Gtk.Align.END, vexpand=True,
                             margin_top=12, margin_bottom=12)
        self.views: list[TurnView] = []
        # Expanded to the whole screen, lines stay a readable length.
        self.scroller = Gtk.ScrolledWindow(
            child=Adw.Clamp(maximum_size=READABLE, child=self.turns), vexpand=True,
            hscrollbar_policy=Gtk.PolicyType.NEVER)

        self.entry = Gtk.Entry(placeholder_text="Ask Osiris", hexpand=True)
        self.entry.add_css_class("harness-input")
        self.entry.connect("activate", self._ask)
        self.send = Gtk.Button(icon_name="go-up-symbolic", tooltip_text="Ask",
                               valign=Gtk.Align.CENTER)
        self.send.add_css_class("harness-send")
        self.send.connect("clicked", self._send_or_stop)
        composer = Gtk.Box(spacing=6)
        composer.add_css_class("harness-composer")
        composer.append(self.entry)
        composer.append(self.send)

        self.footer = Gtk.Label(xalign=0, wrap=True)
        self.footer.add_css_class("harness-meta")
        self.footer.add_css_class("harness-footer")

        bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bottom.append(composer)
        bottom.append(self.footer)
        chat = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        chat.append(self.scroller)
        chat.append(Adw.Clamp(maximum_size=READABLE, child=bottom))
        self.pages = Gtk.Stack(vexpand=True,
                               transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.pages.add_named(chat, "chat")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(header)
        box.append(self.pages)
        # The Skin shapes this surface; the window around it stays transparent,
        # and children are clipped to the surface's rounded corners.
        surface = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                          overflow=Gtk.Overflow.HIDDEN)
        surface.add_css_class("harness-surface")
        box.set_vexpand(True)
        surface.append(box)
        surface.set_hexpand(True)
        # The drawer is anchored to the right edge, so its left edge resizes
        # it; the window manager does the dragging.
        self.resize_handle = Gtk.Box(width_request=8,
                                     cursor=Gdk.Cursor.new_from_name("ew-resize"))
        drag = Gtk.GestureClick()
        drag.connect("pressed", self._begin_resize)
        self.resize_handle.add_controller(drag)
        frame = Gtk.Box()
        frame.append(self.resize_handle)
        frame.append(surface)
        self.set_child(frame)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._key)
        self.add_controller(keys)
        self.connect("close-request", self._close_request)

    def _begin_resize(self, gesture, _presses, x, y) -> None:
        surface = self.get_surface()
        if surface is None:
            return
        found, point = self.resize_handle.compute_point(
            self, Graphene.Point().init(x, y))
        if not found:
            return
        surface.begin_resize(Gdk.SurfaceEdge.WEST, gesture.get_current_event_device(),
                             gesture.get_current_button(), point.x, point.y,
                             gesture.get_current_event_time())

    def _toggle_expanded(self, _button) -> None:
        self.expanded = not self.expanded
        if self.expanded:
            self.maximize()
        else:
            self.unmaximize()
        self.expand_button.set_icon_name(
            "view-restore-symbolic" if self.expanded else "view-fullscreen-symbolic")
        self.expand_button.set_tooltip_text("Back to the drawer" if self.expanded
                                            else "Expand")

    def _realize(self, _window) -> None:
        # Kept out of the dock and the window switcher: it is reached from
        # Super+A and the panel button, and an entry for it in Plank would
        # read as a second, separate application.
        surface = self.get_surface()
        if isinstance(surface, GdkX11.X11Surface):
            surface.set_skip_taskbar_hint(True)
            surface.set_skip_pager_hint(True)

    def _key(self, _controller, keyval, _code, _state) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.app.close_drawer()
            return True
        return False

    def _close_request(self, _window) -> bool:
        self.app.close_drawer()
        return True

    def _ask(self, _entry) -> None:
        text = self.entry.get_text().strip()
        if text and not self.app.conversation.busy:
            self.entry.set_text("")
            self.app.ask(text)

    def _send_or_stop(self, _button) -> None:
        if self.app.conversation.busy:
            self.app.stop()
        else:
            self._ask(self.entry)

    def show_providers(self) -> None:
        if self.app.accounts is None:
            return
        old = self.pages.get_child_by_name("providers")
        if old is not None:
            self.pages.remove(old)
        # A button takes an icon or a label, not both; ButtonContent holds both.
        back = Gtk.Button(child=Adw.ButtonContent(icon_name="go-previous-symbolic",
                                                  label="Back"),
                          halign=Gtk.Align.START)
        back.add_css_class("flat")
        back.connect("clicked", lambda _b: self.pages.set_visible_child_name("chat"))
        page = ProvidersPage(
            self.app.accounts,
            background=self.app.background,
            open_page=self.app.open_page,
            later=lambda seconds, then: GLib.timeout_add_seconds(
                seconds, lambda: then() or False),
            default=self.app.models.default,
            on_model_chosen=self.app.choose_model,
        )
        holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                         margin_start=16, margin_end=16, margin_top=8)
        holder.append(back)
        holder.append(page)
        self.pages.add_named(Gtk.ScrolledWindow(child=holder, vexpand=True), "providers")
        self.pages.set_visible_child_name("providers")

    def summon(self) -> None:
        self.present()
        self.entry.grab_focus()

    def refresh(self, restyle: bool = False) -> None:
        conversation, look = self.app.conversation, self.app.look
        fresh = len(self.views)
        while len(self.views) < len(conversation.turns):
            view = TurnView(conversation.turns[len(self.views)])
            self.views.append(view)
            self.turns.append(view)
        newest = len(self.views) - 1
        for index, (view, turn) in enumerate(zip(self.views, conversation.turns)):
            if restyle:
                view.restyle(turn, look.style, look.scheme)
            elif index >= min(fresh, newest):
                # Turns added just now are drawn once; after that only the
                # newest can still be changing.
                view.update(turn, look.style, look.scheme)
        busy = conversation.busy
        self.send.set_icon_name("media-playback-stop-symbolic" if busy
                                else "go-up-symbolic")
        self.send.set_tooltip_text("Stop" if busy else "Ask")
        self.meta.set_text(self.app.header_line())
        self.footer.set_text(self.app.footer_line())
        self._follow()

    def _follow(self) -> None:
        """Keep the newest text in view, unless the reader has scrolled up."""
        adjustment = self.scroller.get_vadjustment()
        near_bottom = (adjustment.get_upper() - adjustment.get_page_size()
                       - adjustment.get_value()) < 80
        if near_bottom:
            GLib.idle_add(lambda: adjustment.set_value(adjustment.get_upper()))


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.drawer: Drawer | None = None
        self.conversation = Conversation()
        self.harness: Harness | None = None
        self.look: Look | None = None
        self.accounts: OpencodeAccounts | None = None
        self.files = RealFileSystem()
        self.home = SystemIdentity().home
        self.models: Models = load_models(self.files, self.home)
        self.problem = "Starting the Engine..."
        self.open = False
        show = Gio.SimpleAction.new("show", None)
        show.connect("activate", lambda *_: self.toggle())
        self.add_action(show)

    def do_startup(self):
        Adw.Application.do_startup(self)
        # Resident: closing keeps the conversation and the Engine connection.
        self.hold()
        self.look = Look(SystemIdentity().home, self._restyle)
        self.drawer = Drawer(self)
        self.drawer.refresh()
        threading.Thread(target=self._listen, daemon=True).start()

    def do_activate(self):
        self.toggle()

    def toggle(self) -> None:
        if self.drawer is None:
            return
        if self.open:
            self.close_drawer()
        else:
            self.open = True
            self.drawer.summon()

    def close_drawer(self) -> None:
        """Ask the extension to slide the drawer away; minimise if it cannot."""
        self.open = False
        connection = self.get_dbus_connection()
        if connection is None:
            self.drawer.minimize()
            return
        connection.call(
            DRAWER_BUS, DRAWER_PATH, DRAWER_BUS, "Close", None, None,
            Gio.DBusCallFlags.NONE, 1000, None, self._closed)

    def _closed(self, connection, result) -> None:
        try:
            connection.call_finish(result)
        except GLib.Error:
            self.drawer.minimize()

    def header_line(self) -> str:
        named = self.conversation.model_label(self.models.default)
        return f"{named}  ·  {self.conversation.tokens_spent:,} tokens"

    def footer_line(self) -> str:
        if self.harness is None:
            return self.problem
        return "allowance not reported  ·  only talks for now"

    def background(self, work, done) -> None:
        """Run work off the main loop and hand its result back to it."""
        def run():
            try:
                result = work()
            except Exception as error:  # noqa: BLE001 - shown in the drawer
                self.problem = str(error)
                GLib.idle_add(self._refresh)
                return
            GLib.idle_add(lambda: done(result) or False)
        threading.Thread(target=run, daemon=True).start()

    def open_page(self, url: str) -> None:
        Gtk.UriLauncher.new(url).launch(self.drawer, None, None, None)

    def choose_model(self, model: ModelRef) -> None:
        self.models = Models(default=model, fallback=self.models.fallback)
        save_models(self.files, self.home, self.models)
        if self.harness is not None:
            self.background(lambda: self.harness.use_model(model), lambda _r: None)

    def ask(self, text: str) -> None:
        if self.harness is None:
            return
        self.conversation.asked(text)
        self.drawer.refresh()
        threading.Thread(target=self._send, args=(text,), daemon=True).start()

    def stop(self) -> None:
        if self.harness is not None:
            threading.Thread(target=self.harness.stop, daemon=True).start()

    def _send(self, text: str) -> None:
        try:
            self.harness.ask(text)
        except HttpError as error:
            GLib.idle_add(self._failed_to_send, str(error))

    def _failed_to_send(self, message: str) -> bool:
        if self.conversation.turns:
            turn = self.conversation.turns[-1]
            turn.state, turn.error = State.FAILED, message
        self.drawer.refresh()
        return False

    def _listen(self) -> None:
        """Connect to the Engine and pass its events to the main loop, for good.

        The service can restart underneath us; the stream then ends or errors,
        and the Engine is found again.
        """
        files, me = RealFileSystem(), SystemIdentity()
        while True:
            try:
                service = locate(files, me, SubprocessRunner(sink=lambda _l: None))
                engine = OpencodeEngine(UrllibClient(), service)
                # A restarted service has a new password, so the Harness is
                # rebuilt around the new connection; the next question opens
                # a new session.
                self.harness = Harness(engine, HarnessLog(files, me.home / LOG_FILE),
                                       self.models.default)
                self.accounts = OpencodeAccounts(UrllibClient(), service)
                GLib.idle_add(self._refresh)
                for event in engine.events():
                    handled = self.harness.handle(event)
                    if handled is not None:
                        GLib.idle_add(self._apply, handled)
            except Exception as error:  # noqa: BLE001 - shown, then retried
                self.problem = f"The Engine is not reachable: {error}"
                GLib.idle_add(self._refresh)
            time.sleep(RECONNECT_SECONDS)

    def _apply(self, event) -> bool:
        self.conversation.apply(event)
        self.drawer.refresh()
        return False

    def _refresh(self) -> bool:
        self.drawer.refresh()
        return False

    def _restyle(self) -> None:
        if self.drawer is not None:
            self.drawer.refresh(restyle=True)


if __name__ == "__main__":
    sys.exit(Application().run(sys.argv))
