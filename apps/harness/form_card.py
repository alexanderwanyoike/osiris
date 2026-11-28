"""The card for what the model asks the person: each question, its choices,
and the person's answer, which the Harness passes to the Engine."""

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from osiris.harness.engine import (  # noqa: E402
    Choice,
    FormAnswer,
    FormAsked,
    FormField,
)
from osiris.harness.forms import reply  # noqa: E402


class FormCard(Gtk.Box):
    def __init__(self, form: FormAsked, *, on_answer: Callable[[dict[str, FormAnswer]], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("harness-approval")
        self._form = form
        self._on_answer = on_answer
        #: Each question's choices picked, and its answer typed, by its key.
        self._picked: dict[str, Callable[[], tuple[str, ...]]] = {}
        self._typed: dict[str, Gtk.Entry] = {}
        for field in form.fields:
            self._question(field)
        send = Gtk.Button(label="Send", halign=Gtk.Align.START)
        send.add_css_class("suggested-action")
        send.connect("clicked", lambda _b: self._send())
        self.append(send)

    def _question(self, field: FormField) -> None:
        heading = Gtk.Label(label=field.title, xalign=0, wrap=True)
        heading.add_css_class("heading")
        self.append(heading)
        self.append(Gtk.Label(label=field.text, xalign=0, wrap=True))
        self._picked[field.key] = self._choices(field)
        if field.custom:
            self._typed[field.key] = self._entry()

    def _choices(self, field: FormField) -> Callable[[], tuple[str, ...]]:
        """Radio buttons for one of the choices, ticks for any of them."""
        boxes: list[tuple[Gtk.CheckButton, str]] = []
        for choice in field.choices:
            group = boxes[0][0] if boxes and not field.multiple else None
            box = Gtk.CheckButton(child=_lines(choice), group=group)
            boxes.append((box, choice.value))
            self.append(box)
        return lambda: tuple(value for box, value in boxes if box.get_active())

    def _entry(self) -> Gtk.Entry:
        entry = Gtk.Entry(placeholder_text="Or type your own answer", hexpand=True)
        entry.connect("activate", lambda _e: self._send())
        self.append(entry)
        return entry

    def _send(self) -> None:
        picked = {key: choices() for key, choices in self._picked.items()}
        typed = {key: entry.get_text() for key, entry in self._typed.items()}
        self._on_answer(reply(self._form, picked, typed))


def _lines(choice: Choice) -> Gtk.Box:
    lines = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    lines.append(Gtk.Label(label=choice.label, xalign=0, wrap=True))
    if choice.description:
        about = Gtk.Label(label=choice.description, xalign=0, wrap=True)
        about.add_css_class("harness-step-input")
        lines.append(about)
    return lines
