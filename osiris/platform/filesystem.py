"""Reading and writing files, with ownership handled properly.

The ownership part is the reason this is a port rather than bare `pathlib`.
Provisioning runs as root, on a fresh install, before anyone has logged in.
Every directory it creates belongs to root unless it is explicitly handed
back - and chowning the file you wrote while missing the `.config` the same
call created leaves the user unable to write their own configuration directory,
permanently. That shipped once. `write` and `make_directory` take an owner so
it cannot happen quietly again.
"""

from __future__ import annotations

import contextlib
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from osiris.platform.identity import Identity


@runtime_checkable
class FileSystem(Protocol):
    def read(self, path: Path) -> str: ...

    def exists(self, path: Path) -> bool: ...

    def write(
        self,
        path: Path,
        text: str,
        *,
        owner: Identity | None = None,
        mode: int | None = None,
    ) -> None: ...

    def make_directory(self, path: Path, *, owner: Identity | None = None) -> None: ...

    def copy(
        self, source: Path, destination: Path, *, owner: Identity | None = None
    ) -> None: ...

    def remove_tree(self, path: Path) -> None: ...

    def list_directory(self, path: Path) -> list[Path]: ...


class RealFileSystem:
    def read(self, path: Path) -> str:
        return path.read_text()

    def exists(self, path: Path) -> bool:
        return path.exists()

    def write(
        self,
        path: Path,
        text: str,
        *,
        owner: Identity | None = None,
        mode: int | None = None,
    ) -> None:
        self.make_directory(path.parent, owner=owner)
        path.write_text(text)
        if mode is not None:
            path.chmod(mode)
        self._give(path, owner)

    def make_directory(self, path: Path, *, owner: Identity | None = None) -> None:
        """`mkdir -p`, giving every component this call creates to `owner`.

        Components that already existed are left alone - their ownership is not
        ours to change.
        """
        created: list[Path] = []
        probe = path
        while not probe.exists():
            created.append(probe)
            if probe.parent == probe:
                break
            probe = probe.parent
        path.mkdir(parents=True, exist_ok=True)
        for directory in created:
            self._give(directory, owner)

    def copy(
        self, source: Path, destination: Path, *, owner: Identity | None = None
    ) -> None:
        self.make_directory(destination.parent, owner=owner)
        shutil.copy(source, destination)
        self._give(destination, owner)

    def remove_tree(self, path: Path) -> None:
        shutil.rmtree(path, ignore_errors=True)

    def list_directory(self, path: Path) -> list[Path]:
        return sorted(path.iterdir()) if path.is_dir() else []

    def give_tree(self, path: Path, owner: Identity) -> None:
        """Hand `path` and everything under it to `owner`.

        Note the root of the tree, which `os.walk` reports as a parent rather
        than an entry - the half of this that an earlier version missed.
        """
        if not path.exists():
            return
        self._give(path, owner)
        for root, directories, files in os.walk(path):
            for entry in (*directories, *files):
                self._give(Path(root) / entry, owner)

    @staticmethod
    def _give(path: Path, owner: Identity | None) -> None:
        if owner is None:
            return
        # Not root, or the path vanished. Neither is worth aborting for.
        with contextlib.suppress(OSError):
            os.chown(path, owner.uid, owner.gid)


@dataclass
class FakeFileSystem:
    """An in-memory filesystem, so tests assert on content rather than disk."""

    files: dict[Path, str] = field(default_factory=dict)
    directories: set[Path] = field(default_factory=set)
    owners: dict[Path, int] = field(default_factory=dict)
    modes: dict[Path, int] = field(default_factory=dict)

    def read(self, path: Path) -> str:
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path]

    def exists(self, path: Path) -> bool:
        return path in self.files or path in self.directories

    def write(
        self,
        path: Path,
        text: str,
        *,
        owner: Identity | None = None,
        mode: int | None = None,
    ) -> None:
        self.make_directory(path.parent, owner=owner)
        self.files[path] = text
        if mode is not None:
            self.modes[path] = mode
        if owner is not None:
            self.owners[path] = owner.uid

    def make_directory(self, path: Path, *, owner: Identity | None = None) -> None:
        for parent in (path, *path.parents):
            if parent in self.directories:
                continue
            self.directories.add(parent)
            if owner is not None:
                self.owners[parent] = owner.uid

    def copy(
        self, source: Path, destination: Path, *, owner: Identity | None = None
    ) -> None:
        self.write(destination, self.files.get(source, ""), owner=owner)

    def remove_tree(self, path: Path) -> None:
        self.files = {p: t for p, t in self.files.items() if path not in p.parents}
        self.directories = {d for d in self.directories if path not in d.parents}
        self.directories.discard(path)

    def list_directory(self, path: Path) -> list[Path]:
        return sorted(
            {p for p in self.files if p.parent == path}
            | {d for d in self.directories if d.parent == path}
        )

    def give_tree(self, path: Path, owner: Identity) -> None:
        for known in (*self.files, *self.directories):
            if known == path or path in known.parents:
                self.owners[known] = owner.uid
