"""The Allowed tab (#181): every rule saved by "Always allow here", with its
Project, each one taken back from here."""

from __future__ import annotations

from pathlib import Path

from gi.repository import Gtk

from osiris.harness.saved_rules import SavedRule

from .conftest import now, texts, widgets

NPM = SavedRule("rule_1", "bash", "npm *", Path("/home/tester/Code/timer"))
EDIT = SavedRule("rule_2", "edit", "*", None)


def tab(rules: list[SavedRule]):
    from allowed_tab import AllowedTab

    held = list(rules)
    removed: list[str] = []

    def remove(rule: SavedRule) -> None:
        removed.append(rule.id)
        held.remove(rule)

    shown = AllowedTab(
        read=lambda: list(held),
        remove=remove,
        project_name=lambda path: path.name,
        background=now,
    )
    return shown, removed


def test_each_saved_rule_shows_what_it_allows_and_where() -> None:
    shown, _ = tab([NPM, EDIT])
    words = texts(shown)
    assert "bash: npm *" in words and "timer" in words
    assert "edit: *" in words and "Every Project" in words


def test_taking_a_rule_back_removes_it_from_the_list() -> None:
    shown, removed = tab([NPM, EDIT])
    trash = next(
        w
        for w in widgets(shown)
        if isinstance(w, Gtk.Button) and w.get_tooltip_text() == "Take back bash: npm *"
    )
    trash.emit("clicked")
    assert removed == ["rule_1"]
    assert "bash: npm *" not in texts(shown)


def test_with_nothing_saved_it_says_how_rules_come_to_be() -> None:
    shown, _ = tab([])
    assert any("Always allow here" in w for w in texts(shown))
