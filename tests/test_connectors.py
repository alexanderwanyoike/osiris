"""Connectors (#155): MCP servers the person adds, kept in the Engine's own
config so they are theirs and the Engine reloads them."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from osiris.harness.connectors import Connector, State, connectors
from osiris.harness.engine_config import ENGINE_CONFIG
from osiris.platform import FakeFileSystem

CONFIG = {
    "permissions": [],
    "mcp": {
        "servers": {
            "wiki": {"type": "remote", "url": "https://mcp.example.com/mcp"},
            "files": {"type": "local", "command": ["npx", "files"], "disabled": True},
        }
    },
}


def test_the_servers_in_the_config_are_the_connectors_by_name() -> None:
    assert connectors(CONFIG) == [
        Connector("files", command=("npx", "files"), on=False),
        Connector("wiki", url="https://mcp.example.com/mcp"),
    ]


def test_a_config_without_servers_has_no_connectors() -> None:
    assert connectors({}) == []


def test_saving_a_connector_keeps_what_else_the_person_set_on_it() -> None:
    from osiris.harness.connectors import saved

    config = {
        "mcp": {
            "servers": {"wiki": {"type": "remote", "url": "u", "headers": {"A": "b"}}}
        }
    }
    after = saved(
        config, Connector("wiki", url="https://new.example.com/mcp", on=False)
    )
    assert after["mcp"]["servers"]["wiki"] == {
        "type": "remote",
        "url": "https://new.example.com/mcp",
        "headers": {"A": "b"},
        "disabled": True,
    }


def test_a_server_by_command_is_saved_as_local_without_a_url() -> None:
    from osiris.harness.connectors import saved

    config = {"mcp": {"servers": {"wiki": {"type": "remote", "url": "u"}}}}
    after = saved(config, Connector("wiki", command=("npx", "wiki")))
    assert after["mcp"]["servers"]["wiki"] == {
        "type": "local",
        "command": ["npx", "wiki"],
    }


def test_removing_a_connector_leaves_the_others() -> None:
    from osiris.harness.connectors import removed

    assert connectors(removed(CONFIG, "wiki")) == [
        Connector("files", command=("npx", "files"), on=False)
    ]


HOME = Path("/home/tester")


def test_a_saved_connector_is_in_the_engines_config_and_read_back() -> None:
    from osiris.harness.connectors import read_connectors, save_connector

    files = FakeFileSystem()
    files.write(HOME / ENGINE_CONFIG, json.dumps({"permissions": []}))
    assert save_connector(files, HOME, Connector("wiki", url="https://w/mcp"))
    assert read_connectors(files, HOME) == [Connector("wiki", url="https://w/mcp")]
    assert json.loads(files.read(HOME / ENGINE_CONFIG))["permissions"] == []


def test_a_commented_config_is_left_and_saving_says_so() -> None:
    from osiris.harness.connectors import save_connector

    files = FakeFileSystem()
    files.write((HOME / ENGINE_CONFIG).with_suffix(".jsonc"), "// mine\n{}")
    assert not save_connector(files, HOME, Connector("wiki", url="https://w/mcp"))
    assert not files.exists(HOME / ENGINE_CONFIG)


def test_a_removed_connector_is_gone_from_the_engines_config() -> None:
    from osiris.harness.connectors import read_connectors, remove_connector

    files = FakeFileSystem()
    files.write(HOME / ENGINE_CONFIG, json.dumps(CONFIG))
    assert remove_connector(files, HOME, "wiki")
    assert [c.name for c in read_connectors(files, HOME)] == ["files"]


def test_only_connected_servers_are_offered_and_not_osiris_own() -> None:
    from osiris.harness.connectors import State, offered_servers
    from osiris.harness.picker import Entry

    states = {
        "wiki": State("connected"),
        "tracker": State("needs_auth", "sign in", "mcp-tracker"),
        "files": State("disabled"),
        "osiris": State("connected"),
    }
    assert offered_servers(states, own="osiris") == [
        Entry("connector", "wiki", "wiki", "Connector")
    ]


def test_a_typed_command_is_split_as_a_shell_would_without_running_one() -> None:
    from osiris.harness.connectors import command_of

    assert command_of('npx -y "@acme/server files" --root ~/Notes') == (
        "npx",
        "-y",
        "@acme/server files",
        "--root",
        "~/Notes",
    )


def test_a_command_with_an_unclosed_quote_is_no_command() -> None:
    from osiris.harness.connectors import command_of

    assert command_of('npx "server') == ()


@pytest.mark.parametrize(
    ("state", "said"),
    [
        (State("connected"), ("Connected", "success")),
        (State("pending"), ("Starting", "muted")),
        (State("disabled"), ("Off", "muted")),
        (
            State("failed", "connection refused"),
            ("Failed: connection refused", "danger"),
        ),
        (State("needs_auth", "401", "mcp-x"), ("Needs signing in", "warning")),
        (None, ("Not started yet", "muted")),
    ],
)
def test_each_state_is_said_in_plain_words_with_a_tone(
    state: State | None, said: tuple[str, str]
) -> None:
    from osiris.harness.connectors import said_of

    assert said_of(state) == said
