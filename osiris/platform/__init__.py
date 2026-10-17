"""Adapters for everything outside this process.

Running a command, touching the filesystem, asking who the user is. Every one
of those is behind a protocol here, and the rest of the codebase depends on the
protocol rather than the implementation.

That is not ceremony. Before this existed, nothing in the project could be
tested without a virtual machine, because every interesting function reached
straight for `subprocess.run` and `/etc`. The seam is what lets a test say
"given pacstrap fails on the third call" without having a disk to ruin.
"""

from osiris.platform.filesystem import FakeFileSystem, FileSystem, RealFileSystem
from osiris.platform.http import FakeHttpClient, HttpClient, HttpError, UrllibClient
from osiris.platform.identity import FakeIdentity, Identity, SystemIdentity
from osiris.platform.process import (
    CommandError,
    CommandRunner,
    FakeRunner,
    RecordedCall,
    SubprocessRunner,
)

__all__ = [
    "CommandError",
    "CommandRunner",
    "FakeFileSystem",
    "FakeHttpClient",
    "FakeIdentity",
    "FakeRunner",
    "FileSystem",
    "HttpClient",
    "HttpError",
    "Identity",
    "RealFileSystem",
    "RecordedCall",
    "SubprocessRunner",
    "SystemIdentity",
    "UrllibClient",
]
