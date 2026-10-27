"""The Skin tools the Harness's model is given, so it makes Skins the way
Osiris does: from a base Skin, as style sheets and settings, checked and worn
by Osiris, every change undoable, and never with a program of its own."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from osiris.apps.tool_server import TIERS, instructions, server, undo
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
    "create_skin": Tier.UNDOABLE,
    "check_skin": Tier.LOOK,
    "wear_skin": Tier.UNDOABLE,
    "import_gtk_theme": Tier.UNDOABLE,
    "install_icon_set": Tier.UNDOABLE,
    "install_fonts": Tier.UNDOABLE,
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


def test_a_new_skin_starts_from_a_base_and_is_undone_by_deleting_it() -> None:
    skins, log = FakeSkinStore(), new_log()
    answer = text(
        call(skins, "create_skin", {"label": "Old Forest", "base": "colloid"}, log)
    )
    assert "old-forest" in answer and "AGENTS.md" in answer
    assert log.last_changes()[-1].undo == {
        "action": "delete_skin",
        "name": "old-forest",
    }


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


def test_checking_names_every_problem_or_none() -> None:
    skins = FakeSkinStore(
        problems={"colloid": ["a.py is not part of a Skin", "sassc: bad"]}
    )
    assert text(call(skins, "check_skin", {"name": "colloid"}, new_log())) == (
        "a.py is not part of a Skin\nsassc: bad"
    )
    assert text(
        call(FakeSkinStore(), "check_skin", {"name": "colloid"}, new_log())
    ) == ("No problems found.")


def test_downloads_come_in_through_osiris_and_can_be_undone() -> None:
    skins, log = FakeSkinStore(), new_log()
    call(skins, "import_gtk_theme", {"path": "/tmp/Yaru-Green.tar.xz"}, log)
    call(skins, "install_icon_set", {"path": "/tmp/buuf.tar.xz"}, log)
    call(skins, "install_fonts", {"paths": ["/tmp/FiraCode.zip"]}, log)
    assert [change.undo["action"] for change in log.last_changes()[-3:]] == [
        "delete_skin",
        "remove_icon_sets",
        "remove_fonts",
    ]


def test_undoing_skin_steps_reaches_the_skin_store() -> None:
    skins = FakeSkinStore()
    skins.wear("colloid")
    programs = Programs(FakeFileSystem(), FakeRunner(), HOME)
    wallpapers = UserWallpapers(FakeFileSystem(), FakeRunner(), HOME / "w", "")
    undo(
        FakeThemeStore(),
        {"action": "wear_skin", "name": "osiris"},
        programs,
        wallpapers,
        skins=skins,
    )
    assert skins.worn() == "osiris"


def test_the_model_is_told_a_skin_is_data_and_never_a_program() -> None:
    told = instructions(allow_everything=True)
    assert "create_skin" in told and "wear_skin" in told
    assert "never write scripts" in told.lower()
    assert "/usr/share/osiris" in told
