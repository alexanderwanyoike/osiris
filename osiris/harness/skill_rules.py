"""Skills (#154): each one on, off or asked about first, as a permission rule
in the Engine's own config. The last rule that matches wins, so a skill's own
rule goes after the rules it overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from osiris.harness.engine_config import ENGINE_CONFIG, edit, read
from osiris.platform import FileSystem

#: A choice on the Skills page, and the effect its rule has.
EFFECTS = {"off": "deny", "ask": "ask"}
CHOICES = {effect: choice for choice, effect in EFFECTS.items()}


def _own(rule: dict[str, str], skill: str) -> bool:
    return rule.get("action") == "skill" and rule.get("resource") == skill


def choice_of(config: dict[str, Any], skill: str) -> str:
    """ "on", "off" or "ask": a skill with no rule of its own is on."""
    own = [r for r in config.get("permissions", []) if _own(r, skill)]
    return CHOICES.get(own[-1]["effect"], "on") if own else "on"


def chosen(config: dict[str, Any], skill: str, choice: str) -> dict[str, Any]:
    rules = [r for r in config.get("permissions", []) if not _own(r, skill)]
    if choice in EFFECTS:
        rules.append({"action": "skill", "resource": skill, "effect": EFFECTS[choice]})
    config["permissions"] = rules
    return config


def skill_choice(files: FileSystem, home: Path, skill: str) -> str:
    return choice_of(read(files, home / ENGINE_CONFIG), skill)


def choose_skill(files: FileSystem, home: Path, skill: str, choice: str) -> bool:
    """Whether it could be kept: a commented config is left to the person."""
    return edit(
        files, home / ENGINE_CONFIG, lambda config: bool(chosen(config, skill, choice))
    )
