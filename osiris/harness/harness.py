"""The Harness: its Conversations, logged, on whichever Engine it is given."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from osiris.harness.admin import Request
from osiris.harness.engine import (
    Answered,
    Engine,
    Event,
    Failed,
    Finished,
    ModelRef,
    Past,
    PastTurn,
    Reply,
    Revert,
    Stopped,
    ToolCalled,
    ToolRequested,
)
from osiris.harness.log import HarnessLog
from osiris.harness.titles import title_of
from osiris.platform import HttpError

#: Passed to the model with every action the person denies.
REFUSED = (
    "The person said no to this. Do not try it another way without asking "
    "them; tell them what you wanted to do and why, and ask how Osiris should "
    "go on."
)


@dataclass(frozen=True)
class Allowed:
    session: str
    action: str
    resources: tuple[str, ...]
    call: str = ""


@dataclass(frozen=True)
class Refused:
    session: str
    action: str
    resources: tuple[str, ...]
    call: str = ""
    reason: str = ""


#: The Engine's tool for running a command: opencode 2.0 names it shell, and
#: 1.x named it bash.
COMMAND_ACTIONS = frozenset({"shell", "bash"})
_SUDO = re.compile(r"\bsudo\b")


@dataclass(frozen=True)
class Asking:
    """An action the Engine's rules ask about, held until the person answers its
    card."""

    session: str
    request: str
    action: str
    resources: tuple[str, ...]
    call: str = ""
    #: Patterns that would allow it again without asking, as the Engine suggests.
    patterns: tuple[str, ...] = ()


class Answer(Enum):
    """The person's answer to a card."""

    ONCE = "once"
    #: Left to the Engine, which keeps allowing it in the Project.
    ALWAYS = "always"
    DENY = "deny"


#: The rule a step the person denied shows.
DENIED = "You said no"


#: What the Harness decided about a ``ToolRequested``, passed on in its place.
Decision = Allowed | Refused | Asking


