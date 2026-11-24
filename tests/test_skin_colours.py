"""Fixed colours in a person's Skin: colours written in rather than taken from
the Theme, which stay the same whatever Theme is worn."""

from __future__ import annotations

from pathlib import Path

from osiris.skins.colours import fixed_colours


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_a_colour_written_into_a_style_sheet_is_named(tmp_path: Path) -> None:
    sheet = "a { color: $gap-accent; }\nb { background-color: #2f7d4a; }\n"
    write(tmp_path / "mine" / "gtk-3.0" / "gtk-dark.scss", sheet)
    write(tmp_path / "graphite" / "gtk-3.0" / "gtk-dark.scss", "")
    found = fixed_colours(tmp_path / "mine", tmp_path / "graphite")
    assert found == ["gtk-3.0/gtk-dark.scss: #2f7d4a"]
