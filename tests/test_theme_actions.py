"""What the Harness may do with Themes: list them, make one from a Theme
intent, and apply one. A model supplies only the intent; the colours are
Osiris's (CONTEXT.md)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from osiris.model.colour import Colour
from osiris.themes.actions import (
    ThemeActionError,
    apply_theme,
    create_picture_theme,
    create_theme,
    delete_theme,
    find,
    list_themes,
    make_other_half,
    make_theme_pair,
    unused_name,
    use_wallpaper,
    wear_painting,
    wear_picture,
)
from osiris.themes.derive import build
from osiris.themes.intent import Harmony, Mood, ThemeIntent, seeds
from osiris.themes.store import FakeThemeStore


def stored(name: str, label: str, dark: bool = True) -> dict[str, object]:
    return {"name": name, "label": label, "dark": dark}


def test_listing_names_every_theme_and_marks_the_current_one() -> None:
    store = FakeThemeStore(
        themes=[
            stored("nord", "Nord"),
            stored("rose-pine-dawn", "Rose Pine Dawn", False),
        ],
        current="nord",
    )
    assert list_themes(store) == [
        {"name": "nord", "label": "Nord", "dark": True, "current": True},
        {
            "name": "rose-pine-dawn",
            "label": "Rose Pine Dawn",
            "dark": False,
            "current": False,
        },
    ]


def test_a_theme_is_made_by_osiris_rules_from_the_intent_alone() -> None:
    store = FakeThemeStore()
    name = create_theme(
        store,
        label="Harbour",
        seed="#3a6ea5",
        harmony="analogous",
        mood="muted",
        dark=True,
    )
    intent = ThemeIntent(
        seed=Colour("#3a6ea5"), harmony=Harmony.ANALOGOUS, mood=Mood.MUTED, dark=True
    )
    assert name == "harbour"
    assert store.saved == [build("harbour", "Harbour", seeds(intent))]


def test_making_a_theme_never_replaces_one_that_exists() -> None:
    store = FakeThemeStore(themes=[stored("harbour", "Harbour")])
    with pytest.raises(ThemeActionError, match="already a theme called Harbour"):
        create_theme(
            store,
            label="Harbour",
            seed="#3a6ea5",
            harmony="analogous",
            mood="muted",
            dark=True,
        )
    assert store.saved == []


def test_a_label_too_long_for_a_file_name_is_refused() -> None:
    with pytest.raises(ThemeActionError, match="too long"):
        unused_name(FakeThemeStore(), "A very long name " * 20)


def test_a_seed_that_is_not_a_colour_is_refused() -> None:
    with pytest.raises(ThemeActionError, match="not a colour"):
        create_theme(
            FakeThemeStore(),
            label="Harbour",
            seed="sea blue",
            harmony="analogous",
            mood="muted",
            dark=True,
        )


@pytest.mark.parametrize(
    ("harmony", "mood", "offered"),
    [
        ("pretty", "muted", "analogous, complementary"),
        ("analogous", "moody", "muted, balanced, vivid, pastel"),
    ],
)
def test_an_unknown_harmony_or_mood_is_refused_naming_the_choices(
    harmony: str, mood: str, offered: str
) -> None:
    with pytest.raises(ThemeActionError, match=offered):
        create_theme(
            FakeThemeStore(),
            label="Harbour",
            seed="#3a6ea5",
            harmony=harmony,
            mood=mood,
            dark=True,
        )


def test_applying_a_theme_reports_the_one_it_replaced() -> None:
    store = FakeThemeStore(
        themes=[stored("nord", "Nord"), stored("harbour", "Harbour")], current="nord"
    )
    assert apply_theme(store, "harbour") == "nord"
    assert store.applied == ["harbour"]


def test_applying_on_a_machine_that_never_chose_one_replaces_nothing() -> None:
    store = FakeThemeStore(themes=[stored("harbour", "Harbour")])
    assert apply_theme(store, "harbour") is None


def test_applying_an_unknown_theme_is_refused() -> None:
    store = FakeThemeStore(themes=[stored("nord", "Nord")])
    with pytest.raises(ThemeActionError, match="no theme called harbour"):
        apply_theme(store, "harbour")
    assert store.applied == []


def test_deleting_a_theme_removes_it() -> None:
    store = FakeThemeStore(
        themes=[stored("nord", "Nord"), stored("harbour", "Harbour")], current="nord"
    )
    delete_theme(store, "harbour")
    assert store.deleted == ["harbour"]


def test_the_applied_theme_is_never_deleted() -> None:
    store = FakeThemeStore(themes=[stored("harbour", "Harbour")], current="harbour")
    with pytest.raises(ThemeActionError, match="Harbour is applied"):
        delete_theme(store, "harbour")
    assert store.deleted == []


def test_deleting_an_unknown_theme_is_refused() -> None:
    with pytest.raises(ThemeActionError, match="no theme called harbour"):
        delete_theme(FakeThemeStore(), "harbour")


def test_a_new_wallpaper_is_worn_by_a_copy_of_the_theme_in_use() -> None:
    store = FakeThemeStore(
        themes=[
            {"name": "nord", "label": "Nord", "dark": True, "wallpaper_style": "aurora"}
        ],
        current="nord",
    )
    theme, previous = use_wallpaper(store, "rain", "Rain")
    assert (theme, previous) == ("nord-rain", "nord")
    assert store.saved == [
        {
            "name": "nord-rain",
            "label": "Nord Rain",
            "dark": True,
            "wallpaper_style": "rain",
        }
    ]
    assert store.applied == ["nord-rain"]


def test_a_wallpaper_needs_a_theme_in_use_to_wear_it() -> None:
    with pytest.raises(ThemeActionError, match="Apply a theme first"):
        use_wallpaper(FakeThemeStore(), "rain", "Rain")


def test_a_copy_that_would_replace_a_theme_is_refused() -> None:
    store = FakeThemeStore(
        themes=[
            {"name": "nord", "label": "Nord", "dark": True},
            {"name": "nord-rain", "label": "Nord Rain", "dark": True},
        ],
        current="nord",
    )
    with pytest.raises(ThemeActionError, match="already a theme called Nord Rain"):
        use_wallpaper(store, "rain", "Rain")


def test_a_theme_pair_is_a_light_and_a_dark_theme_made_from_one_idea() -> None:
    """#266: two Themes, chosen as one, each naming the other."""
    store = FakeThemeStore()
    names = make_theme_pair(
        store, label="Van", seed="#3f9a4a", harmony="analogous", mood="vivid"
    )
    light, dark = store.saved
    assert names == ("van", "van-night")
    assert (light["dark"], dark["dark"], dark["label"]) == (False, True, "Van Night")
    assert (light["pair"], dark["pair"]) == ("van-night", "van")


