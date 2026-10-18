"""What the Harness may do with Themes: list them, make one from a Theme
intent, and apply one. A model supplies only the intent; the colours are
Osiris's (CONTEXT.md)."""

from __future__ import annotations

import pytest

from osiris.model.colour import Colour
from osiris.themes.actions import (
    ThemeActionError,
    apply_theme,
    create_theme,
    list_themes,
)
from osiris.themes.derive import build
from osiris.themes.intent import Harmony, Mood, ThemeIntent, seeds
from osiris.themes.store import FakeThemeStore


def stored(name: str, label: str, dark: bool = True) -> dict[str, object]:
    return {"name": name, "label": label, "dark": dark}


def test_listing_names_every_theme_and_marks_the_current_one() -> None:
    store = FakeThemeStore(
        themes=[
            stored("nord", "Nord"),
            stored("rose-pine-dawn", "Rose Pine Dawn", False),
        ],
        current="nord",
    )
    assert list_themes(store) == [
        {"name": "nord", "label": "Nord", "dark": True, "current": True},
        {
            "name": "rose-pine-dawn",
            "label": "Rose Pine Dawn",
            "dark": False,
            "current": False,
        },
    ]


def test_a_theme_is_made_by_osiris_rules_from_the_intent_alone() -> None:
    store = FakeThemeStore()
    name = create_theme(
        store,
        label="Harbour",
        seed="#3a6ea5",
        harmony="analogous",
        mood="muted",
        dark=True,
    )
    intent = ThemeIntent(
        seed=Colour("#3a6ea5"), harmony=Harmony.ANALOGOUS, mood=Mood.MUTED, dark=True
    )
    assert name == "harbour"
    assert store.saved == [build("harbour", "Harbour", seeds(intent))]


def test_making_a_theme_never_replaces_one_that_exists() -> None:
    store = FakeThemeStore(themes=[stored("harbour", "Harbour")])
    with pytest.raises(ThemeActionError, match="already a theme called Harbour"):
        create_theme(
            store,
            label="Harbour",
            seed="#3a6ea5",
            harmony="analogous",
            mood="muted",
            dark=True,
        )
    assert store.saved == []


def test_a_seed_that_is_not_a_colour_is_refused() -> None:
    with pytest.raises(ThemeActionError, match="not a colour"):
        create_theme(
            FakeThemeStore(),
            label="Harbour",
            seed="sea blue",
            harmony="analogous",
            mood="muted",
            dark=True,
        )


@pytest.mark.parametrize(
    ("harmony", "mood", "offered"),
    [
        ("pretty", "muted", "analogous, complementary"),
        ("analogous", "moody", "muted, balanced, vivid, pastel"),
    ],
)
def test_an_unknown_harmony_or_mood_is_refused_naming_the_choices(
    harmony: str, mood: str, offered: str
) -> None:
    with pytest.raises(ThemeActionError, match=offered):
        create_theme(
            FakeThemeStore(),
            label="Harbour",
            seed="#3a6ea5",
            harmony=harmony,
            mood=mood,
            dark=True,
        )


def test_applying_a_theme_reports_the_one_it_replaced() -> None:
    store = FakeThemeStore(
        themes=[stored("nord", "Nord"), stored("harbour", "Harbour")], current="nord"
    )
    assert apply_theme(store, "harbour") == "nord"
    assert store.applied == ["harbour"]


def test_applying_on_a_machine_that_never_chose_one_replaces_nothing() -> None:
    store = FakeThemeStore(themes=[stored("harbour", "Harbour")])
    assert apply_theme(store, "harbour") is None


def test_applying_an_unknown_theme_is_refused() -> None:
    store = FakeThemeStore(themes=[stored("nord", "Nord")])
    with pytest.raises(ThemeActionError, match="no theme called harbour"):
        apply_theme(store, "harbour")
    assert store.applied == []
