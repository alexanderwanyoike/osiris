"""The Harness: one conversation, logged, on whichever Engine it is given."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict

from osiris.harness.engine import (
    Answered,
    Engine,
    Event,
    Failed,
    ModelRef,
    Stopped,
    ToolCalled,
    ToolRequested,
)
from osiris.harness.log import HarnessLog
from osiris.harness.tiers import Tier

#: Passed to the model with every rejected tool, so it answers in words instead.
TALK_ONLY = (
    "The Osiris Harness cannot do that: it cannot run commands or read files, "
    "and changes this machine only through the Osiris tools. Answer in words, "
    "or with those tools."
)


class Harness:
    def __init__(
        self,
        engine: Engine,
        log: HarnessLog,
        model: ModelRef | None = None,
        *,
        tiers: Mapping[str, Tier],
    ) -> None:
        """``tiers`` names every action the Harness may take; it rejects the rest."""
        self._engine = engine
        self._log = log
        self._model = model
        self._tiers = tiers
        self._session: str | None = None

    def ask(self, text: str) -> None:
        if self._session is None:
            self._session = self._engine.start(self._model)
        self._log.write("sent", session=self._session, text=text)
        self._engine.send(self._session, text)

    def use_model(self, model: ModelRef) -> None:
        """Answer with this model from now on, in this conversation too."""
        self._model = model
        if self._session is not None:
            self._engine.switch_model(self._session, model)

    def stop(self) -> None:
        if self._session is not None:
            self._engine.stop(self._session)

    def handle(self, event: Event) -> Event | None:
        """Log what the Engine reports and apply policy; the event is passed on.

        None for another program's session: the Engine's stream carries them all.
        """
        if self._session is None or event.session != self._session:
            return None
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
            case ToolRequested(session, request, action, _) if action in self._tiers:
                self._engine.reply(session, request, allow=True, message="")
                self._log.write(
                    "allowed",
                    session=session,
                    action=action,
                    tier=self._tiers[action].value,
                )
            case ToolRequested(session, request, action, resources):
                self._engine.reply(session, request, allow=False, message=TALK_ONLY)
                self._log.write(
                    "rejected",
                    session=session,
                    action=action,
                    resources=list(resources),
                )
            case Failed(session, message):
                self._log.write("failed", session=session, message=message)
            case Stopped(session):
                self._log.write("stopped", session=session)
        return event
