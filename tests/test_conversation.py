"""What the bar shows: questions, streamed answers, and who answered."""

from __future__ import annotations

from osiris.harness.activity import Step
from osiris.harness.conversation import Conversation, State
from osiris.harness.engine import (
    Answered,
    Failed,
    Finished,
    ModelRef,
    PastTurn,
    Stopped,
    Text,
    Tokens,
    ToolCalled,
    ToolRequested,
)
from osiris.harness.harness import Allowed, Refused
from osiris.harness.log import Change
from osiris.harness.tiers import Tier

S = "ses_1"
GPT = ModelRef("openai", "gpt-5.5")


def tokens(input: int, output: int, reasoning: int = 0) -> Tokens:
    return Tokens(input, output, reasoning, cache_read=0, cache_write=0)


def test_a_question_waits_until_the_answer_starts() -> None:
    talk = Conversation()
    turn = talk.asked("hello")
    assert turn.question == "hello"
    assert turn.state is State.WAITING
    assert talk.busy


def test_the_answer_streams_into_the_latest_turn() -> None:
    talk = Conversation()
    talk.asked("hello")
    talk.apply(Text(S, "hi "))
    talk.apply(Text(S, "there"))
    assert talk.turns[-1].answer == "hi there"
    assert talk.turns[-1].state is State.ANSWERING


def test_a_finished_answer_names_its_model_and_frees_the_bar() -> None:
    talk = Conversation()
    talk.asked("hello")
    talk.apply(Text(S, "hi"))
    talk.apply(Answered(S, GPT, tokens(10, 2), cost=0.0))
    talk.apply(Finished(S))
    turn = talk.turns[-1]
    assert turn.state is State.DONE
    assert turn.model == GPT
    assert not talk.busy


def test_the_model_in_play_is_the_last_one_that_answered() -> None:
    talk = Conversation()
    assert talk.model is None
    talk.asked("hello")
    talk.apply(Answered(S, GPT, tokens(1, 1), cost=0.0))
    assert talk.model == GPT


def test_tokens_spent_add_up_across_the_conversation() -> None:
    talk = Conversation()
    talk.asked("one")
    talk.apply(Answered(S, GPT, tokens(10, 2, 3), cost=0.0))
    talk.apply(Finished(S))
    talk.asked("two")
    talk.apply(Answered(S, GPT, tokens(20, 4), cost=0.0))
    assert talk.tokens_spent == 39


def test_a_refused_action_is_shown_on_its_turn() -> None:
    talk = Conversation()
    talk.asked("list /etc")
    talk.apply(ToolCalled(S, "call_1", {"command": "ls /etc"}, executed=False))
    talk.apply(Refused(S, "shell", ("ls /etc",)))
    assert talk.turns[-1].refused == ["shell: ls /etc"]


def test_an_allowed_action_is_not_shown_as_refused() -> None:
    talk = Conversation()
    talk.asked("make it calm")
    talk.apply(ToolRequested(S, "per_1", "osiris_apply_theme", ("*",)))
    talk.apply(Allowed(S, "osiris_apply_theme", Tier.UNDOABLE, ("*",)))
    assert talk.turns[-1].refused == []


def test_every_decided_action_is_a_step_of_its_turn_in_order() -> None:
    talk = Conversation()
    talk.asked("add a pause button")
    talk.apply(Allowed(S, "read", Tier.LOOK, ("main.py",)))
    talk.apply(Refused(S, "bash", ("ls",)))
    talk.apply(Allowed(S, "edit", Tier.UNDOABLE, ("main.py",)))
    assert talk.turns[-1].steps == [
        Step("read", ("main.py",)),
        Step("bash", ("ls",), allowed=False),
        Step("edit", ("main.py",)),
    ]


def test_a_turn_is_thinking_until_a_step_then_doing_that_step() -> None:
    talk = Conversation()
    turn = talk.asked("add a pause button")
    assert turn.doing == "Thinking"
    talk.apply(Allowed(S, "edit", Tier.UNDOABLE, ("pomodoro/main.py",)))
    assert turn.doing == "Editing pomodoro/main.py"


def test_a_failure_keeps_the_engines_reason() -> None:
    talk = Conversation()
    talk.asked("hello")
    talk.apply(Failed(S, "No account is connected"))
    assert talk.turns[-1].state is State.FAILED
    assert talk.turns[-1].error == "No account is connected"
    assert not talk.busy


