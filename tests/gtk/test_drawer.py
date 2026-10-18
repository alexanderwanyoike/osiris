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

        class Look:
            style = None
            scheme = None

        self.look = Look()
        self.asked: list[str] = []
        self.new_conversations = 0

    def ask(self, text: str) -> None:
        self.asked.append(text)
        self.conversation.asked(text)

    def new_conversation(self) -> None:
        self.new_conversations += 1
        self.conversation = Conversation()

    def header_line(self) -> str:
        return "default model"

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
    menus = [w for w in widgets(window) if isinstance(w, Gtk.MenuButton)]
    assert any("default model" in texts(m) for m in menus)
