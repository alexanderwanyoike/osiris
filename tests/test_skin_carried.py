"""What a skinpack carries besides style sheets: icon sets, cursors and fonts,
installed once and shared by every Skin that carries them."""

from __future__ import annotations

import json
from pathlib import Path

from osiris.skins.carried import install
from osiris.skins.pack import read


def make_pack(root: Path) -> Path:
    fields = {"author": "a", "version": "1", "licence": "GPL-3.0", "source": "s"}
    files = {
        "skin.json": json.dumps({"label": "Colloid", **fields}),
        "icons/Colloid-Dark/index.theme": "[Icon Theme]\nName=Colloid-Dark\n",
        "icons/Colloid-cursors/index.theme": "[Icon Theme]\nName=Colloid-cursors\n",
        "fonts/Inter.ttf": "font",
    }
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)
    return root


def test_icon_sets_and_cursors_are_installed_by_name(tmp_path: Path) -> None:
    install(
        read(make_pack(tmp_path / "colloid")), tmp_path / "icons", tmp_path / "fonts"
    )
    assert (tmp_path / "icons" / "Colloid-Dark" / "index.theme").is_file()
    assert (tmp_path / "icons" / "Colloid-cursors" / "index.theme").is_file()


def test_a_set_already_installed_is_kept_as_the_one_copy(tmp_path: Path) -> None:
    existing = tmp_path / "icons" / "Colloid-Dark"
    existing.mkdir(parents=True)
    (existing / "index.theme").write_text("already here")
    install(
        read(make_pack(tmp_path / "colloid")), tmp_path / "icons", tmp_path / "fonts"
    )
    assert (existing / "index.theme").read_text() == "already here"


def a_new_version(root: Path) -> None:
    label = json.loads((root / "skin.json").read_text())
    (root / "skin.json").write_text(json.dumps({**label, "version": "2"}))


def test_a_set_from_an_older_version_of_the_skin_is_replaced(tmp_path: Path) -> None:
    root = make_pack(tmp_path / "colloid")
    install(read(root), tmp_path / "icons", tmp_path / "fonts")
    a_new_version(root)
    (root / "icons" / "Colloid-Dark" / "index.theme").write_text("version 2")
    install(read(root), tmp_path / "icons", tmp_path / "fonts")
    installed = tmp_path / "icons" / "Colloid-Dark" / "index.theme"
    assert installed.read_text() == "version 2"


def test_a_set_the_system_has_is_not_shadowed(tmp_path: Path) -> None:
    """A copy in the person's icons would take over the system's set in every
    program, worn or not."""
    (tmp_path / "system" / "Colloid-Dark").mkdir(parents=True)
    install(
        read(make_pack(tmp_path / "colloid")),
        tmp_path / "icons",
        tmp_path / "fonts",
        system_icons=[tmp_path / "system"],
    )
    assert not (tmp_path / "icons" / "Colloid-Dark").exists()
    assert (tmp_path / "icons" / "Colloid-cursors").is_dir()


def test_fonts_are_installed_once_and_say_when_they_are_new(tmp_path: Path) -> None:
    pack = read(make_pack(tmp_path / "colloid"))
    assert install(pack, tmp_path / "icons", tmp_path / "fonts") is True
    assert (tmp_path / "fonts" / "colloid" / "Inter.ttf").is_file()
    assert install(pack, tmp_path / "icons", tmp_path / "fonts") is False


def test_a_pack_carrying_nothing_installs_nothing(tmp_path: Path) -> None:
    root = tmp_path / "plain"
    root.mkdir()
    fields = {"author": "a", "version": "1", "licence": "GPL-3.0", "source": "s"}
    (root / "skin.json").write_text(json.dumps({"label": "Plain", **fields}))
    assert install(read(root), tmp_path / "icons", tmp_path / "fonts") is False
    assert not (tmp_path / "icons").exists()
