"""Runs the Osiris tool server on stdio, over the real theme engine.

The Engine spawns this when the Harness registers it; what the tools do is in
osiris/apps/tool_server.py and osiris/themes/actions.py, where it is tested.
"""
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for candidate in ("/usr/share/osiris/lib", REPO):
    if os.path.isdir(os.path.join(candidate, "osiris")):
        sys.path.insert(0, candidate)
        break

from skin_store import EngineSkinStore  # noqa: E402
from theme_store import EngineStore, user_wallpapers  # noqa: E402

from osiris.apps.tool_server import server  # noqa: E402
from osiris.harness.log import LOG_FILE, HarnessLog  # noqa: E402
from osiris.harness.media.connected import ConnectedFal  # noqa: E402
from osiris.harness.media.fal import FalImages  # noqa: E402
from osiris.harness.media.pictures import Pictures  # noqa: E402
from osiris.harness.proposals import SKILLS  # noqa: E402
from osiris.harness.trust import auto_mode_on  # noqa: E402
from osiris.platform import (  # noqa: E402
    RealFileSystem,
    SubprocessRunner,
    SystemIdentity,
    UrllibClient,
)
from osiris.programs.programs import Programs  # noqa: E402

if __name__ == "__main__":
    files, home = RealFileSystem(), SystemIdentity().home
    runner = SubprocessRunner(sink=lambda _line: None)
    programs = Programs(files, runner, home)
    wallpapers = user_wallpapers(files, runner, home)
    # A picture takes seconds, and longer when FAL is busy.
    http = UrllibClient(timeout=120)
    fal = ConnectedFal(files, home, lambda key: FalImages(http, key), date.today)
    server(EngineStore(), programs, HarnessLog(files, home / LOG_FILE), wallpapers,
           skins=EngineSkinStore(),
           pictures=Pictures(fal, files, home),
           auto_mode=auto_mode_on(files, home),
           skill_taken=lambda name: files.exists(home / SKILLS / name)).run()
