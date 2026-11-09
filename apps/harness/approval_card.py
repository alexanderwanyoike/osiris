"""The card an action outside the Action tier waits on (#150): what it is,
exactly, and the person's answer. What it shows is decided in
osiris/harness/detail.py and activity.py; what an answer does, in the Harness."""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango  # noqa: E402

from osiris.harness.activity import Step  # noqa: E402
from osiris.harness.detail import detail  # noqa: E402
from osiris.harness.harness import Answer  # noqa: E402


class ApprovalCard(Gtk.Box):
    def __init__(self, held: Step, *, on_answer: Callable[[Answer, str], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("harness-approval")
        self._on_answer = on_answer
        heading = Gtk.Label(label=held.question, xalign=0, wrap=True)
        heading.add_css_class("heading")
        self.append(heading)
        shown = detail(held)
        exact = Gtk.Label(label=shown.asked, xalign=0, wrap=True, selectable=True,
                          wrap_mode=Pango.WrapMode.WORD_CHAR)
        exact.add_css_class("monospace")
        exact.add_css_class("harness-approval-input")
        self.append(exact)
        for name, value in shown.inputs:
            given = Gtk.Label(label=f"{name}: {value}", xalign=0, wrap=True,
                              selectable=True, wrap_mode=Pango.WrapMode.WORD_CHAR)
            given.add_css_class("harness-step-input")
            self.append(given)

        buttons = Gtk.Box(spacing=6)
        for label, answer in (("Allow once", Answer.ONCE),
                              ("Always allow here", Answer.ALWAYS),
                              ("Deny", Answer.DENY)):
            button = Gtk.Button(label=label)
            if answer is Answer.ONCE:
                button.add_css_class("suggested-action")
            if answer is Answer.ALWAYS:
                button.set_tooltip_text(
                    "Allow this and anything like it in this Project, from now "
                    "on, until you remove it from your rules")
            button.connect("clicked", lambda _b, a=answer: self._on_answer(a, ""))
            buttons.append(button)
        self.append(buttons)

        self.entry = Gtk.Entry(placeholder_text="Or tell Osiris what to do instead",
                               hexpand=True)
        self.entry.connect("activate", lambda _e: self._reply())
        self.append(self.entry)

    def _reply(self) -> None:
        text = self.entry.get_text().strip()
        if text:
            self.entry.set_text("")
            self._on_answer(Answer.DENY, text)
