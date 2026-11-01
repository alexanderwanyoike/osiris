"""The reviewer Thoth asks before it calls a Program done (#161), given to the
Engine as one of its subagents and a skill. Its files live in the Engine's own
config, the person's to change, so one is written only where none is."""

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
)


def write_reviewer(files: FileSystem, home: Path) -> None:
    resources = Resources()
    for name in SHIPPED:
        target = home / ENGINE_DIR / name
        if not files.exists(target):
            files.write(target, resources.read(f"engine/{name}"))
