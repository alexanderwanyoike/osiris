"""The first Engine: opencode 2.0's per-user service, over its HTTP API.

How the service is reached, and what it reports, is recorded in the note on
ADR 0015.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from osiris.harness.accounts import Method, ModelInfo, Provider, SignIn, SignInState
from osiris.harness.engine import (
    Answered,
    Event,
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
from osiris.harness.titles import title_of
from osiris.platform import CommandRunner, FileSystem, HttpClient, HttpError, Identity

#: Where the service records its URL and password, relative to the home.
SERVICE_FILE = ".local/state/opencode/service.json"

#: Marks a session as the Harness's, so its history leaves out the sessions
#: opencode's own terminal application opens on the same service.
MINE = {"osiris": "harness"}
#: How many sessions and messages a history reads; more is older than anyone
#: scrolls to.
HISTORY_LIMIT = 200
#: What the Harness called every session before it marked and named them.
UNMARKED_TITLE = "Osiris Harness"
#: opencode serves at most this many messages a page.
MESSAGE_LIMIT = 200

#: Every action stops at a tool request, so the Harness's policy decides.
#: Denying instead strips the tools from the request, which opencode's free
#: tier refuses outright.
ASK_EVERYTHING = [{"action": "*", "resource": "*", "effect": "ask"}]


@dataclass(frozen=True)
class Service:
    url: str
    password: str

    def headers(self) -> dict[str, str]:
        token = base64.b64encode(f"opencode:{self.password}".encode()).decode()
        return {"Authorization": f"Basic {token}"}


def locate(files: FileSystem, identity: Identity, runner: CommandRunner) -> Service:
    """The running service, started first if it is not.

    Starting is idempotent, and it rewrites the state file when an earlier
    service died, so it runs every time rather than trusting a file that may
    name a dead process.
    """
    runner.run("opencode", "service", "start", quiet=True)
    state = json.loads(files.read(identity.home / SERVICE_FILE))
    return Service(state["url"], state["password"])


class OpencodeEngine:
    def __init__(self, http: HttpClient, service: Service) -> None:
        self._http = http
        self._service = service

    def _post(self, path: str, body: object | None = None) -> Any:
        return self._http.request(
            "POST",
            self._service.url + path,
            body=body,
            headers=self._service.headers(),
        )

    def start(
        self, model: ModelRef | None = None, directory: Path | None = None
    ) -> str:
        body: dict[str, object] = {
            "title": "Osiris Harness",
            "permissions": ASK_EVERYTHING,
            "metadata": MINE,
        }
        if directory is not None:
            body["location"] = {"directory": str(directory)}
        if model is not None:
            body["model"] = {"providerID": model.provider, "id": model.model}
        session: str = self._post("/api/session", body)["data"]["id"]
        return session

    def send(self, session: str, text: str) -> None:
        self._post(f"/api/session/{session}/prompt", {"text": text})

    def reply(self, session: str, request: str, *, allow: bool, message: str) -> None:
        self._post(
            f"/api/session/{session}/permission/{request}/reply",
            {"decision": "once" if allow else "reject", "message": message},
        )

    def stop(self, session: str) -> None:
        self._post(f"/api/session/{session}/interrupt")

    def switch_model(self, session: str, model: ModelRef) -> None:
        self._post(
            f"/api/session/{session}/model",
            {"model": {"providerID": model.provider, "id": model.model}},
        )

    def attach_tools(self, name: str, command: list[str]) -> None:
        url = f"{self._service.url}/api/experimental/mcp/{name}"
        # opencode keeps a running server whose registration is unchanged, which
        # would keep serving the code from before an update.
        try:
            self._http.request("DELETE", url, headers=self._service.headers())
        except HttpError as error:
            if error.status != 404:
                raise
        self._http.request(
            "PUT",
            url,
            body={"config": {"type": "local", "command": command}},
            headers=self._service.headers(),
        )

    def rename(self, session: str, title: str) -> None:
        self._http.request(
            "PATCH",
            f"{self._service.url}/api/session/{session}",
            body={"title": title},
            headers=self._service.headers(),
        )

    def move(self, session: str, directory: Path) -> None:
        self._post(f"/api/session/{session}/move", {"directory": str(directory)})

    def _get(self, path: str) -> Any:
        return self._http.request(
            "GET", self._service.url + path, headers=self._service.headers()
        )

    def conversations(self) -> list[Past]:
        sessions = self._get(f"/api/session?limit={HISTORY_LIMIT}")["data"]
        found = []
        for session in sessions:
            if session.get("metadata") != MINE:
                if session.get("title") != UNMARKED_TITLE:
                    continue
                adopted = self._adopt(session["id"])
                if adopted is None:
                    continue
                session = {**session, "title": adopted}
            found.append(
                Past(
                    session["id"],
                    session.get("title", ""),
                    Path(session["location"]["directory"]),
                    # Renaming and moving touch "updated"; "idle" is the last work.
                    session["time"].get("idle", session["time"]["updated"]) / 1000,
                )
            )
        return sorted(found, key=lambda past: past.updated, reverse=True)

    def _adopt(self, session: str) -> str | None:
        """Name and mark one of the Harness's sessions from before it marked
        its own; None for one in which nothing was asked."""
        turns = self.history(session)
        if not turns:
            return None
        title = title_of(turns[0].question)
        self._http.request(
            "PATCH",
            f"{self._service.url}/api/session/{session}",
            body={"title": title, "metadata": MINE},
            headers=self._service.headers(),
        )
        return title

    def _messages(self, session: str) -> list[dict[str, Any]]:
        """Every message of a session, oldest first, a page at a time; a cursor
        carries its order, so only the first page names it."""
        base = f"/api/session/{session}/message?limit={MESSAGE_LIMIT}"
        page = self._get(f"{base}&order=asc")
        messages = list(page["data"])
        while len(page["data"]) == MESSAGE_LIMIT and (page.get("cursor") or {}).get(
            "next"
        ):
            page = self._get(f"{base}&cursor={page['cursor']['next']}")
            messages.extend(page["data"])
        return messages

    def history(self, session: str) -> list[PastTurn]:
        turns: list[PastTurn] = []
        for message in self._messages(session):
            if message.get("type") == "user":
                turns.append(PastTurn(message.get("text", ""), "", None))
            elif message.get("type") == "assistant" and turns:
                said = "".join(
                    part.get("text", "")
                    for part in message.get("content", [])
                    if part.get("type") == "text"
                )
                if said:
                    model = message.get("model") or {}
                    last = turns[-1]
                    turns[-1] = PastTurn(
                        last.question,
                        last.answer + said,
                        ModelRef(model["providerID"], model["id"]) if model else None,
                    )
        return turns

    def action(self, server: str, tool: str) -> str:
        return f"{server}_{tool}"

    def events(self) -> Iterator[Event]:
        reader = _Reader()
        lines = self._http.lines(
            self._service.url + "/api/event", headers=self._service.headers()
        )
        for line in lines:
            if not line.startswith("data:"):
                continue
            event = reader.read(json.loads(line.removeprefix("data:")))
            if event is not None:
                yield event


class _Reader:
    """Turns opencode's events into the Engine's.

    A finished step reports its tokens but not its model; the model was named
    when the step started, so it is remembered until then.
    """

    def __init__(self) -> None:
        self._models: dict[str, ModelRef] = {}

    def read(self, event: dict[str, Any]) -> Event | None:
        kind, data = event.get("type"), event.get("data", {})
        session = data.get("sessionID", "")
        match kind:
            case "session.step.started":
                model = data["model"]
                self._models[data["assistantMessageID"]] = ModelRef(
                    model["providerID"], model["id"]
                )
            case "session.text.delta":
                return Text(session, data["delta"])
            case "session.tool.called":
                return ToolCalled(
                    session, data["id"], data.get("input", {}), data["executed"]
                )
            case "permission.asked":
                return ToolRequested(
                    session, data["id"], data["action"], tuple(data["resources"])
                )
            case "session.step.ended":
                return self._answered(session, data)
            case "session.execution.succeeded":
                return Finished(session)
            case "session.execution.interrupted":
                return Stopped(session)
            case "session.execution.failed":
                return Failed(session, data.get("error", {}).get("message", ""))
        return None

    def _answered(self, session: str, data: dict[str, Any]) -> Answered | None:
        model = self._models.pop(data["assistantMessageID"], None)
        if model is None:
            return None
        tokens = data["tokens"]
        return Answered(
            session,
            model,
            Tokens(
                input=tokens["input"],
                output=tokens["output"],
                reasoning=tokens["reasoning"],
                cache_read=tokens["cache"]["read"],
                cache_write=tokens["cache"]["write"],
            ),
            cost=float(data.get("cost", 0)),
        )


class OpencodeAccounts:
    def __init__(self, http: HttpClient, service: Service) -> None:
        self._http = http
        self._service = service

    def providers(self) -> list[Provider]:
        reply: Any = self._http.request(
            "GET",
            self._service.url + "/api/integration",
            headers=self._service.headers(),
        )
        return [_provider(entry) for entry in reply["data"]]

    def connect_key(self, provider: str, key: str) -> None:
        self._http.request(
            "POST",
            f"{self._service.url}/api/integration/{provider}/connect/key",
            body={"key": key},
            headers=self._service.headers(),
        )

    def start_sign_in(self, provider: str, method: str) -> SignIn:
        reply: Any = self._http.request(
            "POST",
            f"{self._service.url}/api/integration/{provider}/connect/oauth",
            body={"methodID": method},
            headers=self._service.headers(),
        )
        attempt = reply["data"]
        return SignIn(
            provider=provider,
            attempt=attempt["attemptID"],
            url=attempt["url"],
            instructions=attempt["instructions"],
            needs_code=attempt["mode"] == "code",
        )

    def sign_in_state(self, provider: str, attempt: str) -> SignInState:
        reply: Any = self._http.request(
            "GET",
            f"{self._service.url}/api/integration/{provider}/connect/oauth/{attempt}",
            headers=self._service.headers(),
        )
        data = reply["data"]
        return SignInState(data["status"], data.get("message", ""))

    def finish_sign_in(self, provider: str, attempt: str, code: str | None) -> None:
        self._http.request(
            "POST",
            f"{self._service.url}/api/integration/{provider}/connect/oauth/{attempt}/complete",
            body={"code": code},
            headers=self._service.headers(),
        )

    def models(self) -> list[ModelInfo]:
        reply: Any = self._http.request(
            "GET", self._service.url + "/api/model", headers=self._service.headers()
        )
        return [
            ModelInfo(ModelRef(entry["providerID"], entry["id"]), entry["name"])
            for entry in reply["data"]
        ]


def _provider(entry: dict[str, Any]) -> Provider:
    # An environment variable is not something a person can set from a
    # sign-in page, so only keys and OAuth are offered; methods opencode
    # itself marks as legacy are left out.
    methods = tuple(
        Method(
            id=method.get("id"),
            kind=method["type"],
            label=method.get("label", "API key"),
        )
        for method in entry["methods"]
        if method["type"] in ("key", "oauth")
        and not method.get("label", "").endswith("(legacy)")
    )
    return Provider(
        id=entry["id"],
        name=entry["name"],
        methods=methods,
        connected=any(_works(connection) for connection in entry["connections"]),
    )


def _works(connection: dict[str, Any]) -> bool:
    status: str | None = connection.get("status", {}).get("status")
    return status != "needs_auth"
