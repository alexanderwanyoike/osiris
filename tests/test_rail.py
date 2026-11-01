"""The Conversation rail (#167): a tick per question along the Conversation's
edge, showing its length and the part on screen at a glance."""

from __future__ import annotations

from osiris.harness.activity import Step
from osiris.harness.conversation import Turn
from osiris.harness.log import Change
from osiris.harness.rail import tone_of


def test_a_plain_question_has_no_tint() -> None:
    assert tone_of(Turn("what is a theme?")) == "plain"


def test_a_question_whose_answer_changed_something_has_its_own_tint() -> None:
    turn = Turn("make it calm")
    turn.changes.append(Change("Applied Nord", None))
    assert tone_of(turn) == "changed"


def test_a_question_waiting_on_the_person_outranks_a_change() -> None:
    turn = Turn("list /etc")
    turn.changes.append(Change("Applied Nord", None))
    turn.held = Step("shell", ("ls /etc",))
    assert tone_of(turn) == "waiting"


def test_a_question_is_on_screen_when_any_of_it_or_its_answer_is() -> None:
    from osiris.harness.rail import on_screen

    # Three questions starting at 0, 400 and 900 in a Conversation 1500 tall,
    # scrolled to show 350 to 950.
    assert on_screen([0, 400, 900], 1500, top=350, height=600) == [
        True,
        True,
        True,
    ]
    assert on_screen([0, 400, 900], 1500, top=1000, height=500) == [
        False,
        False,
        True,
    ]


def test_where_each_tick_stands_along_the_rail() -> None:
    from osiris.harness.rail import placed

    assert placed([0, 400, 900], 1600) == [0.0, 0.25, 0.5625]


def test_each_question_makes_a_tick_with_where_it_stands_and_how_it_starts() -> None:
    from osiris.harness.rail import Tick, ticks

    calm = Turn("make the desktop calm and quiet, with a soft dark theme please")
    calm.changes.append(Change("Applied Nord", None))
    turns = [Turn("what is a theme?"), calm]
    assert ticks(turns, [0, 500], 1000, top=600, height=400) == [
        Tick(0.0, False, "plain", "what is a theme?"),
        Tick(
            0.5,
            True,
            "changed",
            "make the desktop calm and quiet, with a soft…",
            current=True,
        ),
    ]


def test_the_first_question_on_screen_is_the_current_one() -> None:
    from osiris.harness.rail import ticks

    turns = [Turn("one"), Turn("two"), Turn("three")]
    made = ticks(turns, [0, 400, 900], 1500, top=500, height=600)
    assert [tick.current for tick in made] == [False, True, False]


def test_ticks_stand_evenly_in_a_column_centred_on_the_rail() -> None:
    from osiris.harness.rail import column

    # Five ticks 10 apart on a rail 400 tall: a column 50 tall, centred.
    assert column(5, 400) == (175.0, 10.0)


def test_many_ticks_draw_closer_rather_than_run_past_half_the_rail() -> None:
    from osiris.harness.rail import column

    top, pitch = column(100, 400)
    assert pitch * 100 <= 400 * 0.55
    assert top == (400 - pitch * 100) / 2
