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
    Past,
    PastTurn,
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
            json.dumps({"url": URL, "password": "secret", "pid": 4242}),
        )
        runner = FakeRunner()

        service = locate(files, FakeIdentity(home=home), runner)

        assert service == Service(URL, "secret", pid=4242)
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

    def test_a_session_can_start_in_a_folder(self) -> None:
        http = FakeHttpClient(
            replies={("POST", f"{URL}/api/session"): {"data": {"id": SESSION}}}
        )
        engine(http).start(directory=Path("/home/tester"))
        _, _, body = http.requests[0]
        assert isinstance(body, dict)
        assert body["location"] == {"directory": "/home/tester"}

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

    def test_a_tool_server_is_attached_afresh_for_a_folder(self) -> None:
        """opencode 2.0 keeps tool servers per folder: one attached at home is
        not there for a session in a Project."""
        where = "location%5Bdirectory%5D=%2Fhome%2Ftester%2FCode%2Fpomodoro"
        path = f"{URL}/api/experimental/mcp/osiris?{where}"
        http = FakeHttpClient(replies={("DELETE", path): None, ("PUT", path): None})
        engine(http).attach_tools(
            "osiris",
            ["python3", "/srv/tool_server.py"],
            Path("/home/tester/Code/pomodoro"),
        )
        assert http.requests == [
            ("DELETE", path, None),
            (
                "PUT",
                path,
                {
                    "config": {
                        "type": "local",
                        "command": ["python3", "/srv/tool_server.py"],
                    }
                },
            ),
        ]

    def test_attaching_a_tool_server_never_registered_before_works(self) -> None:
        where = "location%5Bdirectory%5D=%2Fhome%2Ftester"
        path = f"{URL}/api/experimental/mcp/osiris?{where}"
        http = FakeHttpClient(replies={("PUT", path): None})
        engine(http).attach_tools(
            "osiris", ["python3", "/srv/tool_server.py"], Path("/home/tester")
        )
        assert http.requests[-1][0] == "PUT"

    def test_answering_a_request_the_engine_already_withdrew_is_not_an_error(
        self,
    ) -> None:
        """opencode withdraws a step's other requests when one is rejected."""
        engine(FakeHttpClient()).reply(SESSION, "per_2", allow=False, message="no")

    def test_a_tool_servers_requests_name_the_server_and_tool(self) -> None:
        """As opencode 2.0.32 does: ``tools.osiris.apply_theme`` in its code
        mode asks for ``osiris_apply_theme``."""
        assert engine(FakeHttpClient()).action("osiris", "apply_theme") == (
            "osiris_apply_theme"
        )

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


