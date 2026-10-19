"""Edits to /etc/pacman.conf that the install leaves behind.

archinstall writes the repositories it installed from into the new system's
pacman.conf as well as the live one's. For Osiris's own repository that is a
`file://` path on the install medium, which does not exist once the machine
reboots - and pacman fails every `-Syu` on a repository it cannot reach. So
the setup step takes it out again, and names the hosted repository instead.
"""

from __future__ import annotations

import re

_SECTION = re.compile(r"^\[(?P<name>[^\]]+)\]\s*$")
_SERVER = re.compile(r"^\s*Server\s*=\s*(?P<url>\S+)")


def without_local_repository(text: str, name: str) -> str:
    """`text` with every `[name]` section removed that is served from a file.

    Every one, because archinstall writes the section twice: once into the
    live system's pacman.conf, which it then copies onto the target, and once
    more into the target's own. A section runs from its header to the next
    header or the end. Anything else - other repositories, comments, a
    `[name]` served over the network - is returned untouched.
    """
    sections: list[list[str]] = [[]]
    for line in text.splitlines(keepends=True):
        if _SECTION.match(line):
            sections.append([])
        sections[-1].append(line)
    return "".join(
        "".join(section) for section in sections if not _is_local(section, name)
    )


def _is_local(section: list[str], name: str) -> bool:
    header = _SECTION.match(section[0]) if section else None
    if header is None or header.group("name") != name:
        return False
    servers = [match.group("url") for line in section if (match := _SERVER.match(line))]
    return bool(servers) and all(url.startswith("file://") for url in servers)


def with_hosted_repository(text: str, name: str, server: str) -> str:
    """`text` with the install medium's `[name]` replaced by the hosted one.

    Packages must be signed by a key pacman trusts; the database is not
    signed. A `[name]` already served over the network is left as it is.
    """
    cleaned = without_local_repository(text, name)
    if any(
        (header := _SECTION.match(line)) and header.group("name") == name
        for line in cleaned.splitlines()
    ):
        return cleaned
    return (
        cleaned.rstrip("\n")
        + f"\n\n[{name}]\nSigLevel = Required DatabaseOptional\nServer = {server}\n"
    )
