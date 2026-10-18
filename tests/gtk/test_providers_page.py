"""The Providers page: connect accounts and choose the Default model."""

from __future__ import annotations

from dataclasses import dataclass, field

from gi.repository import Gtk
from providers import ProvidersPage

from osiris.harness.accounts import Method, ModelInfo, Provider, SignIn, SignInState
from osiris.harness.engine import ModelRef
from tests.gtk.conftest import find, now, texts

KEY = Method(id=None, kind="key", label="API key")
CHATGPT = Method(id="chatgpt-token-sharing", kind="oauth", label="Sign in with ChatGPT")


@dataclass
class FakeAccounts:
    listed: list[Provider] = field(default_factory=list)
    keys: list[tuple[str, str]] = field(default_factory=list)
    started: list[tuple[str, str]] = field(default_factory=list)

    def providers(self) -> list[Provider]:
        return self.listed

    def connect_key(self, provider: str, key: str) -> None:
        self.keys.append((provider, key))
        self.listed = [
            Provider(p.id, p.name, p.methods, p.connected or p.id == provider)
            for p in self.listed
        ]

    def start_sign_in(self, provider: str, method: str) -> SignIn:
        self.started.append((provider, method))
        return SignIn(provider, "att", "https://auth.example.org/x", "Sign in", False)

    def sign_in_state(self, provider: str, attempt: str) -> SignInState:
        self.listed = [
            Provider(p.id, p.name, p.methods, p.connected or p.id == provider)
            for p in self.listed
        ]
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


def test_once_a_key_is_saved_the_provider_shows_as_connected() -> None:
    accounts = FakeAccounts(
        listed=[Provider("opencode-go", "OpenCode Go", (KEY,), False)]
    )
    page = ProvidersPage(accounts, background=now)
    find(page, Gtk.PasswordEntry).set_text("sk-test")
    find(page, Gtk.Button, "Save").emit("clicked")
    assert "Connected" in texts(page)


def test_signing_in_opens_the_providers_page_and_ends_connected() -> None:
    accounts = FakeAccounts(listed=[Provider("openai", "OpenAI", (CHATGPT,), False)])
    opened: list[str] = []
    page = ProvidersPage(
        accounts, background=now, open_page=opened.append, later=lambda _s, then: then()
    )
    find(page, Gtk.Button, "Sign in with ChatGPT").emit("clicked")
    assert accounts.started == [("openai", "chatgpt-token-sharing")]
    assert opened == ["https://auth.example.org/x"]
    assert "Connected" in texts(page)


def test_a_failed_sign_in_says_why() -> None:
    class Refusing(FakeAccounts):
        def sign_in_state(self, provider: str, attempt: str) -> SignInState:
            return SignInState("failed", "Access was denied")

    accounts = Refusing(listed=[Provider("openai", "OpenAI", (CHATGPT,), False)])
    page = ProvidersPage(
        accounts,
        background=now,
        open_page=lambda _u: None,
        later=lambda _s, then: then(),
    )
    find(page, Gtk.Button, "Sign in with ChatGPT").emit("clicked")
    assert "Access was denied" in texts(page)


def test_a_sign_in_that_returns_a_code_takes_it_from_the_person() -> None:
    finished: list[tuple[str, str, str | None]] = []

    class WithCode(FakeAccounts):
        def start_sign_in(self, provider: str, method: str) -> SignIn:
            return SignIn(
                provider, "att", "https://auth.example.org/d", "Paste the code", True
            )

        def finish_sign_in(self, provider: str, attempt: str, code: str | None) -> None:
            finished.append((provider, attempt, code))

    accounts = WithCode(listed=[Provider("openai", "OpenAI", (CHATGPT,), False)])
    page = ProvidersPage(
        accounts, background=now, open_page=lambda _u: None, later=lambda _s, then: None
    )
    find(page, Gtk.Button, "Sign in with ChatGPT").emit("clicked")
    assert "Paste the code" in texts(page)
    find(page, Gtk.Entry).set_text(" ABCD-1234 ")
    find(page, Gtk.Button, "Finish").emit("clicked")
    assert finished == [("openai", "att", "ABCD-1234")]
