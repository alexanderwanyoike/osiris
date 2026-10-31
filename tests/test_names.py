"""Names made from labels."""

from __future__ import annotations

import pytest

from osiris.model.names import is_slug, slug


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


@pytest.mark.parametrize("name", ["rose-pine", "nord", "untitled"])
def test_a_slug_is_a_name(name: str) -> None:
    assert is_slug(name)


@pytest.mark.parametrize("name", ["", "Nord", "a b", "../x", "a/b", "-x", "x\n"])
def test_anything_else_is_not_a_name(name: str) -> None:
    """A name is joined into paths that are removed, so one that is not a slug
    could reach outside them."""
    assert not is_slug(name)
