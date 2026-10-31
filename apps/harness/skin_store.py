"""The real SkinStore: the theme engine's Skins, for the tool server that acts
and the drawer that undoes."""
import os
import sys
from collections.abc import Sequence
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for candidate in (os.path.join(REPO, "shell", "themes"), "/usr/share/osiris/themes"):
    if os.path.isdir(candidate):
        sys.path.insert(0, candidate)
        break

import engine  # noqa: E402


class EngineSkinStore:
    def skins(self) -> list[dict[str, object]]:
        mine, worn = engine.own_skins(), engine.chosen_skin()
        return [{"name": name, "label": label, "mine": name in mine,
                 "worn": name == worn}
                for name, label, _credit in engine.skin_choices()]

    def worn(self) -> str:
        return engine.chosen_skin()

    def create(self, label: str, base: str) -> Path:
        return Path(engine.skin_folder(engine.create_skin(label, base)))

    def check(self, name: str) -> list[str]:
        return engine.check_skin(name)

    def wear(self, name: str) -> None:
        engine.set_skin(name)

    def delete(self, name: str) -> None:
        engine.delete_skin(name)

    def import_gtk_theme(self, path: Path) -> str:
        return engine.import_gtk_theme(str(path))

    def install_icon_sets(self, path: Path) -> list[str]:
        return engine.import_icon_sets(str(path))

    def remove_icon_sets(self, names: Sequence[str]) -> None:
        engine.remove_icon_sets(list(names))

    def install_fonts(self, paths: Sequence[Path]) -> list[str]:
        return engine.import_fonts([str(path) for path in paths])

    def remove_fonts(self, names: Sequence[str]) -> None:
        engine.remove_fonts(list(names))
