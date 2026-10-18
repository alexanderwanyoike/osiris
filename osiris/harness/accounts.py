"""The Accounts port: the Providers the Engine can reach, and signing in.

Kept apart from the Engine port (ADR 0015): talking to a model and managing
the person's accounts change for different reasons, and a surface that only
connects accounts should not depend on the agent loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable


@dataclass(frozen=True)
class Method:
    """One way to sign in: an API key, or a sign-in page (OAuth)."""

    id: str | None
    kind: Literal["key", "oauth"]
    label: str


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    methods: tuple[Method, ...]
    connected: bool


@dataclass(frozen=True)
class SignIn:
    """A sign-in in progress: a page to open, and whether a code comes back."""

    provider: str
    attempt: str
    url: str
    instructions: str
    needs_code: bool


@runtime_checkable
class Accounts(Protocol):
    def providers(self) -> list[Provider]: ...

    def connect_key(self, provider: str, key: str) -> None: ...

    def start_sign_in(self, provider: str, method: str) -> SignIn: ...
