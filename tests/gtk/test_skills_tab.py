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


def test_a_skill_opens_to_show_what_it_says() -> None:
    from gi.repository import Adw

    shown, _ = tab()
    review = next(
        w
        for w in widgets(shown)
        if isinstance(w, Adw.ExpanderRow) and w.get_title() == "Review"
    )
    review.set_expanded(True)
    assert "# Review\nRead the diff, then the tests." in texts(review)


def choosers(shown) -> dict[str, Gtk.DropDown]:
    return {d.skill: d for d in widgets(shown) if isinstance(d, Gtk.DropDown)}


def test_each_skill_shows_its_choice_and_a_new_one_is_kept() -> None:
    from skills_tab import CHOICES

    shown, choices = tab()
    picked = choosers(shown)
    assert CHOICES[picked["report"].get_selected()] == "off"
    assert CHOICES[picked["review"].get_selected()] == "on"
    picked["review"].set_selected(CHOICES.index("ask"))
    assert choices.made["review"] == "ask"


def test_a_choice_that_could_not_be_kept_says_why_and_goes_back() -> None:
    from skills_tab import CHOICES

    shown, _ = tab(Choices(writable=False))
    review = choosers(shown)["review"]
    review.set_selected(CHOICES.index("off"))
    assert CHOICES[review.get_selected()] == "on"
    assert any("comments" in w for w in texts(shown))
