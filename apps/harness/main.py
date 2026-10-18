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
from gi.repository import Adw, Gdk, GdkX11, Gio, GLib, Gtk, Pango  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for candidate in ("/usr/share/osiris/lib", REPO):
    if os.path.isdir(os.path.join(candidate, "osiris")):
        sys.path.insert(0, candidate)
        break

from osiris.harness.conversation import Conversation, State, Turn  # noqa: E402
from osiris.harness.harness import Harness  # noqa: E402
from osiris.harness.log import LOG_FILE, HarnessLog  # noqa: E402
from osiris.harness.opencode import OpencodeEngine, locate  # noqa: E402
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

DRAWER_BUS = "dev.osiris.HarnessDrawer"
DRAWER_PATH = "/dev/osiris/HarnessDrawer"

CSS = b"""
.harness-question {
    background: alpha(@accent_bg_color, 0.18);
    border-radius: 10px;
    padding: 6px 10px;
}
.harness-small { font-size: smaller; }
"""


class Drawer(Gtk.ApplicationWindow):
    def __init__(self, app: "Application"):
        super().__init__(application=app, title="Harness", decorated=False)
        self.app = app
        self.set_default_size(WIDTH, 800)
        self.connect("realize", self._realize)

        self.header = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        self.header.add_css_class("dim-label")
        self.header.add_css_class("harness-small")

        self.turns = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14,
                             valign=Gtk.Align.END, vexpand=True)
        self.scroller = Gtk.ScrolledWindow(
            child=self.turns, vexpand=True,
            hscrollbar_policy=Gtk.PolicyType.NEVER)

        self.entry = Gtk.Entry(placeholder_text="Ask Osiris", hexpand=True)
        self.entry.connect("activate", self._ask)
        self.stop_button = Gtk.Button(icon_name="media-playback-stop-symbolic",
                                      tooltip_text="Stop", visible=False)
        self.stop_button.add_css_class("flat")
        self.stop_button.connect("clicked", lambda _b: app.stop())
        line = Gtk.Box(spacing=8)
        line.append(self.entry)
        line.append(self.stop_button)

        self.footer = Gtk.Label(xalign=0, wrap=True)
        self.footer.add_css_class("dim-label")
        self.footer.add_css_class("harness-small")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                      margin_top=12, margin_bottom=12,
                      margin_start=14, margin_end=14)
        box.append(self.header)
        box.append(Gtk.Separator())
        box.append(self.scroller)
        box.append(line)
        box.append(self.footer)
        self.set_child(box)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._key)
        self.add_controller(keys)
        self.connect("close-request", self._close_request)

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

    def summon(self) -> None:
        self.present()
        self.entry.grab_focus()

    def refresh(self) -> None:
        conversation = self.app.conversation
        child = self.turns.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            self.turns.remove(child)
            child = following
        for turn in conversation.turns:
            self.turns.append(self._turn(turn))
        self.stop_button.set_visible(conversation.busy)
        self.entry.set_sensitive(not conversation.busy)
        self.header.set_text(self.app.header_line())
        self.footer.set_text(self.app.footer_line())
        # Follow the answer as it streams.
        adjustment = self.scroller.get_vadjustment()
        GLib.idle_add(lambda: adjustment.set_value(adjustment.get_upper()))
        if not conversation.busy:
            self.entry.grab_focus()

    @staticmethod
    def _turn(turn: Turn) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        question = Gtk.Label(label=turn.question, xalign=0, wrap=True,
                             selectable=True, halign=Gtk.Align.END)
        question.add_css_class("harness-question")
        box.append(question)
        answer = turn.answer or ("..." if turn.state is State.WAITING else "")
        if answer:
            box.append(Gtk.Label(label=answer, xalign=0, wrap=True,
                                 selectable=True))
        for refused in turn.refused:
            note = Gtk.Label(label=f"Not allowed yet: {refused}", xalign=0,
                             wrap=True)
            note.add_css_class("dim-label")
            note.add_css_class("harness-small")
            box.append(note)
        if turn.state is State.FAILED:
            error = Gtk.Label(label=turn.error or "The answer failed.",
                              xalign=0, wrap=True, selectable=True)
            error.add_css_class("error")
            box.append(error)
        if turn.state is State.STOPPED:
            stopped = Gtk.Label(label="Stopped.", xalign=0)
            stopped.add_css_class("dim-label")
            box.append(stopped)
        return box


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.drawer: Drawer | None = None
        self.conversation = Conversation()
        self.harness: Harness | None = None
        self.problem = "Starting the Engine..."
        self.open = False
        show = Gio.SimpleAction.new("show", None)
        show.connect("activate", lambda *_: self.toggle())
        self.add_action(show)

    def do_startup(self):
        Adw.Application.do_startup(self)
        # Resident: closing keeps the conversation and the Engine connection.
        self.hold()
        display = Gdk.Display.get_default()
        if display is not None:
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS)
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
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
        Gio.DBus.session.call(
            DRAWER_BUS, DRAWER_PATH, DRAWER_BUS, "Close", None, None,
            Gio.DBusCallFlags.NONE, 1000, None, self._closed)

    def _closed(self, connection, result) -> None:
        try:
            connection.call_finish(result)
        except GLib.Error:
            self.drawer.minimize()

    def header_line(self) -> str:
        model = self.conversation.model
        named = f"{model.provider} / {model.model}" if model else "default model"
        return f"{named}  ·  {self.conversation.tokens_spent:,} tokens"

    def footer_line(self) -> str:
        if self.harness is None:
            return self.problem
        return "allowance not reported  ·  only talks for now"

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
                self.harness = Harness(engine, HarnessLog(files, me.home / LOG_FILE))
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


if __name__ == "__main__":
    sys.exit(Application().run(sys.argv))
