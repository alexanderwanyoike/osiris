"""Finding a theme among many: families, search, filters and favourites."""

from __future__ import annotations

import pytest

from osiris.themes.library import Family, Filter, arrange, family_of, slug


def theme(name: str, accent: str, dark: bool = True, label: str | None = None) -> dict:
    return {
        "name": name,
        "label": label or name.replace("-", " ").title(),
        "dark": dark,
        "colors": {"accent": accent},
    }


NORD = theme("nord", "#88c0d0")
TOKYO = theme("tokyo-night", "#7aa2f7")
FOREST = theme("everforest", "#a7c080")
DAWN = theme("rose-pine-dawn", "#907aa9", dark=False, label="Rose Pine Dawn")
EMBER = theme("ember", "#e4572e")
SLATE = theme("slate", "#8a8f94")
LIBRARY = [NORD, TOKYO, FOREST, DAWN, EMBER, SLATE]


@pytest.mark.parametrize(
    ("accent", "family"),
    [
        ("#88c0d0", Family.TEAL),
        ("#7aa2f7", Family.BLUE),
        ("#a7c080", Family.GREEN),
        ("#907aa9", Family.PURPLE),
        ("#e4572e", Family.RED),
        ("#e5a50a", Family.YELLOW),
        ("#f5821f", Family.ORANGE),
        ("#eb6f92", Family.PINK),
        ("#8a8f94", Family.NEUTRAL),
    ],
)
def test_a_theme_belongs_to_the_family_of_its_accent(
    accent: str, family: Family
) -> None:
    assert family_of(theme("t", accent)) is family


def titles(sections: list[tuple[str, list[dict]]]) -> list[str]:
    return [title for title, _ in sections]


def names(sections: list[tuple[str, list[dict]]]) -> list[str]:
    return [t["name"] for _, themes in sections for t in themes]


def test_themes_are_grouped_by_family_in_wheel_order() -> None:
    sections = arrange(LIBRARY)
    assert titles(sections) == [
        "Reds",
        "Greens",
        "Teals",
        "Blues",
        "Purples",
        "Neutrals",
    ]


def test_favourites_come_first_and_are_not_repeated() -> None:
    sections = arrange(LIBRARY, favourites={"everforest", "ember"})
    assert sections[0][0] == "Favourites"
    assert [t["name"] for t in sections[0][1]] == ["ember", "everforest"]
    assert names(sections).count("everforest") == 1


def test_search_matches_the_label_ignoring_case() -> None:
    assert names(arrange(LIBRARY, query="PINE")) == ["rose-pine-dawn"]


def test_search_matches_a_family() -> None:
    assert names(arrange(LIBRARY, query="green")) == ["everforest"]


@pytest.mark.parametrize(
    ("chosen", "expected"),
    [
        (Filter.DARK, {"nord", "tokyo-night", "everforest", "ember", "slate"}),
        (Filter.LIGHT, {"rose-pine-dawn"}),
        (Filter.ALL, {t["name"] for t in LIBRARY}),
    ],
)
def test_filters_choose_by_variant(chosen: Filter, expected: set[str]) -> None:
    assert set(names(arrange(LIBRARY, chosen=chosen))) == expected


def test_mine_shows_only_user_themes() -> None:
    sections = arrange(LIBRARY, chosen=Filter.MINE, mine={"ember"})
    assert names(sections) == ["ember"]


def test_within_a_section_themes_are_alphabetical() -> None:
    blues = [theme("zed", "#3a6ea5"), theme("aqua-blue", "#4a7fd0"), TOKYO]
    assert names(arrange(blues)) == ["aqua-blue", "tokyo-night", "zed"]


def test_nothing_matching_gives_no_sections() -> None:
    assert arrange(LIBRARY, query="no such theme") == []


@pytest.mark.parametrize(
    ("label", "name"),
    [
        ("Harbour", "harbour"),
        ("Late  Night: Teal!", "late-night-teal"),
        ("  Rosé  ", "ros"),
        ("!!!", "untitled"),
    ],
)
def test_a_label_becomes_a_name_safe_as_a_file_and_a_gtk_theme(
    label: str, name: str
) -> None:
    assert slug(label) == name
