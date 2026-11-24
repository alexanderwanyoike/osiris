"""FAL's catalog of image models, which changes without Osiris changing."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

from osiris.harness.media.error import MediaError
from osiris.harness.media.image_model import ImageModel
from osiris.harness.media.model_spec import ModelSpec
from osiris.harness.media.wide_size import wide_size
from osiris.platform import HttpClient, HttpError

CATALOG = "https://api.fal.ai/v1/models"
_UNREADABLE = "Osiris could not read FAL's list of image models; check the connection."


class FalCatalog:
    def __init__(self, http: HttpClient, key: Callable[[], str | None]) -> None:
        self._http = http
        self._key = key

    def search(self, words: str) -> list[ImageModel]:
        wanted: dict[str, str | int] = {
            "category": "text-to-image",
            "status": "active",
            "limit": 12,
        }
        if words.strip():
            wanted["q"] = words
        query = urlencode(wanted)
        entries = self._entries(f"{CATALOG}?{query}")
        return [_model(entry) for entry in entries if _draws_pictures(entry)]

    def spec(self, model: str) -> ModelSpec:
        query = urlencode({"endpoint_id": model, "expand": "openapi-3.0"})
        entries = self._entries(f"{CATALOG}?{query}")
        if not entries or not _offered(entries[0]):
            raise MediaError(
                f"{model} is not an image model FAL offers; "
                "find one with find_image_models."
            )
        return _spec(entries[0], model)

    def _entries(self, url: str) -> list[dict[str, object]]:
        try:
            key = self._key()
            headers = {"Authorization": f"Key {key}"} if key else {}
            answer = self._http.request("GET", url, headers=headers)
        except HttpError as error:
            if error.status == 404:
                return []
            if error.status == 429:
                raise MediaError(
                    "FAL is limiting requests for its model list; try again in a "
                    "minute."
                ) from None
            raise MediaError(_UNREADABLE) from None
        except ValueError:
            raise MediaError(_UNREADABLE) from None
        models = answer.get("models") if isinstance(answer, dict) else None
        if not isinstance(models, list):
            raise MediaError(_UNREADABLE)
        return [entry for entry in models if isinstance(entry, dict)]


def _offered(entry: dict[str, object]) -> bool:
    details = entry.get("metadata")
    return (
        _draws_pictures(entry)
        and isinstance(details, dict)
        and details.get("category") == "text-to-image"
        and details.get("status") == "active"
    )


def _draws_pictures(entry: dict[str, object]) -> bool:
    # FAL files vector models as text-to-image, but an SVG cannot be a Wallpaper.
    return "vector" not in str(entry.get("endpoint_id", ""))


def _spec(entry: dict[str, object], model: str) -> ModelSpec:
    spec: Any = entry.get("openapi")
    try:
        path = _runs_at(spec["paths"], model)
        body = spec["paths"][f"/{path}"]["post"]["requestBody"]
        schema = body["content"]["application/json"]["schema"]["$ref"]
        name = schema.rsplit("/", 1)[1]
        described = spec["components"]["schemas"][name]
        if set(described.get("required", ())) - {"prompt"}:
            raise MediaError(f"{model} needs more than a description; choose another.")
        fields = described["properties"]
        return ModelSpec(
            path, frozenset(fields), wide_size(fields.get("image_size", {}))
        )
    except KeyError, TypeError, AttributeError, IndexError:
        raise MediaError(_UNREADABLE) from None


def _runs_at(paths: Any, model: str) -> str:
    if f"/{model}" in paths:
        return model
    posts = [
        path
        for path, ways in paths.items()
        if "post" in ways and "/requests/" not in path
    ]
    if len(posts) != 1:
        raise KeyError(model)
    return str(posts[0]).removeprefix("/")


def _model(entry: dict[str, object]) -> ImageModel:
    about = entry.get("metadata")
    details = about if isinstance(about, dict) else {}
    endpoint = str(entry.get("endpoint_id", ""))
    return ImageModel(
        endpoint,
        str(details.get("display_name") or endpoint),
        str(details.get("description") or ""),
    )
