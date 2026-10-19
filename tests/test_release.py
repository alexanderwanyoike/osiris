"""A release: the ISO built from a tag, and the checksum published beside it."""

from __future__ import annotations

import pytest

from osiris.iso.release import (
    ReleaseError,
    checksum_line,
    publish_order,
    version_from_tag,
)


def test_a_tag_names_the_version_it_releases() -> None:
    assert version_from_tag("v0.1.0", code_version="0.1.0") == "0.1.0"


def test_a_tag_that_disagrees_with_the_code_is_refused() -> None:
    """Homes are brought up to the code's version, so a release must carry it."""
    with pytest.raises(ReleaseError, match=r"0\.2\.0.*0\.1\.0"):
        version_from_tag("v0.2.0", code_version="0.1.0")


def test_a_tag_must_be_v_and_a_version() -> None:
    with pytest.raises(ReleaseError, match="not a release tag"):
        version_from_tag("nightly", code_version="0.1.0")


def test_the_checksum_is_in_the_form_sha256sum_checks() -> None:
    assert checksum_line("osiris-0.1.0-x86_64.iso", "ab" * 32) == (
        f"{'ab' * 32}  osiris-0.1.0-x86_64.iso\n"
    )


def test_packages_are_published_before_the_database_that_names_them() -> None:
    names = [
        "osiris.db",
        "osiris-0.1.0-1-any.pkg.tar.zst",
        "osiris.db.tar.gz",
        "osiris-0.1.0-1-any.pkg.tar.zst.sig",
        "osiris.files",
        "osiris.files.tar.gz",
    ]
    packages, databases = publish_order(names)
    assert packages == [
        "osiris-0.1.0-1-any.pkg.tar.zst",
        "osiris-0.1.0-1-any.pkg.tar.zst.sig",
    ]
    assert databases == [
        "osiris.db",
        "osiris.db.tar.gz",
        "osiris.files",
        "osiris.files.tar.gz",
    ]


def test_the_databases_repo_add_set_aside_are_not_published() -> None:
    packages, databases = publish_order(["osiris.db.tar.gz", "osiris.db.tar.gz.old"])
    assert (packages, databases) == ([], ["osiris.db.tar.gz"])
