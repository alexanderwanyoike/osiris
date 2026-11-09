"""What the bar shows: questions, streamed answers, and who answered."""

from __future__ import annotations

import pytest

from osiris.harness.activity import Step
from osiris.harness.admin import Request
from osiris.harness.conversation import Conversation, State, Turn
from osiris.harness.engine import (
    Answered,
    Delivered,
    Failed,
    Finished,
    ModelRef,
    PastTurn,
    Stopped,
    Text,
    Tokens,
    ToolCalled,
    ToolFinished,
    ToolRequested,
)
from osiris.harness.harness import Allowed, Asking, Refused
from osiris.harness.log import Change
from osiris.harness.tasks import Progress, Task

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


@pytest.mark.parametrize("ending", ["", "\n", "\n\n"])
def test_text_after_a_complete_step_starts_a_new_paragraph(ending: str) -> None:
    talk = Conversation()
    talk.asked("make a timer")
    talk.apply(Text(S, f"Wired up the controls.{ending}"))
    talk.apply(Answered(S, GPT, tokens(10, 2), cost=0.0))
    talk.apply(Text(S, "Built your app."))
    assert talk.turns[-1].answer == "Wired up the controls.\n\nBuilt your app."


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
    assert talk.turns[-1].steps == [Step("shell", ("ls /etc",), allowed=False)]


@pytest.mark.parametrize(
    ("name", "given", "action", "resources"),
    [
        ("read", {"path": "/etc/hostname"}, "read", ("/etc/hostname",)),
        ("write", {"path": "main.py", "content": "x"}, "edit", ("main.py",)),
        ("edit", {"filePath": "main.py"}, "edit", ("main.py",)),
        ("shell", {"command": "uname -r"}, "shell", ("uname -r",)),
        ("websearch", {"query": "gtk 4"}, "websearch", ("gtk 4",)),
        ("subagent", {"agent": "reviewer", "prompt": "x"}, "subagent", ("reviewer",)),
        (
            "patch",
            {"patchText": "*** Begin Patch\n*** Update File: /c/main.py\n+x"},
            "edit",
            ("/c/main.py",),
        ),
    ],
)
def test_a_tool_the_engine_ran_without_asking_is_a_step(
    name: str, given: dict[str, object], action: str, resources: tuple[str, ...]
) -> None:
    """The Engine's rules allowed it, so no decision of the Harness's names it
    (ADR 0020); it is shown as the action it is."""
    talk = Conversation()
    talk.asked("go on")
    talk.apply(ToolCalled(S, "c1", given, False, name))
    assert talk.turns[-1].steps == [Step(action, resources, True, "c1", given)]


def test_a_tool_that_then_asks_is_held_and_shown_once_answered() -> None:
    """The call is reported before the Engine asks about it."""
    talk = Conversation()
    talk.asked("list /etc")
    talk.apply(ToolCalled(S, "c1", {"command": "ls /etc"}, False, "shell"))
    talk.apply(Asking(S, "per_1", "shell", ("ls /etc",), "c1"))
    assert talk.turns[-1].steps == []
    assert talk.turns[-1].held is not None
    talk.apply(Allowed(S, "shell", ("ls /etc",), "c1"))
    assert [step.call for step in talk.turns[-1].steps] == ["c1"]


def test_while_a_card_waits_the_answer_says_it_waits_for_the_person() -> None:
    """Not that it runs the action: nothing runs until the person answers."""
    talk = Conversation()
    talk.asked("list /etc")
    talk.apply(ToolCalled(S, "c1", {"command": "ls /etc"}, False, "shell"))
    talk.apply(Asking(S, "per_1", "shell", ("ls /etc",), "c1"))
    assert talk.turns[-1].doing == "Waiting for you"


def test_what_auto_mode_allows_is_shown_once() -> None:
    talk = Conversation()
    talk.asked("list /etc")
    talk.apply(ToolCalled(S, "c1", {"command": "ls /etc"}, False, "shell"))
    talk.apply(Allowed(S, "shell", ("ls /etc",), "c1"))
    assert [step.call for step in talk.turns[-1].steps] == ["c1"]


def test_the_catalogues_code_is_not_read_for_steps() -> None:
    """What it runs comes from the tool server (#183): code written another way
    would hide a step."""
    talk = Conversation()
    talk.asked("make it calm")
    code = "await tools.osiris.create_theme(i); await tools.osiris.apply_theme(t)"
    talk.apply(ToolCalled(S, "c1", {"code": code}, False, "execute"))
    assert talk.turns[-1].steps == []


