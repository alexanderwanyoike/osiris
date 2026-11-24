"""FAL as the tool server reaches it, with the key read at each request so a
key saved or removed in Settings counts without restarting anything."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path

from osiris.harness.media.error import MediaError
from osiris.harness.media.key import fal_key
from osiris.harness.media.limit import DailyLimit
from osiris.harness.media.limit_setting import daily_limit
from osiris.harness.media.maker import ImageMaker
from osiris.harness.media.model_setting import saved_model
from osiris.platform import FileSystem

USAGE_FILE = ".config/osiris/media/images"


class ConnectedFal:
    def __init__(
        self,
        files: FileSystem,
        home: Path,
        maker_for: Callable[[str, Callable[[], None]], ImageMaker],
        today: Callable[[], date],
    ) -> None:
        self._files = files
        self._home = home
        self._maker_for = maker_for
        self._today = today

    def make(self, description: str, model: str | None = None) -> bytes:
        key = fal_key(self._files, self._home)
        if key is None:
            raise MediaError(
                "FAL is not connected. The person can add a key in Settings, "
                "in the Media section of Models."
            )
        chosen = model or saved_model(self._files, self._home)
        return self._maker_for(key, self._counter()).make(description, chosen)

    def _counter(self) -> Callable[[], None]:
        images = daily_limit(self._files, self._home)
        if images is None:
            return lambda: None
        usage = self._home / USAGE_FILE
        return DailyLimit(self._files, usage, self._today, images=images).take