def test_a_stopped_answer_keeps_what_had_arrived() -> None:
    talk = Conversation()
    talk.asked("hello")
    talk.apply(Text(S, "partial"))
    talk.apply(Stopped(S))
    assert talk.turns[-1].state is State.STOPPED
    assert talk.turns[-1].answer == "partial"


def test_events_before_any_question_change_nothing() -> None:
    talk = Conversation()
    talk.apply(Text(S, "stray"))
    assert talk.turns == []


def test_before_any_answer_the_header_names_the_chosen_default() -> None:
    talk = Conversation()
    assert (
        talk.model_label(default=ModelRef("openai", "gpt-6.1-sol"))
        == "openai / gpt-6.1-sol"
    )
    assert talk.model_label(default=None) == "default model"


def test_once_a_model_answers_the_header_names_that_one() -> None:
    talk = Conversation()
    talk.asked("hello")
    talk.apply(Answered(S, GPT, tokens(1, 1), cost=0.0))
    assert (
        talk.model_label(default=ModelRef("openai", "gpt-6.1-sol"))
        == "openai / gpt-5.5"
    )


MADE = Change("Made Harbour", {"action": "delete_theme", "name": "harbour"})
APPLIED = Change("Applied Harbour", {"action": "apply_theme", "name": "nord"})


def test_a_turn_keeps_the_changes_it_led_to() -> None:
    talk = Conversation()
    talk.asked("make it calm")
    talk.changed([MADE, APPLIED])
    assert talk.turns[-1].changes == [MADE, APPLIED]
    assert talk.turns[-1].undoable


def test_undoing_a_turn_reverses_its_changes_newest_first() -> None:
    talk = Conversation()
    talk.asked("make it calm")
    talk.changed([MADE, APPLIED])
    assert talk.turns[-1].undo_steps() == [APPLIED.undo, MADE.undo]


def test_a_change_with_nothing_to_return_to_is_skipped_by_undo() -> None:
    talk = Conversation()
    talk.asked("make it calm")
    talk.changed([MADE, Change("Applied Harbour", None)])
    assert talk.turns[-1].undo_steps() == [MADE.undo]


def test_an_undone_turn_cannot_be_undone_again() -> None:
    talk = Conversation()
    talk.asked("make it calm")
    talk.changed([MADE])
    talk.turns[-1].undone = True
    assert not talk.turns[-1].undoable


def test_a_turn_that_changed_nothing_offers_no_undo() -> None:
    talk = Conversation()
    talk.asked("hello")
    talk.changed([])
    assert not talk.turns[-1].undoable


def test_a_turn_knows_the_programs_it_changed_once_each_in_order() -> None:
    talk = Conversation()
    talk.asked("make a timer and a notes app")
    talk.changed(
        [
            Change("Made Pomodoro", None, program="pomodoro"),
            MADE,
            Change("Made Notes", None, program="notes"),
            Change("Pomodoro: Add a pause button", None, program="pomodoro"),
        ]
    )
    assert talk.turns[-1].programs == ["pomodoro", "notes"]


def test_a_new_conversation_has_no_title_yet() -> None:
    assert Conversation().title is None


def test_a_conversation_is_titled_by_its_first_question() -> None:
    talk = Conversation()
    talk.asked("Make me a calm theme\nfor working late")
    talk.asked("Now warmer")
    assert talk.title == "Make me a calm theme"


def test_a_long_first_question_is_shortened_for_the_title() -> None:
    talk = Conversation()
    talk.asked("Build me a small pomodoro timer app in Python with breaks and stats")
    assert talk.title == "Build me a small pomodoro timer app in Python…"


def test_a_past_conversation_comes_back_with_its_answers() -> None:
    talk = Conversation.restored(
        [PastTurn("make a timer", "Made it.", GPT), PastTurn("thanks", "", None)]
    )
    assert [(t.question, t.answer, t.state, t.model) for t in talk.turns] == [
        ("make a timer", "Made it.", State.DONE, GPT),
        ("thanks", "", State.DONE, None),
    ]
    assert talk.title == "make a timer"
    assert talk.model == GPT
    assert not talk.busy


def test_a_conversation_knows_every_program_it_has_touched() -> None:
    talk = Conversation()
    talk.asked("make a timer")
    talk.changed([Change("Made Pomodoro", None, program="pomodoro")])
    talk.asked("and a notes app")
    talk.changed(
        [
            Change("Made Notes", None, program="notes"),
            Change("Pomodoro: Add a pause button", None, program="pomodoro"),
        ]
    )
    assert talk.programs == ["pomodoro", "notes"]
