"""Who Osiris is in the history of what it makes for a person."""

from __future__ import annotations

#: An address that can never be mailed, so no one is written to by mistake.
OSIRIS = ("Osiris", "osiris@osiris.invalid")


def as_osiris() -> tuple[str, ...]:
    """git options that commit as Osiris, whether or not the person set a name."""
    return ("-c", f"user.name={OSIRIS[0]}", "-c", f"user.email={OSIRIS[1]}")
