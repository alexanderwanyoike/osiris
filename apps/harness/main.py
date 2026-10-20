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
from dataclasses import dataclass
from pathlib import Path
import sys
import threading
import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkX11", "4.0")
gi.require_version("Graphene", "1.0")
from gi.repository import Adw, Gdk, GdkX11, Gio, GLib, GObject, Graphene, Gtk, Pango  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for candidate in ("/usr/share/osiris/lib", REPO):
    if os.path.isdir(os.path.join(candidate, "osiris")):
        sys.path.insert(0, candidate)
        break
# render.py and look.py sit beside this file.
sys.path.insert(0, HERE)

from admin_card import AdminCard  # noqa: E402
from look import Look  # noqa: E402
from providers import ProvidersPage  # noqa: E402
from canvas import Canvas, open_in_code  # noqa: E402
from program_card import ProgramCard  # noqa: E402
from render import TurnView  # noqa: E402
from sidebar import Sidebar  # noqa: E402
from theme_store import EngineStore, user_wallpapers  # noqa: E402

from osiris.apps.tool_server import NAME as TOOLS, TIERS, undo  # noqa: E402

from osiris.harness import admin  # noqa: E402
from osiris.harness.conversation import Conversation, State, Turn  # noqa: E402
from osiris.harness.harness import Harness  # noqa: E402
from osiris.harness.history import (  # noqa: E402
    CODE_DIR,
    group,
    misplaced,
    project_program,
)
from osiris.harness.log import LOG_FILE, HarnessLog  # noqa: E402
from osiris.harness.engine import Failed, Finished, ModelRef, Stopped  # noqa: E402
from osiris.harness.opencode import OpencodeAccounts, OpencodeEngine, locate  # noqa: E402
from osiris.harness.settings import Models, load_models, save_models  # noqa: E402
from osiris.harness.trust import allow_everything, allows_everything  # noqa: E402
from osiris.programs.programs import Programs  # noqa: E402
from osiris.provision.upgrade import Upgrade  # noqa: E402
from osiris.platform import (  # noqa: E402
    HttpError,
    ProcFs,
    RealFileSystem,
    SubprocessRunner,
    SystemIdentity,
    UrllibClient,
)

APP_ID = "dev.osiris.Harness"
#: Seconds between looks at whether Osiris was upgraded under the Harness.
UPGRADE_POLL = 10
# Matches WIDTH in harness-drawer@osiris, which sizes the window to the
# monitor's full height.
WIDTH = 440
RECONNECT_SECONDS = 3
#: The widest the conversation grows, in pixels, however wide the drawer.
READABLE = 820
#: Narrower than this the drawer is Compact: the sidebar folds away behind its
#: toggle (CONTEXT.md, docs/HARNESS-LAYOUT.md).
COMPACT_BELOW = "max-width: 760sp"
#: Narrower than this there is no room for the Canvas; the cards under each
#: answer carry the same things.
NO_CANVAS_BELOW = "max-width: 1100sp"
#: The top bar's title before the first question.
UNTITLED = "New conversation"

#: Run by the Engine for every session; it acts through the theme engine.
TOOL_SERVER = os.path.join(HERE, "tool_server.py")

DRAWER_BUS = "dev.osiris.HarnessDrawer"
DRAWER_PATH = "/dev/osiris/HarnessDrawer"


@dataclass
class AdminPending:
    """An admin password request waiting on the person: the D-Bus call to
    answer, what it asks, its card and the timer that lets it lapse."""
    invocation: Gio.DBusMethodInvocation
    request: admin.Request
    card: AdminCard
    lapse: int


