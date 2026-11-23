"""FAL's catalog of image models, which changes without Osiris changing."""

from __future__ import annotations

from urllib.parse import urlencode

from osiris.harness.media.error import MediaError
from osiris.harness.media.image_model import ImageModel
from osiris.platform import HttpClient, HttpError

CATALOG = "https://api.fal.ai/v1/models"
_UNREADABLE = "Osiris could not read FAL's list of image models; check the connection."


class FalCatalog:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def search(self, words: str) -> list[ImageModel]:
        query = urlencode(
            {"category": "text-to-image", "status": "active", "limit": 12, "q": words}
        )
        return [_model(entry) for entry in self._entries(f"{CATALOG}?{query}")]

    def _entries(self, url: str) -> list[dict[str, object]]:
        try:
            answer = self._http.request("GET", url)
        except HttpError, ValueError:
            raise MediaError(_UNREADABLE) from None
        models = answer.get("models") if isinstance(answer, dict) else None
        if not isinstance(models, list):
            raise MediaError(_UNREADABLE)
        return [entry for entry in models if isinstance(entry, dict)]


def _model(entry: dict[str, object]) -> ImageModel:
    about = entry.get("metadata")
    details = about if isinstance(about, dict) else {}
    endpoint = str(entry.get("endpoint_id", ""))
    return ImageModel(
        endpoint,
        str(details.get("display_name") or endpoint),
        str(details.get("description") or ""),
    )
