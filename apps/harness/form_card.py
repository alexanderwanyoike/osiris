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


class FormCard(Gtk.Box):
    def __init__(self, form: FormAsked, *, on_answer: Callable[[dict[str, FormAnswer]], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("harness-approval")
        self._on_answer = on_answer
        #: Each question's answer as it stands, by its key.
        self._answers: dict[str, Callable[[], FormAnswer]] = {}
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
        picked = self._choices(field)
        typed = self._entry() if field.custom else None

        def answer() -> FormAnswer:
            text = typed.get_text().strip() if typed is not None else ""
            return text or picked()

        self._answers[field.key] = answer

    def _choices(self, field: FormField) -> Callable[[], FormAnswer]:
        """Radio buttons for one of the choices, ticks for any of them."""
        boxes: list[tuple[Gtk.CheckButton, str]] = []
        for choice in field.choices:
            group = boxes[0][0] if boxes and not field.multiple else None
            box = Gtk.CheckButton(child=_lines(choice), group=group)
            boxes.append((box, choice.value))
            self.append(box)

        def picked() -> FormAnswer:
            values = tuple(value for box, value in boxes if box.get_active())
            return values if field.multiple else next(iter(values), "")

        return picked

    def _entry(self) -> Gtk.Entry:
        entry = Gtk.Entry(placeholder_text="Or type your own answer", hexpand=True)
        entry.connect("activate", lambda _e: self._send())
        self.append(entry)
        return entry

    def _send(self) -> None:
        answers = {key: answer() for key, answer in self._answers.items()}
        self._on_answer({key: value for key, value in answers.items() if value})


def _lines(choice: Choice) -> Gtk.Box:
    lines = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    lines.append(Gtk.Label(label=choice.label, xalign=0, wrap=True))
    if choice.description:
        about = Gtk.Label(label=choice.description, xalign=0, wrap=True)
        about.add_css_class("harness-step-input")
        lines.append(about)
    return lines