class Drawer(Gtk.ApplicationWindow):
    def __init__(self, app: "Application"):
        super().__init__(application=app, title="Osiris", decorated=False)
        self.app = app
        self.add_css_class("harness-drawer")
        self.set_default_size(WIDTH, 800)
        self.connect("realize", self._realize)

        self.sidebar_toggle = Gtk.ToggleButton(icon_name="sidebar-show-symbolic",
                                               tooltip_text="Conversations")
        self.sidebar_toggle.add_css_class("flat")
        new = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="New conversation")
        new.add_css_class("flat")
        new.connect("clicked", lambda _b: self.app.new_conversation())
        self.title = Gtk.Label(label=UNTITLED, xalign=0, hexpand=True,
                               ellipsize=Pango.EllipsizeMode.END)
        self.title.add_css_class("harness-title")
        providers_button = Gtk.Button(icon_name="open-menu-symbolic",
                                      tooltip_text="Providers and accounts")
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
        header.append(self.sidebar_toggle)
        header.append(new)
        header.append(self.title)
        self.canvas_toggle = Gtk.ToggleButton(icon_name="sidebar-show-right-symbolic",
                                              tooltip_text="Canvas", sensitive=False)
        self.canvas_toggle.add_css_class("flat")
        self.canvas_toggle.connect("toggled", self._canvas_toggled)
        header.append(self.canvas_toggle)
        header.append(self.expand_button)
        header.append(providers_button)

        self.turns = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                             valign=Gtk.Align.END, vexpand=True,
                             margin_top=12, margin_bottom=12)
        self.views: list[TurnView] = []
        # Expanded to the whole screen, lines stay a readable length.
        self.scroller = Gtk.ScrolledWindow(
            child=Adw.Clamp(maximum_size=READABLE, child=self.turns), vexpand=True,
            hscrollbar_policy=Gtk.PolicyType.NEVER)

        self.entry = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, accepts_tab=False,
                                  hexpand=True, top_margin=6, bottom_margin=6)
        self.entry.add_css_class("harness-input")
        placeholder = Gtk.Label(label="Ask Osiris", xalign=0, valign=Gtk.Align.START,
                                margin_top=6, can_target=False)
        placeholder.add_css_class("harness-meta")
        self.entry.get_buffer().connect(
            "changed", lambda b: placeholder.set_visible(b.get_char_count() == 0))
        enter = Gtk.EventControllerKey()
        enter.connect("key-pressed", self._composer_key)
        self.entry.add_controller(enter)
        typed = Gtk.Overlay(child=self.entry)
        typed.add_overlay(placeholder)

        self.model_label = Gtk.Label(ellipsize=Pango.EllipsizeMode.START)
        self.model_label.add_css_class("harness-meta")
        self.models = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.models.add_css_class("navigation-sidebar")
        self.models.connect("row-activated", self._model_chosen)
        model_face = Gtk.Box(spacing=4)
        model_face.append(Gtk.Image(icon_name="pan-down-symbolic"))
        model_face.append(self.model_label)
        self.model_menu = Gtk.MenuButton(
            child=model_face, tooltip_text="Model",
            popover=Gtk.Popover(child=self.models))
        self.model_menu.add_css_class("flat")
        self.model_menu.connect("notify::active", self._models_shown)
        self.send = Gtk.Button(icon_name="go-up-symbolic", tooltip_text="Ask",
                               valign=Gtk.Align.CENTER)
        self.send.add_css_class("harness-send")
        self.send.connect("clicked", self._send_or_stop)
        controls = Gtk.Box(spacing=6)
        controls.append(Gtk.Box(hexpand=True))
        controls.append(self.model_menu)
        controls.append(self.send)
        composer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        composer.add_css_class("harness-composer")
        composer.append(typed)
        composer.append(controls)

        self.footer = Gtk.Label(xalign=0, wrap=True)
        self.footer.add_css_class("harness-meta")
        self.footer.add_css_class("harness-footer")

        bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bottom.append(composer)
        bottom.append(self.footer)
        chat = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        chat.append(self.scroller)
        chat.append(Adw.Clamp(maximum_size=READABLE, child=bottom))
        self.canvas = Canvas(read=lambda path: path.read_text(errors="replace"),
                             open_in_code=open_in_code,
                             scheme=app.look.scheme if app.look is not None else None)
        self.canvas.set_visible(False)
        body = Gtk.Paned(start_child=chat, end_child=self.canvas,
                         shrink_start_child=False, resize_end_child=True,
                         wide_handle=False, position=480)
        self.pages = Gtk.Stack(vexpand=True,
                               transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.pages.add_named(body, "chat")
        self.sidebar = Sidebar(
            on_open=lambda session: self._chosen(self.app.open_past, session),
            on_new=lambda: self._chosen(self.app.new_conversation),
            on_new_in=lambda folder: self._chosen(self.app.new_conversation, folder),
            on_archive=lambda session: self.app.archive(session),
            on_delete=lambda session, title: self.app.ask_to_delete(session, title))
        self.split = Adw.OverlaySplitView(sidebar=self.sidebar, content=self.pages,
                                          min_sidebar_width=220,
                                          max_sidebar_width=280, vexpand=True)
        self.sidebar_toggle.bind_property(
            "active", self.split, "show-sidebar",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        self.sidebar_toggle.set_active(True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(header)
        box.append(self.split)
        layout = Adw.BreakpointBin(child=box, width_request=320, height_request=360)
        # Of the breakpoints that match, libadwaita applies only the last added,
        # so the narrower one comes last and repeats the wider one's setters.
        no_canvas = Adw.Breakpoint.new(Adw.BreakpointCondition.parse(NO_CANVAS_BELOW))
        compact = Adw.Breakpoint.new(Adw.BreakpointCondition.parse(COMPACT_BELOW))
        for breakpoint in (no_canvas, compact):
            breakpoint.add_setter(self.canvas_toggle, "visible", False)
            breakpoint.add_setter(self.canvas, "visible", False)
        compact.add_setter(self.split, "collapsed", True)
        compact.add_setter(self.sidebar_toggle, "active", False)
        layout.add_breakpoint(no_canvas)
        layout.add_breakpoint(compact)
        # The Skin shapes this surface; the window around it stays transparent,
        # and children are clipped to the surface's rounded corners.
        surface = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                          overflow=Gtk.Overflow.HIDDEN)
        surface.add_css_class("harness-surface")
        layout.set_vexpand(True)
        surface.append(layout)
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
        self.app.expand(self.expanded)
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

    def _ask(self) -> None:
        buffer = self.entry.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        if text.strip() and not self.app.conversation.busy:
            buffer.set_text("")
            self.app.ask(text.strip())

    def _composer_key(self, _controller, keyval, _code, state) -> bool:
        # Enter asks; Shift+Enter starts a new line.
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and not (
                state & Gdk.ModifierType.SHIFT_MASK):
            self._ask()
            return True
        return False

    def _send_or_stop(self, _button) -> None:
        if self.app.conversation.busy:
            self.app.stop()
        else:
            self._ask()

    def _models_shown(self, button, _spec) -> None:
        if not button.get_active():
            return
        while (row := self.models.get_row_at_index(0)) is not None:
            self.models.remove(row)
        providers = Gtk.Label(label="Providers and accounts…", xalign=0)
        providers.model = None
        self.models.append(providers)
        if self.app.accounts is None:
            return
        accounts = self.app.accounts
        self.app.background(accounts.models, self._models_found)

    def _models_found(self, found) -> None:
        # Above "Providers and accounts…", in the Engine's order.
        for position, info in enumerate(found):
            label = Gtk.Label(label=info.name, xalign=0)
            label.model = info.ref
            self.models.insert(label, position)

    def _model_chosen(self, _list, row) -> None:
        chosen = row.get_child().model
        self.model_menu.popdown()
        if chosen is None:
            self.show_providers()
        else:
            self.app.choose_model(chosen)
        self.refresh()

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
            allows_everything=self.app.everything_allowed,
            on_allow_everything=self.app.set_allow_everything,
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

    def _chosen(self, act, *args) -> None:
        """Act on a choice in the sidebar; narrow, the list then folds away."""
        act(*args)
        if self.split.get_collapsed():
            self.sidebar_toggle.set_active(False)

    def show_canvas(self, programs) -> None:
        """What the Conversation made; the Canvas opens the first time there is
        something to show."""
        had = self.canvas_toggle.get_sensitive()
        self.canvas.show(programs)
        self.canvas_toggle.set_sensitive(bool(programs))
        if programs and not had:
            self.canvas_toggle.set_active(True)
        elif not programs:
            self.canvas_toggle.set_active(False)

    def _canvas_toggled(self, toggle) -> None:
        # As in the prototype: the Canvas takes the sidebar's room.
        shown = toggle.get_active()
        self.canvas.set_visible(shown)
        self.sidebar_toggle.set_active(not shown)

    def show_history(self, projects, loose) -> None:
        self.sidebar.show_history(projects, loose, getattr(self.app, "session", None),
                                  getattr(self.app, "running", frozenset()))

    def clear(self) -> None:
        for view in self.views:
            self.turns.remove(view)
        self.views = []

    def refresh(self, restyle: bool = False) -> None:
        conversation, look = self.app.conversation, self.app.look
        fresh = len(self.views)
        while len(self.views) < len(conversation.turns):
            view = TurnView(conversation.turns[len(self.views)],
                            on_undo=self.app.undo,
                            program_card=self.app.program_card,
                            admin_card=self.app.admin_card)
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
        self.title.set_text(conversation.title or UNTITLED)
        self.model_label.set_text(conversation.model_label(self.app.models.default))
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
        #: Conversations still being answered while another is on screen,
        #: by session.
        self.backgrounded: dict[str, Conversation] = {}
        self.harness: Harness | None = None
        self.log: HarnessLog | None = None
        #: The past Conversations the sidebar shows, newest first.
        self.pasts: list = []
        self.look: Look | None = None
        self.accounts: OpencodeAccounts | None = None
        self.files = RealFileSystem()
        self.home = SystemIdentity().home
        self.models: Models = load_models(self.files, self.home)
        self.problem = "Starting the Engine..."
        #: What each Program's card is waiting on, or what went wrong, by name.
        self.program_busy: dict[str, str] = {}
        self.program_problem: dict[str, str] = {}
        self.open = False
        self.upgrade = Upgrade(self.files)
        self.processes = ProcFs()
        self.uid = os.getuid()
        #: The Engine's process, which the agent's commands descend from.
        self.engine_pid: int | None = None
        #: Admin password requests waiting on the person, by session.
        self.admin_pending: dict[str, AdminPending] = {}
        self._admin_object = 0
        show = Gio.SimpleAction.new("show", None)
        show.connect("activate", lambda *_: self.toggle())
        self.add_action(show)

    def do_startup(self):
        Adw.Application.do_startup(self)
        # Resident: closing keeps the conversation and the Engine connection.
        self.hold()
        self.look = Look(SystemIdentity().home, self._restyle)
        # Before the Engine is started, which inherits it, so the agent's sudo
        # asks here.
        os.environ.update(admin.agent_environment(os.environ))
        self.drawer = Drawer(self)
        self.drawer.refresh()
        threading.Thread(target=self._listen, daemon=True).start()
        GLib.timeout_add_seconds(UPGRADE_POLL, self._restart_if_upgraded)

    def _restart_if_upgraded(self) -> bool:
        """Quit once Osiris is upgraded under it and nothing is under way;
        D-Bus starts the new code on the next Super+A."""
        in_use = (self.open or self.conversation.busy
                  or bool(self.backgrounded) or bool(self.program_busy))
        if not self.upgrade.restart_due(in_use=in_use):
            return GLib.SOURCE_CONTINUE
        self.quit()
        return GLib.SOURCE_REMOVE

    def do_activate(self):
        self.toggle()

    def do_dbus_register(self, connection, object_path):
        if not Adw.Application.do_dbus_register(self, connection, object_path):
            return False
        interface = Gio.DBusNodeInfo.new_for_xml(admin.INTERFACE_XML).interfaces[0]
        self._admin_object = connection.register_object(
            admin.OBJECT_PATH, interface, self._admin_call, None, None)
        return True

    def do_dbus_unregister(self, connection, object_path):
        if self._admin_object:
            connection.unregister_object(self._admin_object)
            self._admin_object = 0
        Adw.Application.do_dbus_unregister(self, connection, object_path)

    def _admin_call(self, connection, sender, _path, _interface, _method,
                    parameters, invocation) -> None:
        """The helper asks; who it is comes from the bus, never from what it
        says about itself."""
        command, _prompt = parameters.unpack()

        def identified(bus, result) -> None:
            try:
                (pid,) = bus.call_finish(result).unpack()
            except GLib.Error:
                invocation.return_dbus_error(admin.REFUSED, "the caller is unknown")
                return
            self.admin_asked(pid, command, invocation)

        connection.call(
            "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
            "GetConnectionUnixProcessID", GLib.Variant("(s)", (sender,)),
            GLib.VariantType("(u)"), Gio.DBusCallFlags.NONE, -1, None, identified)

    def admin_asked(self, caller: int, command, invocation) -> None:
        """Judge a request from the process ``caller``; show its card, or answer
        at once."""
        session = self.harness.running_sudo() if self.harness is not None else None
        verdict = admin.judge(self.processes, caller, command, uid=self.uid,
                              engine=self.engine_pid, session=session)
        if isinstance(verdict, admin.Refuse):
            invocation.return_dbus_error(admin.REFUSED, verdict.reason)
            return
        conversation = (self._conversation_of(verdict.session)
                        if isinstance(verdict, admin.Show) else None)
        if conversation is None:
            invocation.return_dbus_error(admin.NOT_THE_AGENTS,
                                         "not a command Osiris is running")
        elif verdict.session in self.admin_pending:
            invocation.return_value(GLib.Variant("(bs)", (False, "")))
        else:
            self._show_admin_card(verdict, conversation, invocation)

    def _show_admin_card(self, shown, conversation: Conversation, invocation) -> None:
        session, request = shown.session, shown.request
        card = AdminCard(request,
                         on_allow=lambda password: self.admin_answer(session, password),
                         on_deny=lambda: self.admin_answer(session, None))
        lapse = GLib.timeout_add_seconds(
            admin.HARNESS_GIVES_UP, lambda: self.admin_answer(session, None) or False)
        self.admin_pending[session] = AdminPending(invocation, request, card, lapse)
        conversation.needs_password(request)
        if session != self.session:
            self.open_past(session)
        if not self.open:
            self.toggle()
        self.drawer.refresh()
        card.entry.grab_focus()

    def admin_card(self, request: admin.Request) -> Gtk.Widget:
        """The card for a waiting request, the same one each time it is drawn,
        so what is typed in it survives a redraw."""
        for pending in self.admin_pending.values():
            if pending.request is request:
                return pending.card
        return Gtk.Box()

    def admin_answer(self, session: str, password: str | None) -> None:
        """Answer a waiting request once: with the password, or refused when
        it is None. The password goes to the helper and is not kept."""
        pending = self.admin_pending.pop(session, None)
        if pending is None:
            return
        GLib.source_remove(pending.lapse)
        pending.invocation.return_value(
            GLib.Variant("(bs)", (password is not None, password or "")))
        if self.harness is not None:
            self.harness.admin_answered(session, pending.request,
                                        approved=password is not None)
        conversation = self._conversation_of(session)
        if conversation is not None:
            conversation.password_answered()
        self.drawer.refresh()

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

    def expand(self, expanded: bool) -> None:
        """Ask the extension to fill the screen above the dock, or to restore
        the drawer; maximise instead if it is not there."""
        connection = self.get_dbus_connection()
        if connection is None:
            self._maximise(expanded)
            return
        connection.call(
            DRAWER_BUS, DRAWER_PATH, DRAWER_BUS, "Expand",
            GLib.Variant("(b)", (expanded,)), None, Gio.DBusCallFlags.NONE, 1000,
            None, lambda c, r: self._expanded(c, r, expanded))

    def _expanded(self, connection, result, expanded: bool) -> None:
        try:
            connection.call_finish(result)
        except GLib.Error:
            self._maximise(expanded)

    def _maximise(self, expanded: bool) -> None:
        if expanded:
            self.drawer.maximize()
        else:
            self.drawer.unmaximize()

    def _closed(self, connection, result) -> None:
        try:
            connection.call_finish(result)
        except GLib.Error:
            self.drawer.minimize()

    def footer_line(self) -> str:
        if self.harness is None:
            return self.problem
        spent = self.conversation.tokens_spent
        return f"{spent:,} tokens  ·  allowance not reported"

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

    def programs(self) -> Programs:
        return Programs(self.files, SubprocessRunner(sink=lambda _line: None), self.home)

    def program_card(self, name: str) -> Gtk.Widget:
        found = [p for p in self.programs().programs() if p.manifest.name == name]
        if not found:
            gone = Gtk.Label(label=f"{name} is no longer in ~/Code", xalign=0)
            gone.add_css_class("harness-meta")
            return gone
        return ProgramCard(found[0], on_try=self.try_program,
                           on_install=self.install_program, on_fix=self.fix_program,
                           busy=self.program_busy.get(name),
                           problem=self.program_problem.get(name))

    def _program_work(self, name: str, waiting: str, work, done) -> None:
        """Run a Program's build or install off the main loop, showing it on
        its card and keeping what went wrong there."""
        self.program_busy[name] = waiting
        self.program_problem.pop(name, None)
        self.drawer.refresh(restyle=True)

        def run():
            try:
                result = work()
            except Exception as error:  # noqa: BLE001 - shown on the card
                GLib.idle_add(finish, None, str(error))
                return
            GLib.idle_add(finish, result, None)

        def finish(result, problem):
            self.program_busy.pop(name, None)
            if problem is not None:
                self.program_problem[name] = problem
            else:
                done(result)
            self.drawer.refresh(restyle=True)
            return False

        threading.Thread(target=run, daemon=True).start()

    def try_program(self, name: str) -> None:
        def launch(prepared) -> None:
            argv, folder = prepared
            launcher = Gio.SubprocessLauncher.new(Gio.SubprocessFlags.NONE)
            launcher.set_cwd(str(folder))
            try:
                launcher.spawnv(argv)
            except GLib.Error as error:
                self.program_problem[name] = error.message

        self._program_work(name, "Building…",
                           lambda: self.programs().prepare_try(name), launch)

    def install_program(self, name: str) -> None:
        label = self.programs().manifest(name).label
        dialog = Adw.AlertDialog(
            heading=f"Install {label}?",
            body=(f"{label} will be in the applications menu and the launcher, "
                  "and can be kept in the dock.\n\nPrograms are not confined yet: "
                  "it runs as you, with everything you can reach."))
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("install", "Install")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_close_response("cancel")

        def chosen(_dialog, response: str) -> None:
            if response == "install":
                self._program_work(name, "Installing…",
                                   lambda: self.programs().install(name),
                                   lambda _commit: None)

        dialog.connect("response", chosen)
        dialog.present(self.drawer)

    def fix_program(self, name: str, problem: str) -> None:
        self.program_problem.pop(name, None)
        label = self.programs().manifest(name).label
        self.ask(f"{label} failed to build or start:\n\n```\n{problem}\n```\n\n"
                 "Please fix it.")

    def undo(self, turn: Turn) -> None:
        """Reverse what a turn changed, newest first, without the model."""
        steps = turn.undo_steps()

        def reverse() -> None:
            store, programs = EngineStore(), self.programs()
            wallpapers = user_wallpapers(
                self.files, SubprocessRunner(sink=lambda _line: None), self.home)
            for step in steps:
                undo(store, step, programs, wallpapers)

        def undone(_result) -> None:
            turn.undone = True
            if self.log is not None:
                self.log.write("undone", changes=[c.summary for c in turn.changes])
            self.drawer.refresh()

        self.background(reverse, undone)

    @property
    def session(self) -> str | None:
        return self.harness.session if self.harness is not None else None

    @property
    def running(self) -> frozenset[str]:
        return self.harness.running if self.harness is not None else frozenset()

    def load_history(self) -> None:
        if self.harness is None:
            return
        harness, log, home = self.harness, self.log, self.home

        def gather():
            pasts = harness.conversations()
            # Conversations from before the Harness moved them itself.
            moves = misplaced(pasts, log.programs_worked_on() if log else [], home,
                              Path.exists)
            for session, folder in moves:
                harness.move(session, folder)
            return harness.conversations() if moves else pasts

        def show(pasts) -> None:
            self.pasts = pasts
            self.drawer.show_history(*group(pasts, home))

        self.background(gather, show)

    def update_canvas(self) -> None:
        # What this run changed, and what the Conversation changed before, as
        # the log has it: a reopened Conversation brings its Canvas back.
        earlier = self.log.programs_of(self.session) if self.log and self.session else []
        # A Conversation in a Program's Project is about that Program first.
        here = project_program(self.harness.directory, self.home) if self.harness else None
        names = list(dict.fromkeys([*([here] if here else []), *earlier,
                                    *self.conversation.programs]))
        programs = self.programs()

        def gather():
            known = {p.manifest.name: p for p in programs.programs()}
            return [(known[name], programs.files(name))
                    for name in names if name in known]

        self.background(gather, self.drawer.show_canvas)

    def archive(self, session: str) -> None:
        if self.harness is None:
            return
        harness = self.harness
        self.background(lambda: harness.archive(session), lambda _r: self.load_history())

    def ask_to_delete(self, session: str, title: str) -> None:
        dialog = Adw.AlertDialog(
            heading=f"Delete “{title}”?",
            body=("This erases the conversation from opencode and from Osiris, "
                  "and cannot be undone. What it did stays done: a Theme "
                  "applied or a Program made is not removed."))
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_close_response("cancel")

        def chosen(_dialog, response: str) -> None:
            if response != "delete" or self.harness is None:
                return
            harness, on_screen = self.harness, session == self.session
            self.background(lambda: harness.delete(session),
                            lambda _r: self._deleted(session, on_screen=on_screen))

        dialog.connect("response", chosen)
        dialog.present(self.drawer)

    def _deleted(self, session: str, *, on_screen: bool) -> None:
        self.backgrounded.pop(session, None)
        if on_screen:
            self.conversation = Conversation()
            self.drawer.clear()
            self.drawer.refresh()
        self.load_history()

    def open_past(self, session: str) -> None:
        if self.harness is None or session == self.session or not self._leave():
            return
        harness = self.harness
        # Shown at once and kept by its session until the Harness has made it
        # current, so its events reach it while resume is under way.
        live = self.backgrounded.get(session)
        if live is not None:
            self.conversation = live
            self.drawer.clear()
            self.drawer.refresh()

        def opened(past) -> None:
            if live is None:
                self.conversation = self._restored(session, past)
                self.drawer.clear()
            else:
                self.backgrounded.pop(session, None)
            self.drawer.refresh()
            self.load_history()
            self.update_canvas()

        self.background(lambda: harness.resume(session), opened)

    @property
    def everything_allowed(self) -> bool:
        return allows_everything(self.files, self.home)

    def set_allow_everything(self, on: bool) -> None:
        """Keep the person's choice; the tool server tells the model when it
        starts, so it is restarted."""
        allow_everything(self.files, self.home, on=on)
        if self.harness is not None:
            self.background(self.harness.restart_tools, lambda _r: None)

    def _restored(self, session: str, past) -> Conversation:
        """A past Conversation with its tokens, Program cards and Undo, which
        the Engine's history does not carry and the log does."""
        if self.log is None:
            return Conversation.restored(past)
        return Conversation.restored(past,
                                     tokens_spent=self.log.tokens_spent(session),
                                     changes=self.log.changes_by_question(session),
                                     undone=self.log.undone())

    def new_conversation(self, folder: Path | None = None) -> None:
        """A new Conversation, in ``folder``'s Project or in none."""
        if not self._leave():
            return
        self.conversation = Conversation()
        if self.harness is not None:
            self.harness.new_conversation(folder)
        self.drawer.clear()
        self.drawer.refresh()
        self.drawer.entry.grab_focus()
        self.load_history()
        self.update_canvas()

    def _leave(self) -> bool:
        """Keep the Conversation on screen while Osiris still works on it;
        False while its first question is on the way, as it has no session
        to be kept by until the Engine opens one."""
        if not self.conversation.busy:
            return True
        if self.session is None:
            return False
        self.backgrounded[self.session] = self.conversation
        return True

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
            return
        GLib.idle_add(lambda: self.load_history() or False)

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
                self.engine_pid = service.pid
                engine = OpencodeEngine(UrllibClient(), service)
                tiers = {engine.action(TOOLS, tool): tier for tool, tier in TIERS.items()}
                # A restarted service has a new password, so the Harness is
                # rebuilt around the new connection; the next question opens
                # a new session.
                self.log = HarnessLog(files, me.home / LOG_FILE)
                self.harness = Harness(engine, self.log, self.models.default,
                                       tiers=tiers, directory=me.home,
                                       tools=(TOOLS, [sys.executable, TOOL_SERVER]),
                                       may_touch=self.programs().holds,
                                       allow_everything=lambda: allows_everything(
                                           self.files, self.home))
                self.accounts = OpencodeAccounts(UrllibClient(), service)
                GLib.idle_add(self._refresh)
                GLib.idle_add(lambda: self.load_history() or False)
                for event in engine.events():
                    handled = self.harness.handle(event)
                    if handled is not None:
                        GLib.idle_add(self._apply, handled)
            except Exception as error:  # noqa: BLE001 - shown, then retried
                self.problem = f"The Engine is not reachable: {error}"
                GLib.idle_add(self._refresh)
            time.sleep(RECONNECT_SECONDS)

    def _conversation_of(self, session: str) -> Conversation | None:
        """The Conversation an event is for: one kept working off screen, the
        one on screen, or none."""
        if session in self.backgrounded:
            return self.backgrounded[session]
        return self.conversation if session == self.session else None

    def _apply(self, event) -> bool:
        conversation = self._conversation_of(event.session)
        if conversation is None:
            return False
        conversation.apply(event)
        if isinstance(event, Finished | Stopped | Failed):
            self._ended(event.session, conversation)
        self.drawer.refresh()
        return False

    def _ended(self, session: str, conversation: Conversation) -> None:
        """An answer is over. One that ended off screen is let go, for the
        history to show; the changes and the Canvas are the screen's."""
        self.admin_answer(session, None)
        self.backgrounded.pop(session, None)
        if conversation is self.conversation and self.log is not None:
            changes = self.log.last_changes()
            conversation.changed(changes)
            worked_on = [c.program for c in changes if c.program]
            if worked_on and self.harness is not None:
                harness, folder = self.harness, self.home / CODE_DIR / worked_on[0]
                self.background(lambda: harness.worked_on(session, folder),
                                lambda _r: self.load_history())
            self.update_canvas()
        self.load_history()

    def _refresh(self) -> bool:
        self.drawer.refresh()
        return False

    def _restyle(self) -> None:
        if self.drawer is not None:
            self.drawer.refresh(restyle=True)
            self.drawer.canvas.restyle(self.look.scheme)


if __name__ == "__main__":
    sys.exit(Application().run(sys.argv))
