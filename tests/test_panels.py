"""The Canvas's panels (#194): a group of tabs for each kind of thing it shows,
tiled side by side in the order they opened."""

from __future__ import annotations

from osiris.harness.panels import Kind, Panels, Tab

MAIN = Tab(Kind.CODE, "pomodoro/main.py", "main.py")
README = Tab(Kind.CODE, "pomodoro/README.md", "README.md")
TIDY = Tab(Kind.CHANGES, "msg_3", "Tidy main.py")


def test_a_tab_opens_in_the_group_of_its_kind_and_is_selected() -> None:
    panels = Panels()
    panels.open(MAIN)
    panels.open(README)
    (code,) = panels.groups
    assert (code.kind, code.tabs, code.selected) == (Kind.CODE, [MAIN, README], README)


def test_a_tab_already_open_is_selected_again_not_opened_twice() -> None:
    panels = Panels()
    panels.open(MAIN)
    panels.open(README)
    panels.open(MAIN)
    (code,) = panels.groups
    assert (code.tabs, code.selected) == ([MAIN, README], MAIN)


def test_groups_tile_in_the_order_they_opened() -> None:
    panels = Panels()
    panels.open(TIDY)
    panels.open(MAIN)
    assert [group.kind for group in panels.groups] == [Kind.CHANGES, Kind.CODE]


def test_closing_a_tab_selects_the_one_before_it() -> None:
    panels = Panels()
    panels.open(MAIN)
    panels.open(README)
    panels.close(README)
    (code,) = panels.groups
    assert (code.tabs, code.selected) == ([MAIN], MAIN)


def test_closing_a_groups_last_tab_closes_the_group() -> None:
    """The other groups take its room."""
    panels = Panels()
    panels.open(MAIN)
    panels.open(TIDY)
    panels.close(MAIN)
    assert [group.kind for group in panels.groups] == [Kind.CHANGES]
