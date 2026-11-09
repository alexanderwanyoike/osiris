"""The first Engine: opencode 2.0's per-user service, over its HTTP API.

How the service is reached, and what it reports, is recorded in the note on
ADR 0015.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from osiris.harness.accounts import Method, ModelInfo, Provider, SignIn, SignInState
from osiris.harness.connectors import State
from osiris.harness.context import CHARACTERS, KINDS, ContextUse
from osiris.harness.engine import (
    Answered,
    Delivered,
    Event,
    Failed,
    FileChange,
    Finished,
    ModelRef,
    Past,
    PastTurn,
    Reply,
    Revert,
    Stopped,
    Text,
    Tokens,
    ToolCalled,
    ToolFinished,
    ToolRequested,
)
from osiris.harness.markdown import next_step
from osiris.harness.picker import Entry, Reference
from osiris.harness.saved_rules import SavedRule
from osiris.harness.skill_rules import SkillInfo
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


@dataclass(frozen=True)
class Service:
    url: str
    password: str
    #: The service's process, which the agent's commands descend from.
    pid: int | None = None

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
    return Service(state["url"], state["password"], state.get("pid"))


#: Characters a URL query carries as they are; everything else is escaped.
_UNRESERVED = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)


def _sized(message: dict[str, Any]) -> list[tuple[str, str]]:
    """A context message's parts, each with the kind it counts as."""
    if message["type"] == "system":
        return [("instructions", message.get("text", ""))]
    if message["type"] == "user":
        return [("questions", message.get("text", ""))]
    if message["type"] != "assistant":
        return []
    return [
        ("tools", json.dumps(part))
        if part["type"] == "tool"
        else ("answers", part.get("text", ""))
        for part in message.get("content", [])
    ]


def _in_use(tokens: dict[str, Any]) -> int:
    cache = tokens.get("cache", {})
    return int(
        tokens["input"]
        + cache.get("read", 0)
        + cache.get("write", 0)
        + tokens["output"]
    )


def _in(directory: Path) -> str:
    """The query naming the folder a request is about."""
    return f"?location%5Bdirectory%5D={_quoted(str(directory))}"