def test_the_other_half_of_a_theme_made_alone_completes_its_pair() -> None:
    """#266: Osiris makes the Theme asked for, then offers its other half."""
    store = FakeThemeStore()
    create_theme(
        store,
        label="Harbour",
        seed="#3a6ea5",
        harmony="analogous",
        mood="muted",
        dark=True,
    )
    assert make_other_half(store, "harbour") == "harbour-day"
    halves = {theme["name"]: theme for theme in store.themes()}
    assert halves["harbour"]["pair"] == "harbour-day"
    assert halves["harbour-day"]["pair"] == "harbour"
    assert halves["harbour-day"]["dark"] is False


def test_a_theme_already_in_a_pair_has_no_other_half_to_make() -> None:
    store = FakeThemeStore()
    make_theme_pair(
        store, label="Van", seed="#3f9a4a", harmony="analogous", mood="vivid"
    )
    with pytest.raises(ThemeActionError, match="already has"):
        make_other_half(store, "van")


def test_a_theme_wears_a_picture_osiris_found_or_painted() -> None:
    """A whole look: each half of a pair gets a real wallpaper."""
    store = FakeThemeStore(
        themes=[{**stored("van", "Van", False), "wallpaper": "generated"}]
    )
    kept: list[tuple[str, Path]] = []

    def keep(name: str, picture: Path) -> Path:
        kept.append((name, picture))
        return Path(f"/home/tester/.local/share/osiris/pictures/{name}.jpg")

    previous = wear_picture(store, "van", Path("/tmp/van-day.jpg"), keep)
    assert previous == "generated"
    assert kept == [("van", Path("/tmp/van-day.jpg"))]
    assert (
        find(store, "van")["wallpaper"]
        == "/home/tester/.local/share/osiris/pictures/van.jpg"
    )


