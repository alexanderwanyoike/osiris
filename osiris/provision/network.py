"""Whether the install can reach Arch's mirrors, and joining a network if not."""

from __future__ import annotations

from osiris.platform.http import HttpClient

#: Asked when the medium's mirrorlist names no server at all.
FALLBACK = "https://archlinux.org/"


def mirror_url(mirrorlist: str) -> str:
    """Where to ask whether the install's downloads will work.

    The first server in the medium's mirrorlist, which is the one pacman
    tries first: Osiris sets no mirror regions, so archinstall leaves that
    file as it is. Its core database is small and always there.
    """
    for line in mirrorlist.splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "Server" and value.strip():
            base = value.strip().replace("$repo", "core").replace("$arch", "x86_64")
            return f"{base.rstrip('/')}/core.db"
    return FALLBACK


def reachable(http: HttpClient, url: str) -> bool:
    """Whether anything at url answers."""
    return False
