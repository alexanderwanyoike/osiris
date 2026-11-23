"""FAL as the tool server reaches it, with the key read at each request so a
key saved or removed in Settings counts without restarting anything."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path

from osiris.harness.media.error import MediaError
from osiris.harness.media.fal import FalImages
from osiris.harness.media.key import fal_key
from osiris.harness.media.limit import DailyLimit
from osiris.harness.media.limit_setting import daily_limit
from osiris.platform import FileSystem, HttpClient

USAGE_FILE = ".config/osiris/media/images"


class ConnectedFal:
    def __init__(
        self,
        files: FileSystem,
        home: Path,
        http: HttpClient,
        today: Callable[[], date],
    ) -> None:
        self._files = files
        self._home = home
        self._http = http
        self._today = today

    def make(self, description: str) -> bytes:
        key = fal_key(self._files, self._home)
        if key is None:
            raise MediaError(
                "FAL is not connected. The person can add a key in Settings, "
                "in the Media section of Models."
            )
        fal = FalImages(self._http, key)
        images = daily_limit(self._files, self._home)
        if images is None:
            return fal.make(description)
        limited = DailyLimit(
            fal, self._files, self._home / USAGE_FILE, self._today, images=images
        )
        return limited.make(description)
