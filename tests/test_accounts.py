"""Connecting the person's own accounts through the opencode service."""

from __future__ import annotations

from osiris.harness.accounts import Method, Provider
from osiris.harness.opencode import OpencodeAccounts, Service
from osiris.platform import FakeHttpClient

URL = "http://127.0.0.1:49374"

# As opencode 2.0.32 lists it, with no account connected.
OPENAI = {
    "id": "openai",
    "name": "OpenAI",
    "methods": [
        {"type": "key"},
        {"type": "env", "names": ["OPENAI_API_KEY"]},
        {
            "id": "chatgpt-token-sharing",
            "type": "oauth",
            "label": "Sign in with ChatGPT",
        },
        {
            "id": "chatgpt-headless",
            "type": "oauth",
            "label": "Codex device code (legacy)",
        },
    ],
    "connections": [],
}


def accounts(http: FakeHttpClient) -> OpencodeAccounts:
    return OpencodeAccounts(http, Service(URL, "secret"))


def test_a_provider_lists_the_ways_a_person_can_sign_in() -> None:
    http = FakeHttpClient(
        replies={("GET", f"{URL}/api/integration"): {"data": [OPENAI]}}
    )
    assert accounts(http).providers() == [
        Provider(
            id="openai",
            name="OpenAI",
            methods=(
                Method(id=None, kind="key", label="API key"),
                Method(
                    id="chatgpt-token-sharing",
                    kind="oauth",
                    label="Sign in with ChatGPT",
                ),
                Method(
                    id="chatgpt-headless",
                    kind="oauth",
                    label="Codex device code (legacy)",
                ),
            ),
            connected=False,
        )
    ]


def test_a_provider_with_a_working_credential_is_connected() -> None:
    signed_in = {
        **OPENAI,
        "connections": [
            {
                "type": "credential",
                "id": "cred_1",
                "label": "ChatGPT",
                "method": "oauth",
            }
        ],
    }
    http = FakeHttpClient(
        replies={("GET", f"{URL}/api/integration"): {"data": [signed_in]}}
    )
    assert accounts(http).providers()[0].connected


def test_a_connection_that_needs_signing_in_again_is_not_connected() -> None:
    expired = {
        **OPENAI,
        "connections": [
            {
                "type": "credential",
                "id": "cred_1",
                "label": "ChatGPT",
                "method": "oauth",
                "status": {"status": "needs_auth", "message": "Sign in again"},
            }
        ],
    }
    http = FakeHttpClient(
        replies={("GET", f"{URL}/api/integration"): {"data": [expired]}}
    )
    assert not accounts(http).providers()[0].connected
