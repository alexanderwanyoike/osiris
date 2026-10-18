"""Connecting the person's own accounts through the opencode service."""

from __future__ import annotations

import pytest

from osiris.harness.accounts import Method, ModelInfo, Provider, SignIn, SignInState
from osiris.harness.engine import ModelRef
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


def test_an_api_key_is_given_to_the_engine_for_that_provider() -> None:
    path = f"{URL}/api/integration/opencode-go/connect/key"
    http = FakeHttpClient(replies={("POST", path): None})
    accounts(http).connect_key("opencode-go", "sk-test")
    assert http.requests == [("POST", path, {"key": "sk-test"})]


def test_signing_in_starts_an_attempt_with_a_page_to_open() -> None:
    path = f"{URL}/api/integration/openai/connect/oauth"
    attempt = {
        "attemptID": "att_1",
        "url": "https://auth.openai.com/authorize?x=1",
        "instructions": "Sign in, then return here.",
        "mode": "auto",
        "time": {"created": 1, "expires": 2},
    }
    http = FakeHttpClient(replies={("POST", path): {"data": attempt}})
    sign_in = accounts(http).start_sign_in("openai", "chatgpt-token-sharing")
    assert http.requests == [("POST", path, {"methodID": "chatgpt-token-sharing"})]
    assert sign_in == SignIn(
        provider="openai",
        attempt="att_1",
        url="https://auth.openai.com/authorize?x=1",
        instructions="Sign in, then return here.",
        needs_code=False,
    )


def test_a_sign_in_in_code_mode_asks_the_person_to_paste_a_code_back() -> None:
    path = f"{URL}/api/integration/openai/connect/oauth"
    attempt = {
        "attemptID": "att_2",
        "url": "https://auth.openai.com/device",
        "instructions": "Enter the code shown.",
        "mode": "code",
        "time": {"created": 1, "expires": 2},
    }
    http = FakeHttpClient(replies={("POST", path): {"data": attempt}})
    assert accounts(http).start_sign_in("openai", "chatgpt-headless").needs_code


@pytest.mark.parametrize(
    ("reply", "state"),
    [
        ({"status": "pending"}, SignInState("pending", "")),
        ({"status": "complete"}, SignInState("complete", "")),
        ({"status": "failed", "message": "Denied"}, SignInState("failed", "Denied")),
        ({"status": "expired"}, SignInState("expired", "")),
    ],
)
def test_a_sign_in_reports_how_far_it_has_got(
    reply: dict[str, str], state: SignInState
) -> None:
    path = f"{URL}/api/integration/openai/connect/oauth/att_1"
    times = {"time": {"created": 1, "expires": 2}}
    http = FakeHttpClient(replies={("GET", path): {"data": {**reply, **times}}})
    assert accounts(http).sign_in_state("openai", "att_1") == state


def test_finishing_a_sign_in_passes_the_code_the_person_pasted() -> None:
    path = f"{URL}/api/integration/openai/connect/oauth/att_2/complete"
    http = FakeHttpClient(replies={("POST", path): None})
    accounts(http).finish_sign_in("openai", "att_2", "ABCD-1234")
    assert http.requests == [("POST", path, {"code": "ABCD-1234"})]


def test_finishing_a_sign_in_that_needs_no_code_sends_none() -> None:
    path = f"{URL}/api/integration/openai/connect/oauth/att_1/complete"
    http = FakeHttpClient(replies={("POST", path): None})
    accounts(http).finish_sign_in("openai", "att_1", None)
    assert http.requests == [("POST", path, {"code": None})]


def test_the_models_the_engine_can_reach_are_listed_by_name() -> None:
    pickle = {
        "id": "big-pickle",
        "modelID": "big-pickle",
        "providerID": "opencode",
        "name": "Big Pickle",
        "enabled": True,
    }
    http = FakeHttpClient(replies={("GET", f"{URL}/api/model"): {"data": [pickle]}})
    assert accounts(http).models() == [
        ModelInfo(ModelRef("opencode", "big-pickle"), "Big Pickle")
    ]
