"""Packaged configuration."""

from __future__ import annotations

import configparser
import json
import re
from importlib import resources as importlib_resources

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


#: Every key-file resource, with the values it is rendered with in use. These
#: are GKeyFile, desktop-entry and systemd formats: all "[group]" and
#: "key=value", which configparser reads closely enough to catch a missing
#: header, a stray line or an unrendered placeholder.
KEY_FILES = {
    "desktop/dconf-defaults": {
        "applets": "'panel1:left:0:menu@cinnamon.org:0'",
        "dock_items": "'nemo.dockitem'",
        "wallpaper": "/usr/share/backgrounds/osiris/osiris-obsidian.png",
    },
    "desktop/99-osiris.gschema.override": {"wallpaper": "/w.png"},
    "desktop/slick-greeter.conf": {"wallpaper": "/w.png"},
    "desktop/lightdm.conf": {},
    "desktop/plank.desktop": {},
    "desktop/osiris-theme.desktop": {},
    "boot/osiris.plymouth": {},
    "iso/osiris-installer.service": {"launcher": "/usr/local/bin/osiris-installer"},
}


def parsed(text: str) -> configparser.ConfigParser:
    # systemd units repeat keys (After=), so duplicates are allowed; keys keep
    # their case, which every one of these formats is sensitive to.
    parser = configparser.ConfigParser(
        interpolation=None, strict=False, comment_prefixes=("#", ";")
    )
    parser.optionxform = str  # type: ignore[assignment, method-assign]
    parser.read_string(text)
    return parser


class TestEveryKeyFile:
    def test_every_resource_is_covered(self) -> None:
        """A new key-file resource has to be added here to be checked."""
        root = importlib_resources.files("osiris.resources")
        found = {
            f"{group.name}/{entry.name}"
            for group in root.iterdir()
            if group.is_dir() and group.name not in ("__pycache__",)
            for entry in group.iterdir()
            if entry.name.endswith((".conf", ".desktop", ".override", ".service",
                                    ".plymouth"))
            or entry.name == "dconf-defaults"
        }  # fmt: skip
        assert found - {"terminal/ghostty.conf"} == set(KEY_FILES)

    @pytest.mark.parametrize("name", sorted(KEY_FILES))
    def test_it_renders_completely_and_parses(
        self, resources: Resources, name: str
    ) -> None:
        text = resources.render(name, KEY_FILES[name])
        assert not re.search(r"@[A-Z][A-Z0-9_]*@", text), "unrendered marker"
        assert parsed(text).sections(), f"{name} has no [group]"

    @pytest.mark.parametrize(
        "name", ["desktop/plank.desktop", "desktop/osiris-theme.desktop"]
    )
    def test_autostart_entries_are_runnable(
        self, resources: Resources, name: str
    ) -> None:
        entry = parsed(resources.read(name))["Desktop Entry"]
        assert entry["Type"] == "Application"
        assert entry["Exec"]


class TestLauncher:
    def test_it_renders_to_valid_python(self, resources: Resources) -> None:
        text = resources.render(
            "bin/launcher", {"command": "osiris-setup", "script": "/x/setup.py"}
        )
        compile(text, "launcher", "exec")
        assert text.startswith("#!/usr/bin/env python3\n")
        assert '"/x/setup.py"' in text


class TestOsRelease:
    """os-release(5): shell-compatible KEY=value lines, comments allowed."""

    def test_it_names_osiris_and_stays_arch_like(self, resources: Resources) -> None:
        fields = dict(
            line.split("=", 1)
            for line in resources.read("system/os-release").splitlines()
            if line and not line.startswith("#")
        )
        assert fields["NAME"] == '"Osiris"'
        assert fields["PRETTY_NAME"] == '"Osiris"'
        assert fields["ID"] == "osiris"
        assert fields["ID_LIKE"] == "arch"
        assert all(re.fullmatch(r"[A-Z_]+", key) for key in fields)
