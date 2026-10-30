"""The Osiris tool server: what the Harness's model may ask Osiris to do.

It speaks MCP over stdio, and the Harness registers it with the Engine when it
starts. Every call still raises a permission request in the Engine, which the
Harness decides by Action tier; the annotations here only tell a client which
tools are looks.
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Mapping
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from osiris.harness.log import HarnessLog
from osiris.harness.tiers import Tier
from osiris.programs.programs import FOLLOW_THEME, Programs
from osiris.themes import actions
from osiris.themes.intent import Harmony, Mood
from osiris.themes.store import ThemeStore
from osiris.themes.wallpapers import UserWallpapers, WallpaperError

NAME = "osiris"

INSTRUCTIONS = f"""\
You are Osiris, the AI built into the Osiris desktop you are running on, and
the person knows you by that name. You can list its themes, make a new
one and apply it. You never choose a theme's colours: describe what the person
asked for as a seed colour, a harmony, a mood and light or dark, and Osiris
derives a harmonious, legible palette from that. Applying a theme repaints the
whole desktop at once, and the person can undo it.

You can also build Programs: anything the person wants to keep and use. Start
one with create_program, which makes its folder as a git repository and tells
you its path; to work on an existing Program, find its folder with
list_programs. Write its code there with your file tools, always by the
absolute path those give you, never with ~; {{reach}} Write in Python, C or
C++, Rust, Go or JavaScript unless the person asks for another language.
Anything with a window is GTK 4 and libadwaita (GJS for JavaScript), never
tkinter, Qt, Electron or a web view, so it looks like the rest of Osiris, and
never give it colours of its own: style only with libadwaita's named colours
(@accent_bg_color, @window_bg_color, @card_bg_color and the rest), so it
follows the person's Theme as they change it, unless they ask otherwise.
A window also follows a Theme change live, without a restart, when its
application's startup handler runs this (Python; the same calls in any
language), which every Program with a window needs:

{FOLLOW_THEME} Every Program has an icon that shows what it is: icon.svg in its
folder, named as "icon" in its osiris-program.json; give one to any Program
that lacks it. Keep its osiris-program.json true: build and run are lists of words run
in its folder. Commit every change with commit_program, one atomic change per
commit with a message saying what it does. check_program finds Python that does
not compile. The person tries and installs a Program themselves, from the card
under your answer; a failed build comes back to you to fix."""

#: What the model may touch beyond its tools, by the person's choice
#: (osiris.harness.trust).
REACH = {
    False: "nothing outside that folder is\nyours to touch, and you cannot run "
    "commands.",
    True: "the person has allowed you\neverything: you may run commands and read "
    "or change any file, though a\nProgram's code still belongs in its own folder.",
}


def instructions(*, allow_everything: bool) -> str:
    return INSTRUCTIONS.replace("{reach}", REACH[allow_everything])


#: How far each tool reaches, which decides how the Harness answers its requests.
TIERS = {
    "list_themes": Tier.LOOK,
    "create_theme": Tier.UNDOABLE,
    "apply_theme": Tier.UNDOABLE,
    "list_programs": Tier.LOOK,
    "create_program": Tier.UNDOABLE,
    "commit_program": Tier.UNDOABLE,
    "check_program": Tier.LOOK,
    "make_wallpaper": Tier.UNDOABLE,
}

#: A seed as the model must give it; words like "dusk blue" are refused.
Seed = Annotated[str, Field(pattern="^#[0-9a-fA-F]{6}$")]

ANNOTATIONS = {
    Tier.LOOK: ToolAnnotations(read_only_hint=True),
    Tier.UNDOABLE: ToolAnnotations(read_only_hint=False, destructive_hint=False),
}


#: Failures a model can act on, such as a shader that does not compile.
EXPLAINED = (actions.ThemeActionError, WallpaperError)


def explained[**P, R](tool: Callable[P, R]) -> Callable[P, R]:
    """Give the model a tool's anticipated failure with its reason; the SDK
    withholds the reason of any exception that is not a ToolError."""

    @functools.wraps(tool)
    def call(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return tool(*args, **kwargs)
        except EXPLAINED as error:
            raise ToolError(str(error)) from error

    return call


def undo(
    store: ThemeStore,
    step: Mapping[str, str],
    programs: Programs,
    wallpapers: UserWallpapers,
) -> None:
    """Run the step a logged change recorded to reverse itself."""
    match step["action"]:
        case "apply_theme":
            actions.apply_theme(store, step["name"])
        case "delete_theme":
            actions.delete_theme(store, step["name"])
        case "revert_commit":
            programs.revert(step["name"], step["commit"])
        case "trash_program":
            programs.trash(step["name"])
        case "delete_wallpaper":
            wallpapers.delete(step["name"])
        case other:
            raise actions.ThemeActionError(f"Osiris cannot undo {other}")


def server(
    store: ThemeStore,
    programs: Programs,
    log: HarnessLog,
    wallpapers: UserWallpapers,
    *,
    allow_everything: bool = False,
) -> MCPServer:
    """The tools, acting on ``store``; every change they make is written to
    ``log`` with the step that undoes it."""
    tools = MCPServer(
        NAME,
        instructions=instructions(allow_everything=allow_everything),
        log_level="WARNING",
    )

    @tools.tool(annotations=ANNOTATIONS[TIERS["list_themes"]])
    @explained
    def list_themes() -> list[dict[str, object]]:
        """The themes on this desktop, light or dark, and which is applied."""
        return actions.list_themes(store)

    @tools.tool(annotations=ANNOTATIONS[TIERS["create_theme"]])
    @explained
    def create_theme(
        label: str, seed: Seed, harmony: Harmony, mood: Mood, dark: bool
    ) -> str:
        """Make a theme and keep it with the person's own themes.

        label: what the person will see it called, such as "Harbour".
        seed: the colour the theme grows from, as #rrggbb; only its hue counts.
        harmony: how its colours relate. analogous is calm, complementary
        contrasts, split-complementary is lively, triadic is playful and
        monochrome is tonal.
        mood: muted, balanced, vivid or pastel.
        dark: a dark background, or a light one.

        Returns the theme's name, which apply_theme takes.
        """
        name = actions.create_theme(
            store,
            label=label,
            seed=seed,
            harmony=harmony.value,
            mood=mood.value,
            dark=dark,
        )
        log.write(
            "changed",
            summary=f"Made {label}",
            undo={"action": "delete_theme", "name": name},
        )
        return f"Made {label}, named {name}."

    @tools.tool(annotations=ANNOTATIONS[TIERS["apply_theme"]])
    @explained
    def apply_theme(name: str) -> str:
        """Apply a theme to the whole desktop, by its name from list_themes."""
        previous = actions.apply_theme(store, name)
        log.write(
            "changed",
            summary=f"Applied {actions.find(store, name)['label']}",
            undo={"action": "apply_theme", "name": previous} if previous else None,
        )
        return f"Applied {name}" + (f" in place of {previous}." if previous else ".")

    @tools.tool(annotations=ANNOTATIONS[TIERS["list_programs"]])
    @explained
    def list_programs() -> list[dict[str, object]]:
        """The Programs built on this desktop, where their source is, and
        whether the latest commit of each is installed."""
        return [
            {
                "name": program.manifest.name,
                "label": program.manifest.label,
                "description": program.manifest.description,
                "folder": str(program.source),
                "installed": program.installed is not None,
                "up_to_date": program.installed == program.head,
            }
            for program in programs.programs()
        ]

    @tools.tool(annotations=ANNOTATIONS[TIERS["create_program"]])
    @explained
    def create_program(
        label: str,
        description: str,
        run: list[str],
        icon_svg: str,
        build: list[str] | None = None,
        terminal: bool = False,
    ) -> str:
        """Start a Program in ~/Code: its folder, manifest, README, AGENTS.md
        and a first commit.

        label: what the person will see it called, such as "Pomodoro".
        description: one line saying what it does.
        run: the words that start it, run in its folder: ["python3", "main.py"].
        build: the words that build it, if it needs building:
        ["cargo", "build", "--release"].
        terminal: true for a script or command that should open in a terminal.
        icon_svg: an icon that shows what it is at a glance, as a whole SVG
        document with a 128 by 128 viewBox, flat and simple like the Papirus
        icons around it on the desktop.
        """
        manifest = programs.create(
            label,
            description,
            run=run,
            build=build,
            terminal=terminal,
            icon_svg=icon_svg,
        )
        log.write(
            "changed",
            summary=f"Made {label}",
            undo={"action": "trash_program", "name": manifest.name},
            program=manifest.name,
        )
        return (
            f"Made {label} in {programs.source(manifest.name)}, named "
            f"{manifest.name}. "
            "Write its code there, then commit it."
        )

    @tools.tool(annotations=ANNOTATIONS[TIERS["commit_program"]])
    @explained
    def commit_program(name: str, message: str) -> str:
        """Commit what changed in a Program as one atomic change.

        message: what this one change does, such as "Add a pause button".
        """
        commit = programs.commit(name, message)
        label = programs.manifest(name).label
        log.write(
            "changed",
            summary=f"{label}: {message}",
            undo={"action": "revert_commit", "name": name, "commit": commit},
            program=name,
        )
        return f"Committed {message} as {commit[:7]}."

    @tools.tool(annotations=ANNOTATIONS[TIERS["check_program"]])
    @explained
    def check_program(name: str) -> str:
        """Find Python in a Program that does not compile, without running it.
        Other languages are checked by their build when the person tries them."""
        problems = programs.check(name)
        return "\n".join(problems) if problems else "No problems found."

    @tools.tool(annotations=ANNOTATIONS[TIERS["make_wallpaper"]])
    @explained
    def make_wallpaper(label: str, shader: str) -> str:
        """Make a moving wallpaper and put it on the desktop, worn by a copy of
        the theme in use, so the theme itself is untouched.

        label: what the person will see it called, such as "Rain".
        shader: GLSL 1.20 defining vec3 wallpaper(vec2 uv), which returns the
        colour of each pixel, drawn on the GPU every frame. uv runs from (0, 0)
        at the top left to (1, 1). Already declared for you: u_time, where the
        loop is, from 0 to 1, coming round every 60 seconds, so animate with
        sin(TURN * u_time) and the like, where the end meets the start (TURN is
        two pi); u_size, the screen in pixels; the theme's colours as vec3:
        u_background, u_surface, u_foreground, u_accent, u_accent_muted,
        u_success, u_warning, u_danger, and the wallpaper's own tones u_base,
        u_shape and u_line; u_dark, 1.0 on a dark theme. Use only these
        colours, so the wallpaper follows the theme. End with
        compose(uv, fill, line, 0.42): it lays a fill and a line strength,
        each 0 to 1, over the theme's base and keeps the centre quiet for the
        Osiris mark. GLSL 1.20 has no %, no bitwise operators and no textures;
        give loops constant bounds. It runs every frame: keep it cheap, and the
        motion slow and calm. A shader that does not compile comes back with
        the errors by its own line numbers; fix it and call again.
        """
        name = wallpapers.write(label, shader)
        log.write(
            "changed",
            summary=f"Made the {label} wallpaper",
            undo={"action": "delete_wallpaper", "name": name},
        )
        theme, previous = actions.use_wallpaper(store, name, label)
        theme_label = actions.find(store, theme)["label"]
        log.write(
            "changed",
            summary=f"Made {theme_label}",
            undo={"action": "delete_theme", "name": theme},
        )
        log.write(
            "changed",
            summary=f"Applied {theme_label}",
            undo={"action": "apply_theme", "name": previous},
        )
        return f"Made the {label} wallpaper and applied it as {theme_label}."

    return tools
