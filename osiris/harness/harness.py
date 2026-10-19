"""The Harness: one conversation, logged, on whichever Engine it is given."""

from __future__ import annotations

import posixpath
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from osiris.harness.engine import (
    Answered,
    Engine,
    Event,
    Failed,
    Finished,
    ModelRef,
    Past,
    PastTurn,
    Stopped,
    ToolCalled,
    ToolRequested,
)
from osiris.harness.log import HarnessLog
from osiris.harness.tiers import Tier
from osiris.harness.titles import title_of
from osiris.platform import HttpError

#: Passed to the model with every rejected tool, so it finds another way.
REFUSED = (
    "Osiris cannot do that: it cannot run commands or read files, "
    "and changes this machine only through the Osiris tools. Answer in words, "
    "or with those tools."
)


@dataclass(frozen=True)
class Allowed:
    session: str
    action: str
    tier: Tier
    resources: tuple[str, ...]


@dataclass(frozen=True)
class Refused:
    session: str
    action: str
    resources: tuple[str, ...]


#: The Engine's own file tools, allowed only on files inside a Program: reading
#: is a look, and editing is undoable because a Program's changes are commits.
FILE_TIERS = {
    "read": Tier.LOOK,
    "external_directory": Tier.LOOK,
    "edit": Tier.UNDOABLE,
}

#: What the Harness decided about a ``ToolRequested``, passed on in its place.
Decision = Allowed | Refused


class Harness:
    def __init__(
        self,
        engine: Engine,
        log: HarnessLog,
        model: ModelRef | None = None,
        *,
        tiers: Mapping[str, Tier],
        directory: Path,
        may_touch: Callable[[Path], bool],
        tools: tuple[str, list[str]] | None = None,
    ) -> None:
        """``tiers`` names every action the Harness may take; it rejects the rest.
        File actions are allowed only on paths ``may_touch`` accepts, read from
        ``directory``, where the Harness's session runs."""
        self._engine = engine
        self._log = log
        self._model = model
        self._tiers = tiers
        self._directory = directory
        #: Where a Conversation with no Project runs.
        self._home = directory
        self._may_touch = may_touch
        #: The tool server, which the Engine keeps per folder.
        self._tools = tools
        self._tools_in: set[Path] = set()
        self._session: str | None = None
        #: Sessions working on a question, served whichever one is on screen,
        #: and the folder each runs in.
        self._running: dict[str, Path] = {}

    def ask(self, text: str) -> None:
        if self._session is None:
            self._ready(self._directory)
            self._session = self._engine.start(self._model, self._directory)
            self._engine.rename(self._session, title_of(text))
        self._running[self._session] = self._directory
        self._log.write("sent", session=self._session, text=text)
        self._engine.send(self._session, text)

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

    def worked_on(self, folder: Path) -> None:
        """A Conversation with no Project takes the Project of the first Program
        it works on; one already in a Project stays there (CONTEXT.md)."""
        if self._session is None or self._directory != self._home:
            return
        self._engine.move(self._session, folder)
        self._directory = folder
        if self._session in self._running:
            self._running[self._session] = folder
        self._ready(folder)

    def move(self, session: str, folder: Path) -> None:
        self._engine.move(session, folder)

    def use_model(self, model: ModelRef) -> None:
        """Answer with this model from now on, in this conversation too."""
        self._model = model
        if self._session is not None:
            self._engine.switch_model(self._session, model)

    def stop(self) -> None:
        if self._session is not None:
            self._engine.stop(self._session)

    def _tier(
        self, session: str, action: str, resources: tuple[str, ...]
    ) -> Tier | None:
        if action in self._tiers:
            return self._tiers[action]
        folder = self._running.get(session, self._directory)
        if (
            action in FILE_TIERS
            and resources
            and all(self._inside(folder, resource) for resource in resources)
        ):
            return FILE_TIERS[action]
        return None

    def _inside(self, folder: Path, resource: str) -> bool:
        """Whether a path the Engine names, relative to the session's folder or
        absolute, and perhaps a folder pattern ending in ``*``, is one the
        Harness may touch. ``..`` is resolved first, so it cannot climb out."""
        path = posixpath.join(str(folder), resource.removesuffix("*"))
        return self._may_touch(Path(posixpath.normpath(path)))

    def _reply(self, session: str, request: str, *, allow: bool, message: str) -> None:
        """Answer a request; one the Engine cannot take is logged, so a single
        bad reply never ends the conversation."""
        try:
            self._engine.reply(session, request, allow=allow, message=message)
        except HttpError as error:
            self._log.write(
                "reply-failed", session=session, request=request, error=str(error)
            )

    def handle(self, event: Event) -> Event | Decision | None:
        """Log what the Engine reports and apply policy; the event is passed on.

        None for another program's session: the Engine's stream carries them all.
        """
        if event.session != self._session and event.session not in self._running:
            return None
        if isinstance(event, Finished | Stopped | Failed):
            self._running.pop(event.session, None)
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
            case ToolCalled(session, call, arguments, executed):
                self._log.write(
                    "tool",
                    session=session,
                    call=call,
                    input=arguments,
                    executed=executed,
                )
            case ToolRequested(session, request, action, resources) if (
                tier := self._tier(session, action, resources)
            ):
                self._reply(session, request, allow=True, message="")
                self._log.write(
                    "allowed",
                    session=session,
                    action=action,
                    tier=tier.value,
                    resources=list(resources),
                )
                return Allowed(session, action, tier, resources)
            case ToolRequested(session, request, action, resources):
                self._reply(session, request, allow=False, message=REFUSED)
                self._log.write(
                    "rejected",
                    session=session,
                    action=action,
                    resources=list(resources),
                )
                return Refused(session, action, resources)
            case Failed(session, message):
                self._log.write("failed", session=session, message=message)
            case Stopped(session):
                self._log.write("stopped", session=session)
        return event
