"""The Skills tab (#154): each skill the Engine can load, where it came from,
what it says, and whether Osiris may use it."""

from __future__ import annotations

from gi.repository import Gtk

from osiris.harness.skill_rules import SkillInfo

from .conftest import now, texts, widgets

REVIEW = SkillInfo(
    "review",
    "Review",
    "Review a change",
    "/home/tester/.config/opencode/skills/review/SKILL.md",
    "# Review\nRead the diff, then the tests.",
)
REPORT = SkillInfo("report", "Report", "Report a bug", "/builtin/report.md", "x")


class Choices:
    def __init__(self, writable: bool = True) -> None:
        self.made: dict[str, str] = {"report": "off"}
        self.writable = writable

    def choice(self, skill: str) -> str:
        return self.made.get(skill, "on")

    def choose(self, skill: str, choice: str) -> bool:
        if self.writable:
            self.made[skill] = choice
        return self.writable


def tab(choices: Choices | None = None):
    from skills_tab import SkillsTab

    choices = choices or Choices()
    return SkillsTab(
        read=lambda: [REPORT, REVIEW],
        choice=choices.choice,
        choose=choices.choose,
        origin=lambda path: "Comes with the Engine" if "builtin" in path else "Yours",
        background=now,
    ), choices


def test_each_skill_shows_where_it_came_from_and_what_it_is_for() -> None:
    shown, _ = tab()
    words = texts(shown)
    assert "Review" in words and "Report" in words
    assert any("Yours" in w and "Review a change" in w for w in words)
    assert any("Comes with the Engine" in w for w in words)
