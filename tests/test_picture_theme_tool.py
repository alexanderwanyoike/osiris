"""Asking for a Theme from a description of a picture."""

from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from PIL import Image

from osiris.apps.tool_server import TIERS, instructions, server
from osiris.harness.log import LOG_FILE, Change, HarnessLog
from osiris.harness.media.error import MediaError
from osiris.harness.media.pictures import Pictures
from osiris.harness.tiers import Tier
from osiris.platform import FakeFileSystem, FakeRunner
from osiris.programs.programs import Programs
from osiris.themes.store import FakeThemeStore
from osiris.themes.wallpapers import UserWallpapers

HOME = Path("/home/tester")
FOREST = {"label": "Misty Forest", "picture": "A misty forest at dawn"}


def png() -> bytes:
    data = io.BytesIO()
    Image.new("RGB", (64, 36), (30, 60, 45)).save(data, "PNG")
    return data.getvalue()


@dataclass
class Maker:
    failure: Exception | None = None
    asked: list[str] = field(default_factory=list)

    def make(self, description: str) -> bytes:
        self.asked.append(description)
        if self.failure is not None:
            raise self.failure
        return png()


def tool_server(
    store: FakeThemeStore, maker: Maker, log: HarnessLog, files: FakeFileSystem
) -> MCPServer:
    runner = FakeRunner()
    return server(
        store,
        Programs(files, runner, HOME),
        log,
        UserWallpapers(files, runner, HOME / "wallpapers", ""),
        pictures=Pictures(maker, files, HOME),
    )


def nord() -> FakeThemeStore:
    return FakeThemeStore(
        themes=[{"name": "nord", "label": "Nord", "dark": True}], current="nord"
    )


def test_the_tool_is_offered_only_where_pictures_can_be_made() -> None:
    files = FakeFileSystem()
    log = HarnessLog(files, HOME / LOG_FILE)
    offered = asyncio.run(tool_server(nord(), Maker(), log, files).list_tools())

    assert "make_picture_theme" in {tool.name for tool in offered}
    assert TIERS["make_picture_theme"] is Tier.UNDOABLE


def test_a_described_picture_becomes_the_applied_theme() -> None:
    store, maker, files = nord(), Maker(), FakeFileSystem()
    log = HarnessLog(files, HOME / LOG_FILE)

    asyncio.run(
        tool_server(store, maker, log, files).call_tool("make_picture_theme", FOREST)
    )

    picture = HOME / "Pictures/Osiris/misty-forest.png"
    assert store.current() == "misty-forest"
    assert store.saved[0]["wallpaper"] == str(picture)
    assert files.blobs[picture] == png()
    assert maker.asked[0].startswith("A misty forest at dawn. ")
    assert "no text" in maker.asked[0]
    assert log.last_changes() == [
        Change("Made Misty Forest", {"action": "delete_theme", "name": "misty-forest"}),
        Change("Applied Misty Forest", {"action": "apply_theme", "name": "nord"}),
    ]


def test_the_style_leaves_room_for_a_picture_with_people_in_it() -> None:
    store, maker, files = nord(), Maker(), FakeFileSystem()
    crowd = {"label": "Festival", "picture": "A festival crowd at dusk"}

    asyncio.run(
        tool_server(store, maker, HarnessLog(files, HOME / LOG_FILE), files).call_tool(
            "make_picture_theme", crowd
        )
    )

    assert "no people" not in maker.asked[0]


def test_the_style_leaves_the_look_of_the_picture_to_the_person() -> None:
    store, maker, files = nord(), Maker(), FakeFileSystem()
    duel = {"label": "Duel", "picture": "A flat anime duel"}

    asyncio.run(
        tool_server(store, maker, HarnessLog(files, HOME / LOG_FILE), files).call_tool(
            "make_picture_theme", duel
        )
    )

    assert "cinematic" not in maker.asked[0]
    assert "calm" not in maker.asked[0]


def test_a_label_in_use_is_refused_before_anything_is_spent() -> None:
    store, maker, files = nord(), Maker(), FakeFileSystem()
    log = HarnessLog(files, HOME / LOG_FILE)

    with pytest.raises(ToolError, match="already a theme called Nord"):
        asyncio.run(
            tool_server(store, maker, log, files).call_tool(
                "make_picture_theme", {"label": "Nord", "picture": "A fjord"}
            )
        )

    assert maker.asked == []


def test_a_failed_picture_reaches_the_model_with_its_reason() -> None:
    store, files = nord(), FakeFileSystem()
    maker = Maker(failure=MediaError("FAL is not connected; add a key in Settings."))
    log = HarnessLog(files, HOME / LOG_FILE)

    with pytest.raises(ToolError, match="add a key in Settings"):
        asyncio.run(
            tool_server(store, maker, log, files).call_tool(
                "make_picture_theme", FOREST
            )
        )

    assert store.saved == []
    assert store.current() == "nord"


def test_the_model_is_told_when_to_generate_a_picture_and_that_it_costs() -> None:
    told = " ".join(instructions(auto_mode=False).split())

    assert "make_picture_theme" in told
    assert "costs the person money" in told
