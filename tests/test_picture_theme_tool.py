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
from osiris.harness.media.image_model import ImageModel
from osiris.harness.media.model_setting import DEFAULT_IMAGE_MODEL, saved_model
from osiris.harness.media.model_spec import ModelSpec
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
    models: list[str] = field(default_factory=list)

    def make(self, description: str, model: str) -> bytes:
        self.asked.append(description)
        self.models.append(model)
        if self.failure is not None:
            raise self.failure
        return png()


class Catalog:
    def search(self, _words: str) -> list[ImageModel]:
        return [ImageModel("vendor/flat", "Flat", "Draws flat pictures")]

    def spec(self, model: str) -> ModelSpec:
        if model != "vendor/flat":
            raise MediaError(f"{model} is not an image model FAL offers")
        return ModelSpec(model, frozenset({"prompt"}))


def tool_server(
    store: FakeThemeStore, maker: Maker, log: HarnessLog, files: FakeFileSystem
) -> MCPServer:
    runner = FakeRunner()
    return server(
        store,
        Programs(files, runner, HOME),
        log,
        UserWallpapers(files, runner, HOME / "wallpapers", ""),
        pictures=Pictures(maker, files, HOME, Catalog()),
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
        Change(
            f"Made Misty Forest with {DEFAULT_IMAGE_MODEL}",
            {"action": "delete_theme", "name": "misty-forest"},
        ),
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


def test_a_model_the_person_named_makes_that_picture() -> None:
    store, maker, files = nord(), Maker(), FakeFileSystem()
    log = HarnessLog(files, HOME / LOG_FILE)

    asyncio.run(
        tool_server(store, maker, log, files).call_tool(
            "make_picture_theme", {**FOREST, "image_model": "vendor/flat"}
        )
    )

    assert maker.models == ["vendor/flat"]
    assert log.last_changes()[0].summary == "Made Misty Forest with vendor/flat"


def test_with_no_model_named_the_default_makes_the_picture() -> None:
    store, maker, files = nord(), Maker(), FakeFileSystem()
    log = HarnessLog(files, HOME / LOG_FILE)

    asyncio.run(
        tool_server(store, maker, log, files).call_tool("make_picture_theme", FOREST)
    )

    assert maker.models == [DEFAULT_IMAGE_MODEL]


def test_the_model_can_see_fals_image_models_and_the_default() -> None:
    files = FakeFileSystem()
    log = HarnessLog(files, HOME / LOG_FILE)

    reply = asyncio.run(
        tool_server(nord(), Maker(), log, files).call_tool(
            "find_image_models", {"search": "flat"}
        )
    )

    text = reply.content[0].text
    assert "vendor/flat" in text
    assert DEFAULT_IMAGE_MODEL in text
    assert TIERS["find_image_models"] is Tier.LOOK


def test_a_person_can_make_a_model_their_default() -> None:
    files = FakeFileSystem()
    log = HarnessLog(files, HOME / LOG_FILE)

    asyncio.run(
        tool_server(nord(), Maker(), log, files).call_tool(
            "set_default_image_model", {"model": "vendor/flat"}
        )
    )

    assert saved_model(files, HOME) == "vendor/flat"
    change = log.last_changes()[0]
    assert change.summary == "Made vendor/flat the default image model"
    assert change.undo == {
        "action": "set_default_image_model",
        "model": "",
    }
    assert TIERS["set_default_image_model"] is Tier.UNDOABLE


def test_an_empty_choice_goes_back_to_the_shipped_default() -> None:
    files = FakeFileSystem()
    log = HarnessLog(files, HOME / LOG_FILE)
    tools = tool_server(nord(), Maker(), log, files)
    asyncio.run(tools.call_tool("set_default_image_model", {"model": "vendor/flat"}))

    asyncio.run(tools.call_tool("set_default_image_model", {"model": ""}))

    assert saved_model(files, HOME) is None
    assert log.last_changes()[-1].undo == {
        "action": "set_default_image_model",
        "model": "vendor/flat",
    }


def test_a_model_fal_does_not_offer_cannot_become_the_default() -> None:
    files = FakeFileSystem()
    log = HarnessLog(files, HOME / LOG_FILE)

    with pytest.raises(ToolError, match="not an image model"):
        asyncio.run(
            tool_server(nord(), Maker(), log, files).call_tool(
                "set_default_image_model", {"model": "vendor/video"}
            )
        )

    assert saved_model(files, HOME) is None


def test_the_result_names_the_model_that_made_the_picture() -> None:
    store, maker, files = nord(), Maker(), FakeFileSystem()
    log = HarnessLog(files, HOME / LOG_FILE)

    reply = asyncio.run(
        tool_server(store, maker, log, files).call_tool(
            "make_picture_theme", {**FOREST, "image_model": "vendor/flat"}
        )
    )

    assert "vendor/flat" in reply.content[0].text


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


def test_the_model_only_changes_the_image_model_when_asked() -> None:
    told = " ".join(instructions(auto_mode=False).split())

    assert "find_image_models" in told
    assert "never pick a different model yourself" in told
    assert "set_default_image_model" in told


def test_a_painted_picture_becomes_the_wallpaper_of_one_half_of_a_pair() -> None:
    """A whole look paints a light picture for the light Theme and a dark one
    for the dark, with the person's image model."""
    store = FakeThemeStore(
        themes=[
            {"name": "van", "label": "Van", "dark": False, "wallpaper": "generated"}
        ],
        current="van",
    )
    maker, files = Maker(), FakeFileSystem()
    log = HarnessLog(files, HOME / LOG_FILE)
    sunny = {"name": "van", "picture": "The van on a sunny road"}

    asyncio.run(
        tool_server(store, maker, log, files).call_tool("paint_theme_wallpaper", sunny)
    )

    picture = HOME / "Pictures/Osiris/van.png"
    assert store.themes()[0]["wallpaper"] == str(picture)
    assert files.blobs[picture] == png()
    assert maker.asked[0].startswith("The van on a sunny road. ")
    assert log.last_changes() == [
        Change(
            f"Painted a wallpaper for Van with {DEFAULT_IMAGE_MODEL}",
            {"action": "set_theme_wallpaper", "name": "van", "wallpaper": "generated"},
        )
    ]