def test_each_tool_the_server_ran_is_a_step_once() -> None:
    talk = Conversation()
    talk.asked("make it calm")
    talk.ran(["osiris_create_theme"])
    talk.ran(["osiris_create_theme", "osiris_apply_theme"])
    assert [step.action for step in talk.turns[-1].steps] == [
        "osiris_create_theme",
        "osiris_apply_theme",
    ]


def todos(*items: tuple[str, str]) -> dict[str, object]:
    return {"todos": [{"content": c, "status": s} for c, s in items]}


def test_the_engines_task_list_is_kept_on_its_turn_as_it_changes() -> None:
    """As opencode 2.2.4 does: each todowrite call carries the whole list."""
    talk = Conversation()
    talk.asked("make two files")
    first = todos(("Create c.txt", "in_progress"), ("Edit a.txt", "pending"))
    talk.apply(ToolCalled(S, "c1", first, False, "todowrite"))
    later = todos(("Create c.txt", "completed"), ("Edit a.txt", "in_progress"))
    talk.apply(ToolCalled(S, "c2", later, False, "todowrite"))
    turn = talk.turns[-1]
    assert turn.tasks == [
        Task("Create c.txt", Progress.DONE),
        Task("Edit a.txt", Progress.UNDER_WAY),
    ]
    assert turn.steps == []


def test_a_step_carries_the_input_of_its_tool_call() -> None:
    talk = Conversation()
    talk.asked("list /etc")
    talk.apply(ToolCalled(S, "call_1", {"command": "ls /etc"}, executed=False))
    talk.apply(Allowed(S, "shell", ("ls /etc",), "call_1"))
    assert talk.turns[-1].steps[0].input == {"command": "ls /etc"}


def test_a_step_carries_what_its_tool_call_gave_back() -> None:
    talk = Conversation()
    talk.asked("list /etc")
    talk.apply(Allowed(S, "shell", ("ls /etc",), "call_1"))
    talk.apply(ToolFinished(S, "call_1", "NetworkManager\nUPower\n", exit=0))
    step = talk.turns[-1].steps[0]
    assert (step.output, step.exit, step.error) == ("NetworkManager\nUPower\n", 0, "")


def test_a_step_whose_tool_failed_carries_why() -> None:
    talk = Conversation()
    talk.asked("read the notes")
    talk.apply(Allowed(S, "read", ("notes.txt",), "call_1"))
    talk.apply(ToolFinished(S, "call_1", "", error="File not found"))
    assert talk.turns[-1].steps[0].error == "File not found"


def test_a_refused_step_carries_the_rule_that_refused_it() -> None:
    talk = Conversation()
    talk.asked("list /etc")
    talk.apply(Refused(S, "shell", ("ls /etc",), "call_1", "Runs only with X on"))
    assert talk.turns[-1].steps[0].refused_by == "Runs only with X on"


def test_an_action_held_for_the_person_waits_on_its_turn_until_answered() -> None:
    talk = Conversation()
    talk.asked("list /etc")
    asking = Asking(S, "per_1", "shell", ("ls /etc",), "call_1")
    talk.apply(asking)
    assert talk.turns[-1].asking == asking
    talk.apply(Allowed(S, "shell", ("ls /etc",), "call_1"))
    assert talk.turns[-1].asking is None


def test_two_actions_asked_at_once_each_get_their_card_in_turn() -> None:
    """The model may call two commands in parallel; the second waits behind
    the first and comes up when the first is answered (#229)."""
    talk = Conversation()
    talk.asked("set up the tests")
    first = Asking(S, "per_1", "shell", ("command -v xvfb-run",), "call_1")
    second = Asking(S, "per_2", "shell", ("git status --short",), "call_2")
    talk.apply(first)
    talk.apply(second)
    assert talk.turns[-1].asking == first
    talk.apply(Allowed(S, "shell", ("command -v xvfb-run",), "call_1"))
    assert talk.turns[-1].asking == second


def test_an_action_held_for_the_person_shows_as_the_step_it_would_be() -> None:
    talk = Conversation()
    talk.asked("list /etc")
    talk.apply(ToolCalled(S, "call_1", {"command": "ls -la /etc"}, executed=False))
    talk.apply(Asking(S, "per_1", "shell", ("ls /etc",), "call_1"))
    held = talk.turns[-1].held
    assert held is not None
    assert (held.action, held.input) == ("shell", {"command": "ls -la /etc"})


