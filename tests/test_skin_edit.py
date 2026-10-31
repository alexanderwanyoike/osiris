"""Editing a person's Skin: its name, the style it is built on, and the icons,
cursor and font it wears. Each save is a commit, so it can be undone."""

from __future__ import annotations

import json
from pathlib import Path

from osiris.model.author import as_osiris
from osiris.platform.process import FakeRunner
from osiris.skins.check import problems
from osiris.skins.edit import Edit, save
from osiris.skins.pack import read
from osiris.skins.share import duplicate

FIELDS = {"version": "1", "licence": "GPL-3.0", "source": "s"}


def make_pack(root: Path, label: str, author: str, palette: str) -> Path:
    (root / "sass").mkdir(parents=True)
    (root / "skin.json").write_text(
        json.dumps({"label": label, "author": author, **FIELDS})
    )
    (root / "sass" / "_palette.scss").write_text(palette)
    return root


def mine(tmp_path: Path) -> Path:
    shipped = read(
        make_pack(tmp_path / "shipped" / "colloid", "Colloid", "Vince", "colloid")
    )
    return duplicate(shipped, tmp_path / "mine", FakeRunner(), label="Sharp").root


def keep(label: str = "Sharp") -> Edit:
    return Edit(label=label, style=None, icons=None, cursor=None, font=None)


def test_renaming_keeps_the_skin_where_it_is(tmp_path: Path) -> None:
    root = mine(tmp_path)
    renamed = save(read(root), keep("Sharp Night"), FakeRunner())
    assert (renamed.name, renamed.label) == ("sharp", "Sharp Night")


def test_icons_cursor_and_font_are_worn_with_the_skin(tmp_path: Path) -> None:
    root = mine(tmp_path)
    edit = Edit("Sharp", None, icons="Papirus", cursor="Bibata", font="Inter 10")
    edited = save(read(root), edit, FakeRunner())
    assert edited.look("dark").icons == "Papirus"
    assert (edited.look("light").cursor, edited.look("light").font) == (
        "Bibata",
        "Inter 10",
    )


def test_leaving_a_choice_empty_keeps_the_themes(tmp_path: Path) -> None:
    root = mine(tmp_path)
    save(read(root), Edit("Sharp", None, "Papirus", None, None), FakeRunner())
    edited = save(read(root), keep(), FakeRunner())
    assert edited.look("dark").icons is None
    assert "look" not in json.loads((root / "skin.json").read_text())


def test_a_new_style_brings_its_sheets_and_credits_and_keeps_the_rest(
    tmp_path: Path,
) -> None:
    root = mine(tmp_path)
    graphite = read(
        make_pack(tmp_path / "shipped" / "graphite", "Graphite", "Vince L", "graphite")
    )
    edit = Edit("Sharp", graphite, icons="Papirus", cursor=None, font=None)
    edited = save(read(root), edit, FakeRunner())
    assert (root / "sass" / "_palette.scss").read_text() == "graphite"
    assert (edited.label, edited.author, edited.style) == (
        "Sharp",
        "Vince L",
        "graphite",
    )
    assert edited.look("dark").icons == "Papirus"
    assert "--skin sharp" in (root / "AGENTS.md").read_text()


def test_a_save_is_committed_as_osiris(tmp_path: Path) -> None:
    root, runner = mine(tmp_path), FakeRunner()
    save(read(root), keep("Sharp Night"), runner)
    assert runner.ran("git", "-C", str(root), "add", "-A")
    assert any(
        call.argv[: 3 + len(as_osiris())] == ("git", "-C", str(root), *as_osiris())
        and "commit" in call.argv
        for call in runner.calls
    )


def test_a_copy_remembers_the_style_it_came_from(tmp_path: Path) -> None:
    assert read(mine(tmp_path)).style == "colloid"


def test_a_skin_given_itself_as_its_style_keeps_everything(tmp_path: Path) -> None:
    """Review of #134: a Skin opened from a shared copy of a shipped one could
    resolve to itself as its style and was emptied."""
    root = mine(tmp_path)
    saved = save(read(root), Edit("Sharp", read(root), None, None, None), FakeRunner())
    assert (root / "sass" / "_palette.scss").read_text() == "colloid"
    assert saved.label == "Sharp"


