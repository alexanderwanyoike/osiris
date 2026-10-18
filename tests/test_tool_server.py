"""The Osiris tool server: the Theme actions as MCP tools a model can call."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from osiris.apps.tool_server import TIERS, server, undo
from osiris.harness.log import LOG_FILE, Change, HarnessLog
from osiris.harness.tiers import Tier
from osiris.platform import FakeFileSystem
from osiris.themes.actions import ThemeActionError
from osiris.themes.store import FakeThemeStore

HARBOUR = {
    "label": "Harbour",
    "seed": "#3a6ea5",
    "harmony": "analogous",
    "mood": "muted",
    "dark": True,
}


def new_log() -> HarnessLog:
    return HarnessLog(FakeFileSystem(), Path("/home/tester") / LOG_FILE)


def tools(store: FakeThemeStore) -> dict[str, Any]:
    tool_list = asyncio.run(server(store, new_log()).list_tools())
    return {tool.name: tool for tool in tool_list}


def call(
    store: FakeThemeStore,
    name: str,
    arguments: dict[str, Any],
    log: HarnessLog | None = None,
) -> Any:
    return asyncio.run(server(store, log or new_log()).call_tool(name, arguments))


def test_the_server_offers_the_theme_actions_and_nothing_else() -> None:
    assert set(tools(FakeThemeStore())) == {
        "list_themes",
        "create_theme",
        "apply_theme",
    }


def test_listing_is_a_look_and_making_or_applying_an_undoable_change() -> None:
    assert TIERS == {
        "list_themes": Tier.LOOK,
        "create_theme": Tier.UNDOABLE,
        "apply_theme": Tier.UNDOABLE,
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
    call(store, "create_theme", HARBOUR)
    assert [theme["name"] for theme in store.saved] == ["harbour"]


def test_a_refused_action_reaches_the_model_with_its_reason() -> None:
    store = FakeThemeStore(themes=[{"name": "nord", "label": "Nord", "dark": True}])
    with pytest.raises(ToolError, match="no theme called harbour"):
        call(store, "apply_theme", {"name": "harbour"})


def test_the_server_logs_only_warnings_into_the_engines_output() -> None:
    assert server(FakeThemeStore(), new_log()).settings.log_level == "WARNING"


def test_making_a_theme_is_logged_as_a_change_undone_by_deleting_it() -> None:
    log = new_log()
    call(FakeThemeStore(), "create_theme", HARBOUR, log)
    assert log.last_changes() == [
        Change("Made Harbour", {"action": "delete_theme", "name": "harbour"})
    ]


def test_applying_is_logged_as_a_change_undone_by_the_theme_it_replaced() -> None:
    log = new_log()
    store = FakeThemeStore(
        themes=[
            {"name": "nord", "label": "Nord", "dark": True},
            {"name": "harbour", "label": "Harbour", "dark": True},
        ],
        current="nord",
    )
    call(store, "apply_theme", {"name": "harbour"}, log)
    assert log.last_changes() == [
        Change("Applied Harbour", {"action": "apply_theme", "name": "nord"})
    ]


def test_a_first_theme_applied_has_nothing_to_return_to() -> None:
    log = new_log()
    store = FakeThemeStore(
        themes=[{"name": "harbour", "label": "Harbour", "dark": True}]
    )
    call(store, "apply_theme", {"name": "harbour"}, log)
    assert log.last_changes() == [Change("Applied Harbour", None)]


def test_a_refused_action_changes_nothing_and_logs_no_change() -> None:
    log = new_log()
    with pytest.raises(ToolError):
        call(FakeThemeStore(), "apply_theme", {"name": "harbour"}, log)
    assert log.last_changes() == []


def test_undo_runs_the_step_a_change_recorded() -> None:
    store = FakeThemeStore(
        themes=[
            {"name": "nord", "label": "Nord", "dark": True},
            {"name": "harbour", "label": "Harbour", "dark": True},
        ],
        current="harbour",
    )
    undo(store, {"action": "apply_theme", "name": "nord"})
    undo(store, {"action": "delete_theme", "name": "harbour"})
    assert store.applied == ["nord"]
    assert store.deleted == ["harbour"]


def test_an_unknown_undo_step_is_refused() -> None:
    with pytest.raises(ThemeActionError, match="cannot undo"):
        undo(FakeThemeStore(), {"action": "format_disk", "name": "sda"})


def test_a_model_is_told_a_seed_is_a_hex_colour_before_it_tries() -> None:
    seed = tools(FakeThemeStore())["create_theme"].inputSchema["properties"]["seed"]
    assert seed["pattern"] == "^#[0-9a-fA-F]{6}$"
