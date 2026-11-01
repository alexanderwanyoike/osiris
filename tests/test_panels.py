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
