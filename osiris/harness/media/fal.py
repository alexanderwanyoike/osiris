"""FAL, the first Media provider."""

from __future__ import annotations

import base64

from osiris.harness.media.error import MediaError
from osiris.platform import HttpClient, HttpError

ENDPOINT = "https://fal.run/fal-ai/flux/schnell"
_NO_PICTURE = "FAL did not return a picture."

_REASONS = {
    0: (
        "Osiris could not reach FAL; check the connection. The picture may still "
        "have been charged, so ask the person before trying again."
    ),
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
        except UnicodeEncodeError:
            raise MediaError(_REASONS[401]) from None
        except ValueError:
            raise MediaError(_NO_PICTURE) from None
        return _picture(answer)


def _picture(answer: object) -> bytes:
    missing = MediaError(_NO_PICTURE)
    if not isinstance(answer, dict):
        raise missing
    if any(answer.get("has_nsfw_concepts") or ()):
        raise MediaError(
            "FAL's safety filter blocked this picture; describe it differently."
        )
    images = answer.get("images")
    first = images[0] if isinstance(images, list) and images else None
    url = first.get("url") if isinstance(first, dict) else None
    if not isinstance(url, str) or not url.startswith("data:image/"):
        raise missing
    try:
        return base64.b64decode(url.partition(",")[2], validate=True)
    except ValueError:
        raise missing from None
