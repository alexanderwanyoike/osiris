"""The drawer window: its top bar and composer, expanding for deep work, and
back."""

from __future__ import annotations

import gi

gi.require_version("Adw", "1")
from gi.repository import Adw  # noqa: E402

from osiris.harness.conversation import Conversation  # noqa: E402
from osiris.harness.settings import Models  # noqa: E402

from .conftest import texts, widgets  # noqa: E402


class FakeApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="dev.osiris.HarnessTest")
        self.conversation = Conversation()
        self.accounts = None
        self.models = Models(None, None)
        self.in_auto_mode = False

        class Look:
            style = None
            scheme = None

        self.look = Look()
        self.asked: list[str] = []
        self.new_conversations = 0
        self.opened: list[str] = []
        self.unqueued: list[str] = []
        self.stopped = 0
        self.gone_back: list[object] = []
        self.shown_changes: list[object] = []
        self.sent_now: list[str] = []

    def open_past(self, session: str) -> None:
        self.opened.append(session)

    def ask(self, text: str) -> None:
        self.asked.append(text)
        self.conversation.asked(text)

    def undo(self, _turn: object) -> None:
        pass

    def ask_to_go_back(self, turn: object, _again: bool = False) -> None:
        self.gone_back.append(turn)

    def show_changes(self, turn: object) -> None:
        self.shown_changes.append(turn)

    def send_now(self, text: str) -> None:
        self.sent_now.append(text)

    def program_card(self, name: str) -> object:
        from gi.repository import Gtk

        return Gtk.Label(label=name)

    def admin_card(self, _request: object) -> object:
        from gi.repository import Gtk

        return Gtk.Box()

    def approval_card(self, _turn: object) -> object:
        from gi.repository import Gtk

        return Gtk.Label(label="approval card")

    def stop(self) -> None:
        self.stopped += 1

    def unqueue(self, message: str) -> str:
        self.unqueued.append(message)
        return self.conversation.unqueued(message)

    def new_conversation(self) -> None:
        self.new_conversations += 1
        self.conversation = Conversation()

    def footer_line(self) -> str:
        return ""


def drawer():
    import main

    window = main.Drawer(FakeApp())
    calls: list[str] = []
    window.maximize = lambda: calls.append("maximize")  # type: ignore[method-assign]
    window.unmaximize = lambda: calls.append("unmaximize")  # type: ignore[method-assign]
    return window, calls


def test_the_expand_button_asks_to_fill_the_screen_and_to_come_back() -> None:
    """Expanding goes through the extension, which keeps the drawer at the
    right edge and maximises it; without the extension the app maximises."""
    window, _ = drawer()
    asked: list[bool] = []
    window.app.expand = asked.append
    window.expand_button.emit("clicked")
    window.expand_button.emit("clicked")
    assert asked == [True, False]


def test_the_expand_button_points_the_way_the_drawer_will_go() -> None:
    """The drawer sits at the right edge: it widens to the left and comes
    back to the right."""
    window, _ = drawer()
    window.app.expand = lambda _expanded: None
    assert window.expand_button.get_icon_name() == "xsi-go-previous-symbolic"
    window.expand_button.emit("clicked")
    assert window.expand_button.get_icon_name() == "xsi-go-next-symbolic"
    window.expand_button.emit("clicked")
    assert window.expand_button.get_icon_name() == "xsi-go-previous-symbolic"


def test_the_left_edge_is_a_handle_for_resizing_the_drawer() -> None:
    window, _ = drawer()
    handle = window.resize_handle
    assert handle.get_cursor() is not None
    assert handle.get_cursor().get_name() == "ew-resize"
    assert window.get_child().get_first_child() is handle


class FakeGesture:
    def get_current_event_device(self) -> None:
        return None

    def get_current_button(self) -> int:
        return 1

    def get_current_event_time(self) -> int:
        return 42


