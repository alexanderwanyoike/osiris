"""The conversation as the bar shows it, kept apart from GTK so it is tested."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

from osiris.harness.activity import THINKING, WRITING, Step
from osiris.harness.engine import (
    Answered,
    Event,
    Failed,
    Finished,
    ModelRef,
    PastTurn,
    Stopped,
    Text,
)
from osiris.harness.harness import Allowed, Decision, Refused
from osiris.harness.log import Change
from osiris.harness.titles import title_of


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
    steps: list[Step] = field(default_factory=list)
    #: What Osiris is doing now, in words.
    doing: str = THINKING
    error: str = ""
    changes: list[Change] = field(default_factory=list)
    undone: bool = False

    @property
    def programs(self) -> list[str]:
        """The Programs this turn changed, each once, in the order they changed."""
        named = (change.program for change in self.changes if change.program)
        return list(dict.fromkeys(named))

    @property
    def undoable(self) -> bool:
        return not self.undone and bool(self.undo_steps())

    def undo_steps(self) -> list[Mapping[str, str]]:
        """What reverses this turn's changes, the newest first."""
        return [change.undo for change in reversed(self.changes) if change.undo]


class Conversation:
    def __init__(self) -> None:
        self.turns: list[Turn] = []
        self.model: ModelRef | None = None
        self.tokens_spent = 0
        #: Each step's text is written on its own, so the next starts a paragraph.
        self._step_ended = False

    @property
    def title(self) -> str | None:
        return title_of(self.turns[0].question) if self.turns else None

    @property
    def programs(self) -> list[str]:
        """Every Program this Conversation has changed, in the order it first did."""
        return list(
            dict.fromkeys(name for turn in self.turns for name in turn.programs)
        )

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

    @classmethod
    def restored(cls, past: list[PastTurn], tokens_spent: int = 0) -> Conversation:
        """A past Conversation as it ended."""
        talk = cls()
        talk.tokens_spent = tokens_spent
        for turn in past:
            talk.turns.append(Turn(turn.question, turn.answer, State.DONE, turn.model))
            talk.model = turn.model or talk.model
        return talk

    def changed(self, changes: list[Change]) -> None:
        """Record what the latest question led to, as the Harness log has it."""
        if self.turns:
            self.turns[-1].changes = changes

    def apply(self, event: Event | Decision) -> None:
        if not self.turns:
            return
        turn = self.turns[-1]
        match event:
            case Text(_, delta):
                if self._step_ended and turn.answer:
                    turn.answer = turn.answer.rstrip("\n") + "\n\n"
                self._step_ended = False
                turn.answer += delta
                turn.state = State.ANSWERING
                turn.doing = WRITING
            case Answered(_, model, tokens, _):
                turn.model = self.model = model
                turn.doing = THINKING
                self._step_ended = True
                self.tokens_spent += tokens.input + tokens.output + tokens.reasoning
            case Allowed(_, action, _, resources):
                turn.steps.append(Step(action, resources))
                turn.doing = turn.steps[-1].doing
            case Refused(_, action, resources):
                turn.steps.append(Step(action, resources, allowed=False))
                turn.doing = THINKING
            case Finished():
                turn.state = State.DONE
            case Stopped():
                turn.state = State.STOPPED
            case Failed(_, message):
                turn.state = State.FAILED
                turn.error = message
