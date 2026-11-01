"""The question Thoth asks before going back to before a question (#158)."""

import gi

gi.require_version("Adw", "1")
from gi.repository import Adw  # noqa: E402


def going_back_dialog(lost: str, *, again: bool) -> Adw.AlertDialog:
    """``lost`` says what the person loses, in the Conversation's words."""
    dialog = Adw.AlertDialog(
        heading="Try this question again?" if again else "Edit this question?",
        body=lost)
    dialog.add_response("cancel", "Cancel")
    dialog.add_response("back", "Go back and try again" if again else "Go back and edit")
    dialog.set_response_appearance("back", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.set_close_response("cancel")
    return dialog
