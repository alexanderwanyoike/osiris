"""FAL's catalog of image models, as Osiris searches it."""

from __future__ import annotations

import pytest

from osiris.harness.media.catalog import CATALOG, FalCatalog
from osiris.harness.media.error import MediaError
from osiris.harness.media.image_model import ImageModel
from osiris.platform import FakeHttpClient, HttpError

SEARCH = f"{CATALOG}?category=text-to-image&status=active&limit=12&q=flat+anime"
DETAILS = f"{CATALOG}?endpoint_id=fal-ai%2Fone&expand=openapi-3.0"


def catalog(http: FakeHttpClient) -> FalCatalog:
    return FalCatalog(http)


def listed(endpoint: str, name: str, about: str) -> dict[str, object]:
    return {
        "endpoint_id": endpoint,
        "metadata": {"display_name": name, "description": about},
    }


def test_a_search_finds_active_text_to_image_models() -> None:
    reply = {"models": [listed("fal-ai/one", "One", "Draws flat anime")]}
    http = FakeHttpClient(replies={("GET", SEARCH): reply})

    assert catalog(http).search("flat anime") == [
        ImageModel("fal-ai/one", "One", "Draws flat anime")
    ]


def test_an_empty_search_lists_what_fal_offers() -> None:
    every = f"{CATALOG}?category=text-to-image&status=active&limit=12"
    reply = {"models": [listed("fal-ai/one", "One", "Draws")]}
    http = FakeHttpClient(replies={("GET", every): reply})

    assert [model.id for model in catalog(http).search("")] == ["fal-ai/one"]


def described(
    category: str = "text-to-image",
    status: str = "active",
    required: tuple[str, ...] = ("prompt",),
) -> dict[str, object]:
    return {
        "models": [
            {
                "endpoint_id": "fal-ai/one",
                "metadata": {"category": category, "status": status},
                "openapi": {
                    "paths": {
                        "/fal-ai/one": {
                            "post": {
                                "requestBody": {
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "$ref": "#/components/schemas/OneInput"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "components": {
                        "schemas": {
                            "OneInput": {
                                "required": list(required),
                                "properties": {"prompt": {}, "image_size": {}},
                            }
                        }
                    },
                },
            }
        ]
    }


def test_a_models_inputs_come_from_its_published_schema() -> None:
    http = FakeHttpClient(replies={("GET", DETAILS): described()})

    assert catalog(http).inputs("fal-ai/one") == {"prompt", "image_size"}


@pytest.mark.parametrize(
    "answer",
    [
        described(category="text-to-video"),
        described(status="deprecated"),
        {"models": []},
        HttpError(404, "Endpoint(s) not found"),
    ],
)
def test_anything_but_an_active_image_model_is_refused(answer: object) -> None:
    http = FakeHttpClient(replies={("GET", DETAILS): answer})

    with pytest.raises(MediaError, match="not an image model FAL offers"):
        catalog(http).inputs("fal-ai/one")


def test_a_catalog_that_cannot_be_read_is_given_a_plain_reason() -> None:
    http = FakeHttpClient(replies={("GET", SEARCH): HttpError(0, "no route")})

    with pytest.raises(MediaError, match="FAL's list of image models"):
        catalog(http).search("flat anime")


def test_vector_models_are_not_offered_because_they_cannot_be_a_wallpaper() -> None:
    vector = "fal-ai/one/text-to-vector"
    details = f"{CATALOG}?endpoint_id=fal-ai%2Fone%2Ftext-to-vector&expand=openapi-3.0"
    entry = {
        "endpoint_id": vector,
        "metadata": {"category": "text-to-image", "status": "active"},
    }
    reply = {"models": [listed("fal-ai/one", "One", "Draws"), listed(vector, "V", "")]}
    http = FakeHttpClient(
        replies={("GET", SEARCH): reply, ("GET", details): {"models": [entry]}}
    )

    assert [model.id for model in catalog(http).search("flat anime")] == ["fal-ai/one"]
    with pytest.raises(MediaError, match="not an image model"):
        catalog(http).inputs(vector)


def test_a_model_that_needs_more_than_a_description_is_refused() -> None:
    answer = described(required=("prompt", "image_url"))
    http = FakeHttpClient(replies={("GET", DETAILS): answer})

    with pytest.raises(MediaError, match="needs more than a description"):
        catalog(http).inputs("fal-ai/one")