class TestHistory:
    def test_the_harnesss_sessions_are_marked_as_its_own(self) -> None:
        http = FakeHttpClient(
            replies={("POST", f"{URL}/api/session"): {"data": {"id": SESSION}}}
        )
        engine(http).start()
        _, _, body = http.requests[0]
        assert isinstance(body, dict)
        assert body["metadata"] == {"osiris": "harness"}

    def test_a_session_is_renamed(self) -> None:
        path = f"{URL}/api/session/{SESSION}"
        http = FakeHttpClient(replies={("PATCH", path): {"data": {}}})
        engine(http).rename(SESSION, "Make me a calm theme")
        assert http.requests == [("PATCH", path, {"title": "Make me a calm theme"})]

    def test_past_conversations_are_the_harnesss_sessions_newest_first(self) -> None:
        def session(sid: str, title: str, folder: str, updated: int, mine: bool):
            return {
                "id": sid,
                "title": title,
                "location": {"directory": folder},
                "time": {"created": updated - 10, "updated": updated},
                **({"metadata": {"osiris": "harness"}} if mine else {}),
            }

        http = FakeHttpClient(
            replies={
                ("GET", f"{URL}/api/session?limit=200"): {
                    "data": [
                        session("ses_a", "Calm theme", "/home/tester", 1000, True),
                        session("ses_tui", "refactor", "/home/tester/x", 3000, False),
                        session(
                            "ses_b",
                            "Pomodoro",
                            "/home/tester/Code/pomodoro",
                            2000,
                            True,
                        ),
                    ]
                }
            }
        )
        assert engine(http).conversations() == [
            Past("ses_b", "Pomodoro", Path("/home/tester/Code/pomodoro"), 2.0),
            Past("ses_a", "Calm theme", Path("/home/tester"), 1.0),
        ]

    def test_a_past_conversation_is_rebuilt_from_its_messages(self) -> None:
        model = {"id": "gpt-6.1-sol", "providerID": "openai"}
        http = FakeHttpClient(
            replies={
                (
                    "GET",
                    f"{URL}/api/session/{SESSION}/message?limit=200&order=asc",
                ): {
                    "data": [
                        {"id": "m1", "type": "user", "text": "make a timer"},
                        {
                            "id": "m2",
                            "type": "assistant",
                            "model": model,
                            "content": [{"type": "tool", "name": "read"}],
                        },
                        {"id": "m3", "text": "Instructions from: AGENTS.md"},
                        {
                            "id": "m4",
                            "type": "assistant",
                            "model": model,
                            "content": [{"type": "text", "text": "Made it."}],
                        },
                        {"id": "m5", "type": "idle"},
                        {"id": "m6", "type": "user", "text": "thanks"},
                    ]
                }
            }
        )
        assert engine(http).history(SESSION) == [
            PastTurn("make a timer", "Made it.", ModelRef("openai", "gpt-6.1-sol")),
            PastTurn("thanks", "", None),
        ]

    def test_sessions_from_before_the_harness_marked_its_own_are_adopted(
        self,
    ) -> None:
        old = {
            "id": "ses_old",
            "title": "Osiris Harness",
            "location": {"directory": "/home/tester"},
            "time": {"created": 1, "updated": 5000},
        }
        empty = {**old, "id": "ses_empty", "time": {"created": 1, "updated": 4000}}
        first = "&order=asc"
        http = FakeHttpClient(
            replies={
                ("GET", f"{URL}/api/session?limit=200"): {"data": [old, empty]},
                ("GET", f"{URL}/api/session/ses_old/message?limit=200{first}"): {
                    "data": [{"id": "m1", "type": "user", "text": "Which kernel?"}]
                },
                ("GET", f"{URL}/api/session/ses_empty/message?limit=200{first}"): {
                    "data": []
                },
                ("PATCH", f"{URL}/api/session/ses_old"): {"data": {}},
            }
        )
        assert engine(http).conversations() == [
            Past("ses_old", "Which kernel?", Path("/home/tester"), 5.0)
        ]
        assert (
            "PATCH",
            f"{URL}/api/session/ses_old",
            {"title": "Which kernel?", "metadata": {"osiris": "harness"}},
        ) in http.requests

    def test_a_long_conversation_is_read_page_by_page(self) -> None:
        def page(start: int, count: int) -> list[dict[str, object]]:
            return [
                {"id": f"m{i}", "type": "user", "text": f"question {i}"}
                for i in range(start, start + count)
            ]

        base = f"{URL}/api/session/{SESSION}/message"
        http = FakeHttpClient(
            replies={
                ("GET", f"{base}?limit=200&order=asc"): {
                    "data": page(0, 200),
                    "cursor": {"next": "two", "previous": None},
                },
                ("GET", f"{base}?limit=200&cursor=two"): {
                    "data": page(200, 3),
                    "cursor": {"next": "three", "previous": "one"},
                },
            }
        )
        turns = engine(http).history(SESSION)
        assert len(turns) == 203
        assert turns[-1].question == "question 202"

    def test_a_session_is_moved_into_a_folder(self) -> None:
        path = f"{URL}/api/session/{SESSION}/move"
        http = FakeHttpClient(replies={("POST", path): None})
        engine(http).move(SESSION, Path("/home/tester/Code/pomodoro"))
        assert http.requests == [
            ("POST", path, {"directory": "/home/tester/Code/pomodoro"})
        ]

    def test_a_conversation_is_as_recent_as_its_last_work_not_its_last_rename(
        self,
    ) -> None:
        renamed = {
            "id": "ses_a",
            "title": "Old work",
            "location": {"directory": "/home/tester"},
            "time": {"created": 1000, "updated": 9000, "idle": 2000},
            "metadata": {"osiris": "harness"},
        }
        recent = {**renamed, "id": "ses_b", "title": "Recent work"}
        recent["time"] = {"created": 3000, "updated": 4000, "idle": 4000}
        http = FakeHttpClient(
            replies={
                ("GET", f"{URL}/api/session?limit=200"): {"data": [renamed, recent]}
            }
        )
        assert [p.title for p in engine(http).conversations()] == [
            "Recent work",
            "Old work",
        ]

    def test_archiving_marks_a_session_and_hides_it_from_the_history(self) -> None:
        path = f"{URL}/api/session/{SESSION}"
        http = FakeHttpClient(replies={("PATCH", path): {"data": {}}})
        engine(http).archive(SESSION)
        assert http.requests == [
            ("PATCH", path, {"metadata": {"osiris": "harness", "archived": True}})
        ]
        archived = {
            "id": "ses_x",
            "title": "Old",
            "location": {"directory": "/home/tester"},
            "time": {"created": 1, "updated": 2},
            "metadata": {"osiris": "harness", "archived": True},
        }
        http = FakeHttpClient(
            replies={("GET", f"{URL}/api/session?limit=200"): {"data": [archived]}}
        )
        assert engine(http).conversations() == []

    def test_deleting_a_session(self) -> None:
        path = f"{URL}/api/session/{SESSION}"
        http = FakeHttpClient(replies={("DELETE", path): None})
        engine(http).delete(SESSION)
        assert http.requests == [("DELETE", path, None)]

    def test_a_session_says_which_folder_it_runs_in(self) -> None:
        path = f"{URL}/api/session/{SESSION}"
        http = FakeHttpClient(
            replies={
                ("GET", path): {
                    "data": {"location": {"directory": "/home/tester/Code/pomodoro"}}
                }
            }
        )
        assert engine(http).where(SESSION) == Path("/home/tester/Code/pomodoro")
