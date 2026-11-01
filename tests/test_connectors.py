"""Connectors (#155): MCP servers the person adds, kept in the Engine's own
config so they are theirs and the Engine reloads them."""

from __future__ import annotations

from osiris.harness.connectors import Connector, connectors

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

