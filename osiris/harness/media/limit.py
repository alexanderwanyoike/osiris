"""A hard daily limit on paid pictures.

The usage file is plain text with one line per request, holding its date.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path

from osiris.harness.media.error import MediaError
from osiris.harness.media.maker import ImageMaker
from osiris.platform import FileSystem

DAILY_IMAGES = 20


class DailyLimit:
    def __init__(
        self,
        maker: ImageMaker,
        files: FileSystem,
        usage: Path,
        today: Callable[[], date],
        *,
        images: int = DAILY_IMAGES,
    ) -> None:
        self._maker = maker
        self._files = files
        self._usage = usage
        self._today = today
        self._images = images

    def make(self, description: str) -> bytes:
        day = self._today().isoformat()
        if self._used(day) >= self._images:
            raise self._reached()
        self._files.append(self._usage, f"{day}\n")
        # Counted again after writing: two servers racing for the last picture
        # may both stop, but can never both spend it.
        if self._used(day) > self._images:
            raise self._reached()
        return self._maker.make(description)

    def _reached(self) -> MediaError:
        return MediaError(
            f"Osiris has reached today's limit of {self._images} pictures."
        )

    def _used(self, day: str) -> int:
        if not self._files.exists(self._usage):
            return 0
        return self._files.read(self._usage).splitlines().count(day)
