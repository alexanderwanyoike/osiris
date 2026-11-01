"""The conversation as the bar shows it, kept apart from GTK so it is tested."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from enum import Enum

from osiris.harness.activity import THINKING, WRITING, Step
from osiris.harness.admin import Request
from osiris.harness.detail import patched_file
from osiris.harness.engine import (
    Answered,
    Delivered,
    Event,
    Failed,
    Finished,
    ModelRef,
    PastTurn,
    Stopped,
    Text,
    ToolCalled,
    ToolFinished,
)
from osiris.harness.harness import Allowed, Asking, Decision, Refused
from osiris.harness.log import Change
from osiris.harness.status import Status
from osiris.harness.tasks import TASK_TOOL, Task, tasks_of
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
    #: A command of this answer's waiting for the administrator password.
    admin: Request | None = None
    #: An action of this answer's waiting for the person to answer its card,
    #: and the step it would be, with the input the model gave it.
    asking: Asking | None = None
    held: Step | None = None
    #: The Engine's plan for this answer, as it last reported it.
    tasks: list[Task] = field(default_factory=list)
    #: The question's message at the Engine, once it has been sent.
    message: str = ""
    #: A word from Thoth about this question, such as why it could not go back.
    note: str = ""

    @property
    def commits(self) -> list[tuple[str, str]]:
        """Each Program commit the question made, as (Program, commit): the
        commit its Undo would revert."""
        return [
            (change.undo["name"], change.undo["commit"])
            for change in self.changes
            if change.undo and change.undo.get("action") == "revert_commit"
        ]

    @property
    def programs(self) -> list[str]:
        """The Programs this turn changed, each once, in the order they changed."""
        named = (change.program for change in self.changes if change.program)
        return list(dict.fromkeys(named))

    def end(self, state: State) -> None:
        """An answer that ends leaves no card waiting: the Engine has moved on."""
        self.state = state
        self.asking = self.held = None

    @property
    def undoable(self) -> bool:
        return not self.undone and bool(self.undo_steps())

    def undo_steps(self) -> list[Mapping[str, str]]:
        """What reverses this turn's changes, the newest first."""
        return [change.undo for change in reversed(self.changes) if change.undo]


@dataclass(frozen=True)
class Waiting:
    """A message sent while Thoth worked, not yet taken in."""

    message: str
    text: str


#: Tools whose action, the name the rules and steps use, differs from their own.
_ACTIONS = {"write": "edit", "patch": "edit", "apply_patch": "edit", "bash": "shell"}
#: The input naming what a tool works on, in the order looked for.
_SUBJECT = (
    "command",
    "path",
    "filePath",
    "file_path",
    "pattern",
    "url",
    "query",
    "agent",
)


#: A tool server's tool called from the catalogue's code:
#: ``tools.osiris.apply_theme(`` or ``tools["osiris"].list_themes(``. Built-in
#: tools, ``tools.shell(``, are reported as calls of their own.
_SERVER_CALL = re.compile(r"tools(?:\.(\w+)|\[\"([^\"]+)\"\])\.(\w+)\s*\(")


def _from_code(call: str, arguments: Mapping[str, object]) -> list[Step]:
    """The tool servers' tools the catalogue's code runs, as steps."""
    code = str(arguments.get("code", ""))
    return [
        Step(f"{dotted or quoted}_{tool}", ("*",), True, call, arguments)
        for dotted, quoted, tool in _SERVER_CALL.findall(code)
    ]


def _ran(name: str, call: str, arguments: Mapping[str, object]) -> Step:
    """A tool the Engine ran without asking, as the step it would have been."""
    subject = next((arguments[key] for key in _SUBJECT if key in arguments), None)
    if subject is None and isinstance(patch := arguments.get("patchText"), str):
        subject = patched_file(patch)
    resources = (str(subject),) if subject is not None else ()
    return Step(_ACTIONS.get(name, name), resources, True, call, arguments)


