"""A turn in the drawer: what its answer changed, and the Undo for it."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import replace

from gi.repository import GLib, Gtk
from render import TurnView

from osiris.harness.activity import Step
from osiris.harness.admin import Request
from osiris.harness.conversation import State, Turn
from osiris.harness.detail import FOLD
from osiris.harness.harness import Asking
from osiris.harness.log import Change
from osiris.harness.markdown import InlineStyle

from .conftest import find, shown, texts, widgets

STYLE = InlineStyle(code_foreground="#ffffff", code_background="#000000")
MADE = Change("Made Harbour", {"action": "delete_theme", "name": "harbour"})
APPLIED = Change("Applied Harbour", {"action": "apply_theme", "name": "nord"})


def drawn(
    turn: Turn,
    undone: list[Turn] | None = None,
    cards: list[str] | None = None,
    clock: Callable[[], float] = lambda: 0.0,
) -> TurnView:
    def card(name: str) -> Gtk.Widget:
        (cards if cards is not None else []).append(name)
        return Gtk.Label(label=f"card for {name}")

    view = TurnView(
        turn,
        on_undo=(undone if undone is not None else []).append,
        program_card=card,
        clock=clock,
    )
    view.update(turn, STYLE, None)
    return view


def finished(*changes: Change) -> Turn:
    return Turn("make it calm", "Done.", State.DONE, changes=list(changes))


def test_a_turn_that_changed_something_says_what_and_offers_undo() -> None:
    undone: list[Turn] = []
    turn = finished(MADE, APPLIED)
    view = drawn(turn, undone)
    assert "Made Harbour  ·  Applied Harbour" in texts(view)
    find(view, Gtk.Button, "Undo").emit("clicked")
    assert undone == [turn]


def test_an_undone_turn_says_so_and_offers_no_undo() -> None:
    turn = finished(MADE)
    turn.undone = True
    view = drawn(turn)
    assert "Undone" in texts(view)
    assert not any(
        isinstance(w, Gtk.Button) and w.get_label() == "Undo" for w in widgets(view)
    )


def test_a_turn_that_changed_nothing_shows_no_changes() -> None:
    view = drawn(finished())
    assert not any("Undo" in text for text in texts(view))


def test_a_turn_that_changed_programs_shows_a_card_for_each() -> None:
    cards: list[str] = []
    turn = finished(
        Change("Made Pomodoro", None, program="pomodoro"),
        Change("Made Notes", None, program="notes"),
    )
    view = drawn(turn, cards=cards)
    assert cards == ["pomodoro", "notes"]
    assert "card for pomodoro" in texts(view)


def test_a_working_turn_says_it_is_thinking_and_for_how_long() -> None:
    now = [100.0]
    turn = Turn("make a timer")
    view = drawn(turn, clock=lambda: now[0])
    now[0] = 114.0
    view.update(turn, STYLE, None)
    assert "Thinking" in shown(view)
    assert "14s" in shown(view)


def happens(condition: Callable[[], bool], within: float = 2.0) -> bool:
    """Whether condition comes true while the main loop runs, within seconds."""
    deadline = time.monotonic() + within
    while time.monotonic() < deadline:
        GLib.MainContext.default().iteration(False)
        if condition():
            return True
        time.sleep(0.01)
    return False


def test_the_time_counts_up_each_second_while_osiris_works() -> None:
    now = [100.0]
    view = drawn(Turn("make a timer"), clock=lambda: now[0])
    now[0] = 103.0
    assert happens(lambda: "3s" in shown(view))


def test_once_the_answer_ends_the_working_row_goes_and_stops_counting() -> None:
    turn = Turn("make a timer")
    view = drawn(turn)
    turn.state = State.DONE
    view.update(turn, STYLE, None)
    assert "Thinking" not in shown(view)
    assert not view.working.ticking


def test_what_osiris_did_is_kept_folded_under_the_answer() -> None:
    turn = finished()
    turn.steps = [
        Step("edit", ("pomodoro/main.py",)),
        Step("bash", ("ls /etc",), allowed=False),
    ]
    record = find(drawn(turn), Gtk.Expander)
    assert record.get_label() == "Used 2 tools"
    assert not record.get_expanded()
    steps = record.get_child()
    assert "Edited pomodoro/main.py" in texts(steps)
    assert "Not allowed to run ls /etc" in texts(steps)
    icons = [w.get_icon_name() for w in widgets(steps) if isinstance(w, Gtk.Image)]
    assert icons == ["object-select-symbolic", "changes-prevent-symbolic"]


def test_a_step_opens_to_show_what_it_asked_and_what_came_back() -> None:
    turn = finished()
    turn.steps = [
        Step(
            "shell",
            ("ls /etc",),
            input={"command": "ls /etc | head -2"},
            output="NetworkManager\nUPower\n",
        )
    ]
    record = find(drawn(turn), Gtk.Expander)
    step = find(record.get_child(), Gtk.Expander)
    assert texts(step.get_label_widget()) == ["Ran ls /etc"]
    assert not step.get_expanded()
    assert {"ls /etc | head -2", "NetworkManager", "UPower"} <= set(
        texts(step.get_child())
    )


def test_a_step_shows_its_output_once_it_arrives() -> None:
    turn = Turn("list /etc", "", State.ANSWERING)
    running = Step("shell", ("ls /etc",), input={"command": "ls /etc"})
    turn.steps = [running]
    view = drawn(turn)
    turn.steps = [replace(running, output="NetworkManager\n")]
    view.update(turn, STYLE, None)
    step = find(find(view, Gtk.Expander).get_child(), Gtk.Expander)
    assert "NetworkManager" in texts(step.get_child())


def test_an_edit_step_marks_the_lines_it_removed_and_added() -> None:
    turn = finished()
    turn.steps = [
        Step(
            "edit",
            ("main.py",),
            input={"path": "main.py", "oldString": "a = 1", "newString": "a = 2"},
        )
    ]
    step = find(find(drawn(turn), Gtk.Expander).get_child(), Gtk.Expander)
    marked = {
        w.get_text(): w.get_css_classes()
        for w in widgets(step.get_child())
        if isinstance(w, Gtk.Label)
    }
    assert "harness-removed" in marked["- a = 1"]
    assert "harness-added" in marked["+ a = 2"]


def test_long_output_is_folded_until_asked_for() -> None:
    turn = finished()
    output = "".join(f"line {n}\n" for n in range(40))
    turn.steps = [Step("shell", ("seq",), input={"command": "seq"}, output=output)]
    step = find(find(drawn(turn), Gtk.Expander).get_child(), Gtk.Expander)
    assert "line 39" not in texts(step.get_child())
    more = find(step.get_child(), Gtk.Button)
    assert more.get_label() == f"Show {40 - FOLD} more lines"
    more.emit("clicked")
    assert "line 39" in texts(step.get_child())


def test_a_refused_step_shows_the_rule_that_refused_it() -> None:
    turn = finished()
    turn.steps = [
        Step("shell", ("ls",), allowed=False, refused_by="Runs only with X on")
    ]
    step = find(find(drawn(turn), Gtk.Expander).get_child(), Gtk.Expander)
    note = next(
        w
        for w in widgets(step.get_child())
        if isinstance(w, Gtk.Label) and w.get_text() == "Runs only with X on"
    )
    assert "harness-step-note" in note.get_css_classes()


def test_a_tool_shows_its_inputs() -> None:
    turn = finished()
    turn.steps = [Step("osiris_apply_theme", ("*",), input={"name": "calm-night"})]
    step = find(find(drawn(turn), Gtk.Expander).get_child(), Gtk.Expander)
    assert "name: calm-night" in texts(step.get_child())


def test_an_action_held_for_the_person_shows_its_card_under_the_answer() -> None:
    turn = Turn("list /etc", "Looking.", State.ANSWERING)
    turn.asking = Asking("ses_1", "per_1", "shell", ("ls /etc",))
    turn.held = Step("shell", ("ls /etc",))
    asked: list[Turn] = []

    def approval_card(held: Turn) -> Gtk.Widget:
        asked.append(held)
        return Gtk.Label(label="approval card")

    view = TurnView(
        turn,
        on_undo=lambda _t: None,
        program_card=lambda _n: Gtk.Box(),
        approval_card=approval_card,
    )
    view.update(turn, STYLE, None)
    assert asked == [turn]
    assert "approval card" in texts(view)


def test_an_answer_that_took_no_steps_keeps_no_record() -> None:
    view = drawn(finished())
    assert not any(text.startswith("Used") for text in shown(view))


def test_a_command_waiting_for_the_password_shows_its_card_under_the_answer() -> None:
    asked: list[Request] = []
    card = Gtk.Label(label="admin card")

    def admin_card(request: Request) -> Gtk.Widget:
        asked.append(request)
        return card

    turn = Turn("install cowsay", "Installing.", State.ANSWERING)
    turn.admin = Request(("pacman", "-S", "cowsay"))
    view = TurnView(
        turn, on_undo=lambda _t: None, program_card=Gtk.Label, admin_card=admin_card
    )
    view.update(turn, STYLE, None)
    view.update(turn, STYLE, None)
    assert asked[-1] == turn.admin
    assert card.get_parent() is view.extras
    turn.admin = None
    view.update(turn, STYLE, None)
    assert "admin card" not in texts(view)


def test_the_engines_task_list_shows_each_step_and_how_far_it_has_got() -> None:
    from osiris.harness.tasks import Progress, Task

    tasks = [
        Task("Create c.txt", Progress.DONE),
        Task("Edit a.txt", Progress.UNDER_WAY),
        Task("Run the tests", Progress.TO_DO),
    ]
    view = drawn(Turn("make two files", "", State.ANSWERING, tasks=tasks))
    rows = [w for w in widgets(view) if w.has_css_class("harness-task")]
    assert [texts(row) for row in rows] == [
        ["Create c.txt"],
        ["Edit a.txt"],
        ["Run the tests"],
    ]
    assert [
        next(c for c in ("done", "under-way", "to-do") if row.has_css_class(c))
        for row in rows
    ] == ["done", "under-way", "to-do"]


def test_the_task_list_stays_once_the_answer_ends() -> None:
    from osiris.harness.tasks import Progress, Task

    turn = Turn(
        "make two files",
        "Done.",
        State.DONE,
        tasks=[Task("Create c.txt", Progress.DONE)],
    )
    assert "Create c.txt" in texts(drawn(turn))


def test_a_question_offers_edit_and_try_again_when_it_may() -> None:
    """Both go back to before it first (#158)."""
    edited: list[Turn] = []
    again: list[Turn] = []
    turn = Turn("make y.txt", "Made it.", State.DONE, message="msg_2")
    view = TurnView(
        turn,
        on_undo=lambda _t: None,
        program_card=lambda _n: Gtk.Label(),
        edit=edited.append,
        try_again=again.append,
        may_go_back=lambda _t: True,
    )
    view.update(turn, STYLE, None)
    edit = find(view, Gtk.Button, "Edit")
    assert "before this question" in edit.get_tooltip_text()
    edit.emit("clicked")
    find(view, Gtk.Button, "Try again").emit("clicked")
    assert (edited, again) == ([turn], [turn])


def test_neither_is_offered_when_it_may_not_go_back() -> None:
    turn = Turn("make y.txt", "", State.ANSWERING, message="msg_2")
    view = TurnView(
        turn,
        on_undo=lambda _t: None,
        program_card=lambda _n: Gtk.Label(),
        edit=lambda _t: None,
        try_again=lambda _t: None,
        may_go_back=lambda _t: False,
    )
    view.update(turn, STYLE, None)
    assert "Edit" not in texts(view)
    assert "Try again" not in texts(view)


def test_a_note_about_the_question_is_shown_under_its_answer() -> None:
    """Such as why it could not be gone back to."""
    turn = Turn("make x.txt", "Made it.", State.DONE, note="Nothing went back.")
    assert "Nothing went back." in texts(drawn(turn))


def edited(state: State) -> Turn:
    turn = Turn("tidy main.py", "Tidied.", state, message="msg_3")
    turn.steps.append(Step("edit", ("main.py",)))
    return turn


def test_an_answer_that_edited_files_offers_its_changes_once_it_ends() -> None:
    shown: list[Turn] = []
    turn = edited(State.DONE)
    view = TurnView(
        turn,
        on_undo=lambda _t: None,
        program_card=lambda _n: Gtk.Label(),
        show_changes=shown.append,
    )
    view.update(turn, STYLE, None)
    find(view, Gtk.Button, "Changes").emit("clicked")
    assert shown == [turn]


def test_an_answer_still_editing_or_that_edited_nothing_offers_no_changes() -> None:
    for turn in (edited(State.ANSWERING), finished()):
        view = TurnView(
            turn,
            on_undo=lambda _t: None,
            program_card=lambda _n: Gtk.Label(),
            show_changes=lambda _t: None,
        )
        view.update(turn, STYLE, None)
        assert "Changes" not in texts(view)


def icon_button(root: Gtk.Widget, icon: str) -> Gtk.Button:
    return next(
        w
        for w in widgets(root)
        if isinstance(w, Gtk.Button) and w.get_icon_name() == icon
    )


def going_back(may: bool, state: State = State.DONE) -> tuple[TurnView, Turn, list]:
    asked: list[tuple[str, Turn]] = []
    turn = Turn("make y.txt", "Made it.", state, message="msg_2")
    view = TurnView(
        turn,
        on_undo=lambda _t: None,
        program_card=lambda _n: Gtk.Label(),
        edit=lambda t: asked.append(("edit", t)),
        try_again=lambda t: asked.append(("again", t)),
        may_go_back=lambda _t: may,
    )
    view.update(turn, STYLE, None)
    return view, turn, asked


def test_a_question_is_edited_from_a_pencil_beside_it() -> None:
    view, turn, asked = going_back(may=True)
    pencil = icon_button(view, "document-edit-symbolic")
    question = next(
        w for w in widgets(view) if "harness-question" in w.get_css_classes()
    )
    assert pencil.get_parent() is question.get_parent()
    assert pencil.get_visible()
    assert pencil.get_tooltip_text().startswith("Edit this question")
    pencil.emit("clicked")
    assert asked == [("edit", turn)]


def test_the_pencil_is_hidden_while_the_question_may_not_be_gone_back_to() -> None:
    view, _, _ = going_back(may=False, state=State.ANSWERING)
    assert not icon_button(view, "document-edit-symbolic").get_visible()


def tried(may: bool) -> tuple[TurnView, Turn, list[Turn]]:
    again: list[Turn] = []
    turn = Turn("make y.txt", "Made it.", State.DONE, message="msg_2")
    view = TurnView(
        turn,
        on_undo=lambda _t: None,
        program_card=lambda _n: Gtk.Label(),
        try_again=again.append,
        may_try_again=lambda _t: may,
    )
    view.update(turn, STYLE, None)
    return view, turn, again


def test_the_latest_answer_is_tried_again_from_an_arrow_by_its_model_and_time() -> None:
    view, turn, again = tried(may=True)
    arrow = icon_button(view, "view-refresh-symbolic")
    meta = next(w for w in widgets(view) if "harness-meta" in w.get_css_classes())
    assert arrow.get_parent() is meta.get_parent()
    assert arrow.get_tooltip_text().startswith("Try this question again")
    arrow.emit("clicked")
    assert again == [turn]


def test_an_answer_that_may_not_be_tried_again_has_no_arrow() -> None:
    view, _, _ = tried(may=False)
    assert not any(
        isinstance(w, Gtk.Button) and w.get_icon_name() == "view-refresh-symbolic"
        for w in widgets(view)
    )
