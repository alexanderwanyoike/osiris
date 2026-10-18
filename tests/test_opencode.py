"""The opencode adapter, against events recorded from opencode 2.0.32."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from osiris.harness.engine import (
    Answered,
    Failed,
    Finished,
    ModelRef,
    Stopped,
    Text,
    Tokens,
    ToolCalled,
    ToolRequested,
)
from osiris.harness.opencode import (
    ASK_EVERYTHING,
    SERVICE_FILE,
    OpencodeEngine,
    Service,
    locate,
)
from osiris.platform import FakeFileSystem, FakeHttpClient, FakeIdentity, FakeRunner

URL = "http://127.0.0.1:49374"
SESSION = "ses_eb47d80feffe3d0JrczUcoVEMq"
STEP = "msg_14b827f39001PUnYctEeCQ7CBJ"
PICKLE = {"id": "big-pickle", "providerID": "opencode"}

# A plain answer, as the event stream delivered it (fields trimmed).
ANSWER = [
    {"type": "server.connected", "data": {}},
    {"type": "session.execution.started", "data": {"sessionID": SESSION}},
    {
        "type": "session.step.started",
        "data": {
            "sessionID": SESSION,
            "agent": "build",
            "model": PICKLE,
            "assistantMessageID": STEP,
        },
    },
    {
        "type": "session.text.delta",
        "data": {"sessionID": SESSION, "assistantMessageID": STEP, "delta": "hello "},
    },
    {
        "type": "session.text.delta",
        "data": {"sessionID": SESSION, "assistantMessageID": STEP, "delta": "there"},
    },
    {
        "type": "session.step.ended",
        "data": {
            "sessionID": SESSION,
            "assistantMessageID": STEP,
            "finish": "stop",
            "cost": 0,
            "tokens": {
                "input": 148,
                "output": 11,
                "reasoning": 79,
                "cache": {"read": 4004, "write": 0},
            },
        },
    },
    {"type": "session.usage.updated", "data": {"sessionID": SESSION, "cost": 0}},
    {"type": "session.execution.succeeded", "data": {"sessionID": SESSION}},
]

# The model reaching for the shell in a session that asks for everything.
TOOL = [
    {
        "type": "session.tool.called",
        "data": {
            "sessionID": SESSION,
            "assistantMessageID": STEP,
            "id": "bc9122d7",
            "input": {"command": "ls /etc"},
            "executed": False,
        },
    },
    {
        "type": "session.tool.input.started",
        "data": {"sessionID": SESSION, "id": "bc9122d7", "name": "shell"},
    },
    {
        "type": "permission.asked",
        "data": {
            "id": "per_14b99bc5a001drhmJZhNc5wHRG",
            "sessionID": SESSION,
            "action": "shell",
            "resources": ["ls /etc"],
            "save": ["ls *"],
        },
    },
]

FREE_TIER_REFUSAL = {
    "type": "session.execution.failed",
    "data": {
        "sessionID": SESSION,
        "error": {
            "type": "provider.auth",
            "message": "OpenCode's free tier can only be used from within OpenCode.",
            "status": 403,
        },
    },
}


def stream(*events: dict[str, object]) -> list[str]:
    """Events framed as the server sends them, heartbeats included."""
    lines: list[str] = []
    for event in events:
        lines += [f"data: {json.dumps(event)}", "", ": heartbeat", ""]
    return lines


def engine(http: FakeHttpClient) -> OpencodeEngine:
    return OpencodeEngine(http, Service(URL, "secret"))


class TestLocate:
    def test_the_service_is_started_then_read_from_its_state_file(self) -> None:
        home = Path("/home/tester")
        files = FakeFileSystem()
        files.write(
            home / SERVICE_FILE,
            json.dumps({"url": URL, "password": "secret", "pid": 1}),
        )
        runner = FakeRunner()

        service = locate(files, FakeIdentity(home=home), runner)

        assert service == Service(URL, "secret")
        assert runner.commands == ["opencode service start"]

    def test_the_password_is_sent_as_basic_auth_for_the_opencode_user(self) -> None:
        token = base64.b64encode(b"opencode:secret").decode()
        assert Service(URL, "secret").headers() == {"Authorization": f"Basic {token}"}


class TestSessions:
    def test_a_session_asks_before_every_action(self) -> None:
        http = FakeHttpClient(
            replies={("POST", f"{URL}/api/session"): {"data": {"id": SESSION}}}
        )
        assert engine(http).start() == SESSION
        _, _, body = http.requests[0]
        assert isinstance(body, dict)
        assert body["permissions"] == ASK_EVERYTHING
        assert ASK_EVERYTHING == [{"action": "*", "resource": "*", "effect": "ask"}]

    def test_a_chosen_model_is_named_on_the_session(self) -> None:
        http = FakeHttpClient(
            replies={("POST", f"{URL}/api/session"): {"data": {"id": SESSION}}}
        )
        engine(http).start(ModelRef("openai", "gpt-5.5"))
        _, _, body = http.requests[0]
        assert isinstance(body, dict)
        assert body["model"] == {"providerID": "openai", "id": "gpt-5.5"}

    def test_sending_posts_the_text_as_a_prompt(self) -> None:
        path = f"{URL}/api/session/{SESSION}/prompt"
        http = FakeHttpClient(replies={("POST", path): {"data": {}}})
        engine(http).send(SESSION, "hello")
        assert http.requests == [("POST", path, {"text": "hello"})]

    def test_stopping_interrupts_the_session(self) -> None:
        path = f"{URL}/api/session/{SESSION}/interrupt"
        http = FakeHttpClient(replies={("POST", path): {"interrupted": True}})
        engine(http).stop(SESSION)
        assert http.requests == [("POST", path, None)]

    def test_switching_model_names_it_on_the_session(self) -> None:
        path = f"{URL}/api/session/{SESSION}/model"
        http = FakeHttpClient(replies={("POST", path): {"data": {}}})
        engine(http).switch_model(SESSION, ModelRef("openai", "gpt-5.5"))
        assert http.requests == [
            ("POST", path, {"model": {"providerID": "openai", "id": "gpt-5.5"}})
        ]

    @pytest.mark.parametrize(("allow", "decision"), [(True, "once"), (False, "reject")])
    def test_a_tool_request_is_answered_once_or_rejected(
        self, allow: bool, decision: str
    ) -> None:
        path = f"{URL}/api/session/{SESSION}/permission/per_1/reply"
        http = FakeHttpClient(replies={("POST", path): None})
        engine(http).reply(SESSION, "per_1", allow=allow, message="why")
        assert http.requests == [
            ("POST", path, {"decision": decision, "message": "why"})
        ]


class TestEvents:
    def events(self, *recorded: dict[str, object]) -> list[object]:
        http = FakeHttpClient(streams={f"{URL}/api/event": stream(*recorded)})
        return list(engine(http).events())

    def test_an_answer_streams_as_text_then_names_its_model_and_tokens(self) -> None:
        assert self.events(*ANSWER) == [
            Text(SESSION, "hello "),
            Text(SESSION, "there"),
            Answered(
                SESSION,
                ModelRef("opencode", "big-pickle"),
                Tokens(
                    input=148, output=11, reasoning=79, cache_read=4004, cache_write=0
                ),
                cost=0.0,
            ),
            Finished(SESSION),
        ]

    def test_every_tool_call_is_reported_and_a_permission_becomes_a_request(
        self,
    ) -> None:
        assert self.events(*TOOL) == [
            ToolCalled(SESSION, "bc9122d7", {"command": "ls /etc"}, executed=False),
            ToolRequested(
                SESSION, "per_14b99bc5a001drhmJZhNc5wHRG", "shell", ("ls /etc",)
            ),
        ]

    def test_a_refusal_is_a_failure_carrying_the_engines_message(self) -> None:
        assert self.events(FREE_TIER_REFUSAL) == [
            Failed(
                SESSION, "OpenCode's free tier can only be used from within OpenCode."
            )
        ]

    def test_an_interrupted_run_is_stopped(self) -> None:
        interrupted = {
            "type": "session.execution.interrupted",
            "data": {"sessionID": SESSION},
        }
        assert self.events(interrupted) == [Stopped(SESSION)]
