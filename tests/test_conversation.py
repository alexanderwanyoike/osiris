"""What the bar shows: questions, streamed answers, and who answered."""

from __future__ import annotations

from osiris.harness.conversation import Conversation, State
from osiris.harness.engine import (
    Answered,
    Failed,
    Finished,
    ModelRef,
    Stopped,
    Text,
    Tokens,
    ToolCalled,
    ToolRequested,
)

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
    talk.apply(ToolRequested(S, "per_1", "shell", ("ls /etc",)))
    assert talk.turns[-1].refused == ["shell: ls /etc"]


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
