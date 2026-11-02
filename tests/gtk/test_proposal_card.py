"""A skill Osiris proposes (#154), on a card under the answer: read in full,
kept or not."""

from __future__ import annotations

from gi.repository import Gtk

from osiris.harness.proposals import Proposal

from .conftest import texts, widgets

TIDY = Proposal("tidy-imports", "Sort and group imports", "1. Run ruff.\n2. Check.")


def card(decided: bool | None = None):
    from proposal_card import ProposalCard

    kept: list[str] = []
    declined: list[str] = []
    shown = ProposalCard(
        TIDY,
        decided,
        on_keep=lambda p: kept.append(p.name),
        on_decline=lambda p: declined.append(p.name),
    )
    return shown, kept, declined


def button(shown, label: str) -> Gtk.Button:
    return next(
        w
        for w in widgets(shown)
        if isinstance(w, Gtk.Button) and w.get_label() == label
    )


def test_the_proposal_is_shown_in_full() -> None:
    shown, _, _ = card()
    words = texts(shown)
    assert "tidy-imports" in words
    assert "Sort and group imports" in words
    assert "1. Run ruff.\n2. Check." in words


def test_keeping_or_declining_is_passed_on() -> None:
    shown, kept, declined = card()
    button(shown, "Keep it").emit("clicked")
    assert kept == ["tidy-imports"]
    shown, kept, declined = card()
    button(shown, "No thanks").emit("clicked")
    assert declined == ["tidy-imports"]


def test_once_decided_it_says_which_and_offers_no_choice() -> None:
    shown, _, _ = card(decided=True)
    assert "Kept among your skills" in texts(shown)
    assert not any(isinstance(w, Gtk.Button) for w in widgets(shown))
    shown, _, _ = card(decided=False)
    assert "Not kept" in texts(shown)


def test_the_skills_text_never_takes_the_keyboard_and_so_is_never_all_selected() -> (
    None
):
    """When the buttons go, focus would fall to the first label that takes it,
    and a selectable label selects all it says as it does."""
    shown, _, _ = card(decided=True)
    body = next(w for w in widgets(shown) if w.has_css_class("harness-proposal-body"))
    assert body.get_selectable()
    assert not body.get_focusable()
