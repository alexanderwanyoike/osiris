"""The drawer window: its top bar and composer, expanding for deep work, and
back."""

from __future__ import annotations

import gi

gi.require_version("Adw", "1")
from gi.repository import Adw  # noqa: E402

from osiris.harness.conversation import Conversation  # noqa: E402
from osiris.harness.settings import Models  # noqa: E402


class FakeApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="dev.osiris.HarnessTest")
        self.conversation = Conversation()
        self.accounts = None
        self.models = Models(None, None)
        self.everything_allowed = False

        class Look:
            style = None
            scheme = None

        self.look = Look()
        self.asked: list[str] = []
        self.new_conversations = 0
        self.opened: list[str] = []

    def open_past(self, session: str) -> None:
        self.opened.append(session)

    def ask(self, text: str) -> None:
        self.asked.append(text)
        self.conversation.asked(text)

    def undo(self, _turn: object) -> None:
        pass

    def program_card(self, name: str) -> object:
        from gi.repository import Gtk

        return Gtk.Label(label=name)

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
    """Expanding goes through the extension, which stops above the dock; the
    window manager's maximise would cover Plank."""
    window, _ = drawer()
    asked: list[bool] = []
    window.app.expand = asked.append
    window.expand_button.emit("clicked")
    window.expand_button.emit("clicked")
    assert asked == [True, False]


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
    app.set_allow_everything = lambda _on: None
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
