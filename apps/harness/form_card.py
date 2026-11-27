"""The card for what the model asks the person: each question, its choices,
and the person's answer, which the Harness passes to the Engine."""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from osiris.harness.engine import Choice, FormAsked, FormField  # noqa: E402

Answers = dict[str, str | tuple[str, ...]]


class FormCard(Gtk.Box):
    def __init__(self, form: FormAsked, *, on_answer: Callable[[Answers], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("harness-approval")
        self._on_answer = on_answer
        for field in form.fields:
            self._question(field)

    def _question(self, field: FormField) -> None:
        heading = Gtk.Label(label=field.title, xalign=0, wrap=True)
        heading.add_css_class("heading")
        self.append(heading)
        self.append(Gtk.Label(label=field.text, xalign=0, wrap=True))
        for choice in field.choices:
            self.append(_choice_button(choice))


def _choice_button(choice: Choice) -> Gtk.Button:
    lines = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    lines.append(Gtk.Label(label=choice.label, xalign=0, wrap=True))
    if choice.description:
        about = Gtk.Label(label=choice.description, xalign=0, wrap=True)
        about.add_css_class("harness-step-input")
        lines.append(about)
    return Gtk.Button(child=lines)
