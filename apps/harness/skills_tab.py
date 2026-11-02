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


class SkillsTab(Gtk.Box):
    def __init__(self, read: Callable[[], list[SkillInfo]],
                 choice: Callable[[str], str], choose: Callable[[str, str], bool],
                 origin: Callable[[str], str], background):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add_css_class("harness-skills")
        self._choice, self._choose, self._origin = choice, choose, origin
        self._list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")
        self.append(self._list)
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
        return row
