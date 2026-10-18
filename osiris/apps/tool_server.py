"""The Osiris tool server: what the Harness's model may ask Osiris to do.

It speaks MCP over stdio, and the Harness registers it with the Engine when it
starts. Every call still raises a permission request in the Engine, which the
Harness decides by Action tier; the annotations here only tell a client which
tools are looks.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

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


def server(store: ThemeStore) -> FastMCP:
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
        return f"Made {label}, named {name}."

    @tools.tool(annotations=ANNOTATIONS[TIERS["apply_theme"]])
    def apply_theme(name: str) -> str:
        """Apply a theme to the whole desktop, by its name from list_themes."""
        previous = actions.apply_theme(store, name)
        return f"Applied {name}" + (f" in place of {previous}." if previous else ".")

    return tools
