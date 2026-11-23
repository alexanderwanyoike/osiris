"""FAL, the first media Provider."""

from __future__ import annotations

import base64
from typing import cast

from osiris.harness.media.error import MediaError
from osiris.platform import HttpClient, HttpError

ENDPOINT = "https://fal.run/fal-ai/flux/schnell"

_REASONS = {
    0: "Osiris could not reach FAL; check the connection.",
    401: "FAL did not accept the key; check it in Settings.",
    403: "FAL refused the request; the account may be out of credit.",
}


class FalImages:
    def __init__(self, http: HttpClient, key: str) -> None:
        self._http = http
        self._key = key

    def make(self, description: str) -> bytes:
        try:
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
        except HttpError as error:
            # Not chained: the error's body could echo the request and its key.
            reason = _REASONS.get(
                error.status, f"FAL could not make the picture ({error.status})."
            )
            raise MediaError(reason) from None
        images = cast("dict[str, list[dict[str, str]]]", answer)["images"]
        return base64.b64decode(images[0]["url"].split(",", 1)[1])
