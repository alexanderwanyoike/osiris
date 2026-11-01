"""A Program's files as the Canvas's tree shows them (#198): nested in their
folders, folders before files, each in name order."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Node:
    name: str
    path: Path
    #: A folder's contents; a file has none.
    children: tuple[Node, ...] = ()

    @property
    def folder(self) -> bool:
        return bool(self.children)


def tree(paths: list[Path], under: Path = Path()) -> tuple[Node, ...]:
    """The files in ``paths``, relative to their Program, under ``under``."""
    folders: dict[str, list[Path]] = {}
    files: list[Node] = []
    for path in paths:
        first, *rest = path.relative_to(under).parts
        if rest:
            folders.setdefault(first, []).append(path)
        else:
            files.append(Node(first, path))
    nested = [
        Node(name, under / name, tree(inside, under / name))
        for name, inside in folders.items()
    ]
    return tuple(
        sorted(nested, key=lambda node: node.name.lower())
        + sorted(files, key=lambda node: node.name.lower())
    )