def test_a_skin_without_history_gets_one_before_saving(tmp_path: Path) -> None:
    root = make_pack(tmp_path / "mine" / "opened", "Opened", "Someone", "opened")
    runner = FakeRunner()
    save(read(root), keep("Opened"), runner)
    assert runner.ran("git", "-C", str(root), "init", "-q")


def test_a_skin_with_history_is_not_initialised_again(tmp_path: Path) -> None:
    root = mine(tmp_path)
    (root / ".git").mkdir(exist_ok=True)
    runner = FakeRunner()
    save(read(root), keep(), runner)
    assert not runner.ran("git", "-C", str(root), "init", "-q")


def test_taking_a_style_copes_with_a_linked_folder_in_the_skin(tmp_path: Path) -> None:
    root = mine(tmp_path)
    (tmp_path / "elsewhere").mkdir()
    (root / "linked").symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    graphite = read(
        make_pack(tmp_path / "shipped" / "graphite", "Graphite", "V", "graphite")
    )
    save(read(root), Edit("Sharp", graphite, None, None, None), FakeRunner())
    assert (root / "sass" / "_palette.scss").read_text() == "graphite"
    assert not (root / "linked").exists()
    assert (tmp_path / "elsewhere").is_dir()


def test_icons_set_per_variant_survive_a_save_that_did_not_change_them(
    tmp_path: Path,
) -> None:
    root = mine(tmp_path)
    label = json.loads((root / "skin.json").read_text())
    label["look"] = {"icons": {"light": "Papirus-Light", "dark": "Papirus-Dark"}}
    (root / "skin.json").write_text(json.dumps(label))
    saved = save(
        read(root), Edit("Sharp", None, "Papirus-Dark", None, None), FakeRunner()
    )
    assert saved.look("light").icons == "Papirus-Light"
    assert saved.look("dark").icons == "Papirus-Dark"


def test_taking_a_persons_skin_as_style_records_that_skin(tmp_path: Path) -> None:
    """Review of #137: the Skin taken was recorded as the style it was itself
    started from, so the editor showed a different style than was chosen."""
    root = mine(tmp_path)
    shipped = read(tmp_path / "shipped" / "colloid")
    other = duplicate(shipped, tmp_path / "mine", FakeRunner(), label="Soft")
    saved = save(read(root), Edit("Sharp", other, None, None, None), FakeRunner())
    assert saved.style == "soft"


def test_taking_a_style_copies_only_a_skins_layout_and_data(tmp_path: Path) -> None:
    """Review of #137: a person's Skin taken as a style brought everything in
    it, programs and stray folders included."""
    root = mine(tmp_path)
    other = make_pack(tmp_path / "mine" / "loud", "Loud", "Me", "loud")
    (other / "follow.py").write_text("print()")
    (other / "notes").mkdir()
    (other / "notes" / "plan.md").write_text("plan")
    (other / "sass" / "build.sh").write_text("make")
    (other / "sass" / ".draft.scss").write_text("draft")
    (other / "sass" / "_palette.scss").chmod(0o755)
    save(read(root), Edit("Sharp", read(other), None, None, None), FakeRunner())
    assert sorted(p.name for p in root.iterdir()) == ["AGENTS.md", "sass", "skin.json"]
    assert [p.name for p in (root / "sass").iterdir()] == ["_palette.scss"]
    assert problems(root) == []


def test_a_styles_credits_come_with_it(tmp_path: Path) -> None:
    """Shipped Skins credit their authors in LICENSE and SOURCES.md beside the
    layout; the licence travels with the sheets it covers."""
    root = mine(tmp_path)
    graphite = make_pack(tmp_path / "shipped" / "graphite", "Graphite", "V", "g")
    (graphite / "LICENSE").write_text("GPL")
    (graphite / "SOURCES.md").write_text("from upstream")
    save(read(root), Edit("Sharp", read(graphite), None, None, None), FakeRunner())
    assert (root / "LICENSE").read_text() == "GPL"
    assert (root / "SOURCES.md").read_text() == "from upstream"
