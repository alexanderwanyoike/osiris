"""The card under an answer that built or changed a Program (docs/PROGRAMS.md).

Try and Install are the person's actions, never the Harness's; what each does
is in osiris/programs, where it is tested. A failed build is shown here and
goes back to the Harness only when the person asks.
"""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango  # noqa: E402

from osiris.programs.programs import Program, State  # noqa: E402


class ProgramCard(Gtk.Box):
    def __init__(self, program: Program, *, on_try: Callable[[str], None],
                 on_install: Callable[[str], None],
                 on_fix: Callable[[str, str], None],
                 busy: str | None = None, problem: str | None = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                         halign=Gtk.Align.START)
        self.add_css_class("harness-program")
        name = program.manifest.name
        title = Gtk.Label(label=program.manifest.label, xalign=0)
        title.add_css_class("heading")
        self.append(title)
        about = Gtk.Label(label=program.manifest.description, xalign=0, wrap=True,
                          wrap_mode=Pango.WrapMode.WORD_CHAR)
        about.add_css_class("harness-meta")
        self.append(about)

        actions = Gtk.Box(spacing=6)
        try_it = Gtk.Button(label="Try")
        try_it.connect("clicked", lambda _b: on_try(name))
        actions.append(try_it)
        if program.state is State.UP_TO_DATE:
            actions.append(Gtk.Label(label="Installed"))
        else:
            install = Gtk.Button(
                label="Install" if program.state is State.NOT_INSTALLED else "Update")
            install.add_css_class("suggested-action")
            install.connect("clicked", lambda _b: on_install(name))
            actions.append(install)
        if busy is not None:
            for button in (child for child in _children(actions)
                           if isinstance(child, Gtk.Button)):
                button.set_sensitive(False)
            actions.append(Gtk.Label(label=busy))
        self.append(actions)

        if problem is not None:
            shown = Gtk.Label(label=problem, xalign=0, wrap=True, selectable=True,
                              wrap_mode=Pango.WrapMode.WORD_CHAR)
            shown.add_css_class("harness-error")
            shown.add_css_class("monospace")
            self.append(shown)
            fix = Gtk.Button(label="Fix it", halign=Gtk.Align.START)
            fix.connect("clicked", lambda _b: on_fix(name, problem))
            self.append(fix)


def _children(box: Gtk.Widget):
    child = box.get_first_child()
    while child is not None:
        yield child
        child = child.get_next_sibling()
