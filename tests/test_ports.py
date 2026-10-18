"""Adapters satisfy the ports the rest of the code depends on."""

from __future__ import annotations

from osiris.harness.accounts import Accounts
from osiris.harness.engine import Engine
from osiris.harness.opencode import OpencodeAccounts, OpencodeEngine, Service
from osiris.platform import FakeHttpClient

SERVICE = Service("http://127.0.0.1:1", "secret")


def test_the_opencode_engine_is_an_engine() -> None:
    assert isinstance(OpencodeEngine(FakeHttpClient(), SERVICE), Engine)


def test_opencode_accounts_are_accounts() -> None:
    assert isinstance(OpencodeAccounts(FakeHttpClient(), SERVICE), Accounts)
