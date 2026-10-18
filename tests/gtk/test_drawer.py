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
