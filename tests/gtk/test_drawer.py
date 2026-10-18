"""The drawer window: expanding for deep work, and back."""

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


def test_the_expand_button_fills_the_screen_and_brings_the_drawer_back() -> None:
    window, calls = drawer()
    window.expand_button.emit("clicked")
    window.expand_button.emit("clicked")
    assert calls == ["maximize", "unmaximize"]


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
