"""The reviewers Thoth asks before it calls a Program (#161) or a Skin (#269)
done, given to the Engine as its subagents and skills. Their files live in the
Engine's own config, the person's to change, so one is written only where none
is."""

from __future__ import annotations

from pathlib import Path

from osiris.platform import FileSystem
from osiris.resources.loader import Resources

ENGINE_DIR = ".config/opencode"

SHIPPED = (
    "agents/reviewer.md",
    "skills/review/SKILL.md",
    "skills/review/NOTICE.md",
    "skills/review/LICENSE-MIT",
    "skills/review/LICENSE-APACHE",
    "agents/skin-reviewer.md",
    "skills/skin-review/SKILL.md",
)


def write_reviewer(files: FileSystem, home: Path) -> None:
    resources = Resources()
    for name in SHIPPED:
        target = home / ENGINE_DIR / name
        if not files.exists(target):
            files.write(target, resources.read(f"engine/{name}"))
