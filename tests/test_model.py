"""The domain model. No ports, no fakes - it has no dependencies to invert."""

from __future__ import annotations

import pytest

from osiris.model.disk import (
    MINIMUM_BYTES,
    Disk,
    human,
)
from osiris.model.layout import InstallMode
from osiris.model.request import MINIMUM_PASSPHRASE, InstallRequest, InvalidRequest


def a_disk(**overrides: object) -> Disk:
    defaults = {"path": "/dev/vda", "size": 30 * 1000**3, "label": "Test"}
    return Disk(**{**defaults, **overrides})  # type: ignore[arg-type]


class TestUsability:
    def test_a_disk_below_the_minimum_is_refused_with_a_reason(self) -> None:
        disk = a_disk(size=MINIMUM_BYTES - 1)
        assert not disk.usable
        assert "too small" in (disk.unusable_because or "")

    def test_a_mounted_disk_is_refused(self) -> None:
        """Almost always the medium being booted from."""
        disk = a_disk(mounted=True)
        assert not disk.usable
        assert "in use" in (disk.unusable_because or "")

    def test_a_large_idle_disk_is_usable(self) -> None:
        assert a_disk().usable
        assert a_disk().unusable_because is None


class TestHumanSizes:
    @pytest.mark.parametrize(
        ("size", "expected"),
        [
            (512, "512 B"),
            (30 * 1000**3, "30.0 GB"),
            (1000**4, "1.0 TB"),
        ],
    )
    def test_reported_in_the_units_on_the_box(self, size: int, expected: str) -> None:
        assert human(size) == expected


class TestValidation:
    def a_request(self, **overrides: object) -> InstallRequest:
        defaults = {
            "disk": a_disk(),
            "username": "alex",
            "password": "osiris123",
        }
        return InstallRequest(**{**defaults, **overrides})  # type: ignore[arg-type]

    def test_a_sound_request_is_valid(self) -> None:
        assert self.a_request().valid

    @pytest.mark.parametrize(
        "username", ["", "1alex", "Alex", "al ex", "al;ex", "-alex"]
    )
    def test_usernames_useradd_would_refuse(self, username: str) -> None:
        assert not self.a_request(username=username).valid

    @pytest.mark.parametrize("username", ["alex", "_system", "a-b_c9"])
    def test_usernames_useradd_accepts(self, username: str) -> None:
        assert self.a_request(username=username).valid

    def test_a_short_password_is_refused(self) -> None:
        assert not self.a_request(password="short").valid

    def test_an_unusable_disk_is_refused(self) -> None:
        assert not self.a_request(disk=a_disk(mounted=True)).valid

    def test_every_problem_is_reported_at_once(self) -> None:
        """A form should show all of them, not one per attempt."""
        request = self.a_request(username="", password="x", hostname="bad name")
        assert len(request.problems) == 3

    def test_validate_raises_with_every_problem_named(self) -> None:
        with pytest.raises(InvalidRequest) as caught:
            self.a_request(username="", password="x").validate()
        assert "username" in str(caught.value)
        assert "password" in str(caught.value)


class TestEncryption:
    def a_request(self, **overrides: object) -> InstallRequest:
        defaults = {
            "disk": a_disk(),
            "username": "alex",
            "password": "osiris123",
            "encrypt": True,
            "passphrase": "a long passphrase",
        }
        return InstallRequest(**{**defaults, **overrides})  # type: ignore[arg-type]

    def test_a_sound_encrypted_request_is_valid(self) -> None:
        assert self.a_request().valid

    @pytest.mark.parametrize(
        "passphrase", ["", "short", "x" * (MINIMUM_PASSPHRASE - 1)]
    )
    def test_a_short_passphrase_is_refused(self, passphrase: str) -> None:
        request = self.a_request(passphrase=passphrase)
        assert not request.valid
        assert any("passphrase" in problem for problem in request.problems)

    @pytest.mark.parametrize(
        "passphrase", ["p\u00e4ssphrase", "pass\tphrase", "\u5bc6\u7801" * 4]
    )
    def test_a_passphrase_that_may_not_be_typeable_at_boot_is_refused(
        self, passphrase: str
    ) -> None:
        assert not self.a_request(passphrase=passphrase).valid

    def test_the_passphrase_is_ignored_without_encryption(self) -> None:
        assert self.a_request(encrypt=False, passphrase="").valid

    def test_free_space_is_left_to_the_layout_to_judge(self) -> None:
        """Whether it works depends on the disk's ESP; see Layout.problems."""
        assert self.a_request(mode=InstallMode.FREE_SPACE).valid

    def test_an_existing_partition_cannot_be_encrypted(self) -> None:
        request = self.a_request(
            mode=InstallMode.EXISTING_PARTITION, root_partition="/dev/vda2"
        )
        assert not request.valid
        assert any("existing partition" in p for p in request.problems)

    def test_neither_secret_is_in_the_repr(self) -> None:
        text = repr(self.a_request())
        assert "a long passphrase" not in text
        assert "osiris123" not in text
