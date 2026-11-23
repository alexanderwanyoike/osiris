"""FAL, the first Media provider."""

from __future__ import annotations

import base64
from collections.abc import Callable
from urllib.parse import urlsplit

from osiris.harness.media.error import MediaError
from osiris.platform import HttpClient, HttpError

RUN = "https://fal.run"
DEFAULT_MODEL = "fal-ai/flux/schnell"
_NO_PICTURE = "FAL did not return a picture."
_LARGEST_PICTURE = 64 * 1024 * 1024

_REASONS = {
    0: (
        "Osiris could not reach FAL; check the connection. The picture may still "
        "have been charged, so ask the person before trying again."
    ),
    401: "FAL did not accept the key; check it in Settings.",
    403: "FAL refused the request; the account may be out of credit.",
}


class FalImages:
    def __init__(
        self,
        http: HttpClient,
        key: str,
        inputs: Callable[[str], frozenset[str]],
    ) -> None:
        self._http = http
        self._key = key
        self._inputs = inputs

    def make(self, description: str, model: str | None = None) -> bytes:
        chosen = model or DEFAULT_MODEL
        body = _request(description, self._inputs(chosen))
        try:
            answer = self._http.request(
                "POST",
                f"{RUN}/{chosen}",
                body=body,
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
        return _picture(answer, self._http)


def _request(description: str, accepted: frozenset[str]) -> dict[str, object]:
    wanted: dict[str, object] = {
        "prompt": description,
        "image_size": {"width": 1920, "height": 1080},
        "num_images": 1,
        "output_format": "png",
        "sync_mode": True,
    }
    if "image_size" not in accepted:
        wanted["aspect_ratio"] = "16:9"
    return {name: value for name, value in wanted.items() if name in accepted}


def _picture(answer: object, http: HttpClient) -> bytes:
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
    if not isinstance(url, str):
        raise missing
    if _in_fal_storage(url):
        return _fetched(url, http)
    if not url.startswith("data:image/"):
        raise missing
    try:
        return base64.b64decode(url.partition(",")[2], validate=True)
    except ValueError:
        raise missing from None


def _in_fal_storage(url: str) -> bool:
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.scheme != "https":
        return False
    if host == "fal.media" or host.endswith(".fal.media"):
        return True
    return host == "storage.googleapis.com" and parts.path.startswith("/falserverless/")


def _fetched(url: str, http: HttpClient) -> bytes:
    try:
        return http.download(url, limit=_LARGEST_PICTURE)
    except HttpError:
        raise MediaError(
            "FAL made the picture, but Osiris could not download it."
        ) from None
