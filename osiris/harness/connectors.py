"""Connectors (#155): the MCP servers a person adds to Thoth.

They are kept in the Engine's own config, under ``mcp.servers``, where the
Engine reads and reloads them and where they stay the person's (ADR 0020);
opencode 2.2.4 offers no API that saves them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Connector:
    name: str
    #: A local server's command, or empty for one reached by ``url``.
    command: tuple[str, ...] = ()
    url: str = ""
    on: bool = True


def connectors(config: dict[str, Any]) -> list[Connector]:
    servers: dict[str, dict[str, Any]] = config.get("mcp", {}).get("servers", {})
    return [
        Connector(
            name,
            command=tuple(server.get("command", ())),
            url=server.get("url", ""),
            on=not server.get("disabled", False),
        )
        for name, server in sorted(servers.items())
    ]


def saved(config: dict[str, Any], connector: Connector) -> dict[str, Any]:
    """``config`` with ``connector`` added or changed in place; what else the
    person set on the server, such as headers or sign-in, is kept."""
    servers = config.setdefault("mcp", {}).setdefault("servers", {})
    server = dict(servers.get(connector.name, {}))
    for key in ("type", "command", "url", "disabled"):
        server.pop(key, None)
    where: dict[str, Any] = (
        {"type": "local", "command": list(connector.command)}
        if connector.command
        else {"type": "remote", "url": connector.url}
    )
    servers[connector.name] = {
        **where,
        **server,
        **({} if connector.on else {"disabled": True}),
    }
    return config


def removed(config: dict[str, Any], name: str) -> dict[str, Any]:
    config.get("mcp", {}).get("servers", {}).pop(name, None)
    return config
