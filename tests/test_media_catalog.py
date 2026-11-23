"""FAL's catalog of image models, as Osiris searches it."""

from __future__ import annotations

import pytest

from osiris.harness.media.catalog import CATALOG, FalCatalog
from osiris.harness.media.error import MediaError
from osiris.harness.media.image_model import ImageModel
from osiris.platform import FakeHttpClient, HttpError

SEARCH = f"{CATALOG}?category=text-to-image&status=active&limit=12&q=flat+anime"


def listed(endpoint: str, name: str, about: str) -> dict[str, object]:
    return {
        "endpoint_id": endpoint,
        "metadata": {"display_name": name, "description": about},
    }


def test_a_search_finds_active_text_to_image_models() -> None:
    reply = {"models": [listed("fal-ai/one", "One", "Draws flat anime")]}
    http = FakeHttpClient(replies={("GET", SEARCH): reply})

    assert FalCatalog(http).search("flat anime") == [
        ImageModel("fal-ai/one", "One", "Draws flat anime")
    ]


def test_a_catalog_that_cannot_be_read_is_given_a_plain_reason() -> None:
    http = FakeHttpClient(replies={("GET", SEARCH): HttpError(0, "no route")})

    with pytest.raises(MediaError, match="FAL's list of image models"):
        FalCatalog(http).search("flat anime")
