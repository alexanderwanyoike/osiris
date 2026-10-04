"""Packaged configuration."""

from __future__ import annotations

import json
import re

import pytest

from osiris.resources.loader import (
    MissingPlaceholder,
    MissingResource,
    Resources,
)


@pytest.fixture
def resources() -> Resources:
    return Resources()


class TestReading:
    def test_a_packaged_file_reads(self, resources: Resources) -> None:
        assert "oh-my-zsh" in resources.read("shell/zshrc")

    def test_a_missing_file_raises_rather_than_returning_empty(
        self, resources: Resources
    ) -> None:
        with pytest.raises(MissingResource):
            resources.read("nowhere/at/all")

    def test_exists_reports_honestly(self, resources: Resources) -> None:
        assert resources.exists("terminal/ghostty.conf")
        assert not resources.exists("terminal/nonsense.conf")


class TestTheConfigurationItself:
    """The point of ADR 0004: these are now checkable.

    As a Python string constant, a malformed fastfetch config was a perfectly
    valid Python program. The error surfaced at a user's first login, as
    fastfetch silently falling back to the stock Arch art.
    """

    def test_the_fastfetch_config_is_valid_json(self, resources: Resources) -> None:
        raw = resources.read("fetch/fastfetch.jsonc")
        json.loads(re.sub(r"^\s*//.*$", "", raw, flags=re.M))

    def test_the_fastfetch_logo_is_the_text_one(self, resources: Resources) -> None:
        """fastfetch on Arch links no image libraries.

        A PNG logo silently falls back to the stock Arch ASCII art, so the
        source has to be the braille text file and the type file-raw.
        """
        raw = resources.read("fetch/fastfetch.jsonc")
        config = json.loads(re.sub(r"^\s*//.*$", "", raw, flags=re.M))
        assert config["logo"]["type"] == "file-raw"
        assert config["logo"]["source"].endswith(".txt")

    def test_the_shell_config_does_not_assume_a_writable_config_dir(
        self, resources: Resources
    ) -> None:
        """It creates what it needs.

        ZSH_CUSTOM lives under ~/.config/osiris, and on a fresh install nothing
        has created that yet.
        """
        assert "mkdir -p" in resources.read("shell/zshrc")


class TestRendering:
    def test_placeholders_are_substituted(self) -> None:
        rendered = Resources.substitute(
            "theme @NAME@ at @SIZE@", {"name": "nord", "size": 12}
        )
        assert rendered == "theme nord at 12"

    def test_a_placeholder_may_be_called_name(self) -> None:
        """Values are a mapping, not keyword arguments.

        With **values this collided with render's own `name` parameter and
        raised TypeError - found by this test, which is why the signature
        changed.
        """
        assert Resources.substitute("@NAME@", {"name": "ok"}) == "ok"

    def test_a_missing_value_is_an_error(self) -> None:
        with pytest.raises(MissingPlaceholder):
            Resources.substitute("needs @COLOUR@", {"name": "x"})

    def test_braces_are_left_alone(self) -> None:
        """The reason this is not str.format.

        JSON, ini and GRUB theme files are full of braces that mean something
        to their own format and nothing to Python.
        """
        document = '{ "logo": { "padding": { "top": 1 } }, "n": "@NAME@" }'
        assert Resources.substitute(document, {"name": "x"}) == (
            '{ "logo": { "padding": { "top": 1 } }, "n": "x" }'
        )
