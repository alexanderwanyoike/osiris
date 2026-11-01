"""Connectors (#155): the MCP servers a person adds to Thoth.

They are kept in the Engine's own config, under ``mcp.servers``, where the
Engine reads and reloads them and where they stay the person's (ADR 0020);
opencode 2.2.4 offers no API that saves them.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from osiris.harness.engine_config import ENGINE_CONFIG, edit, read
from osiris.harness.picker import Entry
from osiris.platform import FileSystem


@dataclass(frozen=True)
class Connector:
    name: str
    #: A local server's command, or empty for one reached by ``url``.
    command: tuple[str, ...] = ()
    url: str = ""
    on: bool = True


@dataclass(frozen=True)
class State:
    """How the Engine finds a server: "connected", "pending", "disabled",
    "failed" or "needs_auth"."""

    status: str
    #: Why it failed or needs signing in to.
    error: str = ""
    #: The Engine's integration a sign-in goes through.
    integration: str = ""


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


def read_connectors(files: FileSystem, home: Path) -> list[Connector]:
    return connectors(read(files, home / ENGINE_CONFIG))


def save_connector(files: FileSystem, home: Path, connector: Connector) -> bool:
    """Whether it could be saved: a commented config is left to the person."""
    return edit(
        files, home / ENGINE_CONFIG, lambda config: bool(saved(config, connector))
    )


def remove_connector(files: FileSystem, home: Path, name: str) -> bool:
    return edit(files, home / ENGINE_CONFIG, lambda config: bool(removed(config, name)))


def offered_servers(states: dict[str, State], own: str) -> list[Entry]:
    """The servers @ offers: those working now, but not ``own``, the tool
    server Osiris attaches for itself."""
    return [
        Entry("connector", name, name, "Connector")
        for name, state in sorted(states.items())
        if state.status == "connected" and name != own
    ]


class Servers(Protocol):
    def connector_states(self, directory: Path) -> dict[str, State]: ...

    def resources(self, directory: Path) -> list[Entry]: ...


def command_of(typed: str) -> tuple[str, ...]:
    """The argv a typed command names, or none while a quote is open. Split
    as a shell would but never given to one: the Engine runs the argv."""
    try:
        return tuple(shlex.split(typed))
    except ValueError:
        return ()


_SAID = {
    "connected": ("Connected", "success"),
    "pending": ("Starting", "muted"),
    "disabled": ("Off", "muted"),
    "needs_auth": ("Needs signing in", "warning"),
}


def said_of(state: State | None) -> tuple[str, str]:
    """A server's state in plain words, and the tone it is shown in. One the
    Engine has not reported has not been started for the folder yet."""
    if state is None:
        return "Not started yet", "muted"
    if state.status == "failed":
        return f"Failed: {state.error}" if state.error else "Failed", "danger"
    return _SAID.get(state.status, (state.status, "muted"))
