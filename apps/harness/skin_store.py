"""The real SkinStore: the theme engine's Skins, for the tool server."""
import os
import sys

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

    def check(self, name: str) -> list[str]:
        return engine.check_skin(name)

    def wear(self, name: str) -> None:
        engine.set_skin(name)
