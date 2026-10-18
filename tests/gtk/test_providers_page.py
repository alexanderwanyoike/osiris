"""The Providers page: connect accounts and choose the Default model."""

from __future__ import annotations

from dataclasses import dataclass, field

from gi.repository import Gtk
from providers import ProvidersPage

from osiris.harness.accounts import Method, ModelInfo, Provider, SignIn, SignInState
from osiris.harness.engine import ModelRef
from tests.gtk.conftest import find, now, texts

KEY = Method(id=None, kind="key", label="API key")


@dataclass
class FakeAccounts:
    listed: list[Provider] = field(default_factory=list)
    keys: list[tuple[str, str]] = field(default_factory=list)

    def providers(self) -> list[Provider]:
        return self.listed

    def connect_key(self, provider: str, key: str) -> None:
        self.keys.append((provider, key))

    def start_sign_in(self, provider: str, method: str) -> SignIn:
        return SignIn(provider, "att", "https://example.org", "Sign in", False)

    def sign_in_state(self, provider: str, attempt: str) -> SignInState:
        return SignInState("complete", "")

    def finish_sign_in(self, provider: str, attempt: str, code: str | None) -> None:
        pass

    def models(self) -> list[ModelInfo]:
        return [ModelInfo(ModelRef("opencode", "big-pickle"), "Big Pickle")]


def test_each_provider_shows_whether_it_is_connected() -> None:
    accounts = FakeAccounts(
        listed=[
            Provider("openai", "OpenAI", (KEY,), connected=True),
            Provider("opencode-go", "OpenCode Go", (KEY,), connected=False),
        ]
    )
    page = ProvidersPage(accounts, background=now)
    shown = texts(page)
    assert "OpenAI" in shown
    assert "OpenCode Go" in shown
    assert shown.count("Connected") == 1


def test_a_key_typed_for_a_provider_is_given_to_the_engine() -> None:
    accounts = FakeAccounts(
        listed=[Provider("opencode-go", "OpenCode Go", (KEY,), False)]
    )
    page = ProvidersPage(accounts, background=now)
    find(page, Gtk.PasswordEntry).set_text("sk-test")
    find(page, Gtk.Button, "Save").emit("clicked")
    assert accounts.keys == [("opencode-go", "sk-test")]
