"""A skill Osiris proposes (#154), on a card under the answer that proposed
it: read in full, then kept among the person's skills or not."""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from osiris.harness.proposals import Proposal  # noqa: E402

#: The tallest the skill's text stands before it scrolls, in pixels.
TALLEST = 260


class ProposalCard(Gtk.Box):
    def __init__(self, proposal: Proposal, decided: bool | None,
                 on_keep: Callable[[Proposal], None],
                 on_decline: Callable[[Proposal], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("card")
        self.add_css_class("harness-proposal-card")
        heading = Gtk.Label(label="Osiris suggests a skill", xalign=0)
        heading.add_css_class("harness-meta")
        name = Gtk.Label(label=proposal.name, xalign=0)
        name.add_css_class("harness-proposal-name")
        about = Gtk.Label(label=proposal.description, xalign=0, wrap=True)
        says = Gtk.Label(label=proposal.body, xalign=0, yalign=0, wrap=True,
                         selectable=True)
        says.add_css_class("harness-proposal-body")
        says.set_focusable(False)
        read = Gtk.ScrolledWindow(child=says, max_content_height=TALLEST,
                                  propagate_natural_height=True,
                                  hscrollbar_policy=Gtk.PolicyType.NEVER)
        for part in (heading, name, about, read):
            self.append(part)
        self.append(self._choice(proposal, decided, on_keep, on_decline))

    @staticmethod
    def _choice(proposal: Proposal, decided: bool | None,
                on_keep: Callable[[Proposal], None],
                on_decline: Callable[[Proposal], None]) -> Gtk.Widget:
        if decided is not None:
            said = Gtk.Label(label="Kept among your skills" if decided else "Not kept",
                             xalign=0)
            said.add_css_class("harness-meta")
            return said
        keep = Gtk.Button(label="Keep it")
        keep.add_css_class("suggested-action")
        keep.connect("clicked", lambda _b: on_keep(proposal))
        decline = Gtk.Button(label="No thanks")
        decline.add_css_class("flat")
        decline.connect("clicked", lambda _b: on_decline(proposal))
        buttons = Gtk.Box(spacing=6, halign=Gtk.Align.END)
        buttons.append(decline)
        buttons.append(keep)
        return buttons
