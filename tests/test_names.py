"""Names made from labels."""

from __future__ import annotations

import pytest

from osiris.model.names import slug


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
