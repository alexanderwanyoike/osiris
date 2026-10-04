"""Edits to /etc/pacman.conf that the install leaves behind.

archinstall writes the repositories it installed from into the new system's
pacman.conf as well as the live one's. For Osiris's own repository that is a
`file://` path on the install medium, which does not exist once the machine
reboots - and pacman fails every `-Syu` on a repository it cannot reach. So
the setup step takes it out again. When Osiris has a hosted repository the
install will name that instead, and this removes nothing.
"""

from __future__ import annotations

import re

_SECTION = re.compile(r"^\[(?P<name>[^\]]+)\]\s*$")
_SERVER = re.compile(r"^\s*Server\s*=\s*(?P<url>\S+)")


def without_local_repository(text: str, name: str) -> str:
    """`text` with the `[name]` section removed if it is served from a file.

    The section runs from its header to the next header or the end. Anything
    else - other repositories, comments, a `[name]` served over the network -
    is returned untouched.
    """
    lines = text.splitlines(keepends=True)
    start = end = None
    for index, line in enumerate(lines):
        header = _SECTION.match(line)
        if header is None:
            continue
        if start is not None:
            end = index
            break
        if header.group("name") == name:
            start = index
    if start is None:
        return text
    end = len(lines) if end is None else end

    servers = [
        match.group("url")
        for line in lines[start:end]
        if (match := _SERVER.match(line))
    ]
    if not servers or not all(url.startswith("file://") for url in servers):
        return text
    return "".join(lines[:start] + lines[end:])
