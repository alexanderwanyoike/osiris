"""The Osiris tool server: what the Harness's model may ask Osiris to do.

It speaks MCP over stdio, and the Harness registers it with the Engine when it
starts. Every call still raises a permission request in the Engine, which the
Harness decides by Action tier; the annotations here only tell a client which
tools are looks.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from osiris.harness.log import HarnessLog
from osiris.harness.tiers import Tier
from osiris.programs.programs import Programs
from osiris.themes import actions
from osiris.themes.intent import Harmony, Mood
from osiris.themes.store import ThemeStore

NAME = "osiris"

INSTRUCTIONS = """\
Osiris is the desktop you are running on. You can list its themes, make a new
one and apply it. You never choose a theme's colours: describe what the person
asked for as a seed colour, a harmony, a mood and light or dark, and Osiris
derives a harmonious, legible palette from that. Applying a theme repaints the
whole desktop at once, and the person can undo it.

You can also build Programs: anything the person wants to keep and use. Start
one with create_program, which makes ~/Code/<name> as a git repository. Write
its code there with your file tools; nothing outside that folder is yours to
touch, and you cannot run commands. Write in Python, C or C++, Rust, Go or
JavaScript unless the person asks for another language; give anything with a
window GTK 4 and libadwaita (GJS for JavaScript) so it looks like the rest of
Osiris. Keep its osiris-program.json true: build and run are lists of words run
in its folder. Commit every change with commit_program, one atomic change per
commit with a message saying what it does. check_program finds Python that does
not compile. The person tries and installs a Program themselves, from the card
under your answer; a failed build comes back to you to fix."""

#: How far each tool reaches, which decides how the Harness answers its requests.
TIERS = {
    "list_themes": Tier.LOOK,
    "create_theme": Tier.UNDOABLE,
    "apply_theme": Tier.UNDOABLE,
    "list_programs": Tier.LOOK,
    "create_program": Tier.UNDOABLE,
    "commit_program": Tier.UNDOABLE,
    "check_program": Tier.LOOK,
}

#: A seed as the model must give it; words like "dusk blue" are refused.
Seed = Annotated[str, Field(pattern="^#[0-9a-fA-F]{6}$")]

ANNOTATIONS = {
    Tier.LOOK: ToolAnnotations(readOnlyHint=True),
    Tier.UNDOABLE: ToolAnnotations(readOnlyHint=False, destructiveHint=False),
}


def undo(store: ThemeStore, step: Mapping[str, str], programs: Programs) -> None:
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
        case other:
            raise actions.ThemeActionError(f"Osiris cannot undo {other}")


def server(store: ThemeStore, programs: Programs, log: HarnessLog) -> FastMCP:
    """The tools, acting on ``store``; every change they make is written to
    ``log`` with the step that undoes it."""
    tools = FastMCP(NAME, instructions=INSTRUCTIONS, log_level="WARNING")

    @tools.tool(annotations=ANNOTATIONS[TIERS["list_themes"]])
    def list_themes() -> list[dict[str, object]]:
        """The themes on this desktop, light or dark, and which is applied."""
        return actions.list_themes(store)

    @tools.tool(annotations=ANNOTATIONS[TIERS["create_theme"]])
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
    def create_program(
        label: str,
        description: str,
        run: list[str],
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
        """
        manifest = programs.create(
            label, description, run=run, build=build, terminal=terminal
        )
        log.write(
            "changed",
            summary=f"Made {label}",
            undo={"action": "trash_program", "name": manifest.name},
        )
        return (
            f"Made {label} in ~/Code/{manifest.name}, named {manifest.name}. "
            "Write its code there, then commit it."
        )

    @tools.tool(annotations=ANNOTATIONS[TIERS["commit_program"]])
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
        )
        return f"Committed {message} as {commit[:7]}."

    @tools.tool(annotations=ANNOTATIONS[TIERS["check_program"]])
    def check_program(name: str) -> str:
        """Find Python in a Program that does not compile, without running it.
        Other languages are checked by their build when the person tries them."""
        problems = programs.check(name)
        return "\n".join(problems) if problems else "No problems found."

    return tools