class Harness:
    def __init__(
        self,
        engine: Engine,
        log: HarnessLog,
        model: ModelRef | None = None,
        *,
        directory: Path,
        tools: tuple[str, list[str]] | None = None,
        auto_mode: Callable[[], bool] = lambda: False,
    ) -> None:
        """``directory`` is where a Conversation with no Project runs."""
        self._engine = engine
        self._log = log
        self._model = model
        self._directory = directory
        #: Where a Conversation with no Project runs.
        self._home = directory
        #: The tool server, which the Engine keeps per folder.
        self._tools = tools
        self._tools_in: set[Path] = set()
        self._session: str | None = None
        #: Sessions working on a question, served whichever one is on screen,
        #: and the folder each runs in.
        self._running: dict[str, Path] = {}
        self._auto_mode = auto_mode
        #: Each session's latest command: when it was noted, counted across
        #: sessions, and whether it runs sudo.
        self._last_command: dict[str, tuple[int, bool]] = {}
        self._commands_noted = 0
        #: Sessions cut in on: the stop that follows resumes at once.
        self._cutting_in: set[str] = set()
        #: Actions held for the person, by session and request.
        self._waiting: dict[tuple[str, str], Asking] = {}

    def ask(self, text: str) -> str:
        """Send a question; while the session works it waits and steers the
        model at its next step. Answers where it waits."""
        directory, session = self._directory, self._session
        if session is None:
            self._ready(directory)
            session = self._session = self._engine.start(self._model, directory)
            self._engine.rename(session, title_of(text))
        self._running[session] = directory
        self._log.write("sent", session=session, text=text)
        return self._engine.send(session, text)

    def send_now(self, text: str) -> str:
        """Send while the session works, stopping its step at once so the
        model takes this next. Answers where it waits until then."""
        session = self._session
        working = session is not None and session in self._running
        message = self.ask(text)
        if session is not None and working:
            self._cutting_in.add(session)
            self._engine.cut_in(session)
            self._log.write("cut-in", session=session)
        return message

    def withdraw(self, message: str) -> None:
        """Take back a message still waiting in the session on screen."""
        if self._session is None:
            return
        self._engine.withdraw(self._session, message)
        self._log.write("withdrawn", session=self._session, message=message)

    @property
    def session(self) -> str | None:
        return self._session

    @property
    def running(self) -> frozenset[str]:
        return frozenset(self._running)

    @property
    def directory(self) -> Path:
        """The folder the session runs in: its Project, or home for none."""
        return self._directory

    def conversations(self) -> list[Past]:
        return self._engine.conversations()

    def _ready(self, directory: Path) -> None:
        if self._tools is not None and directory not in self._tools_in:
            self._engine.attach_tools(*self._tools, directory)
            self._tools_in.add(directory)

    def restart_tools(self) -> None:
        """Attach the tool server again where it runs now; other folders get a
        fresh one when next used."""
        self._tools_in.clear()
        self._ready(self._directory)

    def resume(self, session: str) -> list[PastTurn]:
        """Continue a past Conversation, in its folder; returns what was said."""
        directory = self._engine.where(session)
        self._session = session
        self._directory = directory
        self._ready(directory)
        return self._engine.history(session)

    def new_conversation(self, folder: Path | None = None) -> None:
        """The next question opens a new session, in ``folder``'s Project or in
        none; the old one is left as it is."""
        self._session = None
        self._directory = folder or self._home

    def archive(self, session: str) -> None:
        self._engine.archive(session)

    def delete(self, session: str) -> None:
        """Erase a Conversation from the Engine and the Harness log; what it did
        stays done (CONTEXT.md)."""
        self._engine.delete(session)
        self._log.forget(session)
        self._running.pop(session, None)
        if session == self._session:
            self.new_conversation()

    def worked_on(self, session: str, folder: Path) -> None:
        """A Conversation with no Project takes the Project of the first Program
        it works on; one already in a Project stays there (CONTEXT.md). Only the
        current one is moved here; the history's pass over misplaced
        Conversations moves the rest."""
        if session != self._session or self._directory != self._home:
            return
        self._engine.move(self._session, folder)
        self._directory = folder
        if self._session in self._running:
            self._running[self._session] = folder
        self._ready(folder)

    def move(self, session: str, folder: Path) -> None:
        self._engine.move(session, folder)

    def go_back(self, session: str, message: str, questions: int = 1) -> Revert | None:
        """Go back to before ``message``: its files and the Conversation, which
        drops ``questions``, that one and those after it. None while the
        session is still answering, which the Engine refuses."""
        if session in self._running:
            return None
        try:
            revert = self._engine.revert(session, message)
        except HttpError as error:
            if error.status == 409:
                return None
            raise
        if not revert.restorable:
            self._engine.cancel_revert(session)
            self._log.write("could-not-go-back", session=session, message=message)
            return revert
        self._engine.keep_revert(session)
        self._log.write(
            "went-back",
            session=session,
            message=message,
            questions=questions,
            files=[change.path for change in revert.files],
        )
        return revert

    def use_model(self, model: ModelRef) -> None:
        """Answer with this model from now on, in this conversation too."""
        self._model = model
        if self._session is not None:
            self._engine.switch_model(self._session, model)

    def stop(self) -> None:
        if self._session is not None:
            self._engine.stop(self._session)

    def running_sudo(self) -> str | None:
        """The session an admin request is for: of those running, the one
        whose latest command runs sudo, the latest to run it first."""
        # Asked on the main loop while handle() runs on the Engine's thread:
        # copied first, so neither changes under the loop.
        commands, running = dict(self._last_command), set(self._running)
        asking = [
            (allowed, session)
            for session, (allowed, sudo) in commands.items()
            if sudo and session in running
        ]
        return max(asking)[1] if asking else None

    def admin_answered(self, session: str, request: Request, *, approved: bool) -> None:
        self._log.write(
            "admin",
            session=session,
            command=list(request.command),
            user=request.user,
            approved=approved,
        )

    def _noted_command(self, session: str, resources: tuple[str, ...]) -> None:
        self._commands_noted += 1
        self._last_command[session] = (
            self._commands_noted,
            any(_SUDO.search(resource) for resource in resources),
        )

    def _reply(self, session: str, request: str, answer: Reply, message: str) -> None:
        """Answer a request; one the Engine cannot take is logged, so a single
        bad reply never ends the conversation."""
        try:
            self._engine.reply(session, request, answer, message)
        except HttpError as error:
            self._log.write(
                "reply-failed", session=session, request=request, error=str(error)
            )

    def answer(
        self, session: str, request: str, answer: Answer, reply: str = ""
    ) -> Decision | None:
        """Answer a card; a typed reply refuses the action and is passed to the
        model in its place. None when nothing is waiting under it."""
        asking = self._waiting.pop((session, request), None)
        if asking is None:
            return None
        allow = answer is not Answer.DENY and not reply
        if not allow:
            self._reply(session, request, Reply.REJECT, reply or REFUSED)
        else:
            always = answer is Answer.ALWAYS
            self._reply(session, request, Reply.ALWAYS if always else Reply.ONCE, "")
        self._log.write(
            "replied",
            session=session,
            action=asking.action,
            resources=list(asking.resources),
            answer=answer.value,
            **({"reply": reply} if reply else {}),
        )
        if allow:
            return Allowed(session, asking.action, asking.resources, asking.call)
        reason = f"You replied: {reply}" if reply else DENIED
        return Refused(session, asking.action, asking.resources, asking.call, reason)

    def _called(self, event: ToolCalled) -> None:
        """Log a tool call; a command is noted even if the Engine's rules ran
        it without asking, so its sudo finds its session."""
        self._log.write(
            "tool",
            session=event.session,
            call=event.call,
            input=event.input,
            executed=event.executed,
        )
        if isinstance(command := event.input.get("command"), str):
            self._noted_command(event.session, (command,))

    def _ended(self, event: Event) -> None:
        """A session that ends is no longer running, unless it was cut in on:
        the Engine goes on with the message at once."""
        if not isinstance(event, Finished | Stopped | Failed):
            return
        for held in [key for key in self._waiting if key[0] == event.session]:
            del self._waiting[held]
        cut_in = event.session in self._cutting_in
        self._cutting_in.discard(event.session)
        if not (cut_in and isinstance(event, Stopped)):
            self._running.pop(event.session, None)

    def handle(self, event: Event) -> Event | Decision | None:
        """Log what the Engine reports and apply policy; the event is passed on.

        None for another program's session: the Engine's stream carries them all.
        """
        if event.session != self._session and event.session not in self._running:
            return None
        self._ended(event)
        match event:
            case Answered(session, model, tokens, cost):
                self._log.write(
                    "answered",
                    session=session,
                    provider=model.provider,
                    model=model.model,
                    tokens=asdict(tokens),
                    cost=cost,
                )
            case ToolCalled():
                self._called(event)
            case ToolRequested(session, request, action, resources, call) if (
                self._auto_mode()
            ):
                if action in COMMAND_ACTIONS:
                    self._noted_command(session, resources)
                self._reply(session, request, Reply.ONCE, "")
                self._log.write(
                    "allowed",
                    session=session,
                    action=action,
                    resources=list(resources),
                    by="auto mode",
                )
                return Allowed(session, action, resources, call)
            case ToolRequested(session, request, action, resources, call, patterns):
                asking = Asking(session, request, action, resources, call, patterns)
                self._waiting[(session, request)] = asking
                self._log.write(
                    "asked",
                    session=session,
                    action=action,
                    resources=list(resources),
                )
                return asking
            case Failed(session, message):
                self._log.write("failed", session=session, message=message)
            case Stopped(session):
                self._log.write("stopped", session=session)
        return event
