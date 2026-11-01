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