def test_a_held_actions_card_goes_when_the_answer_ends() -> None:
    talk = Conversation()
    talk.asked("list /etc")
    talk.apply(Asking(S, "per_1", "shell", ("ls /etc",), "call_1"))
    talk.apply(Stopped(S))
    assert (talk.turns[-1].asking, talk.turns[-1].held) == (None, None)


def test_queued_cards_go_when_the_answer_ends() -> None:
    talk = Conversation()
    talk.asked("set up the tests")
    talk.apply(Asking(S, "per_1", "shell", ("command -v xvfb-run",), "call_1"))
    talk.apply(Asking(S, "per_2", "shell", ("git status --short",), "call_2"))
    talk.apply(Stopped(S))
    talk.apply(Allowed(S, "shell", ("command -v xvfb-run",), "call_1"))
    assert talk.turns[-1].asking is None


def test_an_allowed_action_is_not_shown_as_refused() -> None:
    talk = Conversation()
    talk.asked("make it calm")
    talk.apply(ToolRequested(S, "per_1", "osiris_apply_theme", ("*",)))
    talk.apply(Allowed(S, "osiris_apply_theme", ("*",)))
    assert all(step.allowed for step in talk.turns[-1].steps)


def test_every_decided_action_is_a_step_of_its_turn_in_order() -> None:
    talk = Conversation()
    talk.asked("add a pause button")
    talk.apply(Allowed(S, "read", ("main.py",)))
    talk.apply(Refused(S, "bash", ("ls",)))
    talk.apply(Allowed(S, "edit", ("main.py",)))
    assert talk.turns[-1].steps == [
        Step("read", ("main.py",)),
        Step("bash", ("ls",), allowed=False),
        Step("edit", ("main.py",)),
    ]


def test_a_turn_is_thinking_until_a_step_then_doing_that_step() -> None:
    talk = Conversation()
    turn = talk.asked("add a pause button")
    assert turn.doing == "Thinking"
    talk.apply(Allowed(S, "edit", ("pomodoro/main.py",)))
    assert turn.doing == "Editing pomodoro/main.py"


def test_once_a_step_is_complete_the_turn_is_thinking_again() -> None:
    talk = Conversation()
    turn = talk.asked("add a pause button")
    talk.apply(Allowed(S, "edit", ("pomodoro/main.py",)))
    talk.apply(Answered(S, GPT, tokens(10, 2), cost=0.0))
    assert turn.doing == "Thinking"


def test_while_the_answer_streams_the_turn_is_writing() -> None:
    talk = Conversation()
    turn = talk.asked("hello")
    talk.apply(Text(S, "hi"))
    assert turn.doing == "Writing"


def test_a_refused_step_leaves_the_turn_thinking() -> None:
    talk = Conversation()
    turn = talk.asked("list /etc")
    talk.apply(Allowed(S, "read", ("main.py",)))
    talk.apply(Refused(S, "bash", ("ls /etc",)))
    assert turn.doing == "Thinking"


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


def test_a_restored_conversation_shows_the_tokens_it_had_spent() -> None:
    talk = Conversation.restored(
        [PastTurn("make a timer", "Made it.", GPT)], tokens_spent=2048
    )
    assert talk.tokens_spent == 2048


MADE = Change(
    "Made Pomodoro", {"action": "trash_program", "name": "pomodoro"}, "pomodoro"
)
THEME = Change("Made Harbour", {"action": "delete_theme", "name": "harbour"})


def test_a_restored_conversation_keeps_what_each_answer_changed() -> None:
    """Its Program cards and Undo come back with it."""
    talk = Conversation.restored(
        [PastTurn("make a timer", "Made it.", GPT), PastTurn("a theme", "Done.", GPT)],
        changes=[[MADE], [THEME]],
    )
    assert [turn.changes for turn in talk.turns] == [[MADE], [THEME]]
    assert talk.turns[0].programs == ["pomodoro"]
    assert talk.turns[1].undoable


def test_changes_are_matched_to_the_latest_answers_when_history_is_longer() -> None:
    """Answers from before the log began have no changes to give back."""
    talk = Conversation.restored(
        [PastTurn("hi", "Hello.", GPT), PastTurn("make a timer", "Made it.", GPT)],
        changes=[[MADE]],
    )
    assert [turn.changes for turn in talk.turns] == [[], [MADE]]


def test_an_answer_whose_changes_were_undone_stays_undone() -> None:
    talk = Conversation.restored(
        [PastTurn("a theme", "Done.", GPT)],
        changes=[[THEME]],
        undone=[("Made Harbour",)],
    )
    assert talk.turns[0].undone
    assert not talk.turns[0].undoable


PACMAN = Request(("pacman", "-S", "cowsay"))


