#!/usr/bin/env python3
"""The askpass helper: sudo, run with -A, asks here for the password (ADR 0018).

Installed as /usr/lib/osiris/askpass, which runs this file. It asks the running
Harness first, which shows an admin password card in the Conversation whose
command it is; when the Harness leaves it to the helper, it shows a dialog of
its own naming the program that ran sudo. The password is written to sudo on
standard output and nowhere else.

Whom to answer and what to show is decided in osiris/harness/admin.py, where it
is tested; this file only asks and draws.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for candidate in ("/usr/share/osiris/lib", REPO):
    if os.path.isdir(os.path.join(candidate, "osiris")):
        sys.path.insert(0, candidate)
        break
sys.path.insert(0, HERE)

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from admin_card import AdminCard  # noqa: E402

from osiris.harness import admin  # noqa: E402
from osiris.platform import ProcFs  # noqa: E402


class AdminDialog(Gtk.Window):
    def __init__(self, request: admin.Request, *, asker: str, on_answer):
        super().__init__(title="Administrator password", resizable=False,
                         default_width=440)
        self._on_answer = on_answer
        self._answered = False
        card = AdminCard(request, asker=asker, on_allow=self._answer,
                         on_deny=lambda: self._answer(None))
        for side in ("top", "bottom", "start", "end"):
            card.set_property(f"margin-{side}", 18)
        self.set_child(card)
        self.connect("close-request", self._closed)

    def _answer(self, password: str | None) -> None:
        if self._answered:
            return
        self._answered = True
        self.set_visible(False)
        self._on_answer(password)

    def _closed(self, _window) -> bool:
        self._answer(None)
        return False


def ask_harness(request: admin.Request, prompt: str) -> admin.HarnessAnswer:
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        reply = bus.call_sync(
            admin.BUS_NAME, admin.OBJECT_PATH, admin.INTERFACE, "Ask",
            GLib.Variant("(ass)", (list(request.command), prompt)),
            GLib.VariantType("(bs)"),
            # A Harness that is not running is not started for this: the
            # helper asks itself instead.
            Gio.DBusCallFlags.NO_AUTO_START, admin.ASK_TIMEOUT * 1000, None)
    except GLib.Error as error:
        return admin.HarnessAnswer(
            error=Gio.DBusError.get_remote_error(error) or error.message)
    approved, password = reply.unpack()
    return admin.HarnessAnswer(password=password if approved else None)


def ask_person(program: str, request: admin.Request) -> str | None:
    # Gtk.init_check() succeeds with no display; the display is what counts.
    if not Gtk.init_check() or Gdk.Display.get_default() is None:
        return None
    Adw.init()
    answers: list[str | None] = []
    loop = GLib.MainLoop()

    def answered(password: str | None) -> None:
        answers.append(password)
        loop.quit()

    window = AdminDialog(request, asker=program, on_answer=answered)
    window.present()
    GLib.timeout_add_seconds(admin.ASK_TIMEOUT, lambda: window.close() or False)
    loop.run()
    return answers[0] if answers else None


def main() -> int:
    prompt = sys.argv[1] if len(sys.argv) > 1 else ""
    password = admin.helper_answer(
        ProcFs(), os.getpid(),
        ask_harness=lambda request: ask_harness(request, prompt),
        ask_person=ask_person)
    if password is None:
        return 1
    sys.stdout.write(password + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
