"""The Skin tools the Harness's model is given: it puts Skins on, checked and
worn by Osiris and undoable, and makes none of its own."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from osiris.apps.tool_server import TIERS, instructions, server
from osiris.harness.log import LOG_FILE, HarnessLog
from osiris.harness.tiers import Tier
from osiris.platform import FakeFileSystem, FakeRunner
from osiris.programs.programs import Programs
from osiris.skins.store import FakeSkinStore
from osiris.themes.store import FakeThemeStore
from osiris.themes.wallpapers import UserWallpapers

HOME = Path("/home/tester")
SKIN_TOOLS = {
    "list_skins": Tier.LOOK,
    "wear_skin": Tier.UNDOABLE,
}


def call(
    skins: FakeSkinStore, name: str, arguments: dict[str, Any], log: HarnessLog
) -> Any:
    subject = server(
        FakeThemeStore(),
        Programs(FakeFileSystem(), FakeRunner(), HOME),
        log,
        UserWallpapers(FakeFileSystem(), FakeRunner(), HOME / "w", ""),
        skins=skins,
    )
    return asyncio.run(subject.call_tool(name, arguments))


def text(result: Any) -> str:
    return "".join(getattr(part, "text", "") for part in result.content)


def new_log() -> HarnessLog:
    return HarnessLog(FakeFileSystem(), HOME / LOG_FILE)


def test_the_skin_tools_are_offered_with_their_reach() -> None:
    for name, tier in SKIN_TOOLS.items():
        assert TIERS[name] is tier


def test_a_skin_with_problems_is_not_worn_and_the_model_is_told_why() -> None:
    skins = FakeSkinStore(problems={"colloid": ["follow.py is not part of a Skin"]})
    with pytest.raises(ToolError, match=r"follow\.py is not part of a Skin"):
        call(skins, "wear_skin", {"name": "colloid"}, new_log())
    assert skins.worn() == "osiris"


def test_wearing_is_undone_by_wearing_the_skin_it_replaced() -> None:
    skins, log = FakeSkinStore(), new_log()
    call(skins, "wear_skin", {"name": "colloid"}, log)
    assert skins.worn() == "colloid"
    assert log.last_changes()[-1].undo == {"action": "wear_skin", "name": "osiris"}


def test_osiris_wears_skins_but_builds_none() -> None:
    """Skins Osiris made looked poor in every test. A person can still work on
    one with an agent of their own, but Osiris offers no tools for it."""
    subject = server(
        FakeThemeStore(),
        Programs(FakeFileSystem(), FakeRunner(), HOME),
        new_log(),
        UserWallpapers(FakeFileSystem(), FakeRunner(), HOME / "w", ""),
        skins=FakeSkinStore(),
    )
    offered = {tool.name for tool in asyncio.run(subject.list_tools())}
    building = {
        "create_skin",
        "check_skin",
        "import_gtk_theme",
        "install_icon_set",
        "install_fonts",
    }
    assert {"list_skins", "wear_skin"} <= offered
    assert not offered & building
    assert "You do not make or change Skins" in " ".join(
        instructions(auto_mode=False).split()
    )
