"""The Skills tab (#154): each skill the Engine can load, where it came from,
what it says, and whether Osiris may use it.

Where a skill came from and how a choice is kept are decided in
osiris/harness/skill_rules.py; this draws them and passes on a choice.
"""
from collections.abc import Callable

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gtk  # noqa: E402

from osiris.harness.skill_rules import SkillInfo  # noqa: E402

#: The choices for a skill, in the order offered, and how each is said.
CHOICES = ["on", "ask", "off"]
SAID = {"on": "On", "ask": "Ask first", "off": "Off"}


class SkillsTab(Gtk.Box):
    def __init__(self, read: Callable[[], list[SkillInfo]],
                 choice: Callable[[str], str], choose: Callable[[str, str], bool],
                 origin: Callable[[str], str], background):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add_css_class("harness-skills")
        self._choice, self._choose, self._origin = choice, choose, origin
        intro = Gtk.Label(
            label="Skills teach Osiris how to do a kind of task. Turn one off to "
                  "keep it from Osiris, or have Osiris ask you before it uses one.",
            xalign=0, wrap=True)
        intro.add_css_class("harness-meta")
        self.append(intro)
        self._list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")
        self.append(self._list)
        self._problem = Gtk.Label(xalign=0, wrap=True, visible=False)
        self._problem.add_css_class("harness-problem")
        self.append(self._problem)
        background(read, self._show)

    def _show(self, skills: list[SkillInfo]) -> None:
        self._list.remove_all()
        for skill in skills:
            self._list.append(self._row(skill))

    def _row(self, skill: SkillInfo) -> Gtk.Widget:
        about = " · ".join(filter(None, (self._origin(skill.path), skill.description)))
        row = Adw.ExpanderRow(title=skill.name, subtitle=about, use_markup=False)
        says = Gtk.Label(label=skill.content, xalign=0, wrap=True, selectable=True,
                         margin_top=10, margin_bottom=10, margin_start=14,
                         margin_end=14)
        says.add_css_class("harness-skill-text")
        row.add_row(says)
        picker = Gtk.DropDown.new_from_strings([SAID[c] for c in CHOICES])
        picker.set_valign(Gtk.Align.CENTER)
        picker.skill = skill.id
        picker.set_selected(CHOICES.index(self._choice(skill.id)))
        picker.connect("notify::selected", self._chosen)
        row.add_suffix(picker)
        return row

    def _chosen(self, picker: Gtk.DropDown, _spec) -> None:
        wanted = CHOICES[picker.get_selected()]
        kept = self._choice(picker.skill)
        if wanted == kept:
            return
        if not self._choose(picker.skill, wanted):
            self._problem.set_text("Your opencode config has comments in it, so "
                                   "Osiris leaves it for you to edit by hand.")
            self._problem.set_visible(True)
            # Back to what is kept; this notifies again and returns above.
            picker.set_selected(CHOICES.index(kept))
            return
        self._problem.set_visible(False)
