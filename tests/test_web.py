"""What the browser group's address line makes of what is typed (#197)."""

from __future__ import annotations

import pytest

from osiris.harness.web import address


@pytest.mark.parametrize(
    ("typed", "goes_to"),
    [
        ("https://docs.gtk.org/gtk4/", "https://docs.gtk.org/gtk4/"),
        ("docs.gtk.org", "https://docs.gtk.org"),
        ("  python.org/3/  ", "https://python.org/3/"),
        ("localhost:8000", "http://localhost:8000"),
        ("gtk label css", "https://duckduckgo.com/?q=gtk+label+css"),
        ("why & how", "https://duckduckgo.com/?q=why+%26+how"),
    ],
)
def test_an_address_is_kept_a_site_gets_https_and_words_are_searched(
    typed: str, goes_to: str
) -> None:
    assert address(typed) == goes_to