def test_pressing_the_handle_asks_the_window_manager_to_resize_from_the_west() -> None:
    from gi.repository import Gdk

    window, _ = drawer()
    window.present()
    calls: list[tuple[object, ...]] = []
    surface = window.get_surface()
    surface.begin_resize = lambda *args: calls.append(args)  # type: ignore[method-assign]
    window._begin_resize(FakeGesture(), 1, 4.0, 100.0)
    assert len(calls) == 1
    edge, _device, button, x, y, time = calls[0]
    assert edge == Gdk.SurfaceEdge.WEST
    assert (button, time) == (1, 42)
    assert (x, y) == (4.0, 100.0)


def test_the_conversation_keeps_a_readable_width_when_the_drawer_is_expanded() -> None:
    from tests.gtk.conftest import widgets

    window, _ = drawer()
    clamps = [w for w in widgets(window) if isinstance(w, Adw.Clamp)]
    assert clamps, "the conversation and composer sit in a clamp"
    assert all(600 <= c.get_maximum_size() <= 900 for c in clamps)


def test_the_providers_page_opens_with_a_back_button_carrying_an_arrow() -> None:
    from tests.gtk.conftest import now, widgets
    from tests.gtk.test_providers_page import FakeAccounts

    window, _ = drawer()
    app = window.app
    app.accounts = FakeAccounts()
    app.background = now
    app.open_page = lambda _url: None
    app.choose_model = lambda _model: None
    app.set_auto_mode = lambda _on: None
    window.show_providers()
    backs = [w for w in widgets(window) if isinstance(w, Adw.ButtonContent)]
    assert [(b.get_label(), b.get_icon_name()) for b in backs] == [
        ("Back", "go-previous-symbolic")
    ]


def test_the_top_bar_starts_a_new_conversation() -> None:
    from gi.repository import Gtk

    from tests.gtk.conftest import widgets

    window, _ = drawer()
    (new,) = [
        w
        for w in widgets(window)
        if isinstance(w, Gtk.Button) and w.get_tooltip_text() == "New conversation"
    ]
    new.emit("clicked")
    assert window.app.new_conversations == 1


def test_the_top_bar_names_the_conversation() -> None:
    window, _ = drawer()
    assert window.title.get_text() == "New conversation"
    window.app.conversation.asked("Make me a calm theme")
    window.refresh()
    assert window.title.get_text() == "Make me a calm theme"


def test_a_held_action_is_drawn_with_the_apps_approval_card() -> None:
    from osiris.harness.activity import Step

    window, _ = drawer()
    turn = window.app.conversation.asked("list /etc")
    turn.held = Step("shell", ("ls /etc",))
    window.refresh()
    assert "approval card" in texts(window)


def test_enter_sends_even_while_osiris_is_busy() -> None:
    from gi.repository import Gdk

    window, _ = drawer()
    window.app.conversation.asked("count to sixty")
    window.refresh()
    window.entry.get_buffer().set_text("stop at ten")
    window._composer_key(None, Gdk.KEY_Return, 0, Gdk.ModifierType(0))
    assert window.app.asked == ["stop at ten"]


def waiting_drawer():
    window, _ = drawer()
    window.app.conversation.asked("count to sixty")
    window.app.conversation.queued("msg_2", "stop at ten")
    window.refresh()
    return window


def button(window: object, label: str) -> object:
    from gi.repository import Gtk

    return next(
        w
        for w in widgets(window)
        if isinstance(w, Gtk.Button) and w.get_label() == label
    )


def test_a_waiting_message_is_shown_and_can_be_removed() -> None:
    window = waiting_drawer()
    assert "stop at ten" in texts(window)
    button(window, "Remove").emit("clicked")
    assert window.app.unqueued == ["msg_2"]
    assert "stop at ten" not in texts(window)


def test_editing_a_waiting_message_puts_it_back_in_the_composer() -> None:
    window = waiting_drawer()
    button(window, "Edit").emit("clicked")
    buffer = window.entry.get_buffer()
    text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
    assert text == "stop at ten"
    assert window.app.unqueued == ["msg_2"]


def test_stop_keeps_waiting_messages_in_the_composer_and_sends_none() -> None:
    window = waiting_drawer()
    window.send.emit("clicked")
    buffer = window.entry.get_buffer()
    text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
    assert (window.app.stopped, window.app.unqueued) == (1, ["msg_2"])
    assert text == "stop at ten"


