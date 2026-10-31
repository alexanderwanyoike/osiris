"""Runs the Osiris tool server on stdio, over the real theme engine.

The Engine spawns this when the Harness registers it; what the tools do is in
osiris/apps/tool_server.py and osiris/themes/actions.py, where it is tested.
"""
import os
import sys

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
from osiris.harness.trust import allows_everything  # noqa: E402
from osiris.platform import RealFileSystem, SubprocessRunner, SystemIdentity  # noqa: E402
from osiris.programs.programs import Programs  # noqa: E402

if __name__ == "__main__":
    files, home = RealFileSystem(), SystemIdentity().home
    runner = SubprocessRunner(sink=lambda _line: None)
    programs = Programs(files, runner, home)
    wallpapers = user_wallpapers(files, runner, home)
    server(EngineStore(), programs, HarnessLog(files, home / LOG_FILE), wallpapers,
           skins=EngineSkinStore(),
           allow_everything=allows_everything(files, home)).run()
