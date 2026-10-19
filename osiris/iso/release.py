"""A release: the ISO built from a git tag, with a checksum published beside it.

The release workflow (.github/workflows/release.yml) runs iso/release.py,
which builds the ISO and uploads both files; the decisions are here.
"""

from __future__ import annotations

import re

_TAG = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)$")


class ReleaseError(ValueError):
    pass


def version_from_tag(tag: str, *, code_version: str) -> str:
    """The version a tag releases, which must be the code's own."""
    match = _TAG.match(tag)
    if match is None:
        raise ReleaseError(f"{tag!r} is not a release tag such as v0.1.0")
    version = match.group("version")
    if version != code_version:
        raise ReleaseError(
            f"The tag releases {version} but the code says {code_version}; "
            "bump osiris.__version__ first"
        )
    return version


def checksum_line(name: str, digest: str) -> str:
    """One line of a SHA256SUMS-style file, as `sha256sum -c` reads it."""
    return f"{digest}  {name}\n"


_PACKAGE = (".pkg.tar.zst", ".pkg.tar.zst.sig")


def publish_order(names: list[str]) -> tuple[list[str], list[str]]:
    """A repository's files as two uploads: the packages and their signatures,
    then the databases, so the database never names a package not yet there."""
    packages = sorted(name for name in names if name.endswith(_PACKAGE))
    databases = sorted(name for name in names if not name.endswith(_PACKAGE))
    return packages, databases