def test_a_file_that_is_not_a_picture_is_refused_as_a_wallpaper() -> None:
    store = FakeThemeStore(themes=[stored("van", "Van", False)])
    with pytest.raises(ThemeActionError, match="picture"):
        wear_picture(store, "van", Path("/tmp/van.html"), lambda _n, p: p)


def picture_bytes(colour: tuple[int, int, int]) -> bytes:
    data = io.BytesIO()
    Image.new("RGB", (64, 36), colour).save(data, "PNG")
    return data.getvalue()


def test_a_picture_theme_wears_the_picture_and_takes_its_colours_from_it() -> None:
    store = FakeThemeStore()
    picture = picture_bytes((20, 40, 90))
    kept: list[str] = []

    def keep(name: str, _data: bytes) -> Path:
        kept.append(name)
        return Path(f"/home/tester/Pictures/Osiris/{name}.png")

    name = create_picture_theme(store, label="Night Sea", picture=picture, keep=keep)

    assert name == "night-sea"
    assert kept == ["night-sea"]
    theme = store.saved[0]
    assert theme["label"] == "Night Sea"
    assert theme["wallpaper"] == "/home/tester/Pictures/Osiris/night-sea.png"
    assert theme["dark"] is True
    assert theme["intent"]["harmony"] == "analogous"
    assert store.applied == []


def test_a_picture_in_another_format_is_kept_as_a_png() -> None:
    store = FakeThemeStore()
    data = io.BytesIO()
    Image.new("RGB", (64, 36), (20, 40, 90)).save(data, "WEBP")
    kept: list[bytes] = []

    def keep(name: str, picture: bytes) -> Path:
        kept.append(picture)
        return Path(f"/home/tester/Pictures/Osiris/{name}.png")

    create_picture_theme(store, label="Sea", picture=data.getvalue(), keep=keep)

    assert Image.open(io.BytesIO(kept[0])).format == "PNG"


def test_a_picture_that_cannot_be_saved_warns_of_a_possible_charge() -> None:
    store = FakeThemeStore()

    def keep(_name: str, _data: bytes) -> Path:
        raise OSError("No space left on device")

    with pytest.raises(ThemeActionError, match=r"could not be saved.*ask the person"):
        create_picture_theme(
            store, label="Sea", picture=picture_bytes((20, 40, 90)), keep=keep
        )

    assert store.saved == []


def test_a_picture_that_cannot_be_read_keeps_nothing() -> None:
    store = FakeThemeStore()
    kept: list[str] = []

    def keep(name: str, _data: bytes) -> Path:
        kept.append(name)
        return Path(f"/home/tester/Pictures/Osiris/{name}.png")

    with pytest.raises(ThemeActionError, match=r"could not be read.*ask the person"):
        create_picture_theme(store, label="Broken", picture=b"not a picture", keep=keep)

    assert kept == []
    assert store.saved == []


def test_a_painting_that_cannot_be_read_keeps_nothing_and_may_have_cost() -> None:
    """Review of #272: a paid picture gets the same guards as a picture Theme."""
    store = FakeThemeStore(themes=[stored("van", "Van", False)])
    kept: list[bytes] = []

    def keep(name: str, data: bytes) -> Path:
        kept.append(data)
        return Path(f"/home/tester/Pictures/Osiris/{name}.png")

    with pytest.raises(ThemeActionError, match=r"could not be read.*charged"):
        wear_painting(store, "van", b"not a picture", keep)
    assert kept == []


def test_a_painting_in_another_format_is_kept_as_a_png() -> None:
    store = FakeThemeStore(themes=[stored("van", "Van", False)])
    data = io.BytesIO()
    Image.new("RGB", (8, 8), (10, 120, 110)).save(data, "JPEG")
    kept: list[bytes] = []

    def keep(name: str, picture: bytes) -> Path:
        kept.append(picture)
        return Path(f"/home/tester/Pictures/Osiris/{name}.png")

    wear_painting(store, "van", data.getvalue(), keep)
    assert Image.open(io.BytesIO(kept[0])).format == "PNG"


def test_a_theme_whose_other_half_was_undone_can_be_paired_again() -> None:
    """Review of #271: undoing the other half left the Theme naming it."""
    store = FakeThemeStore()
    create_theme(
        store,
        label="Harbour",
        seed="#3a6ea5",
        harmony="analogous",
        mood="muted",
        dark=True,
    )
    make_other_half(store, "harbour")
    delete_theme(store, "harbour-day")
    assert make_other_half(store, "harbour") == "harbour-day"
