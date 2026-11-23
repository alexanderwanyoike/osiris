"""FAL, the first media Provider."""

from __future__ import annotations

import base64
from typing import cast

from osiris.platform import HttpClient

ENDPOINT = "https://fal.run/fal-ai/flux/schnell"


class FalImages:
    def __init__(self, http: HttpClient, key: str) -> None:
        self._http = http
        self._key = key

    def make(self, description: str) -> bytes:
        answer = self._http.request(
            "POST",
            ENDPOINT,
            body={
                "prompt": description,
                "image_size": {"width": 1920, "height": 1080},
                "num_images": 1,
                "output_format": "png",
                "sync_mode": True,
            },
            headers={"Authorization": f"Key {self._key}"},
        )
        images = cast("dict[str, list[dict[str, str]]]", answer)["images"]
        return base64.b64decode(images[0]["url"].split(",", 1)[1])
