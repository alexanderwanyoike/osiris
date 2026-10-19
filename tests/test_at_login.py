"""What a home needs at login: its first Theme, or its Theme re-applied once
after Osiris is upgraded, so what Osiris generates in it catches up."""

from __future__ import annotations

from osiris.themes.at_login import theme_to_apply

DEFAULT = "osiris-obsidian"


def test_a_home_with_no_theme_chosen_starts_on_the_default() -> None:
    assert theme_to_apply(None, None, "0.2.0", DEFAULT) == DEFAULT


def test_after_an_upgrade_the_persons_own_theme_is_re_applied() -> None:
    assert theme_to_apply("nord", "0.1.0", "0.2.0", DEFAULT) == "nord"


def test_a_home_from_before_homes_were_versioned_is_brought_up_to_date() -> None:
    assert theme_to_apply("nord", None, "0.2.0", DEFAULT) == "nord"


def test_a_home_already_up_to_date_is_left_alone() -> None:
    assert theme_to_apply("nord", "0.2.0", "0.2.0", DEFAULT) is None