def _quoted(text: str) -> str:
    return "".join(
        chr(byte) if chr(byte) in _UNRESERVED else f"%{byte:02X}"
        for byte in text.encode()
    )


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
            "metadata": MINE,
        }
        if directory is not None:
            body["location"] = {"directory": str(directory)}
        if model is not None:
            body["model"] = {"providerID": model.provider, "id": model.model}
        session: str = self._post("/api/session", body)["data"]["id"]
        return session

    def send(
        self, session: str, text: str, references: tuple[Reference, ...] = ()
    ) -> str:
        """opencode puts the message in the session's inbox, delivered at the
        model's next step if it is busy, and answers with the item."""
        body: dict[str, Any] = {"text": text, **_attachments(text, references)}
        item = self._post(f"/api/session/{session}/prompt", body)
        return str((item or {}).get("data", {}).get("id", ""))

    def withdraw(self, session: str, message: str) -> None:
        self._http.request(
            "DELETE",
            self._service.url + f"/api/session/{session}/inbox/{message}",
            headers=self._service.headers(),
        )

    def reply(self, session: str, request: str, answer: Reply, message: str) -> None:
        try:
            self._post(
                f"/api/session/{session}/permission/{request}/reply",
                {"decision": answer.value, "message": message},
            )
        except HttpError as error:
            # Rejecting one of a step's requests withdraws the others, so a reply
            # can arrive after its request is gone.
            if error.status != 404:
                raise

    def revert(self, session: str, message: str) -> Revert:
        staged = self._post(
            f"/api/session/{session}/revert/stage",
            {"messageID": message, "files": True},
        )["data"]
        return Revert(
            _file_changes(staged.get("files", [])), restorable="snapshot" in staged
        )

    def keep_revert(self, session: str) -> None:
        self._post(f"/api/session/{session}/revert/commit")

    def cancel_revert(self, session: str) -> None:
        self._http.request(
            "DELETE",
            self._service.url + f"/api/session/{session}/revert",
            headers=self._service.headers(),
        )

    def stop(self, session: str) -> None:
        self._post(f"/api/session/{session}/interrupt")

    def cut_in(self, session: str) -> None:
        self._post(f"/api/session/{session}/interrupt?resume=true")

    def switch_model(self, session: str, model: ModelRef) -> None:
        self._post(
            f"/api/session/{session}/model",
            {"model": {"providerID": model.provider, "id": model.model}},
        )

    def attach_tools(self, name: str, command: list[str], directory: Path) -> None:
        url = f"{self._service.url}/api/experimental/mcp/{name}{_in(directory)}"
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

    def context_use(self, session: str) -> ContextUse:
        reply: Any = self._http.request(
            "GET",
            f"{self._service.url}/api/session/{session}/context",
            headers=self._service.headers(),
        )
        characters = dict.fromkeys(KINDS, 0)
        used = 0
        for message in reply["data"]:
            for kind, text in _sized(message):
                characters[kind] += len(text)
            if message["type"] == "assistant" and "tokens" in message:
                used = _in_use(message["tokens"])
        return ContextUse(
            {kind: count // CHARACTERS for kind, count in characters.items()}, used
        )

    def connector_states(self, directory: Path) -> dict[str, State]:
        reply: Any = self._http.request(
            "GET",
            f"{self._service.url}/api/mcp{_in(directory)}",
            headers=self._service.headers(),
        )
        return {
            server["name"]: State(
                server["status"]["status"],
                server["status"].get("error", ""),
                server.get("integrationID", ""),
            )
            for server in reply["data"]
        }

    def resources(self, directory: Path) -> list[Entry]:
        reply: Any = self._http.request(
            "GET",
            f"{self._service.url}/api/mcp/resource{_in(directory)}",
            headers=self._service.headers(),
        )
        return [
            Entry(
                "resource",
                found["uri"],
                found["name"],
                ": ".join(filter(None, (found["server"], found.get("description")))),
            )
            for found in reply["data"]["resources"]
        ]

    def skill_details(self, directory: Path) -> list[SkillInfo]:
        reply: Any = self._http.request(
            "GET",
            f"{self._service.url}/api/skill{_in(directory)}",
            headers=self._service.headers(),
        )
        return [
            SkillInfo(
                found["id"],
                found["name"],
                found.get("description", ""),
                found["path"],
                found["content"],
            )
            for found in reply["data"]
        ]

    def saved_rules(self) -> list[SavedRule]:
        reply: Any = self._http.request(
            "GET",
            f"{self._service.url}/api/permission/saved",
            headers=self._service.headers(),
        )
        projects: Any = self._http.request(
            "GET", f"{self._service.url}/api/project", headers=self._service.headers()
        )
        where = {project["id"]: Path(project["canonical"]) for project in projects}
        return [
            SavedRule(
                rule["id"],
                rule["action"],
                rule["resource"],
                where.get(rule["projectID"]),
            )
            for rule in reply["data"]
        ]

    def remove_saved_rule(self, rule: str) -> None:
        self._http.request(
            "DELETE",
            f"{self._service.url}/api/permission/saved/{rule}",
            headers=self._service.headers(),
        )

    def waiting(self, session: str) -> list[ToolRequested]:
        """What the session still waits to be allowed, as it was asked."""
        reply: Any = self._http.request(
            "GET",
            f"{self._service.url}/api/session/{session}/permission",
            headers=self._service.headers(),
        )
        return [_requested(session, request) for request in reply["data"]]

    def skills(self, directory: Path) -> list[Entry]:
        reply: Any = self._http.request(
            "GET",
            f"{self._service.url}/api/skill{_in(directory)}",
            headers=self._service.headers(),
        )
        return [
            Entry("skill", skill["id"], skill["id"], skill.get("description", ""))
            for skill in reply["data"]
        ]

    def rename(self, session: str, title: str) -> None:
        self._http.request(
            "PATCH",
            f"{self._service.url}/api/session/{session}",
            body={"title": title},
            headers=self._service.headers(),
        )

    def archive(self, session: str) -> None:
        self._http.request(
            "PATCH",
            f"{self._service.url}/api/session/{session}",
            body={"metadata": {**MINE, "archived": True}},
            headers=self._service.headers(),
        )

    def delete(self, session: str) -> None:
        self._http.request(
            "DELETE",
            f"{self._service.url}/api/session/{session}",
            headers=self._service.headers(),
        )

    def where(self, session: str) -> Path:
        return Path(
            self._get(f"/api/session/{session}")["data"]["location"]["directory"]
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
            metadata = session.get("metadata") or {}
            if metadata.get("archived") or session.get("parentID"):
                continue
            if metadata.get("osiris") != MINE["osiris"]:
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
                turns.append(
                    PastTurn(message.get("text", ""), "", None, message.get("id", ""))
                )
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
                        next_step(last.answer) + said,
                        ModelRef(model["providerID"], model["id"]) if model else None,
                        last.message,
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


def _uri(entry: Entry) -> str:
    """A Project's file by its path; a server's resource by its own URI."""
    return f"file://{entry.key}" if entry.kind == "file" else entry.key


def _attachments(
    text: str, references: tuple[Reference, ...]
) -> dict[str, list[dict[str, Any]]]:
    """Picked files, resources and skills, each with where the text mentions
    it; a picked server is only named in the text."""
    found: dict[str, list[dict[str, Any]]] = {}
    for ref in references:
        mention = {
            "start": ref.start,
            "end": ref.end,
            "text": text[ref.start : ref.end],
        }
        if ref.entry.kind in ("file", "resource"):
            found.setdefault("files", []).append(
                {
                    "uri": _uri(ref.entry),
                    "name": ref.entry.label,
                    "mention": mention,
                }
            )
        elif ref.entry.kind == "skill":
            found.setdefault("skills", []).append(
                {"id": ref.entry.key, "mention": mention}
            )
    return found


def _file_changes(files: list[dict[str, Any]]) -> tuple[FileChange, ...]:
    return tuple(
        FileChange(f["file"], f["status"], f["additions"], f["deletions"], f["patch"])
        for f in files
    )


#: How a subagent's reply comes back: its child session's answer in a tag.
_SUBAGENT = re.compile(r"\A<subagent [^>]*>\n?(.*?)\n?</subagent>\Z", re.DOTALL)


def _unwrapped(output: str) -> str:
    found = _SUBAGENT.match(output)
    return found.group(1) if found else output


def _finished(session: str, data: dict[str, Any]) -> ToolFinished:
    """The text a tool gave back; a file it gave is left out."""
    output = _unwrapped(
        "".join(
            part.get("text", "")
            for part in data.get("content") or []
            if part.get("type") == "text"
        )
    )
    exit_status = (data.get("metadata") or {}).get("exit")
    return ToolFinished(
        session,
        data["id"],
        output,
        error=(data.get("error") or {}).get("message", ""),
        exit=exit_status if isinstance(exit_status, int) else None,
    )


def _tool(
    kind: str, session: str, data: dict[str, Any], name: str = ""
) -> ToolCalled | ToolRequested | ToolFinished:
    """A tool call, the permission it asks for, or how it ended."""
    if kind == "session.tool.called":
        return ToolCalled(
            session, data["id"], data.get("input", {}), data["executed"], name
        )
    if kind == "permission.asked":
        return _requested(session, data)
    return _finished(session, data)


def _requested(session: str, data: dict[str, Any]) -> ToolRequested:
    return ToolRequested(
        session,
        data["id"],
        data["action"],
        tuple(data["resources"]),
        (data.get("source") or {}).get("id", ""),
        tuple(data.get("save") or ()),
    )


class _Reader:
    """Turns opencode's events into the Engine's.

    A finished step reports its tokens but not its model; the model was named
    when the step started, so it is remembered until then.
    """

    def __init__(self) -> None:
        self._models: dict[str, ModelRef] = {}
        #: Each call's tool, named before the call is reported.
        self._names: dict[str, str] = {}

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
            case (
                "session.tool.called"
                | "permission.asked"
                | "session.tool.success"
                | "session.tool.failed"
            ):
                return _tool(kind, session, data, self._names.pop(data.get("id"), ""))
            case "session.tool.input.started":
                self._names[data["id"]] = data.get("name", "")
            case "session.inbox.delivered":
                return Delivered(session, data["inboxID"])
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
        # An MCP server's sign-in is listed too; it belongs to its connector.
        return [
            _provider(entry)
            for entry in reply["data"]
            if (entry.get("metadata") or {}).get("source") != "mcp"
        ]

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

    def connector_sign_in(self, integration: str) -> SignIn:
        """Start signing in to an MCP server, by the sign-in page it offers."""
        reply: Any = self._http.request(
            "GET",
            f"{self._service.url}/api/integration/{integration}",
            headers=self._service.headers(),
        )
        method = next(m for m in reply["data"]["methods"] if m["type"] == "oauth")
        return self.start_sign_in(integration, method["id"])

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
            ModelInfo(
                ModelRef(entry["providerID"], entry["id"]),
                entry["name"],
                (entry.get("limit") or {}).get("context", 0),
                entry.get("family", ""),
            )
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
