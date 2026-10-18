"""The Osiris tool server: what the Harness's model may ask Osiris to do.

It speaks MCP over stdio, and the Harness registers it with the Engine when it
starts. Every call still raises a permission request in the Engine, which the
Harness decides by Action tier; the annotations here only tell a client which
tools are looks.
"""

from __future__ import annotations

from collections.abc import Mapping

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from osiris.harness.log import HarnessLog
from osiris.harness.tiers import Tier
from osiris.themes import actions
from osiris.themes.intent import Harmony, Mood
from osiris.themes.store import ThemeStore

NAME = "osiris"

INSTRUCTIONS = """\
Osiris is the desktop you are running on. You can list its themes, make a new
one and apply it. You never choose a theme's colours: describe what the person
asked for as a seed colour, a harmony, a mood and light or dark, and Osiris
derives a harmonious, legible palette from that. Applying a theme repaints the
whole desktop at once, and the person can undo it."""

#: How far each tool reaches, which decides how the Harness answers its requests.
TIERS = {
    "list_themes": Tier.LOOK,
    "create_theme": Tier.UNDOABLE,
    "apply_theme": Tier.UNDOABLE,
}

ANNOTATIONS = {
    Tier.LOOK: ToolAnnotations(readOnlyHint=True),
    Tier.UNDOABLE: ToolAnnotations(readOnlyHint=False, destructiveHint=False),
}


def undo(store: ThemeStore, step: Mapping[str, str]) -> None:
    """Run the step a logged change recorded to reverse itself."""
    match step["action"]:
        case "apply_theme":
            actions.apply_theme(store, step["name"])
        case "delete_theme":
            actions.delete_theme(store, step["name"])
        case other:
            raise actions.ThemeActionError(f"Osiris cannot undo {other}")


def server(store: ThemeStore, log: HarnessLog) -> FastMCP:
    """The tools, acting on ``store``; every change they make is written to
    ``log`` with the step that undoes it."""
    tools = FastMCP(NAME, instructions=INSTRUCTIONS, log_level="WARNING")

    @tools.tool(annotations=ANNOTATIONS[TIERS["list_themes"]])
    def list_themes() -> list[dict[str, object]]:
        """The themes on this desktop, light or dark, and which is applied."""
        return actions.list_themes(store)

    @tools.tool(annotations=ANNOTATIONS[TIERS["create_theme"]])
    def create_theme(
        label: str, seed: str, harmony: Harmony, mood: Mood, dark: bool
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

    return tools