def test_an_admin_password_request_is_shown_under_the_answer_asking() -> None:
    talk = Conversation()
    talk.asked("install cowsay")
    talk.asked("and fortune")
    talk.needs_password(PACMAN)
    assert talk.turns[-1].admin == PACMAN
    assert talk.turns[0].admin is None


def test_an_answered_admin_password_request_goes_away() -> None:
    talk = Conversation()
    talk.asked("install cowsay")
    talk.needs_password(PACMAN)
    talk.password_answered()
    assert talk.turns[-1].admin is None


def test_a_conversation_with_no_question_shows_no_admin_request() -> None:
    talk = Conversation()
    talk.needs_password(PACMAN)
    assert talk.turns == []


def test_a_message_sent_while_busy_waits_until_it_reaches_thoth() -> None:
    talk = Conversation()
    first = talk.asked("count to sixty")
    talk.queued("msg_2", "stop at ten")
    assert [w.text for w in talk.waiting] == ["stop at ten"]
    talk.apply(Delivered(S, "msg_2"))
    assert talk.waiting == []
    assert talk.turns[-1].question == "stop at ten"
    assert first.state is State.DONE


def test_a_waiting_message_taken_back_gives_its_text_back() -> None:
    talk = Conversation()
    talk.asked("count to sixty")
    talk.queued("msg_2", "stop at ten")
    assert talk.unqueued("msg_2") == "stop at ten"
    assert talk.waiting == []


def test_a_conversation_with_a_card_open_waits_for_the_person() -> None:
    talk = Conversation()
    talk.asked("list /etc")
    assert not talk.waits_for_person
    talk.apply(Asking(S, "per_1", "shell", ("ls /etc",), "call_1"))
    assert talk.waits_for_person
    talk.apply(Allowed(S, "shell", ("ls /etc",), "call_1"))
    talk.needs_password(Request(("pacman", "-S", "cowsay")))
    assert talk.waits_for_person


def test_a_question_can_be_gone_back_to_once_nothing_is_answering() -> None:
    """Its message names it to the Engine, which refuses while it runs."""
    talk = Conversation.restored([PastTurn("make x.txt", "Made it.", None, "msg_1")])
    first = talk.turns[0]
    assert first.message == "msg_1"
    assert talk.can_go_back(first)
    talk.asked("make y.txt")
    assert not talk.can_go_back(first)
    assert not talk.can_go_back(talk.turns[-1])


def test_only_the_latest_answer_can_be_tried_again() -> None:
    """Trying an earlier one again would drop every answer after it unasked."""
    talk = Conversation.restored(
        [
            PastTurn("make x.txt", "Made it.", None, "msg_1"),
            PastTurn("make y.txt", "Made it.", None, "msg_2"),
        ]
    )
    first, latest = talk.turns
    assert not talk.can_try_again(first)
    assert talk.can_try_again(latest)


@pytest.mark.parametrize(
    ("place", "said"),
    [
        (2, "This question and its answer"),
        (0, "This question and the 2 after it, with their answers,"),
        (1, "This question and the one after it, with their answers,"),
    ],
)
def test_going_back_says_what_will_be_lost(place: int, said: str) -> None:
    talk = Conversation.restored(
        [PastTurn(q, "Done.", None, f"msg_{i}") for i, q in enumerate("abc")]
    )
    lost = talk.losing(talk.turns[place])
    assert lost.startswith(said)
    assert "files" in lost


def test_a_turn_knows_the_program_commits_its_question_made() -> None:
    """What its changes are shown from: a theme or a new folder has no commit."""
    turn = Turn(
        "build a coin flip",
        "Made it.",
        State.DONE,
        changes=[
            Change("Made coin-flip", {"action": "trash_program", "name": "coin-flip"}),
            Change(
                "coin-flip: Add a flip",
                {"action": "revert_commit", "name": "coin-flip", "commit": "abc"},
                "coin-flip",
            ),
            Change("Made Ember", {"action": "delete_theme", "name": "ember"}),
        ],
    )
    assert turn.commits == [("coin-flip", "abc")]


def test_a_past_conversation_comes_back_with_the_skills_its_answers_proposed() -> None:
    from osiris.harness.proposals import Proposal

    tidy = Proposal("tidy-imports", "Sort imports", "Run ruff.")
    talk = Conversation.restored(
        [PastTurn("tidy my imports", "Done.", GPT), PastTurn("thanks", "", GPT)],
        proposals=[[tidy], []],
    )
    assert [t.proposals for t in talk.turns] == [[tidy], []]