def test_the_answer_a_delivered_message_steered_stops_working() -> None:
    from osiris.harness.engine import Delivered

    window = waiting_drawer()
    assert window.views[0].working.ticking
    window.app.conversation.apply(Delivered("ses_1", "msg_2"))
    window.refresh()
    assert not window.views[0].working.ticking


def test_the_composer_takes_more_than_one_line_and_sends_it() -> None:
    from gi.repository import Gtk

    window, _ = drawer()
    assert isinstance(window.entry, Gtk.TextView)
    window.entry.get_buffer().set_text("first line\nsecond line")
    window.send.emit("clicked")
    assert window.app.asked == ["first line\nsecond line"]
    assert window.entry.get_buffer().get_char_count() == 0


def test_the_model_in_play_is_a_menu_in_the_composer() -> None:
    from gi.repository import Gtk

    from tests.gtk.conftest import texts, widgets

    window, _ = drawer()
    window.refresh()
    menus = [w for w in widgets(window) if isinstance(w, Gtk.MenuButton)]
    assert any("default model" in texts(m) for m in menus)


def test_the_sidebar_is_beside_the_conversation_and_has_a_toggle() -> None:
    from gi.repository import Gtk

    from tests.gtk.conftest import widgets

    window, _ = drawer()
    assert isinstance(window.split, Adw.OverlaySplitView)
    (toggle,) = [
        w
        for w in widgets(window)
        if isinstance(w, Gtk.ToggleButton) and w.get_tooltip_text() == "Conversations"
    ]
    toggle.set_active(True)
    assert window.split.get_show_sidebar()


def test_choosing_a_past_conversation_in_the_sidebar_opens_it() -> None:
    from pathlib import Path

    from osiris.harness.engine import Past

    window, _ = drawer()
    past = Past("ses_theme", "Make me a calm theme", Path("/home/tester"), 1.0)
    window.show_history([], [past])
    row = window.sidebar.list.get_row_at_index(2)
    window.sidebar.list.emit("row-activated", row)
    assert window.app.opened == ["ses_theme"]


def test_the_canvas_opens_when_there_is_something_to_show_and_folds_the_sidebar() -> (
    None
):
    from pathlib import Path

    from osiris.programs.manifest import parse
    from osiris.programs.programs import Program

    window, _ = drawer()
    assert not window.canvas_toggle.get_sensitive()
    manifest = parse(
        '{"name": "pomodoro", "label": "Pomodoro", "description": "x",'
        ' "run": ["python3", "main.py"]}'
    )
    window.show_canvas([(Program(manifest, Path("/nonexistent"), "a", None), [])])
    assert window.canvas_toggle.get_sensitive()
    assert window.canvas_toggle.get_active()
    assert window.canvas.get_visible()
    assert not window.split.get_show_sidebar()
    window.canvas_toggle.set_active(False)
    assert not window.canvas.get_visible()
    assert window.split.get_show_sidebar()


def test_the_canvas_draws_code_in_the_themes_colours_from_the_start(
    tmp_path,
) -> None:
    from pathlib import Path

    gi.require_version("GtkSource", "5")
    from gi.repository import GtkSource

    from osiris.programs.manifest import parse
    from osiris.programs.programs import Program

    scheme = GtkSource.StyleSchemeManager.get_default().get_scheme("Adwaita-dark")
    (tmp_path / "main.py").write_text("print('tick')\n")
    import main

    app = FakeApp()
    app.look.scheme = scheme
    window = main.Drawer(app)
    manifest = parse(
        '{"name": "pomodoro", "label": "Pomodoro", "description": "x",'
        ' "run": ["python3", "main.py"]}'
    )
    window.show_canvas([(Program(manifest, tmp_path, "a", None), [Path("main.py")])])
    assert window.canvas.current_view().get_buffer().get_style_scheme() is scheme


