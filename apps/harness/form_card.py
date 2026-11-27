"""The card for what the model asks the person: each question, its choices,
and the person's answer, which the Harness passes to the Engine."""

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from osiris.harness.engine import Choice, FormAsked, FormField  # noqa: E402

Answer = str | tuple[str, ...]
Answers = dict[str, Answer]


class FormCard(Gtk.Box):
    def __init__(self, form: FormAsked, *, on_answer: Callable[[Answers], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("harness-approval")
        self._on_answer = on_answer
        #: One question with one answer goes as soon as it is given; more wait
        #: for Send, so each can be changed until then.
        self._at_once = len(form.fields) == 1 and not form.fields[0].multiple
        #: Each question's answer as it stands, by its key.
        self._answers: dict[str, Callable[[], Answer]] = {}
        for field in form.fields:
            self._question(field)
        if not self._at_once:
            send = Gtk.Button(label="Send", halign=Gtk.Align.START)
            send.add_css_class("suggested-action")
            send.connect("clicked", lambda _b: self._send())
            self.append(send)

    def _question(self, field: FormField) -> None:
        heading = Gtk.Label(label=field.title, xalign=0, wrap=True)
        heading.add_css_class("heading")
        self.append(heading)
        self.append(Gtk.Label(label=field.text, xalign=0, wrap=True))
        picked = self._ticks(field) if field.multiple else self._buttons(field)
        typed = self._entry() if field.custom else None

        def answer() -> Answer:
            text = typed.get_text().strip() if typed is not None else ""
            return text or picked()

        self._answers[field.key] = answer

    def _buttons(self, field: FormField) -> Callable[[], Answer]:
        """One of the choices: the one pressed."""
        chosen: list[str] = []
        group: Gtk.ToggleButton | None = None
        for choice in field.choices:
            button = Gtk.ToggleButton(child=_lines(choice), group=group)
            group = group or button
            button.connect(
                "toggled", lambda b, value=choice.value: self._chose(b, chosen, value)
            )
            self.append(button)
        return lambda: chosen[-1] if chosen else ""

    def _chose(self, button: Gtk.ToggleButton, chosen: list[str], value: str) -> None:
        if not button.get_active():
            return
        chosen.append(value)
        if self._at_once:
            self._send()

    def _ticks(self, field: FormField) -> Callable[[], Answer]:
        """Any of the choices: those ticked."""
        ticks = [(Gtk.CheckButton(child=_lines(c)), c.value) for c in field.choices]
        for tick, _value in ticks:
            self.append(tick)
        return lambda: tuple(value for tick, value in ticks if tick.get_active())

    def _entry(self) -> Gtk.Entry:
        entry = Gtk.Entry(placeholder_text="Or type your own answer", hexpand=True)
        entry.connect("activate", lambda _e: self._send())
        self.append(entry)
        return entry

    def _send(self) -> None:
        self._on_answer({key: answer() for key, answer in self._answers.items()})


def _lines(choice: Choice) -> Gtk.Box:
    lines = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    lines.append(Gtk.Label(label=choice.label, xalign=0, wrap=True))
    if choice.description:
        about = Gtk.Label(label=choice.description, xalign=0, wrap=True)
        about.add_css_class("harness-step-input")
        lines.append(about)
    return lines
