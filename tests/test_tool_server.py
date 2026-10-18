"""The Osiris tool server: the Theme actions as MCP tools a model can call."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from osiris.apps.tool_server import server
from osiris.themes.store import FakeThemeStore


def tools(store: FakeThemeStore) -> dict[str, Any]:
    return {tool.name: tool for tool in asyncio.run(server(store).list_tools())}


def call(store: FakeThemeStore, name: str, arguments: dict[str, Any]) -> Any:
    return asyncio.run(server(store).call_tool(name, arguments))


def test_the_server_offers_the_theme_actions_and_nothing_else() -> None:
    assert set(tools(FakeThemeStore())) == {
        "list_themes",
        "create_theme",
        "apply_theme",
    }


def test_only_listing_is_marked_as_a_look() -> None:
    offered = tools(FakeThemeStore())
    assert offered["list_themes"].annotations.readOnlyHint is True
    for change in ("create_theme", "apply_theme"):
        assert offered[change].annotations.readOnlyHint is False


def test_a_model_is_offered_exactly_the_harmonies_and_moods_osiris_knows() -> None:
    schema = tools(FakeThemeStore())["create_theme"].inputSchema
    choices = {name: definition["enum"] for name, definition in schema["$defs"].items()}
    assert choices == {
        "Harmony": [
            "analogous",
            "complementary",
            "split-complementary",
            "triadic",
            "monochrome",
        ],
        "Mood": ["muted", "balanced", "vivid", "pastel"],
    }


def test_making_a_theme_through_the_server_keeps_it() -> None:
    store = FakeThemeStore()
    call(
        store,
        "create_theme",
        {
            "label": "Harbour",
            "seed": "#3a6ea5",
            "harmony": "analogous",
            "mood": "muted",
            "dark": True,
        },
    )
    assert [theme["name"] for theme in store.saved] == ["harbour"]


def test_a_refused_action_reaches_the_model_with_its_reason() -> None:
    store = FakeThemeStore(themes=[{"name": "nord", "label": "Nord", "dark": True}])
    with pytest.raises(ToolError, match="no theme called harbour"):
        call(store, "apply_theme", {"name": "harbour"})