def test_in_a_narrow_drawer_the_conversation_list_slides_over_the_conversation() -> (
    None
):
    from gi.repository import GLib

    window, _ = drawer()
    window.set_default_size(440, 800)
    window.present()
    context = GLib.MainContext.default()
    for _ in range(200):
        context.iteration(False)
        if window.get_width() == 440:
            break
    for _ in range(50):
        context.iteration(False)
    window.sidebar_toggle.set_active(True)
    assert window.split.get_collapsed()
    assert not window.canvas_toggle.get_visible()


def test_in_a_narrow_drawer_choosing_a_conversation_folds_the_list_away() -> None:
    from pathlib import Path

    from gi.repository import GLib

    from osiris.harness.engine import Past

    window, _ = drawer()
    window.set_default_size(440, 800)
    window.present()
    context = GLib.MainContext.default()
    for _ in range(250):
        context.iteration(False)
    past = Past("ses_theme", "Make me a calm theme", Path("/home/tester"), 1.0)
    window.show_history([], [past])
    window.sidebar_toggle.set_active(True)
    window.sidebar.list.emit("row-activated", window.sidebar.list.get_row_at_index(2))
    assert window.app.opened == ["ses_theme"]
    assert not window.split.get_show_sidebar()


def test_a_draft_never_replaces_what_the_person_typed() -> None:
    window, _ = drawer()
    buffer = window.entry.get_buffer()
    buffer.set_text("half a thought")
    window.draft("Convert this theme")
    text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
    assert "half a thought" in text
    assert "Convert this theme" in text


def test_a_draft_fills_an_empty_input() -> None:
    window, _ = drawer()
    window.draft("Convert this theme")
    buffer = window.entry.get_buffer()
    text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
    assert text == "Convert this theme"


def test_while_osiris_works_a_message_can_be_sent_now() -> None:
    """It stops what Osiris is doing and is taken next (#188)."""
    window, _ = drawer()
    window.app.conversation.asked("count to sixty")
    window.refresh()
    assert window.send_now.get_visible()
    assert "stop" in window.send_now.get_tooltip_text().lower()
    window.entry.get_buffer().set_text("stop, count to ten")
    window.send_now.emit("clicked")
    buffer = window.entry.get_buffer()
    assert window.app.sent_now == ["stop, count to ten"]
    assert buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False) == ""


def test_with_nothing_working_there_is_nothing_to_cut_into() -> None:
    window, _ = drawer()
    window.refresh()
    assert not window.send_now.get_visible()


def test_a_canvas_opened_in_a_narrow_drawer_is_shown_once_it_is_wide() -> None:
    """The narrow drawer hides the Canvas; widening it must bring it back."""
    from pathlib import Path

    from gi.repository import GLib

    from osiris.programs.manifest import parse
    from osiris.programs.programs import Program

    window, _ = drawer()
    context = GLib.MainContext.default()

    def settle(width: int) -> None:
        import time

        window.set_default_size(width, 800)
        window.present()
        deadline = time.monotonic() + 5
        while window.get_width() != width and time.monotonic() < deadline:
            context.iteration(False)
        for _ in range(100):
            context.iteration(False)

    settle(440)
    manifest = parse(
        '{"name": "pomodoro", "label": "Pomodoro", "description": "x",'
        ' "run": ["python3", "main.py"]}'
    )
    window.show_canvas([(Program(manifest, Path("/nonexistent"), "a", None), [])])
    settle(1600)
    assert window.get_width() == 1600
    assert window.canvas_toggle.get_visible()
    assert window.canvas_toggle.get_active()
    assert window.canvas.get_visible()


def test_an_answers_changes_are_left_to_the_canvas_toolbar() -> None:
    """No icon by its time: Changes is opened from the Canvas (#195)."""
    from osiris.harness.conversation import State
    from osiris.harness.log import Change

    window, _ = drawer()
    turn = window.app.conversation.asked("add --times")
    turn.state = State.DONE
    turn.changes.append(
        Change(
            "coin-flip: change",
            {"action": "revert_commit", "name": "coin-flip", "commit": "abc"},
            "coin-flip",
        )
    )
    window.refresh()
    from gi.repository import Gtk

    assert not any(
        isinstance(w, Gtk.Button) and w.get_icon_name() == "view-dual-symbolic"
        for w in widgets(window)
    )
