"""The Conversation panel (#169): where it runs, its connectors, its context
and its changes."""

from __future__ import annotations

from .conftest import texts


def panel():
    from conversation_panel import ConversationPanel

    return ConversationPanel()


def test_it_says_where_the_conversation_runs_and_nothing_else() -> None:
    shown = panel()
    shown.show_where("timer", "main")
    rows = shown.cards["Where"].body
    assert texts(rows) == ["timer", "main"]


def test_a_folder_that_is_no_repository_shows_no_branch() -> None:
    shown = panel()
    shown.show_where("Home", "")
    assert not shown.branch.get_visible()


def test_each_connector_shows_with_its_state() -> None:
    from osiris.harness.connectors import State

    shown = panel()
    shown.show_connectors(
        {"wiki": State("connected"), "tracker": State("needs_auth", "", "mcp_x")}
    )
    words = texts(shown)
    assert "wiki" in words and "Connected" in words
    assert "tracker" in words and "Needs signing in" in words


def test_with_no_connectors_it_says_where_to_add_one() -> None:
    shown = panel()
    shown.show_connectors({})
    assert any("Settings, under MCP" in text for text in texts(shown))


def test_context_is_a_grid_of_squares_with_a_legend_marked_approximate() -> None:
    from conversation_panel import SQUARES

    from osiris.harness.context import Slice

    from .conftest import widgets

    shown = panel()
    shown.show_context(
        [
            Slice("instructions", 6000),
            Slice("questions", 1000),
            Slice("answers", 2000),
            Slice("tools", 1000),
            Slice("free", 90_000),
        ],
        used=10_000,
        window=100_000,
    )
    squares = [w for w in widgets(shown) if w.has_css_class("harness-context-square")]
    assert len(squares) == SQUARES
    assert sum(s.has_css_class("instructions") for s in squares) == SQUARES * 6 // 100
    words = texts(shown)
    assert "10,000 of 100,000 tokens" in words
    assert "Instructions" in words and "6%" in words
    assert any("pproximate" in text for text in words)


def test_each_question_that_changed_something_opens_its_changes() -> None:
    from gi.repository import Gtk

    from .conftest import widgets

    opened: list[int] = []
    shown = panel()
    shown.show_changes(
        [(1, "make it calm", 2), (3, "tidy the timer", 1)], opened.append
    )
    words = texts(shown)
    assert "make it calm" in words and "2 changes" in words
    assert "tidy the timer" in words and "1 change" in words
    rows = [w for w in widgets(shown) if isinstance(w, Gtk.ListBoxRow)]
    rows[1].emit("activate")
    assert opened == [3]


def test_with_nothing_changed_it_says_so() -> None:
    shown = panel()
    shown.show_changes([], lambda _i: None)
    assert "Nothing changed yet." in texts(shown)


def test_a_kind_present_but_under_one_percent_says_so_rather_than_none() -> None:
    from osiris.harness.context import Slice

    shown = panel()
    shown.show_context(
        [Slice("questions", 30), Slice("free", 99_970)], used=30, window=100_000
    )
    assert "<1%" in texts(shown)


def test_long_questions_do_not_widen_the_cards() -> None:
    from conversation_panel import CARD
    from gi.repository import Gtk

    shown = panel()
    shown.show_changes([(0, "a very long question that goes on " * 6, 1)], print)
    shown.show_where("a-project-with-a-rather-long-name-indeed", "main")
    _minimum, natural, _b, _c = shown.measure(Gtk.Orientation.HORIZONTAL, -1)
    assert natural <= CARD + shown.get_margin_start()


def test_with_nothing_asked_yet_context_says_so() -> None:
    from osiris.harness.context import Slice

    shown = panel()
    shown.show_context([Slice("free", 100)], used=0, window=100)
    shown.show_no_context()
    words = texts(shown)
    assert "Nothing asked yet." in words
    assert "0 of 100 tokens" not in words


def test_a_card_collapses_into_a_pill_that_sums_it_up_and_opens_again() -> None:
    from osiris.harness.connectors import State

    shown = panel()
    shown.show_connectors(
        {"wiki": State("connected"), "tracker": State("needs_auth", "", "x")}
    )
    card = shown.cards["MCP"]
    card.toggle()
    assert card.has_css_class("pill")
    assert not card.body.get_visible()
    assert card.summary.get_visible()
    assert card.summary.get_text() == "1 of 2 connected"
    card.toggle()
    assert not card.has_css_class("pill")
    assert card.body.get_visible()
    assert not card.summary.get_visible()


def test_each_pill_sums_up_its_card() -> None:
    from osiris.harness.context import Slice

    shown = panel()
    shown.show_where("timer", "main")
    shown.show_context([Slice("questions", 5000), Slice("free", 95_000)], 5000, 100_000)
    shown.show_changes([(0, "make it calm", 2), (2, "tidy", 1)], print)
    summaries = {name: card.summary.get_text() for name, card in shown.cards.items()}
    assert summaries["Where"] == "timer"
    assert summaries["Context"] == "5% used"
    assert summaries["Changes"] == "2 questions"


def test_a_folded_card_keeps_the_width_of_the_open_ones() -> None:
    import time

    from gi.repository import GLib, Gtk

    shown = panel()
    shown.show_where("timer", "main")
    shown.cards["MCP"].toggle()
    window = Gtk.Window(child=shown, default_width=600, default_height=800)
    window.present()
    context = GLib.MainContext.default()
    deadline = time.monotonic() + 5
    while not shown.get_width() and time.monotonic() < deadline:
        context.iteration(False)
    widths = {name: card.get_width() for name, card in shown.cards.items()}
    window.destroy()
    assert len(set(widths.values())) == 1, widths


def test_a_folded_card_points_down_to_say_it_opens() -> None:
    from gi.repository import Gtk

    from .conftest import widgets

    card = panel().cards["Context"]

    def chevron() -> str:
        found = [w for w in widgets(card) if w.has_css_class("harness-panel-chevron")]
        assert isinstance(found[0], Gtk.Image) and found[0].get_visible()
        return found[0].get_icon_name()

    assert chevron() == "pan-up-symbolic"
    card.toggle()
    assert chevron() == "pan-down-symbolic"