class Conversation:
    def __init__(self) -> None:
        self.turns: list[Turn] = []
        self.model: ModelRef | None = None
        self.tokens_spent = 0
        #: Each step's text is written on its own, so the next starts a paragraph.
        self._step_ended = False
        #: What the model gave each tool call, kept until a decision names it.
        self._inputs: dict[str, Mapping[str, object]] = {}
        #: Messages sent while busy, in order, until each reaches the model.
        self.waiting: list[Waiting] = []

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

    @property
    def waits_for_person(self) -> bool:
        """An approval or admin password card is open on its latest answer."""
        if not self.turns:
            return False
        turn = self.turns[-1]
        return turn.asking is not None or turn.admin is not None

    def model_label(self, default: ModelRef | None) -> str:
        """The model in play: the last that answered, else the one chosen."""
        model = self.model or default
        return f"{model.provider} / {model.model}" if model else "default model"

    def can_go_back(self, turn: Turn) -> bool:
        """Whether going back to before ``turn`` can be offered: it was sent,
        and nothing is answering, which the Engine would refuse."""
        return bool(turn.message) and not self.busy

    def can_try_again(self, turn: Turn) -> bool:
        """Only the latest: trying an earlier one again would drop every
        answer after it unasked."""
        return self.can_go_back(turn) and turn is self.turns[-1]

    def losing(self, turn: Turn) -> str:
        """What going back to before ``turn`` loses, in words."""
        place = next(i for i, t in enumerate(self.turns) if t is turn)
        after = len(self.turns) - place - 1
        if after == 0:
            dropped = "This question and its answer"
        elif after == 1:
            dropped = "This question and the one after it, with their answers,"
        else:
            dropped = f"This question and the {after} after it, with their answers,"
        return (
            f"{dropped} leave the Conversation, and the files they changed in "
            "this Project go back to how they were."
        )

    def asked(self, question: str) -> Turn:
        turn = Turn(question)
        self.turns.append(turn)
        return turn

    @classmethod
    def restored(
        cls,
        past: list[PastTurn],
        tokens_spent: int = 0,
        changes: list[list[Change]] | None = None,
        undone: list[tuple[str, ...]] | None = None,
    ) -> Conversation:
        """A past Conversation as it ended, with what each answer changed.

        ``changes`` holds one list per question the log saw, matched to the
        latest answers: answers from before the log began have none."""
        talk = cls()
        talk.tokens_spent = tokens_spent
        for turn in past:
            talk.turns.append(
                Turn(
                    turn.question,
                    turn.answer,
                    State.DONE,
                    turn.model,
                    message=turn.message,
                )
            )
            talk.model = turn.model or talk.model
        undid = set(undone or [])
        for answer, made in zip(
            reversed(talk.turns), reversed(changes or []), strict=False
        ):
            answer.changes = made
            answer.undone = bool(made) and tuple(c.summary for c in made) in undid
        return talk

    def queued(self, message: str, text: str) -> None:
        self.waiting.append(Waiting(message, text))

    def unqueued(self, message: str) -> str:
        """Take a waiting message back; its text, or nothing if it has gone."""
        for waiting in self.waiting:
            if waiting.message == message:
                self.waiting.remove(waiting)
                return waiting.text
        return ""

    def _delivered(self, message: str) -> None:
        """A waiting message the model took in starts the next question; the
        answer it steered goes on under it."""
        text = self.unqueued(message)
        if not text:
            return
        if self.busy:
            self.turns[-1].end(State.DONE)
        self.asked(text)

    def needs_password(self, request: Request) -> None:
        if self.turns:
            self.turns[-1].admin = request

    def password_answered(self) -> None:
        for turn in self.turns:
            turn.admin = None

    def changed(self, changes: list[Change]) -> None:
        """Record what the latest question led to, as the Harness log has it."""
        if self.turns:
            self.turns[-1].changes = changes

    def _input(self, call: str) -> Mapping[str, object] | None:
        return self._inputs.pop(call, None) if call else None

    def _called(self, turn: Turn, event: ToolCalled) -> None:
        """A tool call: the task list, or a step the Engine ran without asking."""
        call, arguments, name = event.call, event.input, event.name
        if name == TASK_TOOL:
            turn.tasks = tasks_of(arguments)
            return
        self._inputs[call] = arguments
        ran = _from_code(call, arguments) if name == "execute" else None
        if ran is None and name:
            ran = [_ran(name, call, arguments)]
        if ran:
            turn.steps += ran
            turn.doing = turn.steps[-1].doing

    def _step(
        self,
        turn: Turn,
        event: Asking | ToolCalled | Allowed | Refused | ToolFinished,
    ) -> None:
        if isinstance(event, Allowed | Refused):
            turn.asking, turn.held = None, None
        match event:
            case Asking(_, _, action, resources, call):
                turn.steps = [step for step in turn.steps if step.call != call]
                turn.doing = Status.WAITING.value
                turn.asking = event
                turn.held = Step(
                    action, resources, call=call, input=self._inputs.get(call)
                )
            case ToolFinished(_, call, output, error, exit_status):
                turn.steps = [
                    replace(step, output=output, error=error, exit=exit_status)
                    if step.call == call
                    else step
                    for step in turn.steps
                ]
            case ToolCalled():
                self._called(turn, event)
            case Allowed(_, action, resources, call):
                if not any(step.call == call for step in turn.steps if call):
                    turn.steps.append(
                        Step(action, resources, True, call, self._input(call))
                    )
                turn.doing = turn.steps[-1].doing
            case Refused(_, action, resources, call, reason):
                turn.steps.append(
                    Step(
                        action,
                        resources,
                        False,
                        call,
                        self._input(call),
                        refused_by=reason,
                    )
                )
                turn.doing = THINKING

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
            case Asking() | ToolCalled() | Allowed() | Refused() | ToolFinished():
                self._step(turn, event)
            case Delivered(_, message):
                self._delivered(message)
            case Finished():
                turn.end(State.DONE)
            case Stopped():
                turn.end(State.STOPPED)
            case Failed(_, message):
                turn.end(State.FAILED)
                turn.error = message
