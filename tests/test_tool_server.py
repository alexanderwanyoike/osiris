"""The Osiris tool server: the Theme and Program actions as MCP tools a model
can call."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from mcp.server.context import ServerRequestContext
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from osiris.apps.tool_server import TIERS, server, undo
from osiris.harness.log import LOG_FILE, Change, HarnessLog
from osiris.harness.tiers import Tier
from osiris.platform import FakeFileSystem, FakeRunner
from osiris.platform.process import Result
from osiris.programs.manifest import MANIFEST_FILE
from osiris.programs.programs import Programs
from osiris.themes.actions import ThemeActionError
from osiris.themes.store import FakeThemeStore
from osiris.themes.wallpapers import UserWallpapers

HARBOUR = {
    "label": "Harbour",
    "seed": "#3a6ea5",
    "harmony": "analogous",
    "mood": "muted",
    "dark": True,
}


HOME = Path("/home/tester")
POMODORO = HOME / "Code" / "pomodoro"


def new_log() -> HarnessLog:
    return HarnessLog(FakeFileSystem(), HOME / LOG_FILE)


def new_programs(
    files: FakeFileSystem | None = None, runner: FakeRunner | None = None
) -> Programs:
    return Programs(files or FakeFileSystem(), runner or FakeRunner(), HOME)


WALLPAPERS = HOME / ".local/share/osiris/wallpapers"
RAIN = "vec3 wallpaper(vec2 uv) {\n    return u_accent * uv.y;\n}\n"


def new_wallpapers(
    files: FakeFileSystem | None = None, runner: FakeRunner | None = None
) -> UserWallpapers:
    return UserWallpapers(
        files or FakeFileSystem(), runner or FakeRunner(), WALLPAPERS, ""
    )


def tools(store: FakeThemeStore) -> dict[str, Any]:
    subject = server(store, new_programs(), new_log(), new_wallpapers())
    tool_list = asyncio.run(subject.list_tools())
    return {tool.name: tool for tool in tool_list}


def call(
    store: FakeThemeStore,
    name: str,
    arguments: dict[str, Any],
    log: HarnessLog | None = None,
    programs: Programs | None = None,
    wallpapers: UserWallpapers | None = None,
) -> Any:
    subject = server(
        store,
        programs or new_programs(),
        log or new_log(),
        wallpapers or new_wallpapers(),
    )
    return asyncio.run(subject.call_tool(name, arguments))


def test_the_server_offers_the_theme_and_program_actions_and_nothing_else() -> None:
    assert set(tools(FakeThemeStore())) == {
        "list_themes",
        "create_theme",
        "apply_theme",
        "list_programs",
        "create_program",
        "commit_program",
        "check_program",
        "make_wallpaper",
        "propose_skill",
    }


def test_listing_and_checking_are_looks_and_the_rest_undoable_changes() -> None:
    assert TIERS == {
        "list_themes": Tier.LOOK,
        "create_theme": Tier.UNDOABLE,
        "apply_theme": Tier.UNDOABLE,
        "list_programs": Tier.LOOK,
        "create_program": Tier.UNDOABLE,
        "commit_program": Tier.UNDOABLE,
        "check_program": Tier.LOOK,
        "make_wallpaper": Tier.UNDOABLE,
        "list_skins": Tier.LOOK,
        "create_skin": Tier.UNDOABLE,
        "check_skin": Tier.LOOK,
        "wear_skin": Tier.UNDOABLE,
        "import_gtk_theme": Tier.UNDOABLE,
        "install_icon_set": Tier.UNDOABLE,
        "install_fonts": Tier.UNDOABLE,
        # It changes nothing: the person reads it and decides.
        "propose_skill": Tier.LOOK,
    }


def test_only_listing_is_marked_as_a_look() -> None:
    offered = tools(FakeThemeStore())
    assert offered["list_themes"].annotations.read_only_hint is True
    assert offered["list_programs"].annotations.read_only_hint is True
    assert offered["check_program"].annotations.read_only_hint is True
    for change in ("create_theme", "apply_theme", "create_program", "commit_program"):
        assert offered[change].annotations.read_only_hint is False


def test_a_model_is_offered_exactly_the_harmonies_and_moods_osiris_knows() -> None:
    schema = tools(FakeThemeStore())["create_theme"].input_schema
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
    subject = server(FakeThemeStore(), new_programs(), new_log(), new_wallpapers())
    assert subject.settings.log_level == "WARNING"


def test_making_a_theme_is_logged_as_a_change_undone_by_deleting_it() -> None:
    log = new_log()
    call(FakeThemeStore(), "create_theme", HARBOUR, log)
    assert log.last_changes() == [
        Change("Made Harbour", {"action": "delete_theme", "name": "harbour"})
    ]


def asked_by(session: str, subject: MCPServer) -> Context:
    """A tool call as the Engine makes it for one of its sessions."""
    request = ServerRequestContext(
        session=None,
        lifespan_context=None,
        protocol_version="2025-06-18",
        method="tools/call",
        meta={"ai.opencode/sessionID": session},
    )
    return Context(request_context=request, mcp_server=subject)


def test_a_change_is_logged_with_the_conversation_that_asked_for_it() -> None:
    files = FakeFileSystem()
    subject = server(
        FakeThemeStore(),
        new_programs(),
        HarnessLog(files, HOME / LOG_FILE),
        new_wallpapers(),
    )
    asyncio.run(subject.call_tool("create_theme", HARBOUR, asked_by("ses_A", subject)))
    entry = json.loads(files.read(HOME / LOG_FILE).splitlines()[-1])
    assert entry["kind"] == "changed"
    assert entry["session"] == "ses_A"


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
    undo(
        store,
        {"action": "apply_theme", "name": "nord"},
        new_programs(),
        new_wallpapers(),
    )
    undo(
        store,
        {"action": "delete_theme", "name": "harbour"},
        new_programs(),
        new_wallpapers(),
    )
    assert store.applied == ["nord"]
    assert store.deleted == ["harbour"]


def test_an_unknown_undo_step_is_refused() -> None:
    with pytest.raises(ThemeActionError, match="cannot undo"):
        undo(
            FakeThemeStore(),
            {"action": "format_disk", "name": "sda"},
            new_programs(),
            new_wallpapers(),
        )


def test_a_model_is_told_a_seed_is_a_hex_colour_before_it_tries() -> None:
    seed = tools(FakeThemeStore())["create_theme"].input_schema["properties"]["seed"]
    assert seed["pattern"] == "^#[0-9a-fA-F]{6}$"


def test_making_a_program_is_logged_as_a_change_undone_by_the_trash() -> None:
    log = new_log()
    call(
        FakeThemeStore(),
        "create_program",
        {
            "label": "Pomodoro",
            "description": "A focus timer.",
            "run": ["python3", "main.py"],
            "icon_svg": '<svg xmlns="http://www.w3.org/2000/svg"/>',
        },
        log,
    )
    assert log.last_changes() == [
        Change(
            "Made Pomodoro",
            {"action": "trash_program", "name": "pomodoro"},
            program="pomodoro",
        )
    ]


def test_a_commit_is_logged_as_a_change_undone_by_reverting_it() -> None:
    files = FakeFileSystem()
    files.write(
        POMODORO / MANIFEST_FILE,
        '{"name": "pomodoro", "label": "Pomodoro", "description": "A timer.",'
        ' "run": ["python3", "main.py"]}',
    )
    git = f"git -C {POMODORO}"
    runner = FakeRunner(
        results={
            f"{git} status --porcelain": Result((), 0, " M main.py\n"),
            f"{git} rev-parse HEAD": Result((), 0, "abc123\n"),
        }
    )
    log = new_log()
    call(
        FakeThemeStore(),
        "commit_program",
        {"name": "pomodoro", "message": "Add a pause button"},
        log,
        new_programs(files, runner),
    )
    assert log.last_changes() == [
        Change(
            "Pomodoro: Add a pause button",
            {"action": "revert_commit", "name": "pomodoro", "commit": "abc123"},
            program="pomodoro",
        )
    ]


def test_undo_trashes_a_program_or_reverts_a_commit() -> None:
    files = FakeFileSystem()
    files.write(
        POMODORO / MANIFEST_FILE,
        '{"name": "pomodoro", "label": "Pomodoro", "description": "A timer.",'
        ' "run": ["python3", "main.py"]}',
    )
    runner = FakeRunner()
    subject = new_programs(files, runner)
    undo(
        FakeThemeStore(),
        {"action": "revert_commit", "name": "pomodoro", "commit": "abc123"},
        subject,
        new_wallpapers(),
    )
    undo(
        FakeThemeStore(),
        {"action": "trash_program", "name": "pomodoro"},
        subject,
        new_wallpapers(),
    )
    argvs = [call.argv for call in runner.calls]
    assert argvs[0][-3:] == ("revert", "--no-edit", "abc123")
    assert argvs[1] == ("gio", "trash", str(POMODORO))


def test_a_program_cannot_be_made_without_an_icon() -> None:
    schema = tools(FakeThemeStore())["create_program"].input_schema
    assert "icon_svg" in schema["required"]


def test_a_refused_program_reaches_the_model_with_its_reason() -> None:
    with pytest.raises(ToolError, match="The icon is not an SVG"):
        call(
            FakeThemeStore(),
            "create_program",
            {
                "label": "Pomodoro",
                "description": "A focus timer.",
                "run": ["python3", "main.py"],
                "icon_svg": "a tomato",
            },
        )


def test_making_a_program_names_its_folder_as_a_path_a_file_tool_takes() -> None:
    reply = call(
        FakeThemeStore(),
        "create_program",
        {
            "label": "Pomodoro",
            "description": "A focus timer.",
            "run": ["python3", "main.py"],
            "icon_svg": '<svg xmlns="http://www.w3.org/2000/svg"/>',
        },
    )
    text = reply.content[0].text
    assert str(POMODORO) in text
    assert "~" not in text


def test_the_model_is_told_windows_are_gtk_and_libadwaita_and_nothing_else() -> None:
    from osiris.apps.tool_server import INSTRUCTIONS

    assert "tkinter" in INSTRUCTIONS
    assert "GTK 4 and libadwaita" in INSTRUCTIONS


def test_the_model_is_told_the_person_knows_it_as_osiris() -> None:
    from osiris.apps.tool_server import INSTRUCTIONS

    assert "you are osiris" in INSTRUCTIONS.lower()


def test_the_model_checks_then_has_a_program_reviewed_before_calling_it_done() -> None:
    """#161: the quick checks first, then the reviewer, and a partial or a fail
    is never reported as done."""
    from osiris.apps.tool_server import INSTRUCTIONS

    text = " ".join(INSTRUCTIONS.split())
    assert text.index("check_program") < text.index("reviewer subagent")
    assert "the person's own words" in text
    assert "the commit the change started from" in text
    assert "pass, partial or fail" in text
    assert "Never call a Program done on a partial or a fail" in text


def test_making_a_wallpaper_wears_it_and_logs_each_step_to_undo() -> None:
    log = new_log()
    store = FakeThemeStore(
        themes=[{"name": "nord", "label": "Nord", "dark": True}], current="nord"
    )
    call(store, "make_wallpaper", {"label": "Rain", "shader": RAIN}, log)
    assert store.current() == "nord-rain"
    assert log.last_changes() == [
        Change(
            "Made the Rain wallpaper", {"action": "delete_wallpaper", "name": "rain"}
        ),
        Change("Made Nord Rain", {"action": "delete_theme", "name": "nord-rain"}),
        Change("Applied Nord Rain", {"action": "apply_theme", "name": "nord"}),
    ]


def test_a_shader_that_does_not_compile_reaches_the_model_to_fix() -> None:
    runner = FakeRunner(
        results={
            "glslangValidator": Result(
                ("glslangValidator",),
                2,
                "ERROR: 0:6: 'floot' : undeclared identifier\n",
            )
        }
    )
    store = FakeThemeStore(
        themes=[{"name": "nord", "label": "Nord", "dark": True}], current="nord"
    )
    with pytest.raises(ToolError, match="undeclared identifier"):
        call(
            store,
            "make_wallpaper",
            {"label": "Rain", "shader": RAIN},
            wallpapers=new_wallpapers(runner=runner),
        )
    assert store.current() == "nord"


def test_undo_deletes_a_wallpaper_it_made() -> None:
    files = FakeFileSystem()
    wallpapers = new_wallpapers(files)
    wallpapers.write("Rain", RAIN)
    undo(
        FakeThemeStore(),
        {"action": "delete_wallpaper", "name": "rain"},
        new_programs(),
        wallpapers,
    )
    assert not files.exists(WALLPAPERS / "rain" / "shader.glsl")


def test_the_model_is_told_how_a_wallpaper_shader_is_written() -> None:
    described = tools(FakeThemeStore())["make_wallpaper"].description
    for needed in ("vec3 wallpaper(vec2 uv)", "u_time", "GLSL 1.20", "compose("):
        assert needed in described


def test_the_model_is_told_what_waits_for_the_person_and_what_auto_mode_lets_run() -> (
    None
):
    """Commands now ask rather than being out of reach (ADR 0020)."""
    from osiris.apps.tool_server import instructions

    careful = instructions(auto_mode=False)
    assert "you cannot run commands" not in careful
    assert "asks the person" in careful
    auto = instructions(auto_mode=True)
    assert "auto mode" in auto
    assert "rules forbid" in auto


def test_a_proposed_skill_is_logged_for_the_question_being_answered() -> None:
    from osiris.harness.proposals import Proposal

    log = new_log()
    log.write("sent", session="ses_1", text="tidy my imports")
    call(
        FakeThemeStore(),
        "propose_skill",
        {"name": "tidy-imports", "description": "Sort imports", "body": "Run ruff."},
        log,
    )
    assert log.proposals_by_question("ses_1") == [
        [Proposal("tidy-imports", "Sort imports", "Run ruff.")]
    ]


def test_a_skill_with_a_name_that_could_lead_elsewhere_is_refused() -> None:
    log = new_log()
    log.write("sent", session="ses_1", text="tidy my imports")
    result = call(
        FakeThemeStore(),
        "propose_skill",
        {"name": "../evil", "description": "x", "body": "x"},
        log,
    )
    assert result.is_error
    assert log.proposals_by_question("ses_1") == [[]]
