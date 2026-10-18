"""The conversation as the bar shows it, kept apart from GTK so it is tested."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from osiris.harness.engine import (
    Answered,
    Event,
    Failed,
    Finished,
    ModelRef,
    Stopped,
    Text,
    ToolRequested,
)


class State(Enum):
    WAITING = "waiting"
    ANSWERING = "answering"
    DONE = "done"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class Turn:
    question: str
    answer: str = ""
    state: State = State.WAITING
    model: ModelRef | None = None
    refused: list[str] = field(default_factory=list)
    error: str = ""


class Conversation:
    def __init__(self) -> None:
        self.turns: list[Turn] = []
        self.model: ModelRef | None = None
        self.tokens_spent = 0

    @property
    def busy(self) -> bool:
        return bool(self.turns) and self.turns[-1].state in (
            State.WAITING,
            State.ANSWERING,
        )

    def model_label(self, default: ModelRef | None) -> str:
        """The model in play: the last that answered, else the one chosen."""
        model = self.model or default
        return f"{model.provider} / {model.model}" if model else "default model"

    def asked(self, question: str) -> Turn:
        turn = Turn(question)
        self.turns.append(turn)
        return turn

    def apply(self, event: Event) -> None:
        if not self.turns:
            return
        turn = self.turns[-1]
        match event:
            case Text(_, delta):
                turn.answer += delta
                turn.state = State.ANSWERING
            case Answered(_, model, tokens, _):
                turn.model = self.model = model
                self.tokens_spent += tokens.input + tokens.output + tokens.reasoning
            case ToolRequested(_, _, action, resources):
                turn.refused.append(f"{action}: {', '.join(resources)}")
            case Finished():
                turn.state = State.DONE
            case Stopped():
                turn.state = State.STOPPED
            case Failed(_, message):
                turn.state = State.FAILED
                turn.error = message
