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
            theme = None

        self.look = Look()
        self.asked: list[str] = []
        self.new_conversations = 0
        self.opened: list[str] = []
        self.unqueued: list[str] = []
        self.stopped = 0
        self.gone_back: list[object] = []
        self.shown_changes: list[object] = []
        self.sent_now: list[str] = []
        self.offers: dict[str, list[object]] = {"@": [], "/": []}
        self.referenced: list[tuple[object, ...]] = []
        self.offers_fetched = 0

    def open_past(self, session: str) -> None:
        self.opened.append(session)

    def ask(self, text: str, references: tuple[object, ...] = ()) -> None:
        self.asked.append(text)
        self.referenced.append(references)
        self.conversation.asked(text)

    def offered(self, sign: str) -> list[object]:
        return self.offers[sign]

    def refresh_offers(self) -> None:
        self.offers_fetched += 1

    def read_connectors(self) -> list[object]:
        return []

    def save_connector(self, _connector: object) -> bool:
        return True

    def remove_connector(self, _name: str) -> bool:
        return True

    def connector_states(self) -> dict[str, object]:
        return {}

    def undo(self, _turn: object) -> None:
        pass

    def ask_to_go_back(self, turn: object, _again: bool = False) -> None:
        self.gone_back.append(turn)

    def show_changes(self, turn: object) -> None:
        self.shown_changes.append(turn)

    def send_now(self, text: str, references: tuple[object, ...] = ()) -> None:
        self.sent_now.append(text)
        self.referenced.append(references)

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


def test_the_canvas_toolbar_sits_in_the_top_bar_and_opens_the_canvas() -> None:
    """No row of its own: Files, Changes, Terminal and Browser sit at the top
    bar's right, and any of them opens the Canvas."""
    from gi.repository import Gtk

    window, _ = drawer()
    header = next(w for w in widgets(window) if "harness-header" in w.get_css_classes())
    assert window.canvas.toolbar.get_parent() is header
    assert window.canvas.get_first_child() is not window.canvas.toolbar
    files = next(
        w
        for w in widgets(window.canvas.toolbar)
        if isinstance(w, Gtk.Button) and w.get_icon_name() == "folder-symbolic"
    )
    files.emit("clicked")
    assert window.canvas_toggle.get_active()


def test_what_is_picked_in_the_message_box_goes_with_the_question() -> None:
    from gi.repository import Gdk

    from osiris.harness.picker import Entry, Reference

    readme = Entry("file", "/home/tester/Code/timer/README.md", "README.md", "")
    window, _ = drawer()
    window.present()
    window.app.offers["@"] = [readme]
    window.entry.get_buffer().set_text("fix @RE")
    none = Gdk.ModifierType(0)
    window.picker.key(None, Gdk.KEY_Tab, 0, none)
    window._composer_key(None, Gdk.KEY_Return, 0, none)
    assert window.app.referenced == [(Reference(readme, 4, 14),)]


def test_what_is_picked_in_the_message_box_goes_with_a_message_sent_now() -> None:
    from gi.repository import Gdk

    from osiris.harness.picker import Entry, Reference

    readme = Entry("file", "/home/tester/Code/timer/README.md", "README.md", "")
    window, _ = drawer()
    window.present()
    window.app.offers["@"] = [readme]
    window.entry.get_buffer().set_text("fix @RE")
    window.picker.key(None, Gdk.KEY_Tab, 0, Gdk.ModifierType(0))
    window._cut_in(None)
    assert window.app.referenced == [(Reference(readme, 4, 14),)]


def test_tokens_in_the_message_box_follow_the_theme() -> None:
    import main

    from osiris.harness.style import token_colours
    from tests.test_style import DAWN, OBSIDIAN

    app = FakeApp()
    app.look.theme = OBSIDIAN
    window = main.Drawer(app)
    token = window.picker.token.props
    assert token.foreground_rgba.to_string() == "rgb(124,138,235)"
    app.look.theme = DAWN
    window.refresh(restyle=True)
    accent = token_colours(DAWN)[0].lstrip("#")
    rgb = ",".join(str(int(accent[i : i + 2], 16)) for i in (0, 2, 4))
    assert token.foreground_rgba.to_string() == f"rgb({rgb})"


def test_opening_the_picker_fetches_what_it_offers_afresh() -> None:
    from osiris.harness.picker import Entry

    window, _ = drawer()
    window.present()
    window.app.offers["@"] = [Entry("file", "/p/README.md", "README.md", "")]
    window.entry.get_buffer().insert_at_cursor("@")
    window.entry.get_buffer().insert_at_cursor("R")
    assert window.app.offers_fetched == 1


def test_settings_hold_the_persons_connectors_beside_their_providers() -> None:
    from osiris.harness.connectors import Connector, State
    from tests.gtk.conftest import now, texts
    from tests.gtk.test_providers_page import FakeAccounts

    window, _ = drawer()
    app = window.app
    app.accounts = FakeAccounts()
    app.background = now
    app.open_page = lambda _url: None
    app.choose_model = lambda _model: None
    app.set_auto_mode = lambda _on: None
    app.read_connectors = lambda: [Connector("wiki", url="https://w.example/mcp")]
    app.save_connector = lambda _c: True
    app.remove_connector = lambda _n: True
    app.connector_states = lambda: {"wiki": State("connected")}
    window.show_providers()
    shown = texts(window)
    assert "Connectors" in shown
    assert "https://w.example/mcp" in shown and "Connected" in shown


def test_the_rail_has_a_tick_per_question_and_a_click_scrolls_to_it() -> None:
    from tests.gtk.test_composer_picker import settle
    from tests.gtk.test_rail import marks

    window, _ = drawer()
    window.set_default_size(420, 700)
    window.present()
    for n in range(3):
        turn = window.app.conversation.asked(f"question {n}")
        turn.answer = "an answer that runs on\n\n" * 20
    window.refresh()
    settle()
    assert len(marks(window.rail)) == 3
    window.rail_jump(0)
    settle()
    assert window.scroller.get_vadjustment().get_value() == 0


def test_the_current_tick_follows_the_scroll() -> None:
    from tests.gtk.test_composer_picker import settle

    window, _ = drawer()
    window.set_default_size(420, 700)
    window.present()
    for n in range(4):
        turn = window.app.conversation.asked(f"question {n}")
        turn.answer = "an answer that runs on\n\n" * 20
    window.refresh()
    settle()
    view = window.scroller.get_vadjustment()
    view.set_value(view.get_upper())
    settle()
    window.refresh()
    at_foot = [tick.current for tick in window.rail._ticks]
    view.set_value(0)
    settle()
    window.refresh()
    at_head = [tick.current for tick in window.rail._ticks]
    assert at_foot == [False, False, False, True]
    assert at_head == [True, False, False, False]


def test_the_conversation_keeps_its_scrollbar_beside_the_rail() -> None:
    from gi.repository import Gtk

    window, _ = drawer()
    _across, down = window.scroller.get_policy()
    assert down == Gtk.PolicyType.AUTOMATIC


def test_a_conversation_that_fits_on_one_screen_has_no_rail() -> None:
    from tests.gtk.test_composer_picker import settle

    window, _ = drawer()
    window.set_default_size(420, 700)
    window.present()
    for n in range(2):
        window.app.conversation.asked(f"question {n}").answer = "short"
    window.refresh()
    settle()
    window.refresh()
    assert not window.rail.get_visible()
