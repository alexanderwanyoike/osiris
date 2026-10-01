"""Who the process is running as."""

from __future__ import annotations

import pwd
from pathlib import Path

from osiris.platform import FakeIdentity, Identity, SystemIdentity


def test_both_implementations_satisfy_the_port() -> None:
    assert isinstance(SystemIdentity(), Identity)
    assert isinstance(FakeIdentity(), Identity)


def test_home_comes_from_the_account_not_the_environment(
    monkeypatch, tmp_path: Path
) -> None:
    """The reason this module exists.

    Under `su <user> -c`, $HOME is still root's. Anything that trusts it writes
    the user's themes and previews into /root, where they never see them.
    """
    monkeypatch.setenv("HOME", str(tmp_path / "wrong"))
    identity = SystemIdentity()
    assert identity.home != tmp_path / "wrong"
    assert identity.home == Path(pwd.getpwuid(identity.uid).pw_dir)


def test_root_is_recognised() -> None:
    assert FakeIdentity(uid=0).is_root()
    assert not FakeIdentity(uid=1000).is_root()
